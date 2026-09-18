"""D4 batch close-out evaluation (spec-d4-batch-v0.2.md §4).

Runs, in order, for one completed batch:
  1. L-d canary scan of the product workspace (phase=always corpus only,
     whitelist = allowlist originals + README original; strong hit -> fail,
     weak hit -> review flag; claims scope = literal corpus zero-hit).
  2. tests integrity: workspace tests vs MANIFEST.json (set + per-file
     SHA-256; __pycache__ excluded per MANIFEST convention) and vs the
     pre-session snapshot runs/<batch>/before-tests.txt.
  3. Behaviour: evaluator runner public (U01-U10) and hidden (H01-H04)
     suites against the delivered notes.py (subprocess).
  4. Static gates: README.md exists; CHANGES.md <= 10 non-empty entries;
     notes.py imports stdlib only (AST); non-test extra executable files
     recorded (not failing).
  5. verdict.json assembled from all of the above (score = static gates +
     U01-U10 all pass + H01-H04 all pass, frozen success standard).

Usage: python isolation/closeout_batch.py <batch-name>
  workspace = ../t2-prod/<batch-name>   (never inside t2-eval/t2-prep)
Exit 0 iff verdict["isolation_ok"] and verdict["score"]["pass"].
"""
import ast
import datetime as _dt
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
T2EVAL = os.path.dirname(HERE)
T2PREP = os.path.join(os.path.dirname(T2EVAL), "t2-prep")
sys.path.insert(0, HERE)

import verify_package as vp  # noqa: E402

BATCH = sys.argv[1] if len(sys.argv) > 1 else "batch-cc-1"
WS = os.path.abspath(os.path.join(T2EVAL, "..", "t2-prod", BATCH))
RUN_DIR = os.path.join(T2EVAL, "runs", BATCH)
PYTHON = sys.executable

STDLIB = set(getattr(sys, "stdlib_module_names", ()))


def problem(msg):
    print("PROBLEM: " + msg)
    return [msg]


def main():
    verdict = {
        "batch": BATCH,
        "generated": _dt.datetime.now().isoformat(timespec="seconds"),
        "spec": "isolation/spec-d4-batch-v0.2.md",
        "workspace": WS,
        "closeout_tool_sha256": vp.sha256_file(os.path.abspath(__file__)),
        "problems": [],
    }
    problems = []

    if not os.path.isdir(WS):
        sys.exit("workspace not found: " + WS)

    # ---- 1. L-d canary scan (phase=always only) -------------------------
    readme_original = os.path.join(RUN_DIR, "readme-original.md")
    corpus = vp.load_corpus()
    with open(os.path.join(T2EVAL, "MANIFEST.json"), "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    allow = vp.build_allowlist(manifest)
    whitelist = [allow[rel] for rel in sorted(allow)]
    if os.path.isfile(readme_original):
        whitelist.append(readme_original)

    stale, dropped, active, _fsources, _wsources, subset_sha = vp.prepare_corpus(
        corpus, "always", whitelist)
    ld_hits = vp.scan_tree(WS, active)
    strong_hits = [h for h in ld_hits if h["strength"] == "strong"]
    weak_hits = [h for h in ld_hits if h["strength"] != "strong"]
    ld = {
        "phase_filter": "always",
        "corpus_sha256": vp.sha256_file(vp.CORPUS_PATH),
        "active_count": len(active),
        "active_subset_sha256": subset_sha,
        "stale_removed": stale,
        "whitelist_removed": dropped,
        "hits": ld_hits,
        "claims_scope": "zero match in active literal corpus byte patterns (utf-8/utf-16-le)",
        "strong_hits": len(strong_hits),
        "weak_hits": len(weak_hits),
        "isolation_ok": len(strong_hits) == 0 and not stale,
    }
    verdict["ld_scan"] = ld
    if strong_hits:
        problems += problem("L-d strong hit(s): %s"
                            % [(h["path"], h["value"]) for h in strong_hits])
    if stale:
        problems += problem("L-d stale corpus entries: %d" % len(stale))
    print("L-d: %d active (subset %s), hits strong=%d weak=%d"
          % (len(active), subset_sha[:12], len(strong_hits), len(weak_hits)))

    # ---- 2. tests integrity ---------------------------------------------
    tests_ws = os.path.join(WS, "tests")
    ws_tests = {}
    for base, dirs, files in os.walk(tests_ws):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in files:
            p = os.path.join(base, name)
            rel = os.path.relpath(p, tests_ws).replace(os.sep, "/")
            ws_tests[rel] = vp.sha256_file(p)
    manifest_tests = manifest["sections"]["tests"]
    ti = {
        "manifest_entries": len(manifest_tests),
        "workspace_files": len(ws_tests),
        "missing": sorted(set(manifest_tests) - set(ws_tests)),
        "extra": sorted(set(ws_tests) - set(manifest_tests)),
        "modified": sorted(r for r in manifest_tests
                           if r in ws_tests and ws_tests[r] != manifest_tests[r]),
    }
    before_path = os.path.join(RUN_DIR, "before-tests.txt")
    before = {}
    if os.path.isfile(before_path):
        with open(before_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if not line:
                    continue
                digest, _, rel = line.partition("  ")
                before[rel] = digest
        ti["before_vs_after_diff"] = sorted(
            r for r in set(before) | set(ws_tests)
            if before.get(r) != ws_tests.get(r))
    else:
        ti["before_vs_after_diff"] = None
        problems += problem("before-tests.txt missing")
    ti["ok"] = (not ti["missing"] and not ti["extra"] and not ti["modified"]
                and ti["before_vs_after_diff"] == [])
    verdict["tests_integrity"] = ti
    if not ti["ok"]:
        problems += problem("tests integrity failed: %s" % json.dumps(
            {k: ti[k] for k in ("missing", "extra", "modified",
                                "before_vs_after_diff")}, ensure_ascii=False))
    print("tests integrity: %s (missing=%d extra=%d modified=%d before-after-diff=%d)"
          % ("OK" if ti["ok"] else "FAIL", len(ti["missing"]), len(ti["extra"]),
             len(ti["modified"]),
             len(ti["before_vs_after_diff"]) if ti["before_vs_after_diff"] is not None else -1))

    # ---- 3. behaviour: runner public + hidden ----------------------------
    notes = os.path.join(WS, "notes.py")
    behaviour = {}
    for suite in ("public", "hidden"):
        run_id = "%s-eval-%s" % (BATCH, suite)
        cmd = [PYTHON, os.path.join(T2EVAL, "evaluator", "runner.py"),
               "--notes", notes, "--suite", suite, "--run-id", run_id]
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              cwd=os.path.join(T2EVAL, "evaluator"))
        rep_path = os.path.join(T2EVAL, "runs", run_id, "report.json")
        rep = None
        if os.path.isfile(rep_path):
            with open(rep_path, "r", encoding="utf-8") as fh:
                rep = json.load(fh)
        behaviour[suite] = {
            "run_id": run_id,
            "exit": proc.returncode,
            "summary": rep.get("summary") if rep else None,
            "report": "runs/%s/report.json" % run_id,
        }
        print("runner %s: exit=%d summary=%s"
              % (suite, proc.returncode,
                 json.dumps(rep.get("summary"), ensure_ascii=False)
                 if rep else proc.stdout[-200:] + proc.stderr[-200:]))
    verdict["behaviour"] = behaviour

    # ---- 4. static gates --------------------------------------------------
    sg = {}
    sg["readme_exists"] = os.path.isfile(os.path.join(WS, "README.md"))
    changes_path = os.path.join(WS, "CHANGES.md")
    entries = -1
    if os.path.isfile(changes_path):
        with open(changes_path, "r", encoding="utf-8", errors="replace") as fh:
            lines = [ln.strip() for ln in fh]
        body = [ln for ln in lines if ln and not ln.startswith("#")]
        entries = len(body)
    sg["changes_entries_nonempty"] = entries
    sg["changes_within_10"] = 0 <= entries <= 10

    notes_src = None
    bad_imports = []
    if os.path.isfile(notes):
        with open(notes, "r", encoding="utf-8") as fh:
            notes_src = fh.read()
        try:
            tree = ast.parse(notes_src)
            for node in ast.walk(tree):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    mods = [node.module]
                for m in mods:
                    top = m.split(".")[0]
                    if top not in STDLIB and top != "notes":
                        bad_imports.append(m)
        except SyntaxError as exc:
            bad_imports.append("<syntax error: %s>" % exc)
    sg["notes_stdlib_only"] = not bad_imports
    sg["notes_bad_imports"] = bad_imports
    sg["notes_sha256"] = vp.sha256_file(notes) if os.path.isfile(notes) else None

    extra_exec = []
    for rel in sorted(vp.walk_rel(WS)):
        if rel.startswith("tests/") or "/" in rel:
            continue
        if rel.endswith((".py", ".exe", ".bat", ".cmd", ".ps1", ".sh", ".com")):
            if rel not in ("notes.py",):
                extra_exec.append(rel)
    sg["extra_executables_recorded"] = extra_exec
    sg["ok"] = (sg["readme_exists"] and sg["changes_within_10"]
                and sg["notes_stdlib_only"])
    verdict["static_gates"] = sg
    if not sg["ok"]:
        problems += problem("static gates failed: %s" % json.dumps(
            {k: sg[k] for k in ("readme_exists", "changes_entries_nonempty",
                                "changes_within_10", "notes_bad_imports")}))
    print("static gates: %s (readme=%s changes=%s stdlib=%s extra-exec=%s)"
          % ("OK" if sg["ok"] else "FAIL", sg["readme_exists"], entries,
             sg["notes_stdlib_only"], extra_exec))

    # ---- 5. score ---------------------------------------------------------
    def suite_all_pass(suite):
        s = behaviour.get(suite, {}).get("summary") or {}
        cases_total = s.get("cases_total") or 0
        return cases_total > 0 and s.get("cases_passed") == cases_total

    score = {
        "static_gates_ok": sg["ok"],
        "public_all_pass": suite_all_pass("public"),
        "hidden_all_pass": suite_all_pass("hidden"),
    }
    score["pass"] = all(score.values())
    verdict["score"] = score
    verdict["isolation_ok"] = ld["isolation_ok"]
    verdict["problems"] = problems
    verdict["ok"] = verdict["isolation_ok"] and score["pass"] and ti["ok"]

    out = os.path.join(RUN_DIR, "verdict.json")
    os.makedirs(RUN_DIR, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(verdict, fh, ensure_ascii=False, indent=1)
    print("SCORE: %s  isolation_ok=%s  ->  %s"
          % ("PASS" if score["pass"] else "FAIL",
             verdict["isolation_ok"], out))
    return 0 if verdict["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

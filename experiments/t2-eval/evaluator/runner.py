"""Sandbox runner + assertion engine for the T2 evaluator (frozen public-cases v0.1).

Per case: fresh sandbox under runs/<id>/sandbox-<CASE>, initial files written
byte-exactly (fixtures or canonical synthesis), steps executed as
[python, notes.py] + argv with cwd=sandbox (no shell), assertions per case data
plus the general rules from public-cases.md §0:

  - rejected step  -> whole sandbox tree byte-identical (no temp residue)
  - list/search ok -> tree byte-identical (store unchanged)
  - export ok      -> only --out may appear (new file, checked semantically)
  - add ok         -> only --store may change

stdout: empty or JSON-semantic equality. stderr: empty, or exactly one
non-empty line with empty stdout on failure steps.
"""
import argparse
import datetime as _dt
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # t2-eval/
FIXTURES = os.path.join(ROOT, "fixtures")
RUNS = os.path.join(ROOT, "runs")
PY = sys.executable
STEP_TIMEOUT = 30

sys.path.insert(0, HERE)
import cases  # noqa: E402


# ---------- canonical synthesis ----------

def synthesize(records, fmt):
    if fmt == "jsonl":
        return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records).encode("utf-8")
    if fmt == "array":
        return (json.dumps(records, ensure_ascii=False) + "\n").encode("utf-8")
    raise ValueError("bad format: " + repr(fmt))


def filespec_bytes(spec):
    if "fixture" in spec:
        with open(os.path.join(FIXTURES, spec["fixture"]), "rb") as fh:
            return fh.read()
    if "empty" in spec:
        return b""
    if "bytes" in spec:
        return spec["bytes"]
    if "records" in spec:
        return synthesize(spec["records"], spec["format"])
    raise ValueError("bad filespec: " + repr(spec))


# ---------- store parsing mirror (for semantic checks) ----------

def _validate_records_schema(records):
    seen = set()
    for obj in records:
        if not isinstance(obj, dict) or set(obj.keys()) != {"title", "body"}:
            raise ValueError("record schema")
        t, b = obj["title"], obj["body"]
        if not isinstance(t, str) or not isinstance(b, str):
            raise ValueError("record schema")
        if t.strip() == "":
            raise ValueError("blank title")
        if t in seen:
            raise ValueError("duplicate title")
        seen.add(t)


def parse_store(raw):
    """Mirror the product's store parsing. Returns (records, is_array)."""
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("BOM")
    text = raw.decode("utf-8")  # strict; UnicodeDecodeError is a ValueError
    if text == "":
        return [], False
    if text.lstrip()[:1] == "[":
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError("expected JSON array")
        _validate_records_schema(data)
        return data, True
    lines = text.split("\n")
    if text.endswith("\n"):
        lines.pop()
    records = []
    for line in lines:
        if line.strip() == "":
            raise ValueError("blank JSONL line")
        records.append(json.loads(line))
    _validate_records_schema(records)
    return records, False


def check_semantic(raw, expected, fmt):
    records, is_array = parse_store(raw)
    if fmt == "array" and not is_array:
        raise ValueError("expected array format on disk")
    if fmt == "jsonl" and is_array:
        raise ValueError("expected jsonl format on disk")
    if records != expected:
        raise ValueError("semantic mismatch: %r != %r" % (records, expected))


# ---------- sandbox mechanics ----------

def sandbox_tree(root):
    tree = {}
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        for d in dirnames:
            key = d if rel_dir == "." else os.path.normpath(os.path.join(rel_dir, d))
            tree[key] = ("dir", None)
        for f in filenames:
            key = f if rel_dir == "." else os.path.normpath(os.path.join(rel_dir, f))
            with open(os.path.join(dirpath, f), "rb") as fh:
                tree[key] = ("file", fh.read())
    return tree


def tree_diff(pre, post):
    return {k for k in set(pre) | set(post) if pre.get(k) != post.get(k)}


def materialize(argv, sandbox):
    out = []
    for tok in argv:
        if isinstance(tok, tuple):
            if tok[0] != "ABS":
                raise ValueError("bad argv token: " + repr(tok))
            out.append(os.path.join(sandbox, tok[1]))
        else:
            out.append(tok)
    return out


def extract_option(argv, name):
    """Find --opt value / --opt=value the way the product parser would."""
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == name:
            return argv[i + 1] if i + 1 < len(argv) else None
        opt, sep, val = tok.partition("=")
        if sep and opt == name:
            return val
        i += 1
    return None


def argv_rel(value, sandbox):
    if value is None:
        return None
    if os.path.isabs(value):
        value = os.path.relpath(value, sandbox)
    return os.path.normpath(value)


# ---------- step / case execution ----------

def run_step(sandbox, notes_abs, step):
    errors = []
    for rel, spec in (step.get("inject") or {}).items():
        p = os.path.join(sandbox, rel)
        parent = os.path.dirname(p)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(p, "wb") as fh:
            fh.write(filespec_bytes(spec))

    pre = sandbox_tree(sandbox)
    argv = materialize(step["argv"], sandbox)
    try:
        proc = subprocess.run([PY, notes_abs] + argv, cwd=sandbox,
                              capture_output=True, timeout=STEP_TIMEOUT)
        rc, out_b, err_b = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        rc, out_b, err_b = None, b"", b""
        errors.append("timeout (BLOCKED)")

    if rc != step["exit"]:
        errors.append("exit %r != expected %r" % (rc, step["exit"]))

    if step["stdout"] is None:
        if out_b != b"":
            errors.append("stdout not empty: %r" % out_b[:120])
    else:
        try:
            val = json.loads(out_b.decode("utf-8"))
        except Exception as exc:
            errors.append("stdout not valid utf-8/json: %s" % exc)
        else:
            if val != step["stdout"]["json"]:
                errors.append("stdout json mismatch: %r != %r"
                              % (val, step["stdout"]["json"]))

    if step["stderr"] == "empty":
        if err_b != b"":
            errors.append("stderr not empty: %r" % err_b[:160])
    else:  # oneline
        if out_b != b"":
            errors.append("stdout not empty on failure step")
        body = err_b[:-1] if err_b.endswith(b"\n") else err_b
        if body == b"" or b"\n" in body:
            errors.append("stderr not exactly one non-empty line: %r" % err_b[:160])
        else:
            try:
                body.decode("utf-8")
            except UnicodeDecodeError:
                errors.append("stderr not valid utf-8")

    # general tree policy (public-cases.md §0)
    changed = tree_diff(pre, sandbox_tree(sandbox))
    sub = step["argv"][0]
    sub = sub if isinstance(sub, str) else None
    if step["exit"] != 0:
        allowed = set()
    elif sub in ("list", "search"):
        allowed = set()
    elif sub == "export":
        allowed = {argv_rel(extract_option(argv, "--out"), sandbox)}
    elif sub == "add":
        allowed = {argv_rel(extract_option(argv, "--store"), sandbox)}
    else:
        allowed = set()
    allowed.discard(None)
    extra = changed - allowed
    if extra:
        errors.append("sandbox tree changed beyond policy: %s" % sorted(extra))

    for rel, check in (step.get("files_after") or {}).items():
        p = os.path.normpath(os.path.join(sandbox, rel))
        if "absent" in check:
            if os.path.exists(p):
                errors.append("files_after %s: expected absent" % rel)
            continue
        if "dir_empty" in check:
            if not os.path.isdir(p) or os.listdir(p):
                errors.append("files_after %s: expected existing empty dir" % rel)
            continue
        if not os.path.isfile(p):
            errors.append("files_after %s: expected file, missing" % rel)
            continue
        with open(p, "rb") as fh:
            raw = fh.read()
        if "bytes" in check:
            if raw != check["bytes"]:
                errors.append("files_after %s: bytes mismatch" % rel)
        elif "semantic" in check:
            try:
                check_semantic(raw, check["semantic"], check["format"])
            except ValueError as exc:
                errors.append("files_after %s: %s" % (rel, exc))

    return {
        "label": step["label"],
        "argv": [t if not isinstance(t, tuple) else "ABS:" + t[1] for t in step["argv"]],
        "expected_exit": step["exit"],
        "actual_exit": rc,
        "ok": not errors,
        "errors": errors,
        "stderr": err_b.decode("utf-8", "replace")[:300],
    }


def run_case(case, notes_abs, run_dir, tag=None):
    name = "sandbox-%s-%s" % (tag, case["id"]) if tag else "sandbox-" + case["id"]
    sandbox = os.path.join(run_dir, name)
    if os.path.exists(sandbox):
        shutil.rmtree(sandbox)
    os.makedirs(sandbox)
    for d in case["init"].get("dirs", []):
        os.makedirs(os.path.join(sandbox, d), exist_ok=True)
    for rel, spec in case["init"]["files"].items():
        p = os.path.join(sandbox, rel)
        parent = os.path.dirname(p)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(p, "wb") as fh:
            fh.write(filespec_bytes(spec))
    steps = [run_step(sandbox, notes_abs, s) for s in case["steps"]]
    return {"id": case["id"], "pass": all(s["ok"] for s in steps), "steps": steps}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compare_with_expected(results, expected, case_ids):
    """Exact two-directional comparison of failing steps vs a predicted list."""
    actual = {r["id"]: [s["label"] for s in r["steps"] if not s["ok"]] for r in results}
    rows = []
    for cid in case_ids:
        exp = set(expected.get(cid, []))
        act = set(actual.get(cid, []))
        rows.append({
            "id": cid,
            "expected_fail": sorted(exp),
            "actual_fail": sorted(act),
            "missing": sorted(exp - act),
            "unexpected": sorted(act - exp),
            "ok": exp == act,
        })
    return rows


def print_compare(rows):
    for row in rows:
        if row["ok"] and not row["expected_fail"]:
            print("%s PASS (all steps pass, as predicted)" % row["id"])
        elif row["ok"]:
            print("%s PASS (fails exactly steps %s)" % (row["id"], ",".join(row["expected_fail"])))
        else:
            print("%s MISMATCH expected=%s actual=%s missing=%s unexpected=%s"
                  % (row["id"], row["expected_fail"], row["actual_fail"],
                     row["missing"], row["unexpected"]))


def main():
    ap = argparse.ArgumentParser(description="T2 evaluator runner")
    ap.add_argument("--notes", required=True, help="path to notes.py under test")
    ap.add_argument("--suite", default="public",
                    choices=["public", "hidden", "mutants", "defective"])
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()

    notes_abs = os.path.abspath(args.notes)
    if not os.path.isfile(notes_abs):
        sys.exit("notes not found: " + notes_abs)

    label = os.path.splitext(os.path.basename(notes_abs))[0]
    run_id = args.run_id or (_dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + label)
    run_dir = os.path.join(RUNS, run_id)
    os.makedirs(run_dir, exist_ok=True)

    report = {
        "run_id": run_id,
        "generated": _dt.datetime.now().isoformat(timespec="seconds"),
        "suite": args.suite,
        "notes": {"path": notes_abs, "sha256": sha256_file(notes_abs)},
        "python": PY,
    }
    overall_ok = True

    if args.suite in ("public", "hidden"):
        if args.suite == "public":
            suite_cases = cases.get_public_cases()
        else:
            import hidden
            suite_cases = hidden.get_hidden_cases()
        results = [run_case(c, notes_abs, run_dir) for c in suite_cases]
        total_steps = sum(len(r["steps"]) for r in results)
        failed_steps = sum(1 for r in results for s in r["steps"] if not s["ok"])
        report["cases"] = results
        report["summary"] = {
            "cases_total": len(results),
            "cases_passed": sum(1 for r in results if r["pass"]),
            "steps_total": total_steps,
            "steps_failed": failed_steps,
        }
        overall_ok = failed_steps == 0
        for r in results:
            n_ok = sum(1 for s in r["steps"] if s["ok"])
            line = "%s %s (%d/%d steps)" % (r["id"], "PASS" if r["pass"] else "FAIL",
                                            n_ok, len(r["steps"]))
            bad = [s for s in r["steps"] if not s["ok"]]
            if bad:
                line += "  failing: " + ", ".join(s["label"] for s in bad)
            print(line)
            for s in bad[:4]:
                for e in s["errors"][:3]:
                    print("    [%s] %s" % (s["label"], e))
        print("summary: %d/%d cases, %d/%d steps ok  ->  %s"
              % (report["summary"]["cases_passed"], len(results),
                 total_steps - failed_steps, total_steps, run_dir))
    else:
        import mutants
        import predicted
        public_cases = cases.get_public_cases()
        if args.suite == "mutants":
            report["mutants"] = []
            for mid, expected in (("M01", predicted.M01_EXPECTED),
                                  ("M02", predicted.M02_EXPECTED),
                                  ("M03", predicted.M03_EXPECTED)):
                stage = os.path.join(run_dir, "mutant-" + mid)
                os.makedirs(stage, exist_ok=True)
                staged = os.path.join(stage, "notes.py")
                with open(staged, "w", encoding="utf-8", newline="") as fh:
                    fh.write(mutants.build(mid))
                results = [run_case(c, staged, run_dir, tag=mid) for c in public_cases]
                rows = compare_with_expected(results, expected, predicted.ALL_CASE_IDS)
                ok = all(r["ok"] for r in rows)
                overall_ok = overall_ok and ok
                report["mutants"].append({
                    "id": mid, "notes_sha256": sha256_file(staged),
                    "rows": rows, "cases": results, "ok": ok,
                })
                print("== %s (staged at %s) %s" % (mid, staged, "CALIBRATED" if ok else "MISMATCH"))
                print_compare(rows)
            print("mutation calibration: %s  ->  %s"
                  % ("OK" if overall_ok else "FAILED", run_dir))
        else:  # defective
            results = [run_case(c, notes_abs, run_dir, tag="def") for c in public_cases]
            rows = compare_with_expected(results, predicted.DEFECTIVE_EXPECTED,
                                         predicted.ALL_CASE_IDS)
            overall_ok = all(r["ok"] for r in rows)
            report["cases"] = results
            report["comparison"] = rows
            print("== defective %s" % ("PREDICTED-EXACT" if overall_ok else "MISMATCH"))
            print_compare(rows)
            print("defective check: %s  ->  %s" % ("OK" if overall_ok else "FAILED", run_dir))

    with open(os.path.join(run_dir, "report.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    sys.exit(0 if overall_ok else 1)


if __name__ == "__main__":
    main()

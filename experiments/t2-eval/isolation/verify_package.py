"""D2/D4 isolation verifier — spec-d2-isolation-v0.1.md layers L-a/L-b,
plus D4 (spec-d4-batch-v0.2.md) workspace scan mode.

Staging mode (default): assembles the candidate product task package from
the evaluation-side allowlist into runs/<run-id>/staging-package, then
verifies:
  L-a  file set == allowlist exactly; every staged file byte-identical to its
       evaluation-side source (SHA-256); sources cross-checked against
       MANIFEST.json (defective, tests) and frozen-criteria-sha256.txt
       (spec, public-cases).
  L-b  secret-corpus scan over every staged file (UTF-8 and UTF-16-LE byte
       patterns), after a freshness pass (each entry must occur in some
       eval-side secret source, provenance recorded) and a whitelist pass
       (entries legitimately present in allowed public sources are dropped
       and recorded).

Scan mode (--scan-dir <dir>): L-b-equivalent scan of an EXISTING directory
tree (D4 assembled product workspace, pre-session or post-session L-d).
  --phases all      use package+always corpus entries (pre-session: the
                    package may legitimately contain package-phase anchors)
  --phases always   use only phase=always entries (post-session L-d: a
                    repaired product may legitimately contain package-phase
                    anchors, so they must not raise isolation findings)
  --whitelist-extra <path>  additional eval-side public original whose
                    legitimate content drops matching entries (e.g. the
                    eval-side copy of the product README)

Claims scope (all modes): a PASS means "zero match in the active literal
corpus byte patterns"; it is NOT a claim that no secret-shaped material of
any encoding/paraphrase is absent.

Usage:
  python isolation/verify_package.py [run-id]              staging (default
                                                           run-id d2-verify-1)
  python isolation/verify_package.py --scan-dir <dir> --scan-run-id <id>
         [--phases all|always] [--whitelist-extra <p>...] [--label <text>]
Exit 0 iff every check passes. Report JSON lands in runs/<run-id>/report.json.
"""
import argparse
import datetime as _dt
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
T2EVAL = os.path.dirname(HERE)
T2PREP = os.path.join(os.path.dirname(T2EVAL), "t2-prep")

CORPUS_PATH = os.path.join(HERE, "secrets_corpus.json")

FROZEN_PATH = os.path.join(T2EVAL, "runs", "zero-change-check-1",
                           "frozen-criteria-sha256.txt")

# Every corpus entry must occur in at least one of these eval-side files,
# otherwise it is reported STALE and dropped from active scanning.
FRESHNESS_SOURCES = [
    os.path.join(T2PREP, "acceptance", "hidden-groups.md"),
    os.path.join(T2PREP, "acceptance", "mutation-map.md"),
    os.path.join(T2PREP, "README.md"),
    os.path.join(T2PREP, "coordination", "draft-status.md"),
    os.path.join(T2EVAL, "FABRICATION-LOG.md"),
    os.path.join(T2EVAL, "evaluator", "hidden.py"),
    os.path.join(T2EVAL, "evaluator", "mutants.py"),
    os.path.join(T2EVAL, "evaluator", "predicted.py"),
    os.path.join(T2EVAL, "runs", "zero-change-check-1", "verification.txt"),
    # Codex orchestration artifacts (eval-side secrets that could leak):
    r"D:\projects\cline-mcp-workspace\orchestration\tmp\task-t2-fabrication-review.md",
    r"D:\projects\cline-mcp-workspace\orchestration\runs\20260918-132658\last-message.txt",
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def load_frozen():
    anchors = {}
    with open(FROZEN_PATH, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            digest, _, rel = line.partition("  ")
            anchors[rel] = digest
    return anchors


def build_allowlist(manifest):
    """Package-relative path -> evaluation-side absolute source path."""
    allow = {}
    allow["notes.py"] = os.path.join(T2EVAL, "defective", "notes.py")
    allow["T2-SPEC-draft-v0.1.md"] = os.path.join(
        T2PREP, "spec", "T2-SPEC-draft-v0.1.md")
    allow["public-cases.md"] = os.path.join(
        T2PREP, "acceptance", "public-cases.md")
    for rel in sorted(manifest["sections"]["tests"]):
        allow[rel] = os.path.join(T2EVAL, *rel.split("/"))
    return allow


def walk_rel(root):
    found = set()
    for base, _dirs, files in os.walk(root):
        for name in files:
            p = os.path.join(base, name)
            found.add(os.path.relpath(p, root).replace(os.sep, "/"))
    return found


def prepare_corpus(corpus, phase_filter, whitelist_paths):
    """Freshness + whitelist + phase filter over corpus entries.

    Returns (stale, dropped, active, freshness_sources, whitelist_sources,
    active_subset_sha256). dropped/active entries carry provenance:
    which freshness source / whitelist source legitimated or failed them.
    """
    freshness_sources = []
    freshness_texts = []
    for p in FRESHNESS_SOURCES:
        with open(p, "rb") as fh:
            freshness_sources.append({"path": p, "sha256": sha256_file(p)})
            freshness_texts.append((p, fh.read().decode("utf-8", "replace")))

    whitelist_sources = []
    whitelist_bytes = b""
    for p in whitelist_paths:
        with open(p, "rb") as fh:
            whitelist_sources.append({"path": p, "sha256": sha256_file(p)})
            whitelist_bytes += fh.read() + b"\n"

    stale, dropped, active = [], [], []
    for e in corpus:
        v = e["value"]
        phase = e.get("phase", "always")
        if phase not in ("always", "package"):
            stale.append({"value": v, "reason": "unknown phase %r" % phase})
            continue
        if phase_filter == "always" and phase != "always":
            continue  # not in this scan's subset; not stale, not dropped
        src = next((p for p, t in freshness_texts if v in t), None)
        if src is None:
            stale.append({"value": v, "reason": "not in any freshness source"})
        elif v.encode("utf-8") in whitelist_bytes:
            dropped.append({"value": v, "source": "whitelist"})
        else:
            active.append({"value": v, "category": e["category"],
                           "strength": e["strength"], "phase": phase,
                           "freshness_source": src})

    subset_raw = json.dumps([a["value"] for a in active],
                            ensure_ascii=False, separators=(",", ":"))
    return (stale, dropped, active, freshness_sources, whitelist_sources,
            sha256_bytes(subset_raw.encode("utf-8")))


def scan_tree(root, active):
    """Scan every file under root for active corpus byte patterns."""
    hits = []
    for rel in sorted(walk_rel(root)):
        p = os.path.join(root, *rel.split("/"))
        with open(p, "rb") as fh:
            raw = fh.read()
        for e in active:
            v = e["value"]
            enc = ("utf-8" if v.encode("utf-8") in raw else
                   "utf-16-le" if v.encode("utf-16-le") in raw else None)
            if enc:
                hits.append({"path": rel, "value": v, "encoding": enc,
                             "category": e["category"],
                             "strength": e["strength"], "phase": e["phase"]})
    return hits


def load_corpus():
    with open(CORPUS_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)["entries"]


def write_report(run_id, report):
    run_dir = os.path.join(T2EVAL, "runs", run_id)
    os.makedirs(run_dir, exist_ok=True)
    out = os.path.join(run_dir, "report.json")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    return out


def print_corpus_summary(corpus, stale, dropped, active):
    print("corpus: %d total, %d stale, %d whitelist-dropped, %d active"
          % (len(corpus), len(stale), len(dropped), len(active)))
    for s in stale:
        print("  stale: %s (%s)" % (s["value"], s["reason"]))
    for d in dropped:
        print("  whitelist: %s" % d["value"])


def run_staging(run_id):
    staging = os.path.join(T2EVAL, "runs", run_id, "staging-package")
    ok = True
    with open(os.path.join(T2EVAL, "MANIFEST.json"), "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    frozen = load_frozen()
    allow = build_allowlist(manifest)

    problems = []

    # ---- assemble staging package -------------------------------------
    if os.path.exists(staging):
        shutil.rmtree(staging)
    os.makedirs(staging)
    for rel, src in sorted(allow.items()):
        dst = os.path.join(staging, *rel.split("/"))
        parent = os.path.dirname(dst)
        if parent:
            os.makedirs(parent, exist_ok=True)
        shutil.copyfile(src, dst)

    # ---- L-a: file set -------------------------------------------------
    staged = walk_rel(staging)
    expected = set(allow)
    if staged != expected:
        ok = False
        problems.append("file set mismatch: missing=%s extra=%s"
                        % (sorted(expected - staged), sorted(staged - expected)))

    # ---- L-a: byte identity + integrity anchors ------------------------
    integrity = []
    for rel in sorted(expected):
        src = allow[rel]
        src_sha = sha256_file(src)
        dst = os.path.join(staging, *rel.split("/"))
        dst_sha = sha256_file(dst) if os.path.isfile(dst) else None
        entry = {"path": rel, "source_sha256": src_sha, "staged_sha256": dst_sha,
                 "copy_ok": src_sha == dst_sha}
        if not entry["copy_ok"]:
            ok = False
            problems.append("copy not byte-identical: " + rel)
        if rel == "notes.py":
            anchor = manifest["sections"]["defective"]["defective/notes.py"]
        elif rel.startswith("tests/"):
            anchor = manifest["sections"]["tests"][rel]
        elif rel == "T2-SPEC-draft-v0.1.md":
            anchor = frozen["spec\\T2-SPEC-draft-v0.1.md"]
        else:
            anchor = frozen["acceptance\\public-cases.md"]
        entry["anchor"] = "manifest" if rel.startswith("tests/") or rel == "notes.py" else "frozen-criteria"
        entry["anchor_ok"] = (src_sha == anchor)
        if not entry["anchor_ok"]:
            ok = False
            problems.append("source hash != integrity anchor: " + rel)
        integrity.append(entry)

    # ---- L-b: corpus freshness / whitelist / scan -----------------------
    corpus = load_corpus()
    stale, dropped, active, fsources, wsources, subset_sha = prepare_corpus(
        corpus, "all", [allow[rel] for rel in sorted(expected)])

    scan_hits = scan_tree(staging, active)
    if scan_hits:
        ok = False
        for hit in scan_hits:
            problems.append("secret hit: %s contains %r" % (hit["path"], hit["value"]))

    # ---- report ---------------------------------------------------------
    report = {
        "mode": "staging",
        "run_id": run_id,
        "generated": _dt.datetime.now().isoformat(timespec="seconds"),
        "spec": "isolation/spec-d2-isolation-v0.1.md",
        "verifier_sha256": sha256_file(os.path.abspath(__file__)),
        "corpus_sha256": sha256_file(CORPUS_PATH),
        "allowlist": {rel: sha256_file(allow[rel]) for rel in sorted(expected)},
        "staged_files": sorted(staged),
        "integrity": integrity,
        "corpus": {
            "total": len(corpus),
            "phase_filter": "all",
            "stale_removed": stale,
            "whitelist_removed": dropped,
            "active_count": len(active),
            "active_values": [e["value"] for e in active],
            "active_subset_sha256": subset_sha,
            "freshness_sources": fsources,
            "whitelist_sources": wsources,
        },
        "claims_scope": "PASS == zero match in active literal corpus byte patterns (utf-8/utf-16-le); not a claim of zero secrets of any encoding",
        "scan_hits": scan_hits,
        "problems": problems,
        "ok": ok,
    }
    out = write_report(run_id, report)

    print("staging package: %d files at %s" % (len(staged), staging))
    print("L-a integrity: %s" % ("OK" if all(i["copy_ok"] and i["anchor_ok"] for i in integrity) else "FAILED"))
    print_corpus_summary(corpus, stale, dropped, active)
    print("L-b scan hits: %d" % len(scan_hits))
    for hit in scan_hits:
        print("  HIT %s %r" % (hit["path"], hit["value"]))
    print("verdict: %s  ->  %s" % ("PASS" if ok else "FAIL", out))
    return 0 if ok else 1


def run_scan(scan_dir, run_id, phases, whitelist_extra, label):
    if not os.path.isdir(scan_dir):
        print("scan dir not found: %s" % scan_dir)
        return 2
    corpus = load_corpus()

    # Whitelist = evaluation-side originals of allowed public content
    # (allowlist files) + caller-provided extras (e.g. eval-side README copy).
    with open(os.path.join(T2EVAL, "MANIFEST.json"), "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    allow = build_allowlist(manifest)
    whitelist_paths = [allow[rel] for rel in sorted(allow)] + whitelist_extra

    stale, dropped, active, fsources, wsources, subset_sha = prepare_corpus(
        corpus, phases, whitelist_paths)

    files = sorted(walk_rel(scan_dir))
    file_manifest = []
    for rel in files:
        p = os.path.join(scan_dir, *rel.split("/"))
        file_manifest.append({"path": rel, "sha256": sha256_file(p),
                              "bytes": os.path.getsize(p)})

    scan_hits = scan_tree(scan_dir, active)

    problems = []
    if stale:
        problems.append("stale corpus entries: %d" % len(stale))
    if scan_hits:
        for hit in scan_hits:
            problems.append("secret hit: %s contains %r" % (hit["path"], hit["value"]))

    ok = not problems
    report = {
        "mode": "scan",
        "label": label,
        "run_id": run_id,
        "generated": _dt.datetime.now().isoformat(timespec="seconds"),
        "spec": "isolation/spec-d4-batch-v0.2.md",
        "scan_dir": os.path.abspath(scan_dir),
        "phase_filter": phases,
        "verifier_sha256": sha256_file(os.path.abspath(__file__)),
        "corpus_sha256": sha256_file(CORPUS_PATH),
        "files": file_manifest,
        "file_count": len(files),
        "corpus": {
            "total": len(corpus),
            "phase_filter": phases,
            "stale_removed": stale,
            "whitelist_removed": dropped,
            "active_count": len(active),
            "active_values": [e["value"] for e in active],
            "active_subset_sha256": subset_sha,
            "freshness_sources": fsources,
            "whitelist_sources": wsources,
        },
        "claims_scope": "PASS == zero match in active literal corpus byte patterns (utf-8/utf-16-le); not a claim of zero secrets of any encoding",
        "scan_hits": scan_hits,
        "problems": problems,
        "ok": ok,
    }
    out = write_report(run_id, report)

    print("scan: %s" % os.path.abspath(scan_dir))
    print("files: %d   phases: %s" % (len(files), phases))
    print_corpus_summary(corpus, stale, dropped, active)
    print("hits: %d" % len(scan_hits))
    for hit in scan_hits:
        print("  HIT %s %r (%s/%s)" % (hit["path"], hit["value"],
                                       hit["strength"], hit["phase"]))
    print("verdict: %s  ->  %s" % ("PASS" if ok else "FAIL", out))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("run_id", nargs="?", default="d2-verify-1",
                    help="staging run id (default d2-verify-1)")
    ap.add_argument("--scan-dir", help="scan this existing directory tree instead of staging")
    ap.add_argument("--scan-run-id", help="report run id for scan mode")
    ap.add_argument("--phases", choices=["all", "always"], default="all",
                    help="corpus phase subset for scan mode (pre-session: all; L-d: always)")
    ap.add_argument("--whitelist-extra", action="append", default=[],
                    help="extra eval-side public original to whitelist (repeatable)")
    ap.add_argument("--label", default="", help="free-text label recorded in scan report")
    args = ap.parse_args()

    if args.scan_dir:
        rid = args.scan_run_id or (args.run_id if args.run_id != "d2-verify-1" else "d4-scan-1")
        sys.exit(run_scan(args.scan_dir, rid, args.phases,
                          args.whitelist_extra, args.label))
    sys.exit(run_staging(args.run_id))


if __name__ == "__main__":
    main()

"""Supplementary checks for frozen-spec clauses not covered by public cases:
- T2-SPEC L39: unpaired surrogates -> argv value exit 2; store content exit 3;
  no file modifications in either case.
- T2-SPEC L47/R09: export leaves no temp-file residue (normal path).

Run after the reference fixes; evidence for FABRICATION-LOG section 7.
"""
import json
import os
import subprocess
import sys
import tempfile

NOTES = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "reference", "notes.py"))
PY = sys.executable
SURROGATE = "\ud800"

ok = 0
bad = 0


def check(name, cond, detail=""):
    global ok, bad
    if cond:
        ok += 1
        print("PASS " + name)
    else:
        bad += 1
        print("FAIL " + name + " " + detail)


def run(sb, argv):
    return subprocess.run([PY, NOTES] + argv, cwd=sb, capture_output=True)


def one_line_stderr(err):
    body = err[:-1] if err.endswith(b"\n") else err
    return body != b"" and b"\n" not in body


with tempfile.TemporaryDirectory() as sb:
    # 1. argv surrogate -> exit 2 (list / search missing --store guard before fix)
    r = run(sb, ["list", "--store", SURROGATE + "x.jsonl"])
    check("argv surrogate list exit2", r.returncode == 2, f"rc={r.returncode} err={r.stderr[:120]!r}")
    check("argv surrogate list oneline+empty stdout",
          r.stdout == b"" and one_line_stderr(r.stderr))

    r = run(sb, ["search", "--store", SURROGATE + "x.jsonl", "--query", "q"])
    check("argv surrogate search exit2", r.returncode == 2, f"rc={r.returncode}")

    r = run(sb, ["add", "--store", "s.jsonl", "--title", SURROGATE + "t", "--body", "b"])
    check("argv surrogate add title exit2", r.returncode == 2, f"rc={r.returncode}")
    check("argv surrogate add left no file", not os.path.exists(os.path.join(sb, "s.jsonl")))

    # 2. store-content surrogate: the JSON *escape text* \ud800 is pure ASCII on
    #    disk; json.loads then yields a lone surrogate in the record value.
    esc = '{"title": "\\ud800", "body": "b"}\n'
    p = os.path.join(sb, "store.jsonl")
    with open(p, "w", encoding="ascii", newline="") as fh:
        fh.write(esc)
    before = open(p, "rb").read()
    for argv in (["list", "--store", "store.jsonl"],
                 ["search", "--store", "store.jsonl", "--query", "q"],
                 ["export", "--store", "store.jsonl", "--out", "o.json"]):
        r = run(sb, argv)
        with open(p, "rb") as fh:
            after = fh.read()
        check("content surrogate exit3 " + argv[0], r.returncode == 3, f"rc={r.returncode}")
        check("content surrogate bytes unchanged " + argv[0], before == after)
        check("content surrogate oneline+empty stdout " + argv[0],
              r.stdout == b"" and one_line_stderr(r.stderr))
    check("content surrogate export created nothing",
          not os.path.exists(os.path.join(sb, "o.json")))

    # array-format store with surrogate content
    pa = os.path.join(sb, "arr.json")
    with open(pa, "w", encoding="ascii", newline="") as fh:
        fh.write('[{"title": "\\ud800", "body": "b"}]\n')
    r = run(sb, ["list", "--store", "arr.json"])
    check("array content surrogate exit3", r.returncode == 3, f"rc={r.returncode}")

    # 3. export normal path: no temp residue, correct output
    with open(os.path.join(sb, "good.jsonl"), "w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps({"title": "t", "body": "b"}, ensure_ascii=False) + "\n")
    r = run(sb, ["export", "--store", "good.jsonl", "--out", "out.json"])
    check("export ok", r.returncode == 0 and r.stdout == b"" and r.stderr == b"")
    residue = [f for f in os.listdir(sb) if ".tmp" in f or f.startswith(".notes-export-")]
    check("export no temp residue", residue == [], repr(residue))
    with open(os.path.join(sb, "out.json"), "rb") as fh:
        raw = fh.read()
    check("export array semantic",
          raw.decode("utf-8").lstrip()[:1] == "[" and json.loads(raw.decode("utf-8"))
          == [{"title": "t", "body": "b"}])

print(f"\n{ok} passed, {bad} failed")
sys.exit(1 if bad else 0)

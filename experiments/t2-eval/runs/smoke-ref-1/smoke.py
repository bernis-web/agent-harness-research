"""Quick smoke test for reference notes.py: core chain + exit codes + UTF-8 bytes."""
import json
import os
import subprocess
import sys
import tempfile

NOTES = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "reference", "notes.py"))
PY = sys.executable
ok = 0
bad = 0


def run(sandbox, argv):
    return subprocess.run([PY, NOTES] + argv, cwd=sandbox, capture_output=True)


def check(name, cond, detail=""):
    global ok, bad
    if cond:
        ok += 1
        print(f"PASS {name}")
    else:
        bad += 1
        print(f"FAIL {name} {detail}")


with tempfile.TemporaryDirectory() as sb:
    # 1. add with special chars (emoji, fullwidth, backslash, comma)
    r = run(sb, ["add", "--store", "store.jsonl", "--title", '标题"一"',
                 "--body", '行1\n行\t2\\end, "q"全角ＡＢ emoji😀'])
    check("add exit0", r.returncode == 0, f"rc={r.returncode} err={r.stderr!r}")
    check("add silent", r.stdout == b"" and r.stderr == b"")

    r = run(sb, ["add", "--store", "store.jsonl", "--title", "Straße", "--body", "UPPER lower MiXeD"])
    check("add strasse exit0", r.returncode == 0)

    # 2. list round-trips body exactly
    r = run(sb, ["list", "--store", "store.jsonl"])
    recs = json.loads(r.stdout.decode("utf-8"))
    check("list count", len(recs) == 2)
    check("list body fidelity", recs[0]["body"] == '行1\n行\t2\\end, "q"全角ＡＢ emoji😀', repr(recs[0]["body"]))
    check("list title fidelity", recs[0]["title"] == '标题"一"')

    # 3. casefold search
    r = run(sb, ["search", "--store", "store.jsonl", "--query", "strasse"])
    hits = json.loads(r.stdout.decode("utf-8"))
    check("casefold hit", [h["title"] for h in hits] == ["Straße"], repr(hits))

    # 4. rejected add leaves bytes unchanged
    before = open(os.path.join(sb, "store.jsonl"), "rb").read()
    r = run(sb, ["add", "--store", "store.jsonl", "--title", "Straße", "--body", "dup"])
    after = open(os.path.join(sb, "store.jsonl"), "rb").read()
    check("dup exit2", r.returncode == 2, f"rc={r.returncode}")
    check("dup one-line stderr", r.stderr.endswith(b"\n") and r.stderr.count(b"\n") == 1 and r.stderr.strip() != b"")
    check("dup bytes unchanged", before == after)

    # 5. export + reload + array add keeps order
    r = run(sb, ["export", "--store", "store.jsonl", "--out", "out.json"])
    check("export exit0", r.returncode == 0)
    r = run(sb, ["add", "--store", "out.json", "--title", "重载新条", "--body", "reloaded"])
    check("array add exit0", r.returncode == 0)
    arr = json.loads(open(os.path.join(sb, "out.json"), "rb").read().decode("utf-8"))
    check("array order", [a["title"] for a in arr] == ['标题"一"', "Straße", "重载新条"], repr(arr))
    raw = open(os.path.join(sb, "out.json"), "rb").read()
    check("array format kept", raw.decode("utf-8").lstrip()[:1] == "[")

    # 6. env/data errors
    r = run(sb, ["list", "--store", "missing.jsonl"])
    check("missing exit3", r.returncode == 3, f"rc={r.returncode}")
    r = run(sb, ["frobnicate"])
    check("unknown sub exit2", r.returncode == 2, f"rc={r.returncode}")
    r = run(sb, ["search", "--store", "store.jsonl", "--query", "ß"])
    hits = json.loads(r.stdout.decode("utf-8"))
    check("ss fold hit", [h["title"] for h in hits] == ["Straße"], repr(hits))

print(f"\n{ok} passed, {bad} failed")
sys.exit(1 if bad else 0)

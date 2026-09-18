# Spec corner cases beyond the public scenarios (data-substitution robustness).
import json, os, subprocess, sys, tempfile

NOTES = os.path.abspath("notes.py")
FAILURES = []

def check(cond, label):
    if not cond:
        FAILURES.append(label)
        print("FAIL:", label)

def run(sb, argv):
    return subprocess.run([sys.executable, NOTES] + argv, cwd=sb, capture_output=True)

def rd(sb, rel):
    p = os.path.join(sb, rel)
    if not os.path.exists(p):
        return None
    with open(p, "rb") as fh:
        return fh.read()

def wr(sb, rel, data):
    p = os.path.join(sb, rel)
    if os.path.dirname(p):
        os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as fh:
        fh.write(data)

def jout(r):
    return json.loads(r.stdout.decode("utf-8"))

def expect_code(sb, argv, code, label):
    r = run(sb, argv)
    check(r.returncode == code, label + " exit %d got %d stderr=%r" % (code, r.returncode, r.stderr[:150]))
    check(r.stdout == b"", label + " stdout empty")
    body = r.stderr[:-1] if r.stderr.endswith(b"\n") else r.stderr
    check(body != b"" and b"\n" not in body, label + " one-line stderr")
    return r

# 1. BOM store -> exit 3 (explicit format rejection), bytes unchanged
sb = tempfile.mkdtemp()
bom = b"\xef\xbb\xbf" + '{"title":"a","body":"b"}\n'.encode("utf-8")
wr(sb, "bom.jsonl", bom)
expect_code(sb, ["list", "--store", "bom.jsonl"], 3, "BOM list")
check(rd(sb, "bom.jsonl") == bom, "BOM bytes unchanged")

# 2. whitespace-only line -> exit 3
sb = tempfile.mkdtemp()
wr(sb, "s.jsonl", b'{"title":"a","body":"b"}\n   \n')
expect_code(sb, ["list", "--store", "s.jsonl"], 3, "ws line")
sb = tempfile.mkdtemp()
wr(sb, "s.jsonl", b'{"title":"a","body":"b"}\n\r\n')
expect_code(sb, ["list", "--store", "s.jsonl"], 3, "CR-only line")

# 3. CRLF line endings parse fine
sb = tempfile.mkdtemp()
wr(sb, "c.jsonl", '{"title":"a","body":"b"}\r\n{"title":"c","body":"d"}\r\n'.encode("utf-8"))
r = run(sb, ["list", "--store", "c.jsonl"])
check(r.returncode == 0 and jout(r) == [dict(title="a", body="b"), dict(title="c", body="d")], "CRLF parse")

# 4. no trailing LF then add: newline inserted between records
sb = tempfile.mkdtemp()
wr(sb, "n.jsonl", b'{"title":"a","body":"b"}')
r = run(sb, ["add", "--store", "n.jsonl", "--title", "c", "--body", "d"])
check(r.returncode == 0, "add no-LF exit")
raw = rd(sb, "n.jsonl").decode("utf-8")
lines = raw.split("\n")
check(len(lines) == 3 and lines[2] == "" and all(json.loads(l) for l in lines[:2]), "add no-LF structure: %r" % raw)
for ln in lines:
    if ln:
        json.loads(ln)

# 5. array store with leading whitespace before '['
sb = tempfile.mkdtemp()
wr(sb, "w.json", b'\n  [{"title":"a","body":"b"}]')
r = run(sb, ["list", "--store", "w.json"])
check(r.returncode == 0 and jout(r) == [dict(title="a", body="b")], "ws-leading array")

# 6. schema violations -> exit 3, bytes unchanged
cases = {
    "extra key": b'{"title":"a","body":"b","x":1}',
    "missing key": b'{"title":"a"}',
    "non-string title": b'{"title":1,"body":"b"}',
    "null body": b'{"title":"a","body":null}',
    "duplicate titles in store": b'{"title":"a","body":"1"}\n{"title":"a","body":"2"}',
    "blank title in store": b'{"title":"  ","body":"b"}',
    "non-dict line": b'42',
    "string line": b'"hello"',
    "truncated json": b'{"title":"a',
}
for label, data in cases.items():
    sb = tempfile.mkdtemp()
    wr(sb, "bad.jsonl", data)
    expect_code(sb, ["list", "--store", "bad.jsonl"], 3, label + " list")
    expect_code(sb, ["add", "--store", "bad.jsonl", "--title", "n", "--body", "m"], 3, label + " add")
    check(rd(sb, "bad.jsonl") == data, label + " bytes unchanged")

# 7. array store with bad element -> exit 3
sb = tempfile.mkdtemp()
wr(sb, "a.json", b'[{"title":"a","body":"b"},{"title":"a","body":"dup"}]')
expect_code(sb, ["list", "--store", "a.json"], 3, "array dup titles")

# 8. unpaired surrogate escaped in JSON text -> exit 3
sb = tempfile.mkdtemp()
wr(sb, "u.jsonl", b'{"title":"\\ud800","body":"b"}')
expect_code(sb, ["list", "--store", "u.jsonl"], 3, "surrogate store")
check(rd(sb, "u.jsonl") == b'{"title":"\\ud800","body":"b"}', "surrogate bytes unchanged")

# 9. inline --opt=value forms
sb = tempfile.mkdtemp()
r = run(sb, ["add", "--store=s.jsonl", "--title=t1", "--body=b1"])
check(r.returncode == 0 and r.stdout == b"" and r.stderr == b"", "inline add")
check(jout(run(sb, ["list", "--store=s.jsonl"])) == [dict(title="t1", body="b1")], "inline list")
r = run(sb, ["search", "--store=s.jsonl", "--query=t1"])
check(r.returncode == 0 and jout(r) == [dict(title="t1", body="b1")], "inline search")

# 10. --help / -h: exit 0, usage on stdout, no store access
sb = tempfile.mkdtemp()
for a in (["-h"], ["--help"]):
    r = run(sb, a)
    check(r.returncode == 0 and b"usage" in r.stdout.lower() and r.stderr == b"", "help " + a[0])
r = run(sb, [])
check(r.returncode == 2 and r.stdout == b"" and r.stderr.strip() != b"", "no args")

# 11. title with special characters roundtrip (LF/tab/quote/backslash in TITLE)
sb = tempfile.mkdtemp()
r = run(sb, ["add", "--store", "t.jsonl", "--title", 'a"b\\c\td\ne', "--body", "x"])
check(r.returncode == 0, "special title add")
recs = jout(run(sb, ["list", "--store", "t.jsonl"]))
check(recs == [dict(title='a"b\\c\td\ne', body="x")], "special title roundtrip")
raw = rd(sb, "t.jsonl").decode("utf-8")
check(len([l for l in raw.split("\n") if l]) == 1, "special title one physical line")
r = run(sb, ["search", "--store", "t.jsonl", "--query", 'b\\c\td'])
check(jout(r) == [dict(title='a"b\\c\td\ne', body="x")], "special title search")

# 12. add to empty (0-byte) existing file
sb = tempfile.mkdtemp()
wr(sb, "e.jsonl", b"")
r = run(sb, ["add", "--store", "e.jsonl", "--title", "a", "--body", "b"])
check(r.returncode == 0, "add to empty file")
check(jout(run(sb, ["list", "--store", "e.jsonl"])) == [dict(title="a", body="b")], "empty file add list")

# 13. read ops never rewrite (array store bytes identical across list/search)
sb = tempfile.mkdtemp()
wr(sb, "arr.json", b'[{"title":"a","body":"b"}]')
before = rd(sb, "arr.json")
run(sb, ["list", "--store", "arr.json"])
run(sb, ["search", "--store", "arr.json", "--query", "a"])
check(rd(sb, "arr.json") == before, "array store not rewritten by reads")

# 14. export same-path with ./ and abs mix; export out exists -> exit 2 covered; store missing + out ok -> exit 3
sb = tempfile.mkdtemp()
expect_code(sb, ["export", "--store", "nope.jsonl", "--out", "o.json"], 3, "missing store export")
check(rd(sb, "o.json") is None, "missing store export no out")

# 15. dup add rejected on array store leaves bytes identical (order preserved)
sb = tempfile.mkdtemp()
wr(sb, "arr.json", '[{"title":"a","body":"b"},{"title":"c","body":"d"}]'.encode("utf-8"))
before = rd(sb, "arr.json")
expect_code(sb, ["add", "--store", "arr.json", "--title", "c", "--body", "z"], 2, "array dup")
check(rd(sb, "arr.json") == before, "array dup bytes")
r = run(sb, ["add", "--store", "arr.json", "--title", "e", "--body", "f"])
check(r.returncode == 0 and json.loads(rd(sb, "arr.json").decode("utf-8")) ==
      [dict(title="a", body="b"), dict(title="c", body="d"), dict(title="e", body="f")], "array append order")

# 16. blank-title via inline empty and whitespace-only query legality
sb = tempfile.mkdtemp()
wr(sb, "q.jsonl", '{"title":"a b","body":"c"}'.encode("utf-8"))
expect_code(sb, ["add", "--store", "q.jsonl", "--title=", "--body=x"], 2, "inline empty title")
r = run(sb, ["search", "--store", "q.jsonl", "--query", " "])
check(r.returncode == 0 and jout(r) == [dict(title="a b", body="c")], "space query nonempty")

# 17. export writes UTF-8 without BOM; array out reload + search keeps order
sb = tempfile.mkdtemp()
wr(sb, "s.jsonl", '{"title":"x1","body":"y"}\n{"title":"x2","body":"y"}\n'.encode("utf-8"))
r = run(sb, ["export", "--store", "s.jsonl", "--out", "o.json"])
check(r.returncode == 0, "export ok")
raw = rd(sb, "o.json")
check(not raw.startswith(b"\xef\xbb\xbf") and raw.decode("utf-8").startswith("["), "export no BOM array")
check(jout(run(sb, ["search", "--store", "o.json", "--query", "y"])) ==
      [dict(title="x1", body="y"), dict(title="x2", body="y")], "reload search order")

# 18. Unicode casefold conformance: str.casefold() applied to both sides, then
# plain substring. Expectations derived from Python's own casefold tables.
sb = tempfile.mkdtemp()
wr(sb, "i.jsonl", '{"title":"İstanbul","body":"dıyar"}\n{"title":" Diyarbakır ","body":"z"}\n'.encode("utf-8"))
# 'İstanbul'.casefold() == 'i̇stanbul' which does NOT contain 'istanbul'
r = run(sb, ["search", "--store", "i.jsonl", "--query", "istAnbul"])
check(r.returncode == 0 and jout(r) == [], "tr casefold title")
# 'ı' has no ASCII mapping: 'dıyar' does not contain 'diyar'; 'diyarbakır' does
r = run(sb, ["search", "--store", "i.jsonl", "--query", "DIYAR"])
check(jout(r) == [dict(title=" Diyarbakır ", body="z")], "tr casefold body")

# 19. Greek sigma: final sigma in query folds to sigma, matches title
sb = tempfile.mkdtemp()
wr(sb, "g.jsonl", '{"title":"ΟΔΟΣ","body":"x"}\n'.encode("utf-8"))
r = run(sb, ["search", "--store", "g.jsonl", "--query", "οδος"])
check(r.returncode == 0 and jout(r) == [dict(title="ΟΔΟΣ", body="x")], "greek sigma casefold")
r = run(sb, ["search", "--store", "g.jsonl", "--query", "οδoS"])
check(jout(r) == [], "greek vs ascii s distinct")

print()
print("FAILURES:", len(FAILURES))
sys.exit(1 if FAILURES else 0)

# End-to-end walk of public-cases.md U01-U10 with SNAP byte semantics.
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
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as fh:
        fh.write(data)

def ok_silent(sb, argv, label):
    r = run(sb, argv)
    check(r.returncode == 0, label + ": exit0")
    check(r.stdout == b"", label + ": stdout empty")
    check(r.stderr == b"", label + ": stderr empty")
    return r

def reject(sb, argv, code, label):
    r = run(sb, argv)
    check(r.returncode == code, label + ": exit %d (got %d, stderr=%r)" % (code, r.returncode, r.stderr[:120]))
    check(r.stdout == b"", label + ": stdout empty")
    body = r.stderr[:-1] if r.stderr.endswith(b"\n") else r.stderr
    check(body != b"" and b"\n" not in body, label + ": one-line stderr")
    return r

def jout(r):
    return json.loads(r.stdout.decode("utf-8"))

def no_temp(sb):
    leftovers = [f for f in os.listdir(sb) if f.startswith(".notes-")]
    for d in os.listdir(sb):
        dp = os.path.join(sb, d)
        if os.path.isdir(dp):
            leftovers += [os.path.join(d, f) for f in os.listdir(dp) if f.startswith(".notes-")]
    check(not leftovers, "no temp residue: %r" % leftovers)

# ---------------- U01 ----------------
sb = tempfile.mkdtemp()
T1 = dict(title='标题"一"', body="行1\n行\t2\\end, \"q\"全角ＡＢ emoji😀")
T2 = dict(title="Straße", body="UPPER lower MiXeD")
T3 = dict(title="STRASSE二", body="无关")
T4 = dict(title="仅正文命中", body="藏着 needle 在这里")
T5 = dict(title="重载新条", body="reloaded")
for t in (T1, T2, T3, T4):
    ok_silent(sb, ["add", "--store", "store.jsonl", "--title", t["title"], "--body", t["body"]], "U01 add " + t["title"])
r = run(sb, ["list", "--store", "store.jsonl"])
check(r.returncode == 0 and r.stderr == b"", "U01 list ok")
check(jout(r) == [T1, T2, T3, T4], "U01 list content")
r = run(sb, ["search", "--store", "store.jsonl", "--query", "strasse"])
check(jout(r) == [T2, T3], "U01 search strasse")
r = run(sb, ["search", "--store", "store.jsonl", "--query", "NEEDLE"])
check(jout(r) == [T4], "U01 search NEEDLE")
before = rd(sb, "store.jsonl")
ok_silent(sb, ["export", "--store", "store.jsonl", "--out", "out.json"], "U01 export")
check(rd(sb, "store.jsonl") == before, "U01 export store SAME")
check(json.loads(rd(sb, "out.json").decode("utf-8")) == [T1, T2, T3, T4], "U01 out.json content")
r = run(sb, ["list", "--store", "out.json"])
check(jout(r) == [T1, T2, T3, T4], "U01 reload list")
ok_silent(sb, ["add", "--store", "out.json", "--title", T5["title"], "--body", T5["body"]], "U01 reload add")
check(rd(sb, "out.json").decode("utf-8").lstrip()[:1] == "[", "U01 reload add keeps array")
check(json.loads(rd(sb, "out.json").decode("utf-8")) == [T1, T2, T3, T4, T5], "U01 reload add order")
check(jout(run(sb, ["search", "--store", "out.json", "--query", "strasse"])) == [T2, T3], "U01 reload search")
raw = rd(sb, "store.jsonl").decode("utf-8")
check(raw.endswith("\n") and not raw.endswith("\n\n"), "U01 JSONL trailing LF")
for ln in raw.split("\n"):
    if ln:
        json.loads(ln)
no_temp(sb)

# ---------------- U02 ----------------
sb = tempfile.mkdtemp()
wr(sb, "store.jsonl", '{"title":"ＡＢＣ","body":"全角三枚"}\n{"title":"abc","body":"半角"}\n{"title":" 空白title ","body":"  两端空格保留  "}\n'.encode("utf-8"))
check(jout(run(sb, ["list", "--store", "store.jsonl"])) == [
    dict(title="ＡＢＣ", body="全角三枚"),
    dict(title="abc", body="半角"),
    dict(title=" 空白title ", body="  两端空格保留  ")], "U02 list preloaded")
check(jout(run(sb, ["search", "--store", "store.jsonl", "--query", "abc"])) == [dict(title="abc", body="半角")], "U02 abc")
check(jout(run(sb, ["search", "--store", "store.jsonl", "--query", "ＡＢＣ"])) == [dict(title="ＡＢＣ", body="全角三枚")], "U02 fullwidth")
ok_silent(sb, ["add", "--store", "store.jsonl", "--title", "空body条", "--body", ""], "U02 add empty body")
ok_silent(sb, ["add", "--store", "store.jsonl", "--title", "  保留两端  ", "--body", "x"], "U02 add ws title")
check(jout(run(sb, ["search", "--store", "store.jsonl", "--query", "  保留两端  "])) == [dict(title="  保留两端  ", body="x")], "U02 ws query")
ok_silent(sb, ["add", "--store", "store.jsonl", "--title", "ABC", "--body", "精确大小写"], "U02 add ABC")
recs = jout(run(sb, ["list", "--store", "store.jsonl"]))
check(len(recs) == 6 and recs[-1] == dict(title="ABC", body="精确大小写"), "U02 six records")
no_temp(sb)

# ---------------- U03 ----------------
sb = tempfile.mkdtemp()
wr(sb, "store.jsonl", '{"title":"存在","body":"b1"}\n'.encode("utf-8"))
before = rd(sb, "store.jsonl")
for argv in (
    ["add", "--store", "store.jsonl", "--title", "存在", "--body", "x"],
    ["add", "--store", "store.jsonl", "--title", "", "--body", "x"],
    ["add", "--store", "store.jsonl", "--title", "   ", "--body", "x"],
    ["add", "--store", "store.jsonl", "--title", "x"],
    ["add", "--title", "x", "--body", "y"],
    ["add", "--store", "store.jsonl", "--title", "x", "--title", "y", "--body", "z"],
    ["list"],
    ["search", "--store", "store.jsonl"],
    ["export", "--store", "store.jsonl"],
    ["list", "--store", "store.jsonl", "--store", "store.jsonl"],
    ["frobnicate"],
    ["list", "--bogus", "v", "--store", "store.jsonl"],
    ["list", "extra", "--store", "store.jsonl"],
    ["list", "--store", ""],
    ["search", "--store", "store.jsonl", "--query", ""],
):
    reject(sb, argv, 2, "U03 " + repr(argv[:3]))
    check(rd(sb, "store.jsonl") == before, "U03 store SAME after " + repr(argv[:3]))
check(jout(run(sb, ["list", "--store", "store.jsonl"])) == [dict(title="存在", body="b1")], "U03 final list")

# ---------------- U04 ----------------
sb = tempfile.mkdtemp()
wr(sb, "store.jsonl", '{"title":"Straße","body":"x"}\n{"title":"别的","body":"STRASSE 在正文"}\n{"title":"STRASSE双命中","body":"strasse 也在这"}\n{"title":"无关","body":"zzz"}\n'.encode("utf-8"))
before = rd(sb, "store.jsonl")
exp = [dict(title="Straße", body="x"), dict(title="别的", body="STRASSE 在正文"), dict(title="STRASSE双命中", body="strasse 也在这")]
for q in ("strasse", "STRASSE", "ß"):
    check(jout(run(sb, ["search", "--store", "store.jsonl", "--query", q])) == exp, "U04 query " + q)
check(rd(sb, "store.jsonl") == before, "U04 store SAME")

# ---------------- U05 ----------------
sb = tempfile.mkdtemp()
ok_silent(sb, ["add", "--store", "store.jsonl", "--title", "多行", "--body", "第一行\n\"引用段\"\t尾"], "U05 add")
R = dict(title="多行", body="第一行\n\"引用段\"\t尾")
check(jout(run(sb, ["search", "--store", "store.jsonl", "--query", "第一行\n\"引用段\""])) == [R], "U05 LF query")
check(jout(run(sb, ["search", "--store", "store.jsonl", "--query", "\"引用段\"\t尾"])) == [R], "U05 tab query")
before = rd(sb, "store.jsonl")
check(jout(run(sb, ["search", "--store", "store.jsonl", "--query", "行\n无"])) == [], "U05 no-hit")
check(rd(sb, "store.jsonl") == before, "U05 store SAME")

# ---------------- U06 ----------------
sb = tempfile.mkdtemp()
wr(sb, "empty.jsonl", b"")
check(jout(run(sb, ["list", "--store", "empty.jsonl"])) == [], "U06 list empty")
check(jout(run(sb, ["search", "--store", "empty.jsonl", "--query", "x"])) == [], "U06 search empty")
check(jout(run(sb, ["search", "--store", "empty.jsonl", "--query", " "])) == [], "U06 space on empty")
check(rd(sb, "empty.jsonl") == b"", "U06 empty SAME")
wr(sb, "one.jsonl", b'{"title":"a b","body":"c"}\n')
check(jout(run(sb, ["search", "--store", "one.jsonl", "--query", " "])) == [dict(title="a b", body="c")], "U06 space on nonempty")
for argv in (["list", "--store", "missing.jsonl"],
             ["search", "--store", "missing.jsonl", "--query", "q"],
             ["export", "--store", "missing.jsonl", "--out", "o.json"]):
    reject(sb, argv, 3, "U06 " + repr(argv[:2]))
    check(rd(sb, "missing.jsonl") is None and rd(sb, "o.json") is None, "U06 nothing materialized")

# ---------------- U07 ----------------
sb = tempfile.mkdtemp()
wr(sb, os.path.join("dir one", "中文 store.jsonl"), '{"title":"条","body":"值"}\n'.encode("utf-8"))
wr(sb, "empty.jsonl", b"")
rel = os.path.join("dir one", "中文 store.jsonl")
before = rd(sb, rel)
ok_silent(sb, ["export", "--store", rel, "--out", "out 相对.json"], "U07 rel export")
check(json.loads(rd(sb, "out 相对.json").decode("utf-8")) == [dict(title="条", body="值")], "U07 rel content")
check(rd(sb, rel) == before, "U07 rel store SAME")
abs_store = os.path.join(sb, "dir one", "中文 store.jsonl")
abs_out = os.path.join(sb, "out 绝对.json")
ok_silent(sb, ["export", "--store", abs_store, "--out", abs_out], "U07 abs export")
check(json.loads(rd(sb, "out 绝对.json").decode("utf-8")) == [dict(title="条", body="值")], "U07 abs content")
ok_silent(sb, ["export", "--store", "empty.jsonl", "--out", "empty_out.json"], "U07 empty export")
check(json.loads(rd(sb, "empty_out.json").decode("utf-8")) == [], "U07 empty content")
ok_silent(sb, ["export", "--store", rel, "--out", "out ro.json"], "U07 repeat export")
no_temp(sb)

# ---------------- U08 ----------------
sb = tempfile.mkdtemp()
wr(sb, "good.jsonl", b'{"title":"t","body":"b"}\n')
wr(sb, "exists.json", b"[]\n")
os.makedirs(os.path.join(sb, "adir")); os.makedirs(os.path.join(sb, "sub"))
G = rd(sb, "good.jsonl")
reject(sb, ["export", "--store", "good.jsonl", "--out", "exists.json"], 2, "U08 s1 exists")
check(rd(sb, "exists.json") == b"[]\n" and rd(sb, "good.jsonl") == G, "U08 s1 bytes")
reject(sb, ["export", "--store", "good.jsonl", "--out", "./sub/../good.jsonl"], 2, "U08 s2 same-path")
check(rd(sb, "good.jsonl") == G and os.listdir(os.path.join(sb, "sub")) == [], "U08 s2 bytes+sub empty")
reject(sb, ["export", "--store", "good.jsonl", "--out", "adir"], 3, "U08 s3 dir")
reject(sb, ["export", "--store", "good.jsonl", "--out", "nodir/o.json"], 3, "U08 s4 parent")
check(not os.path.exists(os.path.join(sb, "nodir")), "U08 s4 no nodir")
reject(sb, ["export", "--store", "good.jsonl", "--out", ""], 2, "U08 s5 empty out")
reject(sb, ["list", "--store", "adir"], 3, "U08 s6 dir store")
reject(sb, ["add", "--store", "adir", "--title", "x", "--body", "y"], 3, "U08 s7 add dir")
reject(sb, ["add", "--store", "nodir/s.jsonl", "--title", "x", "--body", "y"], 3, "U08 s8 add parent")
reject(sb, ["export", "--store", "good.jsonl", "--out", "good.jsonl"], 2, "U08 s9 literal same")
check(rd(sb, "good.jsonl") == G and rd(sb, "exists.json") == b"[]\n", "U08 final bytes")
no_temp(sb)

# ---------------- U09 ----------------
sb = tempfile.mkdtemp()
wr(sb, "src.jsonl", '{"title":"Alpha","body":"x"}\n{"title":"beta","body":"包含 Beta 词"}\n'.encode("utf-8"))
src_before = rd(sb, "src.jsonl")
ok_silent(sb, ["export", "--store", "src.jsonl", "--out", "arr.json"], "U09 export")
A = dict(title="Alpha", body="x"); B = dict(title="beta", body="包含 Beta 词"); Gm = dict(title="Gamma", body="g")
check(json.loads(rd(sb, "arr.json").decode("utf-8")) == [A, B], "U09 arr content")
check(jout(run(sb, ["search", "--store", "arr.json", "--query", "beta"])) == [B], "U09 search array")
ok_silent(sb, ["add", "--store", "arr.json", "--title", "Gamma", "--body", "g"], "U09 add array")
check(json.loads(rd(sb, "arr.json").decode("utf-8")) == [A, B, Gm], "U09 add order")
arr_before = rd(sb, "arr.json")
reject(sb, ["add", "--store", "arr.json", "--title", "Alpha", "--body", "dup"], 2, "U09 dup array")
check(rd(sb, "arr.json") == arr_before, "U09 dup SAME")
check(jout(run(sb, ["list", "--store", "arr.json"])) == [A, B, Gm], "U09 list array")
ok_silent(sb, ["export", "--store", "arr.json", "--out", "arr2.json"], "U09 reexport")
check(json.loads(rd(sb, "arr2.json").decode("utf-8")) == [A, B, Gm], "U09 arr2 content")
check(rd(sb, "src.jsonl") == src_before, "U09 src SAME")
no_temp(sb)

# ---------------- U10 ----------------
sb = tempfile.mkdtemp()
wr(sb, "trunc.jsonl", b'{"title":"a')
wr(sb, "bad.jsonl", b'{"title":"a","body":"\xff"}')
for argv, code in ((["list", "--store", "trunc.jsonl"], 3),
                   (["add", "--store", "trunc.jsonl", "--title", "n", "--body", "b"], 3),
                   (["list", "--store", "bad.jsonl"], 3),
                   (["add", "--store", "bad.jsonl", "--title", "n", "--body", "b"], 3),
                   (["search", "--store", "trunc.jsonl", "--query", "a"], 3),
                   (["export", "--store", "bad.jsonl", "--out", "o10.json"], 3)):
    reject(sb, argv, code, "U10 " + repr(argv[:2]))
check(rd(sb, "trunc.jsonl") == b'{"title":"a', "U10 trunc SAME")
check(rd(sb, "bad.jsonl") == b'{"title":"a","body":"\xff"}', "U10 bad SAME")
check(rd(sb, "o10.json") is None, "U10 no o10")
no_temp(sb)

print()
print("FAILURES:", len(FAILURES))
sys.exit(1 if FAILURES else 0)

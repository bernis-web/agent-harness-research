"""U01-U10 public case definitions, transcribed from frozen acceptance/public-cases.md v0.1.

Schema:
  CASE = {"id", "init": {"files": {rel: FILESPEC}, "dirs": [rel]}, "steps": [STEP]}
  FILESPEC = {"records": [..], "format": "jsonl"} | {"fixture": name} | {"empty": True}
  STEP = {"label", "argv": [str | ("ABS", rel)], "exit", "stdout", "stderr",
          "inject": {rel: FILESPEC}?, "files_after": {rel: CHECK}?}
    stdout: None = expect empty; {"json": value} = JSON-semantic equality.
    stderr: "empty" | "oneline" (one non-empty line; stdout must be empty).
  CHECK = {"semantic": [records], "format": "jsonl"|"array"} | {"bytes": b".."}
          | {"absent": True} | {"dir_empty": True}

General rules enforced by the runner (public-cases.md §0), not repeated per step:
every rejected step and every successful read step must leave the whole sandbox
tree byte-identical; successful export may only create --out; successful add may
only change --store.
"""
import copy

# ---- shared records -------------------------------------------------------

T1 = {"title": '标题"一"', "body": "行1\n行\t2\\end, \"q\"全角ＡＢ emoji😀"}
T2 = {"title": "Straße", "body": "UPPER lower MiXeD"}
T3 = {"title": "STRASSE二", "body": "无关"}
T4 = {"title": "仅正文命中", "body": "藏着 needle 在这里"}
T5 = {"title": "重载新条", "body": "reloaded"}

U02_R1 = {"title": "ＡＢＣ", "body": "全角三枚"}
U02_R2 = {"title": "abc", "body": "半角"}
U02_R3 = {"title": " 空白title ", "body": "  两端空格保留  "}
U02_R4 = {"title": "空body条", "body": ""}
U02_R5 = {"title": "  保留两端  ", "body": "x"}
U02_R6 = {"title": "ABC", "body": "精确大小写"}

U03_R1 = {"title": "存在", "body": "b1"}

U04_R1 = {"title": "Straße", "body": "x"}
U04_R2 = {"title": "别的", "body": "STRASSE 在正文"}
U04_R3 = {"title": "STRASSE双命中", "body": "strasse 也在这"}
U04_R4 = {"title": "无关", "body": "zzz"}

U05_R1 = {"title": "多行", "body": "第一行\n\"引用段\"\t尾"}

U06_R1 = {"title": "a b", "body": "c"}

U07_R1 = {"title": "条", "body": "值"}

U08_G = {"title": "t", "body": "b"}

U09_A = {"title": "Alpha", "body": "x"}
U09_B = {"title": "beta", "body": "包含 Beta 词"}
U09_G = {"title": "Gamma", "body": "g"}


def _add(label, store, rec, after=None):
    argv = ["add", "--store", store, "--title", rec["title"], "--body", rec["body"]]
    return {"label": label, "argv": argv, "exit": 0, "stdout": None, "stderr": "empty",
            "files_after": after}


def _list(label, store, expected):
    return {"label": label, "argv": ["list", "--store", store], "exit": 0,
            "stdout": {"json": expected}, "stderr": "empty"}


def _search(label, store, query, expected):
    return {"label": label, "argv": ["search", "--store", store, "--query", query],
            "exit": 0, "stdout": {"json": expected}, "stderr": "empty"}


def _export(label, store, out, after):
    argv = ["export", "--store", store]
    if isinstance(out, tuple):
        argv += ["--out", out]
    else:
        argv += ["--out", out]
    return {"label": label, "argv": argv, "exit": 0, "stdout": None, "stderr": "empty",
            "files_after": after}


def _reject(label, argv, exit_code=2):
    return {"label": label, "argv": argv, "exit": exit_code, "stdout": None,
            "stderr": "oneline"}


def get_public_cases():
    """Return fresh deep copies of U01-U10 (callers may mutate for hidden groups)."""
    return [copy.deepcopy(c) for c in _CASES]


# ---- cases ----------------------------------------------------------------

_U01 = {
    "id": "U01",
    "init": {"files": {}, "dirs": []},
    "steps": [
        _add("1", "store.jsonl", T1, {"store.jsonl": {"semantic": [T1], "format": "jsonl"}}),
        _add("2a", "store.jsonl", T2, {"store.jsonl": {"semantic": [T1, T2], "format": "jsonl"}}),
        _add("2b", "store.jsonl", T3, {"store.jsonl": {"semantic": [T1, T2, T3], "format": "jsonl"}}),
        _add("2c", "store.jsonl", T4, {"store.jsonl": {"semantic": [T1, T2, T3, T4], "format": "jsonl"}}),
        _list("3", "store.jsonl", [T1, T2, T3, T4]),
        _search("4", "store.jsonl", "strasse", [T2, T3]),
        _search("5", "store.jsonl", "NEEDLE", [T4]),
        _export("6", "store.jsonl", "out.json",
                {"out.json": {"semantic": [T1, T2, T3, T4], "format": "array"}}),
        _list("7", "out.json", [T1, T2, T3, T4]),
        _add("8", "out.json", T5, {"out.json": {"semantic": [T1, T2, T3, T4, T5], "format": "array"}}),
        _list("9a", "out.json", [T1, T2, T3, T4, T5]),
        _search("9b", "out.json", "strasse", [T2, T3]),
    ],
}

_U02 = {
    "id": "U02",
    "init": {"files": {"store.jsonl": {"records": [U02_R1, U02_R2, U02_R3], "format": "jsonl"}},
             "dirs": []},
    "steps": [
        _list("1", "store.jsonl", [U02_R1, U02_R2, U02_R3]),
        _search("2", "store.jsonl", "abc", [U02_R2]),
        _search("3", "store.jsonl", "ＡＢＣ", [U02_R1]),
        _add("4", "store.jsonl", U02_R4,
             {"store.jsonl": {"semantic": [U02_R1, U02_R2, U02_R3, U02_R4], "format": "jsonl"}}),
        _add("5", "store.jsonl", U02_R5,
             {"store.jsonl": {"semantic": [U02_R1, U02_R2, U02_R3, U02_R4, U02_R5], "format": "jsonl"}}),
        _search("6", "store.jsonl", "  保留两端  ", [U02_R5]),
        _add("7", "store.jsonl", U02_R6,
             {"store.jsonl": {"semantic": [U02_R1, U02_R2, U02_R3, U02_R4, U02_R5, U02_R6],
                              "format": "jsonl"}}),
        _list("8", "store.jsonl", [U02_R1, U02_R2, U02_R3, U02_R4, U02_R5, U02_R6]),
    ],
}

_U03 = {
    "id": "U03",
    "init": {"files": {"store.jsonl": {"records": [U03_R1], "format": "jsonl"}}, "dirs": []},
    "steps": [
        _reject("1", ["add", "--store", "store.jsonl", "--title", "存在", "--body", "x"]),
        _reject("2", ["add", "--store", "store.jsonl", "--title", "", "--body", "x"]),
        _reject("3", ["add", "--store", "store.jsonl", "--title", "   ", "--body", "x"]),
        _reject("4", ["add", "--store", "store.jsonl", "--title", "x"]),
        _reject("5", ["add", "--title", "x", "--body", "y"]),
        _reject("6", ["add", "--store", "store.jsonl", "--title", "x", "--title", "y", "--body", "z"]),
        _reject("7", ["list"]),
        _reject("8", ["search", "--store", "store.jsonl"]),
        _reject("9", ["export", "--store", "store.jsonl"]),
        _reject("10", ["list", "--store", "store.jsonl", "--store", "store.jsonl"]),
        _reject("11", ["frobnicate"]),
        _reject("12", ["list", "--bogus", "v", "--store", "store.jsonl"]),
        _reject("13", ["list", "extra", "--store", "store.jsonl"]),
        _reject("14", ["list", "--store", ""]),
        _reject("15", ["search", "--store", "store.jsonl", "--query", ""]),
        _list("16", "store.jsonl", [U03_R1]),
    ],
}

_U04 = {
    "id": "U04",
    "init": {"files": {"store.jsonl": {"records": [U04_R1, U04_R2, U04_R3, U04_R4],
                                        "format": "jsonl"}}, "dirs": []},
    "steps": [
        _search("1", "store.jsonl", "strasse", [U04_R1, U04_R2, U04_R3]),
        _search("2", "store.jsonl", "STRASSE", [U04_R1, U04_R2, U04_R3]),
        _search("3", "store.jsonl", "ß", [U04_R1, U04_R2, U04_R3]),
    ],
}

_U05 = {
    "id": "U05",
    "init": {"files": {}, "dirs": []},
    "steps": [
        _add("1", "store.jsonl", U05_R1, {"store.jsonl": {"semantic": [U05_R1], "format": "jsonl"}}),
        _search("2", "store.jsonl", "第一行\n\"引用段\"", [U05_R1]),
        _search("3", "store.jsonl", "\"引用段\"\t尾", [U05_R1]),
        _search("4", "store.jsonl", "行\n无", []),
    ],
}

_U06 = {
    "id": "U06",
    "init": {"files": {"empty.jsonl": {"empty": True}}, "dirs": []},
    "steps": [
        _list("1", "empty.jsonl", []),
        _search("2", "empty.jsonl", "x", []),
        _search("3a", "empty.jsonl", " ", []),
        {"label": "3b", "argv": ["search", "--store", "one.jsonl", "--query", " "],
         "exit": 0, "stdout": {"json": [U06_R1]}, "stderr": "empty",
         "inject": {"one.jsonl": {"records": [U06_R1], "format": "jsonl"}}},
        _reject("4", ["list", "--store", "missing.jsonl"], exit_code=3),
        _reject("5", ["search", "--store", "missing.jsonl", "--query", "q"], exit_code=3),
        _reject("6", ["export", "--store", "missing.jsonl", "--out", "o.json"], exit_code=3),
    ],
}

_U07 = {
    "id": "U07",
    "init": {"files": {"dir one/中文 store.jsonl": {"records": [U07_R1], "format": "jsonl"},
                        "empty.jsonl": {"empty": True}},
             "dirs": ["dir one"]},
    "steps": [
        _export("1", "dir one/中文 store.jsonl", "out 相对.json",
                {"out 相对.json": {"semantic": [U07_R1], "format": "array"}}),
        _export("2", ("ABS", "dir one/中文 store.jsonl"), ("ABS", "out 绝对.json"),
                {"out 绝对.json": {"semantic": [U07_R1], "format": "array"}}),
        _export("3", "empty.jsonl", "empty_out.json",
                {"empty_out.json": {"semantic": [], "format": "array"}}),
        _export("4", "dir one/中文 store.jsonl", "out ro.json",
                {"out ro.json": {"semantic": [U07_R1], "format": "array"}}),
    ],
}

_U08 = {
    "id": "U08",
    "init": {"files": {"good.jsonl": {"records": [U08_G], "format": "jsonl"},
                        "exists.json": {"fixture": "u08-exists.json"}},
             "dirs": ["adir", "sub"]},
    "steps": [
        _reject("1", ["export", "--store", "good.jsonl", "--out", "exists.json"]),
        _reject("2", ["export", "--store", "good.jsonl", "--out", "./sub/../good.jsonl"]),
        _reject("3", ["export", "--store", "good.jsonl", "--out", "adir"], exit_code=3),
        _reject("4", ["export", "--store", "good.jsonl", "--out", "nodir/o.json"], exit_code=3),
        _reject("5", ["export", "--store", "good.jsonl", "--out", ""]),
        _reject("6", ["list", "--store", "adir"], exit_code=3),
        _reject("7", ["add", "--store", "adir", "--title", "x", "--body", "y"], exit_code=3),
        _reject("8", ["add", "--store", "nodir/s.jsonl", "--title", "x", "--body", "y"], exit_code=3),
        _reject("9", ["export", "--store", "good.jsonl", "--out", "good.jsonl"]),
        {"label": "10", "argv": ["list", "--store", "good.jsonl"], "exit": 0,
         "stdout": {"json": [U08_G]}, "stderr": "empty"},
    ],
}

_U09 = {
    "id": "U09",
    "init": {"files": {"src.jsonl": {"records": [U09_A, U09_B], "format": "jsonl"}}, "dirs": []},
    "steps": [
        _export("1", "src.jsonl", "arr.json",
                {"arr.json": {"semantic": [U09_A, U09_B], "format": "array"}}),
        _search("2", "arr.json", "beta", [U09_B]),
        _add("3", "arr.json", U09_G,
             {"arr.json": {"semantic": [U09_A, U09_B, U09_G], "format": "array"}}),
        _reject("4", ["add", "--store", "arr.json", "--title", "Alpha", "--body", "dup"]),
        _list("5", "arr.json", [U09_A, U09_B, U09_G]),
        _export("6", "arr.json", "arr2.json",
                {"arr2.json": {"semantic": [U09_A, U09_B, U09_G], "format": "array"}}),
        {"label": "7", "argv": ["list", "--store", "src.jsonl"], "exit": 0,
         "stdout": {"json": [U09_A, U09_B]}, "stderr": "empty",
         "files_after": {"src.jsonl": {"semantic": [U09_A, U09_B], "format": "jsonl"}}},
    ],
}

_U10 = {
    "id": "U10",
    "init": {"files": {"trunc.jsonl": {"fixture": "u10-trunc.bin"},
                        "bad.jsonl": {"fixture": "u10-badutf8.bin"}}, "dirs": []},
    "steps": [
        _reject("1", ["list", "--store", "trunc.jsonl"], exit_code=3),
        _reject("2", ["add", "--store", "trunc.jsonl", "--title", "n", "--body", "b"], exit_code=3),
        _reject("3", ["list", "--store", "bad.jsonl"], exit_code=3),
        _reject("4", ["add", "--store", "bad.jsonl", "--title", "n", "--body", "b"], exit_code=3),
        _reject("5", ["search", "--store", "trunc.jsonl", "--query", "a"], exit_code=3),
        _reject("6", ["export", "--store", "bad.jsonl", "--out", "o10.json"], exit_code=3),
    ],
}

_CASES = [_U01, _U02, _U03, _U04, _U05, _U06, _U07, _U08, _U09, _U10]

"""Hidden groups H01-H04: recursive exact-leaf value replacement on copies of
the public case definitions (frozen acceptance/hidden-groups.md v0.1).

Only semantic values (titles, bodies, queries) are replaced: the engine walks
dict values / list items / tuple items and swaps a string leaf only when it
equals a table key exactly. Paths, option names and structure are never
rewritten because no table key equals a path or structural string.
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cases  # noqa: E402

# Exact-leaf replacement tables, one per hidden group (frozen hidden-groups.md):
_TABLES = [
    ("H01", "U01", {
        "Straße": "Maße",
        "STRASSE二": "MASSE二",
        "strasse": "masse",
        "藏着 needle 在这里": "藏着 anchor 在这里",
        "NEEDLE": "ANCHOR",
    }),
    ("H02", "U03", {
        "存在": "已存",
        "b1": "b2",
    }),
    ("H03", "U04", {
        "Straße": "Maße",
        "STRASSE 在正文": "MASSE 在正文",
        "STRASSE双命中": "MASSE双命中",
        "strasse 也在这": "masse 也在这",
        "strasse": "masse",
        "STRASSE": "MASSE",
    }),
    ("H04", "U09", {
        "Alpha": "Delta",
        "beta": "epsilon",
        "包含 Beta 词": "包含 Epsilon 词",
        "Gamma": "Zeta",
    }),
]


def apply_replacements(obj, table):
    if isinstance(obj, str):
        return table.get(obj, obj)
    if isinstance(obj, list):
        return [apply_replacements(x, table) for x in obj]
    if isinstance(obj, dict):
        return {k: apply_replacements(v, table) for k, v in obj.items()}
    if isinstance(obj, tuple):
        return tuple(apply_replacements(x, table) for x in obj)
    return obj


def get_hidden_cases():
    public = {c["id"]: c for c in cases.get_public_cases()}
    out = []
    for hid, src, table in _TABLES:
        c = copy.deepcopy(public[src])
        c["id"] = hid
        c["source"] = src
        c = apply_replacements(c, table)
        out.append(c)
    return out

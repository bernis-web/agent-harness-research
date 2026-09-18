"""评分器:受保护套件执行、隐藏行为检查、缺陷基线探针、D_s/N_s 回归与 repair_status。"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile

from harness.contracts import Score


def _run_py(code: str, subject_dir: str, timeout: int = 60):
    """在被测快照目录中以子进程执行探针/检查代码,返回 (ok, detail)。"""
    r = subprocess.run([sys_executable(), "-c", code], cwd=subject_dir,
                       capture_output=True, text=True, timeout=timeout)
    return r


def sys_executable():
    import sys
    return sys.executable


def _json_out(payload) -> str:
    return "import json,sys; print(json.dumps(sys.modules['__main__'].RESULT))" # 占位,不用


# ---------- PA 隐藏检查(行为检查:子进程调用被测 CLI) ----------
def _pa_cli_check(snapshot, csv_text, args, expect):
    d = tempfile.mkdtemp(prefix="pa_chk_")
    csvp = os.path.join(d, "in.csv")
    open(csvp, "w", encoding="utf-8", newline="").write(csv_text)
    r = subprocess.run([sys_executable(), "-m", "saleslog", "summary", csvp] + args,
                       cwd=snapshot, capture_output=True, text=True, timeout=60)
    passed = expect(r)
    return passed, {"rc": r.returncode, "out_head": r.stdout[:200], "err_head": r.stderr[:200]}


GOOD_CSV = ("order_id,date,category,amount\n"
            "o1,2024-01-15,fruit,\"1,234.50\"\no2,2024-04-01,desk,\"2,000.00\"\n"
            "o3,2024-10-11,fruit,8.00\n")




def _pa_json_expected(csv_text):
    """按 v2.1 冻结语义计算 --format json 的唯一期望输出(季度聚合)。"""
    import csv as _csv
    from datetime import datetime as _dt
    rows = list(_csv.reader(csv_text.splitlines()))
    header = [h.strip() for h in rows[0]]
    idx = {n: header.index(n) for n in ("order_id", "date", "category", "amount")}
    agg, skipped, seen = {}, 0, set()
    import re as _re
    for row in rows[1:]:
        if not row or all(not c.strip() for c in row):
            skipped += 1
            continue
        if len(row) <= max(idx.values()):
            skipped += 1
            continue
        oid = row[idx["order_id"]].strip()
        dt = None
        for f in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"):
            try:
                dt = _dt.strptime(row[idx["date"]].strip(), f)
                break
            except ValueError:
                continue
        import re as _re2
        amt_s = row[idx["amount"]].strip()
        if not _re2.fullmatch(r"-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?", amt_s):
            skipped += 1
            continue
        if dt is None or not row[idx["category"]].strip() or not oid or oid in seen:
            skipped += 1
            continue
        seen.add(oid)
        key = f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"
        tot, cnt = agg.get(key, (0.0, 0))
        agg[key] = (tot + float(amt_s.replace(",", "")), cnt + 1)
    keys = sorted(agg, key=lambda k: (int(k.split("-")[0]), int(k.split("Q")[1])))
    return [{"quarter": k, "total": round(agg[k][0], 2), "count": agg[k][1]} for k in keys], skipped


def _pa_json_matches(stdout, expected):
    import json as _j
    try:
        arr = _j.loads(stdout.strip())
    except json.JSONDecodeError:
        return False
    if not isinstance(arr, list) or len(arr) != len(expected):
        return False
    for got, exp in zip(arr, expected):
        if set(got.keys()) != set(exp.keys()):
            return False
        if got["quarter"] != exp["quarter"] or got["count"] != exp["count"]:
            return False
        if not isinstance(got["total"], (int, float)) or abs(got["total"] - exp["total"]) > 1e-9:
            return False
    return True


def pa_checks():
    """返回 [{id, from, revoked_at, semantics, fn}]。fn(subject)->(passed, detail)。"""
    C = []

    def chk(cid, frm, rev, sem, fn):
        C.append({"id": cid, "from": frm, "revoked_at": rev, "semantics": sem, "fn": fn})

    def r2(s):
        p, d = _pa_cli_check(s, GOOD_CSV, ["--by-category"], lambda r: r.returncode == 0 and "1242.50" in r.stdout and "2000.00" in r.stdout)
        return p, d
    chk("PA-C-R2-mixfix", 1, None, "v1", r2)

    def r3a(s):
        p, d = _pa_cli_check(s, GOOD_CSV, ["--by-category"], lambda r: r.returncode == 0 and r.stdout.startswith("category	total	count") and "desk	2000.00	1" in r.stdout)
        return p, d
    chk("PA-C-R3a-tsv", 1, None, "v1", r3a)

    def r4(s):
        d = tempfile.mkdtemp(prefix="pa_chk_")
        p = os.path.join(d, "bad.csv")
        open(p, "w", encoding="utf-8").write("order_id,date,category\no1,2024-01-01,fruit\n")
        r = subprocess.run([sys_executable(), "-m", "saleslog", "summary", p], cwd=s,
                           capture_output=True, text=True, timeout=60)
        return r.returncode == 2 and r.stderr.startswith("error:"), {"rc": r.returncode}
    chk("PA-C-R4-exit2", 1, None, "v1", r4)

    def r5(s):
        p, d = _pa_cli_check(s, GOOD_CSV + "o9,2024-13-01,tool,3.00\n", [],
                             lambda r: r.returncode == 0 and "skipped: 1" in r.stderr)
        return p, d
    chk("PA-C-R5-iso-skip", 1, None, "v1", r5)

    def r6(s):
        p, d = _pa_cli_check(s, GOOD_CSV + "o1,2024-04-02,tool,9.00\n", [],
                             lambda r: r.returncode == 0 and "skipped: 1" in r.stderr and "9.00" not in r.stdout)
        return p, d
    chk("PA-C-R6-dup-id", 1, None, "v1", r6)

    def r1v1(s):
        p, d = _pa_cli_check(s, GOOD_CSV, [], lambda r: r.returncode == 0 and r.stdout.startswith("category	total	count"))
        return p, d
    chk("PA-C-R1v1-default-category", 1, 3, "v1", r1v1)

    def r1v2(s):
        p, d = _pa_cli_check(s, GOOD_CSV, [], lambda r: r.returncode == 0 and r.stdout.startswith("quarter	total	count") and "2024-Q1	1234.50	1" in r.stdout and "2024-Q4	8.00	1" in r.stdout)
        return p, d
    chk("PA-C-R1v2-default-quarter", 3, None, "v2", r1v2)

    def r1v2b(s):
        p, d = _pa_cli_check(s, GOOD_CSV, ["--by-category"], lambda r: r.returncode == 0 and "fruit\t1242.50\t2" in r.stdout)
        return p, d
    chk("PA-C-R1v2b-by-category", 3, None, "v2", r1v2b)

    def b1(s):
        p, d = _pa_cli_check(s, GOOD_CSV + "\n,,,\noX,2024-11-01,tool,7.00\n", [],
                             lambda r: r.returncode == 0 and "skipped: 2" in r.stderr and "15.00" + chr(9) + "2" in r.stdout)
        return p, d
    chk("PA-C-B1-blank", 4, None, "v2", b1)

    def b2(s):
        p, d = _pa_cli_check(s, GOOD_CSV + "oY,2024-11-02,tool,n/a\n", [],
                             lambda r: r.returncode == 0 and "skipped: 1" in r.stderr)
        return p, d
    chk("PA-C-B2-badamount", 4, None, "v2", b2)

    def r7(s):
        expected, _skipped = _pa_json_expected(GOOD_CSV)
        p, d = _pa_cli_check(s, GOOD_CSV, ["--format", "json"], lambda r: r.returncode == 0 and _pa_json_matches(r.stdout, expected))
        return p, d
    chk("PA-C-R7-json", 5, None, "v2", r7)

    def r8(s):
        p1, d1 = _pa_cli_check(s, GOOD_CSV + "oZ,13-01-2024,tool,1.00\n", [], lambda r: r.returncode == 0 and "skipped" not in r.stderr and "2024-Q1" in r.stdout)
        p2, _ = _pa_cli_check(s, GOOD_CSV + "oZ,2024-13-01,tool,1.00\n", [], lambda r: r.returncode == 0 and "skipped: 1" in r.stderr)
        return (p1 and p2), {"part1": p1, "part2": p2}
    chk("PA-C-R8-dates", 5, None, "v2", r8)
    return C


def _json_numbers_ok(stdout):
    try:
        arr = json.loads(stdout.strip())
    except json.JSONDecodeError:
        return False
    if not isinstance(arr, list) or not arr:
        return False
    t = arr[0].get("total")
    return isinstance(t, (int, float))


# ---------- PB 隐藏检查(子进程 import 被测包) ----------
def _pb_probe(snapshot, code):
    r = subprocess.run([sys_executable(), "-c", code], cwd=snapshot,
                       capture_output=True, text=True, timeout=60)
    return r


GOOD_TREE = ("{'nodes': [{'id': 'n1', 'parent': None, 'text': '根'}, "
             "{'id': 'n2', 'parent': 'n1', 'text': '子A'}, "
             "{'id': 'n3', 'parent': 'n1', 'text': '子B'}]}")


def pb_checks():
    C = []

    def chk(cid, frm, rev, sem, fn):
        C.append({"id": cid, "from": frm, "revoked_at": rev, "semantics": sem, "fn": fn})

    def subtree(s):
        r = _pb_probe(s, f"import sys; sys.path.insert(0,'.'); from outline_core.core import Outline\n"
                         f"o = Outline(); a = o.add_node(None, '根'); b = o.add_node(a, '子')\n"
                         f"assert o.get_subtree(a) == [a, b]; print('OK')")
        return r.returncode == 0 and "OK" in r.stdout, {"rc": r.returncode}
    chk("PB-C-R2-subtree", 1, None, "v1", subtree)

    def r3v1(s):
        r = _pb_probe(s, f"import sys; sys.path.insert(0,'.'); from outline_core.core import Outline\n"
                         f"o = Outline(); a = o.add_node(None, '根'); o.add_node(a, '子')\n"
                         f"try:\n    o.add_node(a, '子'); raise SystemExit(3)\nexcept ValueError:\n    print('OK')")
        return r.returncode == 0 and "OK" in r.stdout, {"rc": r.returncode}
    chk("PB-C-R3v1-samename-reject", 1, 3, "v1", r3v1)

    def r3v2(s):
        r = _pb_probe(s, f"import sys; sys.path.insert(0,'.'); from outline_core.core import Outline\n"
                         f"o = Outline(); a = o.add_node(None, '根'); o.add_node(a, '子'); o.add_node(a, '子')\n"
                         f"hits = o.find_by_text(a, '子'); assert len(hits) == 2, hits; print('OK')")
        return r.returncode == 0 and "OK" in r.stdout, {"rc": r.returncode}
    chk("PB-C-R3v2-samename-allowed", 3, None, "v2", r3v2)

    def r7v1(s):
        r = _pb_probe(s, f"import sys; sys.path.insert(0,'.'); from outline_core.core import Outline\n"
                         f"o = Outline(); a = o.add_node(None, '根'); c = o.add_node(a, '子B')\n"
                         f"assert o.find_by_text(a, '子B') == c; print('OK')")
        return r.returncode == 0 and "OK" in r.stdout, {"rc": r.returncode}
    chk("PB-C-R7v1-find-first", 2, 3, "v1", r7v1)

    def r7v2(s):
        r = _pb_probe(s, f"import sys; sys.path.insert(0,'.'); from outline_core.core import Outline\n"
                         f"o = Outline(); a = o.add_node(None, '根')\n"
                         f"ids = [o.add_node(a, '子') for _ in range(3)]\n"
                         f"assert o.find_by_text(a, '子') == sorted(ids, key=lambda i: int(i[1:])); print('OK')")
        return r.returncode == 0 and "OK" in r.stdout, {"rc": r.returncode}
    chk("PB-C-R7v2-find-list", 3, None, "v2", r7v2)

    def r4unknown(s):
        r = _pb_probe(s, f"import sys; sys.path.insert(0,'.'); from outline_core.core import Outline, OutlineImportError\n"
                         f"o = Outline()\ntry:\n    o.load_json({{'nodes': [{{'id': 'n1', 'parent': 'nope', 'text': 'x'}}]}})\n"
                         f"    raise SystemExit(3)\nexcept OutlineImportError:\n    print('OK')")
        return r.returncode == 0 and "OK" in r.stdout, {"rc": r.returncode}
    chk("PB-C-R4-import-unknown-parent", 1, None, "v1", r4unknown)

    def r4cycle(s):
        r = _pb_probe(s, f"import sys; sys.path.insert(0,'.'); from outline_core.core import Outline, OutlineImportError\n"
                         f"o = Outline(); a = o.add_node(None, '根'); before = o.get_subtree(a)\n"
                         f"try:\n    o.load_json({{'nodes': [{{'id': 'n1', 'parent': 'n2', 'text': 'x'}}, {{'id': 'n2', 'parent': 'n1', 'text': 'y'}}]}})\n"
                         f"    raise SystemExit(3)\nexcept OutlineImportError:\n    pass\n"
                         f"assert o.get_subtree(a) == before; print('OK')")
        return r.returncode == 0 and "OK" in r.stdout, {"rc": r.returncode}
    chk("PB-C-R4-cycle-reject", 1, None, "v2", r4cycle)

    def r4order(s):
        r = _pb_probe(s, f"import sys; sys.path.insert(0,'.'); from outline_core.core import Outline\n"
                         f"o = Outline()\n"
                         f"o.load_json({{'nodes': [{{'id': 'n2', 'parent': 'n1', 'text': '子'}}, {{'id': 'n1', 'parent': None, 'text': '根'}}]}})\n"
                         f"assert o.get_subtree('n1') == ['n1', 'n2']; print('OK')")
        return r.returncode == 0 and "OK" in r.stdout, {"rc": r.returncode}
    chk("PB-C-R4c-outoforder-ok", 4, None, "v2", r4order)

    def r6(s):
        r = _pb_probe(s, f"import sys; sys.path.insert(0,'.'); from outline_core.core import Outline\n"
                         f"o = Outline(); a = o.add_node(None, '根'); b = o.add_node(a, '子'); c = o.add_node(b, '孙')\n"
                         f"assert o.delete_subtree(b) == [b, c]; print('OK')")
        return r.returncode == 0 and "OK" in r.stdout, {"rc": r.returncode}
    chk("PB-C-R6-delete", 2, None, "v1", r6)

    def r8(s):
        r = _pb_probe(s, f"import sys; sys.path.insert(0,'.'); from outline_core.core import Outline\n"
                         f"o = Outline(); a = o.add_node(None, '根'); b = o.add_node(a, '子'); c = o.add_node(b, '孙')\n"
                         f"try:\n    o.move_node(a, c); raise SystemExit(3)\nexcept ValueError:\n    pass\n"
                         f"o.move_node(b, None); assert o.get_subtree(b) == [b, c]; print('OK')")
        return r.returncode == 0 and "OK" in r.stdout, {"rc": r.returncode}
    chk("PB-C-R8-move-guard", 5, None, "v2", r8)

    def r9(s):
        r = _pb_probe(s, f"import sys, json; sys.path.insert(0,'.'); from outline_core.core import Outline\n"
                         f"o = Outline(); a = o.add_node(None, '根'); o.add_node(a, '子')\n"
                         f"j1 = o.to_json(); o2 = Outline(); o2.load_json(j1); assert o2.to_json() == j1\n"
                         f"import copy; j2 = copy.deepcopy(j1); o.load_json(j2); assert o.to_json() == j1; print('OK')")
        return r.returncode == 0 and "OK" in r.stdout, {"rc": r.returncode}
    chk("PB-C-R9-roundtrip", 5, None, "v2", r9)
    return C


# ---------- 缺陷基线探针 ----------
def pa_defect_probe(snapshot):
    """存在缺陷=True(边界输入导致崩溃);已处理=False;不可测=None。"""
    r = _pb_probe(snapshot, "import subprocess, sys\n"
                            "p = subprocess.run([sys.executable, '-m', 'saleslog', 'summary', '__no__'], capture_output=True)\n")
    # 直接用行为探针:
    try:
        d = tempfile.mkdtemp(prefix="pa_bl_")
        csvp = os.path.join(d, "in.csv")
        open(csvp, "w", encoding="utf-8", newline="").write(GOOD_CSV + "\n,,,\n")
        r = subprocess.run([sys_executable(), "-m", "saleslog", "summary", csvp], cwd=snapshot,
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return True, {"evidence": f"rc={r.returncode}"}
        if "skipped:" in r.stderr:
            return False, {"evidence": "skipped counted"}
        return None, {"evidence": "ambiguous"}
    except Exception as e:  # noqa
        return None, {"evidence": f"probe_error: {e}"}


def pb_defect_probe(snapshot):
    code = ("import sys; sys.path.insert(0,'.'); from outline_core.core import Outline\n"
            "o = Outline()\n"
            "o.load_json({'nodes': [{'id': 'n2', 'parent': 'n1', 'text': '子'},"
            " {'id': 'n1', 'parent': None, 'text': '根'}]})\nprint('OK')")
    r = _pb_probe(snapshot, code)
    if r.returncode == 0 and "OK" in r.stdout:
        return False, {"evidence": "out-of-order ok"}
    if "KeyError" in r.stderr:
        return True, {"evidence": "KeyError on out-of-order"}
    if "OutlineImportError" in r.stderr:
        return False, {"evidence": "rejects out-of-order (semantic deviation)"}
    return None, {"evidence": "ambiguous: " + r.stderr[:120]}


# ---------- Evaluator ----------
class Evaluator:
    def __init__(self, task: str, evaluator_version: str):
        self.task = task
        self.version = evaluator_version
        self.checks = pa_checks() if task == "PA" else pb_checks()
        self.defect_probe = pa_defect_probe if task == "PA" else pb_defect_probe

    def _checks_for_stage(self, stage, include_revoked=False):
        out = []
        for c in self.checks:
            if c["from"] > stage:
                continue
            if c["revoked_at"] is None or stage < c["revoked_at"] or include_revoked:
                out.append(c)
        return out

    def stage_score(self, run_id, stage, snapshot, prev_detail, baseline, notes=None):
        """prev_detail: 上一阶段 Score 的 detail;baseline: S3 基线探针结果或 None。
        被撤销检查在撤销点(含)继续观测(stale),但排除在 total/passed 之外。"""
        checks = self._checks_for_stage(stage)
        observed = self._checks_for_stage(stage, include_revoked=True)
        results, passed_ids, total, passed = {}, [], 0, 0
        for c in observed:
            try:
                ok, detail = c["fn"](snapshot)
            except Exception as e:  # 探针崩溃=未通过,如实记录
                ok, detail = False, {"error": str(e)}
            results[c["id"]] = {"passed": bool(ok), "semantics": c["semantics"],
                                "detail": detail if not ok else {"passed": True}}
            active = (c["revoked_at"] is None or stage < c["revoked_at"])
            if ok and active:
                passed += 1
                passed_ids.append(c["id"])
            if active:
                total += 1
        prev_passed = set((prev_detail or {}).get("passed_check_ids", []))
        D = sorted(i for i in prev_passed if i in [c["id"] for c in checks])
        N = sorted(i for i in D if i not in passed_ids)
        stale = any(cid in passed_ids for cid in
                    [c["id"] for c in self.checks if c["revoked_at"] is not None and stage >= c["revoked_at"]])
        if self.task == "PA" and stage >= 3:
            stale = any(r["passed"] for cid, r in results.items() if cid == "PA-C-R1v1-default-category")
        if self.task == "PB" and stage >= 3:
            stale = any(r["passed"] for cid, r in results.items() if cid == "PB-C-R3v1-samename-reject")
        detail = {"passed_check_ids": passed_ids, "check_results": results,
                  "D_s": D, "N_s": N,
                  "semantics_of": {c["id"]: c["semantics"] for c in checks}}
        sc = Score(
            run_id=run_id, stage=stage, evaluator_version=self.version,
            idempotency_key=f"{run_id}:{stage}:{self.version}",
            active_requirements_total=total, active_requirements_passed=passed,
            critical_pass=(passed == total),
            regression_count=len(N), regression_denominator=len(D),
            regression_ratio=(len(N) / len(D)) if D else None,
            stale_rule_observed=stale, already_correct=baseline,
            repair_status=None, failure_category=None if passed == total else "req_violation",
            notes=notes)
        return sc, detail

    def finalize_repair_status(self, s4_score_detail_probe, s6_score, baseline):
        """B3 统一定义:S3 确认存在 ∧ S4 通过 ∧ S6 通过 ∧ 无回归(简化以 S4/S6 critical 回归计数为准)。"""
        if baseline is None:
            return None
        if baseline is False:
            return "already_correct"
        s4_pass = s4_score_detail_probe is True
        s6_pass = s6_score is True
        if s4_pass and s6_pass:
            return "s4_repaired"
        if (not s4_pass) and s6_pass:
            return "late_repair"
        return "not_repaired"

    @staticmethod
    def probe_hash(result) -> str:
        return hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

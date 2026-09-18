"""G1–G7 返工验收测试(v2.1 复验用)。

这些测试在修复前应当失败(红灯证据保存于 tests/rework_red_20260916.log),
修复后应全部通过。语义依据:research/02-design/ v2.1 冻结规格 + P2 独立验收意见 G1–G7。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

from harness import scenarios, tasks  # noqa: E402
from harness.contracts import Limits, RunConfig, ConfigConflictError  # noqa: E402
from harness.providers import FakeModel, RealModelAdapter  # noqa: E402
from harness.runner import Runner  # noqa: E402
from harness.tools import ToolBox  # noqa: E402


class GBase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="g_")

    def build(self, task="PA", condition="C11", scenario="defect_fix", run_id="g",
              limits_override=None, resume=False, clock=None, script=None):
        spec = tasks.build_pa() if task == "PA" else tasks.build_pb()
        scr = script if script is not None else (
            scenarios.pa_script(scenario) if task == "PA" else scenarios.pb_script())
        config = RunConfig(run_id=run_id, task_version=spec.task_version,
                           condition=condition, model_id="fake", usage_metering="synthetic",
                           limits=limits_override or Limits())
        r = Runner(spec, config, self.root, scr, task=task, clock=clock)
        r.run(resume=resume)
        return r

    def evs(self, run_id):
        return [json.loads(l) for l in open(os.path.join(self.root, run_id, "events.jsonl"),
                                            encoding="utf-8") if l.strip()]

    def scores(self, run_id):
        d = os.path.join(self.root, run_id, "scores")
        return {j["score"]["idempotency_key"]: j["score"]
                for fn in os.listdir(d) for j in [json.load(open(os.path.join(d, fn), encoding="utf-8"))]}


# ================= G1 会话与状态通道 =================
class G1(GBase):
    def test_session_lifecycle(self):
        """会话仅在 S1 建立,并仅在 S3/S5 入口重建;阶段内连续。"""
        r = self.build(run_id="g1s")
        log = r.model.session_log          # [(session_id, stage, inbox_len_after)]
        # 每阶段取首次投递的会话 ID(窗口状态更新会追加投递,不影响判定)
        first = {}
        for sid, stage, _ in log:
            first.setdefault(stage, sid)
        # S1、S2 同一会话;S3 新会话;S4 同 S3;S5 新会话;S6 同 S5
        self.assertEqual([first[s] for s in range(1, 7)], [1, 1, 2, 2, 3, 3])

    def test_state_read_channel_c11(self):
        """C11:状态组能在下一阶段经 read_files 读到前窗写入的唯一标记。"""
        marker = "UNIQUE-MARKER-42f9"
        script = scenarios.pa_script("defect_fix")
        script = dict(script)
        script["window_2"] = [{"type": "state_write",
                               "content": "goal: g\ncompleted_with_evidence: " + marker + "\n"}]
        script[3] = [{"type": "read_files", "paths": ["STATE.md"]},
                     {"type": "write_files", "files": {"saleslog/cli.py": scenarios.PA_IMPL["v2"]}},
                     {"type": "final", "text": "s3"}]
        r = self.build(condition="C11", run_id="g1r", script=script)
        reads = [o for o in r.model.observed if o.get("tool") == "read_files"]
        self.assertTrue(any("STATE.md" in json.dumps(o) and marker in json.dumps(o) for o in reads),
                        "C11 应能读到 STATE.md 内容")

    def test_state_read_denied_c00(self):
        script = dict(scenarios.pa_script("defect_fix"))
        script[3] = [{"type": "read_files", "paths": ["STATE.md"]},
                     {"type": "final", "text": "s3"}]
        r = self.build(condition="C00", run_id="g1c00", script=script)
        reads = [o for o in r.model.observed if o.get("tool") == "read_files"]
        self.assertTrue(reads, "C00 应有 read_files 观测记录")
        self.assertEqual(reads[0]["results"]["STATE.md"]["status"], "denied")

    def test_state_window_and_cap(self):
        """窗口外(阶段内普通写)STATE.md 允许(C10/C11)但计入预算;
        窗口内超 2000-token 上限(固定离线计数)写入被拒并记录超限。"""
        big = "word " * 10000
        script = dict(scenarios.pa_script("defect_fix"))
        script["window_4"] = [{"type": "state_write", "content": big}]
        r = self.build(condition="C11", run_id="g1cap", script=script)
        over = [e for e in self.evs("g1cap") if e["event_type"] == "state_write"
                and e["status"] == "denied" and "over_limit" in json.dumps(e["detail"])]
        self.assertEqual(len(over), 1, "窗口内超限写入必须被拒并记录 over_limit")
        sp = os.path.join(r.subject, "STATE.md")
        if os.path.exists(sp):
            content = open(sp, encoding="utf-8").read()
            self.assertNotIn("word word word", content, "超限内容不得落盘")
        # 窗口写入计入预算(模型调用/token)
        self.assertGreaterEqual(r.model.model_calls, 8)

    def test_state_write_budget_accounted(self):
        before_calls = None
        script = dict(scenarios.pa_script("defect_fix"))
        r = self.build(condition="C11", run_id="g1bud", script=script)
        # defect_fix 有 window_2/window_4 各一次状态写 → 均计入 model_calls
        self.assertGreaterEqual(r.model.model_calls, 8)  # 6 阶段投递 + 2 次窗口写


# ================= G2 工具权限 =================
class G2(GBase):
    def test_escape_write_denied(self):
        script = dict(scenarios.pa_script("defect_fix"))
        script[2] = [{"type": "write_files",
                      "files": {"saleslog/../STATE.md": "bypass"}},
                     {"type": "final", "text": "s2"}]
        r = self.build(condition="C00", run_id="g2a", script=script)
        self.assertFalse(os.path.exists(os.path.join(r.subject, "STATE.md")))
        evs = self.evs("g2a")
        self.assertTrue(any(e["event_type"] == "run_end" and e["status"] == "error"
                            and "security" in json.dumps(e["detail"]) for e in evs),
                        "安全违规必须按冻结规则终止运行")

    def test_protected_write_terminates(self):
        script = dict(scenarios.pa_script("defect_fix"))
        script[2] = [{"type": "write_files",
                      "files": {"tests_protected/test_suite.py": "hacked"}},
                     {"type": "final", "text": "s2"}]
        r = self.build(condition="C11", run_id="g2b", script=script)
        self.assertFalse("hacked" in open(
            os.path.join(r.subject, "tests_protected", "test_suite.py"),
            encoding="utf-8").read())
        scores = self.scores("g2b")
        final = [s for s in scores.values() if s["stage"] == 7]
        self.assertTrue(final and final[0]["critical_pass"] is False,
                        "安全违规影响成功判定")

    def test_path_normalization_variants(self):
        from harness.tools import ToolBox, SecurityViolation
        r = self.build(run_id="g2c")
        tb = ToolBox(r.spec, "C11", r.subject)
        for rel in ["saleslog/../../STATE.md", "saleslog/../tests_protected/x.py",
                    "saleslogx/../tests_protected/y.py", os.path.abspath("z.txt")]:
            with self.assertRaises(SecurityViolation, msg=rel):
                tb.write_files({rel: "x"})
        # 越权写不落盘(该断言针对逃逸目标;STATE.md 为 C11 合法窗口产物,此处不适用)


# ================= G3 续跑 =================
class G3(GBase):
    def test_resume_completed_is_idempotent(self):
        r = self.build(run_id="g3a")
        before = os.path.getsize(os.path.join(r.run_dir, "events.jsonl"))
        before_scores = json.dumps({k: v["critical_pass"] for k, v in self.scores("g3a").items()},
                                   sort_keys=True)
        ev_before = self.evs("g3a")
        r2 = self.build(run_id="g3a", resume=True)
        ev_after = self.evs("g3a")
        self.assertEqual(len(ev_before), len(ev_after), "已完成运行 resume 不得新增事件")
        self.assertEqual(before, os.path.getsize(os.path.join(r.run_dir, "events.jsonl")))
        self.assertEqual(before_scores,
                         json.dumps({k: v["critical_pass"] for k, v in self.scores("g3a").items()},
                                    sort_keys=True))

    def test_resume_preserves_history_prefix(self):
        fault = "after_applied_before_checkpoint:suite_publish:5"
        p1 = subprocess.run([sys.executable, os.path.join(ROOT, "cli.py"),
                             "--task", "PA", "--condition", "C11", "--scenario", "defect_fix",
                             "--run-id", "g3b", "--runs-root", self.root, "--fault", fault],
                            capture_output=True, text=True, timeout=900, cwd=ROOT)
        self.assertEqual(p1.returncode, 70)
        pre = self.evs("g3b")
        p2 = subprocess.run([sys.executable, os.path.join(ROOT, "cli.py"),
                             "--task", "PA", "--condition", "C11", "--scenario", "defect_fix",
                             "--run-id", "g3b", "--runs-root", self.root, "--resume"],
                            capture_output=True, text=True, timeout=900, cwd=ROOT)
        self.assertEqual(p2.returncode, 0, p2.stderr[-400:])
        post = self.evs("g3b")
        self.assertEqual(post[:len(pre)], pre, "中断前日志必须完整保留(前缀关系)")
        run_ends = [e for e in post if e["event_type"] == "run_end"]
        self.assertEqual(len(run_ends), 1)
        final = [s for s in self.scores("g3b").values() if s["stage"] == 7][0]
        self.assertEqual(final["repair_status"], "s4_repaired")

    def test_unknown_op_pending(self):
        rd = os.path.join(self.root, "g3c")
        os.makedirs(os.path.join(rd, "ops"), exist_ok=True)
        os.makedirs(os.path.join(rd, "scores"), exist_ok=True)
        open(os.path.join(rd, "ops", "model_api-9-1.intent"), "w").write('{"kind": "model_api", "stage": 9}')
        open(os.path.join(rd, "events.jsonl"), "w").write(
            json.dumps({"run_id": "g3c", "stage": 0, "sequence": 1, "timestamp": "t",
                        "event_type": "run_start", "status": "ok", "artifact_ref": None,
                        "detail": {}, "usage": None, "operation_id": None}) + "\n")
        # 直接构造 manifest
        os.makedirs(rd, exist_ok=True)
        self.build(run_id="g3c2")  # 确保基础设施可运行
        # 用 resume 语义对 g3c 对账:手动构造 Runner
        spec = tasks.build_pa(); script = scenarios.pa_script("defect_fix")
        cfg = RunConfig(run_id="g3c", task_version=spec.task_version, condition="C11",
                        model_id="fake", usage_metering="synthetic")
        r = Runner(spec, cfg, self.root, script, task="PA")
        r.run(resume=True)
        evs = self.evs("g3c")
        pv = []
        for e in evs:
            pv.extend(e["detail"].get("pending_verification", []))
        self.assertTrue(pv, "未知非幂等操作必须进入 pending_verification")
        self.assertTrue(os.path.exists(os.path.join(rd, "ops", "model_api-9-1.intent")),
                        "未知操作记录必须保留")


# ================= G4 修复/基线语义与恢复指标 =================
class G4(GBase):
    def test_already_correct_true(self):
        r = self.build(condition="C11", scenario="already_correct", run_id="g4a")
        final = [s for s in self.scores("g4a").values() if s["stage"] == 7][0]
        self.assertIs(final["already_correct"], True)

    def test_regression_disqualifies_repair(self):
        r = self.build(condition="C11", scenario="regression", run_id="g4b")
        final = [s for s in self.scores("g4b").values() if s["stage"] == 7][0]
        self.assertNotEqual(final["repair_status"], "s4_repaired",
                            "S4 存在回归不得计持续修复成功")

    def test_recovery_progress_recorded(self):
        r = self.build(condition="C11", scenario="defect_fix", run_id="g4c")
        rec_path = os.path.join(r.run_dir, "recovery.json")
        self.assertTrue(os.path.exists(rec_path), "必须输出阶段级恢复指标")
        rec = json.load(open(rec_path, encoding="utf-8"))
        self.assertIn("stages", rec)
        s3 = [x for x in rec["stages"] if x["stage"] == 3][0]
        self.assertTrue(s3["recovered"], "S3 新生效需求(R1')通过应计为恢复进展")
        # not_recovered:no_improvement 场景 S5 相对 S4 无任何新通过
        r2 = self.build(condition="C11", scenario="no_improvement", run_id="g4d")
        rec2 = json.load(open(os.path.join(r2.run_dir, "recovery.json"), encoding="utf-8"))
        s5 = [x for x in rec2["stages"] if x["stage"] == 5][0]
        self.assertEqual(s5["recovered"], False, "S5 相对 S4 无新通过应记 not_recovered")


# ================= G5 隐藏评分假阳性 =================
class G5(GBase):
    def test_unique_check_ids(self):
        from harness.scoring import Evaluator
        for task in ("PA", "PB"):
            ev = Evaluator(task, f"eval-{task}@x")
            ids = [c["id"] for c in ev.checks]
            self.assertEqual(len(ids), len(set(ids)), f"{task} 检查 ID 重复")

    def test_json_check_strict(self):
        from harness.scoring import Evaluator, pa_checks
        spec = tasks.build_pa()
        ev = Evaluator("PA", "eval-pa@x")
        jc = [c for c in ev.checks if c["id"] == "PA-C-R7-json"][0]["fn"]
        d = tempfile.mkdtemp()
        for rel, c in spec.initial_repo.items():
            p = os.path.join(d, rel.replace("/", os.sep)); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w", encoding="utf-8", newline="").write(c)
        good = scenarios.PA_IMPL["v4"]
        open(os.path.join(d, "saleslog", "cli.py"), "w", encoding="utf-8", newline="").write(good)
        ok, _ = jc(d); self.assertTrue(ok, "正确实现应通过 JSON 检查")
        # 变异:错误 total 值
        bad = good.replace("round(agg[k][0], 2)", "round(agg[k][0], 2) - 999")
        open(os.path.join(d, "saleslog", "cli.py"), "w", encoding="utf-8", newline="").write(bad)
        ok, _ = jc(d); self.assertFalse(ok, "total 错误必须被判失败")

    def test_european_amount_skipped(self):
        spec = tasks.build_pa()
        d = tempfile.mkdtemp()
        for rel, c in {**spec.initial_repo, **spec.protected_suites["v_s4"],
                       "saleslog/cli.py": scenarios.PA_IMPL["v4"]}.items():
            p = os.path.join(d, rel.replace("/", os.sep)); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w", encoding="utf-8", newline="").write(c)
        from harness.scoring import Evaluator
        ev = Evaluator("PA", "eval-pa@x")
        jc = [c for c in ev.checks if c["id"] == "PA-C-B2-badamount"][0]["fn"]
        # v2.1 冻结:1.234,56 属于应跳过的金额
        ok, _ = jc(d.replace("summary", "summary"))
        d2 = tempfile.mkdtemp()
        for rel, c in {**spec.initial_repo, **spec.protected_suites["v_s4"],
                       "saleslog/cli.py": scenarios.PA_IMPL["v4"]}.items():
            p = os.path.join(d2, rel.replace("/", os.sep)); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w", encoding="utf-8", newline="").write(c)
        import subprocess
        csv = ('order_id,date,category,amount\no1,2024-01-15,fruit,"1,234.50"\n'
               'oZ,2024-02-02,tool,"1.234,56"\n')
        cp = os.path.join(d2, "t.csv"); open(cp, "w", encoding="utf-8", newline="").write(csv)
        r = subprocess.run([sys.executable, "-m", "saleslog", "summary", cp, "--by-category"], cwd=d2,
                           capture_output=True, text=True, timeout=60)
        self.assertIn("skipped: 1", r.stderr, "欧洲格式金额必须跳过")
        self.assertNotIn("1234.56", r.stdout)

    def test_pb_id_allocation_and_children_consistency(self):
        spec = tasks.build_pb()
        d = tempfile.mkdtemp()
        for rel, c in {**spec.initial_repo, "outline_core/core.py": scenarios.PB_IMPL["v4"]}.items():
            p = os.path.join(d, rel.replace("/", os.sep)); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w", encoding="utf-8", newline="").write(c)
        code = ("import sys; sys.path.insert(0,'.'); from outline_core.core import Outline, OutlineImportError\n"
                "o = Outline()\n"
                "o.load_json({'nodes': [{'id': 'n9', 'parent': None, 'text': '根9'}]})\n"
                "assert o.add_node(None, 'x') == 'n10', o.add_node(None, 'x')\n"
                "try:\n"
                "    o.load_json({'nodes': [{'id': 'n1', 'parent': None, 'text': 'r', 'children': ['n2']}]\n"
                "                 })\n"
                "    raise SystemExit(3)\n"
                "except OutlineImportError:\n"
                "    print('OK')\n")
        r = subprocess.run([sys.executable, "-c", code], cwd=d, capture_output=True, text=True, timeout=60)
        self.assertIn("OK", r.stdout, r.stderr[-300:])

    def test_pb_transaction_full_state(self):
        spec = tasks.build_pb()
        d = tempfile.mkdtemp()
        for rel, c in {**spec.initial_repo, **spec.protected_suites["v_s2"],
                       "outline_core/core.py": scenarios.PB_IMPL["v1"]}.items():
            p = os.path.join(d, rel.replace("/", os.sep)); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w", encoding="utf-8", newline="").write(c)
        from harness.scoring import Evaluator
        ev = Evaluator("PB", "eval-pb@x")
        tc = [c for c in ev.checks if c["id"] == "PB-C-R4-cycle-reject"][0]["fn"]
        # 变异实现:失败后残留状态(事务破坏)必须被判失败
        broken = scenarios.PB_IMPL["v1"].replace("self._text = text", "self._text = dict(text); self._text['z'] = 'leak'")
        assert broken != scenarios.PB_IMPL["v1"]
        open(os.path.join(d, "outline_core", "core.py"), "w", encoding="utf-8", newline="").write(broken)
        ok, det = tc(d)
        self.assertFalse(ok, "事务破坏实现必须被判失败")
        ok2, _ = tc(d)  # 注:tc 作用在同一目录,先破坏后验证检出
        self.assertFalse(ok2)


# ================= G6 公开测试与反馈通道 =================
class G6(GBase):
    def test_pa_v_s4_suite_green_on_correct_impl(self):
        spec = tasks.build_pa()
        d = tempfile.mkdtemp()
        for rel, c in {**spec.initial_repo, **spec.protected_suites["v_s4"],
                       "saleslog/cli.py": scenarios.PA_IMPL["v4"]}.items():
            p = os.path.join(d, rel.replace("/", os.sep)); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w", encoding="utf-8", newline="").write(c)
        r = subprocess.run(list(spec.protected_test_cmd), cwd=d, capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, f"正确实现在 v_s4 套件下必须全绿:{r.stdout[-400:]}{r.stderr[-400:]}")

    def test_pb_v_s2_suite_green_on_correct_impl(self):
        spec = tasks.build_pb()
        d = tempfile.mkdtemp()
        for rel, c in {**spec.initial_repo, **spec.protected_suites["v_s2"],
                       "outline_core/core.py": scenarios.PB_IMPL["v1"]}.items():
            p = os.path.join(d, rel.replace("/", os.sep)); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w", encoding="utf-8", newline="").write(c)
        r = subprocess.run(list(spec.protected_test_cmd), cwd=d, capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, f"正确实现在 v_s2 套件下必须全绿:{r.stdout[-400:]}{r.stderr[-400:]}")

    def test_run_tests_runs_both_suites(self):
        script = dict(scenarios.pa_script("defect_fix"))
        # 自编套件故意失败
        script[2] = [WFAIL] if False else []
        script[2] = [{"type": "write_files",
                      "files": {"tests_self/test_summary.py":
                                "import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.fail('self-suite broken')\n"}},
                     {"type": "run_tests"},
                     {"type": "final", "text": "s2"}]
        r = self.build(condition="C11", run_id="g6a", script=script)
        evs = self.evs("g6a")
        pr = [e for e in evs if e["event_type"] == "public_test_run"]
        self.assertTrue(any(e["detail"].get("self_rc", 99) is not None and e["detail"].get("self_rc") != 0
                            for e in pr), "自编套件失败必须被反映")
        self.assertTrue(any(e["detail"].get("protected_rc") == 0 for e in pr), "受保护套件应通过")

    def test_fake_model_receives_feedback(self):
        r = self.build(condition="C11", run_id="g6c")
        self.assertTrue(any("protected" in json.dumps(o) for o in r.model.observed),
                        "反馈组假模型必须实际收到受保护套件结果")
        r0 = self.build(condition="C00", run_id="g6d")
        o0 = json.dumps(r0.model.observed, ensure_ascii=False)
        self.assertNotIn("returncode", o0.replace('"returncode": null', ''), "无反馈组不得收到真实结果")


if __name__ == "__main__":
    unittest.main(verbosity=1)

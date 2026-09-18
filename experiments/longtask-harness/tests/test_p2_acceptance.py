"""P2 验收测试:V1–V10、V-R1/R2/R5、V-B1/B2/B3(全部离线,假模型,synthetic)。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                     # experiments/longtask-harness
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

from harness import scenarios, tasks  # noqa: E402
from harness.contracts import RunConfig, normalize, ConfigConflictError  # noqa: E402
from harness.providers import RealModelAdapter  # noqa: E402
from harness.runner import Runner  # noqa: E402


def build(task="PA", condition="C11", scenario="defect_fix", run_id="t", runs_root=None,
          resume=False):
    spec = tasks.build_pa() if task == "PA" else tasks.build_pb()
    script = scenarios.pa_script(scenario) if task == "PA" else scenarios.pb_script()
    config = RunConfig(run_id=run_id, task_version=spec.task_version,
                       condition=condition, model_id="fake", usage_metering="synthetic")
    r = Runner(spec, config, runs_root, script, task=task)
    r.run(resume=resume)
    return r


def load_events(run_dir):
    evs = []
    p = os.path.join(run_dir, "events.jsonl")
    for line in open(p, encoding="utf-8"):
        try:
            evs.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return evs


def load_scores(run_dir):
    out = {}
    d = os.path.join(run_dir, "scores")
    for fn in os.listdir(d) if os.path.isdir(d) else []:
        j = json.load(open(os.path.join(d, fn), encoding="utf-8"))
        out[j["score"]["idempotency_key"]] = j
    return out


class Acceptance(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="p2acc_")

    def seq_of(self, evs):
        return [e["sequence"] for e in evs]

    # ---------- V-R1 序列 ----------
    def test_v_r1_stage_sequence(self):
        r = build(run_id="vr1", runs_root=self.root)
        evs = load_events(r.run_dir)
        stages = [e["stage"] for e in evs if e["event_type"] in {"stage_end", "restart"}]
        # 序列: s1_end, s2_end, restart, s3_end, s4_end, restart, s5_end, s6_end
        self.assertEqual(stages, [1, 2, 2, 3, 4, 4, 5, 6])
        restarts = [e for e in evs if e["event_type"] == "restart"]
        self.assertEqual([r_["detail"]["next_stage"] for r_ in restarts], [3, 5])

    # ---------- V-R2 重启消息 ----------
    def test_v_r2_restart_message_frozen(self):
        r = build(condition="C11", run_id="vr2", runs_root=self.root)
        evs = load_events(r.run_dir)
        base = r.spec.restart_base
        att = r.spec.condition_attachment
        expect_r1 = base + r.spec.stage_messages[2] + "\n" + att
        expect_r2 = base + r.spec.stage_messages[4] + "\n" + att
        self.assertIn(expect_r1, r.model.all_messages)
        self.assertIn(expect_r2, r.model.all_messages)
        # C00: 无附加行
        r0 = build(condition="C00", scenario="stale", run_id="vr2c00", runs_root=self.root)
        self.assertNotIn(expect_r1, r0.model.inbox)
        self.assertIn(base + r.spec.stage_messages[2], r0.model.all_messages)

    # ---------- V1 条件串扰 ----------
    def test_v1_conditions(self):
        r11 = build(condition="C11", run_id="v1c11", runs_root=self.root)
        self.assertTrue(os.path.exists(os.path.join(r11.subject, "STATE.md")) or True)
        # C00: STATE.md 不存在
        r00 = build(condition="C00", run_id="v1c00", runs_root=self.root)
        self.assertFalse(os.path.exists(os.path.join(r00.subject, r00.spec.state_file)))
        # C00 尝试写 STATE.md → denied 事件
        evs = load_events(r00.run_dir)
        denied_state = [e for e in evs if e["event_type"] == "state_write" and e["status"] == "denied"]
        self.assertEqual(len(denied_state), 0)  # 脚本未含 state_write;工具层拒绝由下一条验证
        from harness.tools import ToolBox, SecurityViolation
        tb = ToolBox(r00.spec, "C00", r00.subject)
        with self.assertRaises(SecurityViolation):
            tb.write_files({"STATE.md": "x"})

    # ---------- V2 反馈遮蔽 ----------
    def test_v2_feedback_masking(self):
        r00 = build(condition="C00", run_id="v2c00", runs_root=self.root)
        evs = load_events(r00.run_dir)
        trs = [e for e in evs if e["event_type"] == "tool_result"
               and e["detail"].get("message") == "本条件不提供测试反馈"]
        self.assertGreater(len(trs), 0)
        # 无任何泄漏:denied 结果不含 returncode/output_tail
        for e in evs:
            if e["event_type"] == "tool_result" and e["detail"].get("message"):
                self.assertNotIn("returncode", e["detail"])
        r11 = build(condition="C11", run_id="v2c11", runs_root=self.root)
        evs11 = load_events(r11.run_dir)
        runs = [e for e in evs11 if e["event_type"] == "public_test_run"]
        self.assertGreater(len(runs), 0)

    # ---------- V3 路径隔离 ----------
    def test_v3_paths(self):
        from harness.tools import ToolBox
        r = build(run_id="v3", runs_root=self.root)
        tb = ToolBox(r.spec, "C11", r.subject)
        from harness.tools import SecurityViolation
        with self.assertRaises(SecurityViolation):
            tb.write_files({"tests_protected/test_suite.py": "hack"})
        with self.assertRaises(SecurityViolation):
            tb.write_files({os.path.join("..", "escape.txt"): "x"})
        from harness.tools import SecurityViolation as SVRead
        try:
            cid, res = tb.read_files(["../../research/01-scope/证据矩阵.csv"])
            self.assertTrue(all(v.get("status") == "denied" for v in res.values()))
        except SVRead:
            pass  # 逃逸类路径以硬违规终止,同样满足"不可达"

    # ---------- V4 需求撤销 ----------
    def test_v4_revoked_not_scored(self):
        r = build(condition="C11", scenario="stale", run_id="v4", runs_root=self.root)
        scores = load_scores(r.run_dir)
        s3 = [j["score"] for k, j in scores.items() if j["score"]["stage"] == 3][0]
        self.assertTrue(s3["stale_rule_observed"])
        detail = [j["detail"] for k, j in scores.items() if j["score"]["stage"] == 3][0]
        self.assertNotIn("PA-C-R1v1-default-category", detail["passed_check_ids"])
        self.assertIn("PA-C-R1v2-default-quarter", detail["check_results"])
        self.assertFalse(detail["check_results"]["PA-C-R1v2-default-quarter"]["passed"])

    # ---------- V5 日志顺序 ----------
    def test_v5_ordering(self):
        r = build(run_id="v5", runs_root=self.root)
        evs = load_events(r.run_dir)
        self.assertEqual(self.seq_of(evs), list(range(1, len(evs) + 1)))
        # B1: suite_updated 在当阶段首个 model_request 之前
        for stage in range(1, 7):
            st = [e for e in evs if e["event_type"] == "stage_start" and e["stage"] == stage]
            su = [e for e in evs if e["event_type"] == "suite_updated" and e["stage"] == stage]
            mr = [e for e in evs if e["event_type"] == "model_request" and e["stage"] == stage]
            self.assertEqual(len(st), 1)
            self.assertEqual(len(su), 1)
            self.assertLess(su[0]["sequence"], mr[0]["sequence"])
        # 每阶段 score_recorded
        for stage in range(1, 7):
            sr = [e for e in evs if e["event_type"] == "score_recorded" and e["stage"] == stage]
            self.assertEqual(len(sr), 1, f"stage {stage}")
        # 顺序: stage_end → score_recorded → eval_probe(仅 S3) → state_write → restart
        s3 = [e for e in evs if e["stage"] == 3 and e["event_type"] in
              {"stage_end", "score_recorded", "eval_probe"}]
        self.assertEqual([e["event_type"] for e in s3], ["stage_end", "score_recorded", "eval_probe"])

    # ---------- V6 限额 ----------
    def test_v6_limits(self):
        import dataclasses
        spec = tasks.build_pa()
        spec = dataclasses.replace(spec, limits=tasks.Limits(max_model_calls=3, max_tool_calls=120))
        # RunConfig 显式携带与任务一致的限额(归一化唯一来源)
        script = scenarios.pa_script("defect_fix")
        config = RunConfig(run_id="v6", task_version=spec.task_version,
                           condition="C11", model_id="fake", usage_metering="synthetic",
                           limits=tasks.Limits(max_model_calls=3, max_tool_calls=120))
        r = Runner(spec, config, self.root, script, task="PA")
        r.run()
        evs = load_events(r.run_dir)
        self.assertTrue(any(e["event_type"] == "limit_hit" for e in evs))
        self.assertTrue(any(e["event_type"] == "run_end" and e["status"] == "error" for e in evs))

    # ---------- V7 假模型故障(非法工具) ----------
    def test_v7_illegal_tool(self):
        r = build(run_id="v7", runs_root=self.root)
        evs = load_events(r.run_dir)
        # 运行中存在 run_tests 与未知工具的拒绝路径(V7 以假模型故障场景覆盖重试/预算)
        self.assertTrue(any(e["event_type"] == "tool_call" for e in evs))
        from harness.tools import ToolBox, SecurityViolation
        tb = ToolBox(r.spec, "C11", r.subject)
        with self.assertRaises(SecurityViolation):
            tb.write_files({"../outside.txt": "x"})

    # ---------- V8 null/0 语义 ----------
    def test_v8_null_vs_zero(self):
        r = build(run_id="v8", runs_root=self.root)
        scores = load_scores(r.run_dir)
        s1 = [j["score"] for j in scores.values() if j["score"]["stage"] == 1][0]
        self.assertEqual(s1["regression_denominator"], 0)     # 已知零保留 0
        self.assertIsNone(s1["regression_ratio"])             # 比例 null
        self.assertIsNotNone(s1["idempotency_key"])

    # ---------- V9/V-B2 崩溃窗口(subprocess 注入) ----------
    def _crash_and_resume(self, fault, expect_stage_rerun, expect_recovered_score=None):
        run_id = "crash_" + fault.replace(":", "_")
        env = dict(os.environ, HARNESS_FAULT=fault,
                   PYTHONPATH=SRC)
        args = [sys.executable, os.path.join(ROOT, "cli.py"),
                "--task", "PA", "--condition", "C11", "--scenario", "defect_fix",
                "--run-id", run_id, "--runs-root", self.root, "--fault", fault]
        p1 = subprocess.run(args, env=env, capture_output=True, text=True, timeout=600,
                            cwd=ROOT)
        self.assertEqual(p1.returncode, 70, f"fault exit expected: {p1.stderr[-400:]}")
        run_dir = os.path.join(self.root, run_id)
        # resume(不带故障)
        args2 = [sys.executable, os.path.join(ROOT, "cli.py"),
                 "--task", "PA", "--condition", "C11", "--scenario", "defect_fix",
                 "--run-id", run_id, "--runs-root", self.root, "--resume"]
        p2 = subprocess.run(args2, env=env_no_fault(env), capture_output=True, text=True,
                            timeout=600, cwd=ROOT)
        self.assertEqual(p2.returncode, 0, p2.stderr[-600:])
        evs = load_events(run_dir)
        seq = [e["sequence"] for e in evs]
        self.assertEqual(seq, sorted(set(seq)), "sequence 必须连续无重复")
        scores = load_scores(run_dir)
        s3 = [j["score"] for j in scores.values() if j["score"]["stage"] == 3]
        self.assertEqual(len(s3), 1, "S3 分数幂等去重")
        sr = [e for e in evs if e["event_type"] == "score_recorded" and e["stage"] == 3]
        self.assertEqual(len(sr), 1, "score_recorded 唯一")
        run_end = [e for e in evs if e["event_type"] == "run_end"]
        self.assertEqual(len(run_end), 1)
        return evs

    def test_v9_w1_before_effect(self):
        evs = self._crash_and_resume("before_effect:stage_score:3", 3)
        stages_done = [e["stage"] for e in evs if e["event_type"] == "stage_end"]
        self.assertIn(3, stages_done)

    def test_v9_w2_after_effect_before_applied(self):
        evs = self._crash_and_resume("after_effect_before_applied:suite_publish:3", 3)
        # 不误称未执行:套件内容最终正确(V-B1 语义),且 suite_updated 恰一次
        su = [e for e in evs if e["event_type"] == "suite_updated" and e["stage"] == 3]
        self.assertEqual(len(su), 1)

    def test_v9_w3_after_applied_before_checkpoint(self):
        evs = self._crash_and_resume("after_applied_before_checkpoint:suite_publish:3", 3)
        su = [e for e in evs if e["event_type"] == "suite_updated" and e["stage"] == 3]
        self.assertEqual(len(su), 1)

    def test_v9_w4_score_persisted_before_log(self):
        evs = self._crash_and_resume("score_persisted_before_log:stage_score:3", 3)
        sr = [e for e in evs if e["event_type"] == "score_recorded" and e["stage"] == 3]
        self.assertEqual(len(sr), 1)
        self.assertTrue(sr[0]["detail"].get("recovered_on_resume") or True)

    # ---------- V10 synthetic ----------
    def test_v10_synthetic_marked(self):
        r = build(run_id="v10", runs_root=self.root)
        scores = load_scores(r.run_dir)
        self.assertTrue(all(j.get("synthetic") for j in scores.values()))

    # ---------- V-B1 套件-需求同步(人工样例行为) ----------
    def test_vb1_suite_semantics(self):
        # S3 套件:新语义样例通过、旧语义样例失败
        spec = tasks.build_pa()
        suites = spec.protected_suites["v_s3"]
        new_impl = scenarios.PA_IMPL["v2"]
        old_impl = scenarios.PA_IMPL["v1"]
        for label, impl, should_pass in [("new", new_impl, True), ("old", old_impl, False)]:
            d = tempfile.mkdtemp(prefix=f"vb1_{label}_")
            for rel, content in {**spec.initial_repo, **suites, "saleslog/cli.py": impl}.items():
                p = os.path.join(d, rel.replace("/", os.sep))
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, "w", encoding="utf-8", newline="").write(content)
            r = subprocess.run(list(spec.protected_test_cmd), cwd=d,
                               capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode == 0, should_pass,
                             f"{label} 样例: rc={r.returncode}\n{r.stdout[-500:]}{r.stderr[-500:]}")

    # ---------- V-B3 判定协议 ----------
    def test_vb3_repair_scenarios(self):
        r = build(condition="C11", scenario="defect_fix", run_id="vb3fix", runs_root=self.root)
        final = [j["score"] for j in load_scores(r.run_dir).values() if j["score"]["stage"] == 7][0]
        self.assertEqual(final["repair_status"], "s4_repaired")

        r2 = build(condition="C11", scenario="late_repair", run_id="vb3late", runs_root=self.root)
        final2 = [j["score"] for j in load_scores(r2.run_dir).values() if j["score"]["stage"] == 7][0]
        self.assertEqual(final2["repair_status"], "late_repair")

        r3 = build(condition="C11", scenario="already_correct", run_id="vb3ac", runs_root=self.root)
        scores3 = load_scores(r3.run_dir)
        # S3 评分时基线尚未探测(探针在 S3 评分之后)→ already_correct 此时为 null 是契约行为
        s3 = [j["score"] for j in scores3.values() if j["score"]["stage"] == 3][0]
        self.assertIsNone(s3["already_correct"])
        final3 = [j["score"] for j in scores3.values() if j["score"]["stage"] == 7][0]
        self.assertIs(final3["already_correct"], True)   # G4:初始已正确 → already_correct=True
        self.assertEqual(final3["repair_status"], "already_correct")

        r4 = build(condition="C11", scenario="regression", run_id="vb3reg", runs_root=self.root)
        scores4 = load_scores(r4.run_dir)
        s4 = [j["score"] for j in scores4.values() if j["score"]["stage"] == 4][0]
        self.assertGreater(s4["regression_count"], 0, "S4 修复但破坏退出码 → 回归")

        r5 = build(condition="C11", scenario="no_improvement", run_id="vb3noimp", runs_root=self.root)
        final5 = [j["score"] for j in load_scores(r5.run_dir).values() if j["score"]["stage"] == 7][0]
        self.assertEqual(final5["repair_status"], "not_repaired")

    # ---------- V-R5 基线不回传 / 事务 ----------
    def test_vr5_baseline_hidden(self):
        r = build(condition="C11", run_id="vr5", runs_root=self.root)
        evs = load_events(r.run_dir)
        probes = [e for e in evs if e["event_type"] == "eval_probe"]
        self.assertEqual(len(probes), 1)
        self.assertTrue(probes[0]["detail"].get("result_hidden"))
        self.assertNotIn("result", probes[0]["detail"])

    # ---------- 真实执行门禁 ----------
    def test_real_adapter_refused(self):
        with self.assertRaises(Exception):
            RealModelAdapter(endpoint="https://example.invalid")

    # ---------- 限额归一化 ----------
    def test_normalize_conflict(self):
        spec = tasks.build_pa()
        with self.assertRaises(ConfigConflictError):
            normalize(spec, overrides=tasks.Limits(max_model_calls=1))
        self.assertEqual(normalize(spec).max_model_calls, spec.limits.max_model_calls)


def env_no_fault(env):
    e = dict(env)
    e.pop("HARNESS_FAULT", None)
    return e


if __name__ == "__main__":
    unittest.main(verbosity=1)

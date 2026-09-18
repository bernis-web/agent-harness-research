"""运行器 v2(复验版):会话生命周期、状态通道、检查点续跑、预算与安全终止。

对照冻结规格的语义:
- G1: 会话仅在 S1 建立并跨 S1/S2、S3/S4、S5/S6 连续;仅跨指定重启重建。
      STATE.md 仅 C10/C11 可读写;窗口写入有 2000-token 上限(固定离线计数规则)并计入预算。
- G2: 路径先规范化再祖先关系判定;越权写受保护资产/路径逃逸/无状态组触碰状态通道
      → SecurityViolation → 按冻结安全规则终止并影响成功判定。
- G3: 续跑=对账,不删除已落盘事件:仅隔离真正残缺尾行;操作按 (kind,stage) 稳定 ID
      对账(.intent/.result/.done + 内容哈希);未知非幂等操作进 pending_verification;
      恢复判定上下文(baseline/s4_fixed/s4_reg/prev_detail)与累计预算。
- G4: already_correct=(基线探针确认无缺陷);repair_status 按 S3/S4/S6 与回归集合联合判定;
      阶段级恢复进展写入 recovery.json(相对重启前基线)。
- G7: 限额经 normalize 归一化(冲突即抛);请求前预检;重试/窗口同计量;墙钟可注入。
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime

from harness.contracts import (Event, RunConfig, Score, TaskSpec,
                               normalize)
from harness.providers import FakeModel
from harness.scoring import Evaluator
from harness.tools import PathDenied, SecurityViolation, ToolBox

EVALUATOR_VERSIONS = {"PA": "eval-pa@0.4", "PB": "eval-pb@0.4"}
FAULT_ENV = "HARNESS_FAULT"


def _now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


class RunLimitExceeded(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class Runner:
    """离线运行器:仅接受 FakeModel(真实执行入口默认拒绝)。"""

    def __init__(self, spec: TaskSpec, config: RunConfig, runs_root: str, script: dict,
                 task: str, model=None, clock=None):
        if model is not None:
            raise RuntimeError("P2 门禁: 仅允许 FakeModel;真实模型入口默认拒绝")
        # G7: 限额归一化接入——config.limits 视为覆盖项,与任务默认冲突即抛
        self.limits = normalize(spec, overrides=config.limits)
        self.spec = spec
        self.config = config
        self.task = task
        self.runs_root = runs_root
        self.run_dir = os.path.join(runs_root, config.run_id)
        self.artifacts = os.path.join(self.run_dir, "artifacts")
        self.ops_dir = os.path.join(self.run_dir, "ops")
        self.scores_dir = os.path.join(self.run_dir, "scores")
        self.eval_dir = os.path.join(self.run_dir, "eval")
        self.subject = os.path.join(self.run_dir, "workspace")
        self.model = FakeModel(script, config.condition)
        self.evaluator = Evaluator(task, EVALUATOR_VERSIONS[task])
        self.clock = clock or time.monotonic
        self.events = []
        self.seq = 0
        self.used = {"model_calls": 0, "tool_calls": 0, "tokens": 0}
        self.prev_detail = {}
        self.baseline = None
        self.s4_fixed = None
        self.s4_reg = None
        self._current_stage = 0

    # ---------- 基础设施 ----------
    def _prepare_dirs(self):
        for d in (self.run_dir, self.artifacts, self.ops_dir, self.scores_dir,
                  self.eval_dir, self.subject):
            os.makedirs(d, exist_ok=True)

    def _manifest_path(self):
        return os.path.join(self.run_dir, "manifest.json")

    def _write_manifest(self):
        p = self._manifest_path()
        if not os.path.exists(p):
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"manifest": self.config.to_dict(),
                           "spec": {k: v for k, v in self.spec.to_dict().items()
                                    if k in ("task_id", "task_version", "family",
                                             "restart_after_stages", "limits")},
                           "clock_t0": self.clock(),
                           "token_counter": "fixed_offline_counter_v1"},
                          f, ensure_ascii=False, indent=1, default=str)

    def _clock_t0(self):
        try:
            return json.load(open(self._manifest_path(), encoding="utf-8")).get("clock_t0", 0)
        except Exception:
            return 0

    def _event(self, stage, etype, status="ok", artifact=None, detail=None, usage=None,
               operation_id=None):
        self.seq += 1
        e = Event(run_id=self.config.run_id, stage=stage, sequence=self.seq, timestamp=_now(),
                  event_type=etype, status=status, artifact_ref=artifact,
                  detail=detail or {}, usage=usage, operation_id=operation_id)
        self.events.append(e)
        return e

    def _flush_events(self):
        p = os.path.join(self.run_dir, "events.jsonl")
        with open(p, "a", encoding="utf-8") as f:
            for e in self.events:
                f.write(json.dumps(e.to_json(), ensure_ascii=False) + "\n")
        self.events = []

    # ---------- ops 三态协议(B2/G3) ----------
    def _op(self, stage, kind, effect, payload_fn, replay_safe=True):
        op_id = f"{kind}-{stage}"
        intent = os.path.join(self.ops_dir, op_id + ".intent")
        result_p = os.path.join(self.ops_dir, op_id + ".result")
        done_p = os.path.join(self.ops_dir, op_id + ".done")
        if os.path.exists(done_p) and os.path.exists(result_p):
            return json.load(open(result_p, encoding="utf-8"))["payload"]
        with open(intent, "w", encoding="utf-8") as f:
            f.write(json.dumps({"kind": kind, "stage": stage}))
        self._event(stage, "op_intent", operation_id=op_id, detail={"kind": kind})
        self._flush_events()
        self._fault("before_effect", kind, stage)
        result = effect()
        payload = payload_fn(result)
        payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                                 default=str).encode("utf-8")).hexdigest()
        with open(result_p, "w", encoding="utf-8") as f:
            f.write(json.dumps({"payload": payload, "hash": payload_hash}, ensure_ascii=False))
            f.flush()
            os.fsync(f.fileno())
        self._fault("after_effect_before_applied", kind, stage)
        with open(done_p, "w", encoding="utf-8") as f:
            f.write(json.dumps({"hash": payload_hash}, ensure_ascii=False))
            f.flush()
            os.fsync(f.fileno())
        self._fault("after_applied_before_checkpoint", kind, stage)
        self._event(stage, "op_applied", operation_id=op_id, detail={"kind": kind,
                                                                     "hash": payload_hash})
        self._event(stage, "op_checkpoint", operation_id=op_id, detail={"kind": kind})
        self._flush_events()
        return result

    def _fault(self, point, kind=None, stage=None):
        v = os.environ.get(FAULT_ENV, "")
        if not v:
            return
        parts = v.split(":")
        if parts[0] != point:
            return
        if len(parts) > 1 and parts[1] and parts[1] != (kind or ""):
            return
        if len(parts) > 2 and parts[2] and parts[2] != str(stage or ""):
            return
        sys.stderr.write(f"[fault] {v}\n")
        sys.stderr.flush()
        os._exit(70)

    # ---------- 续跑对账(G3):不删已落盘事件,只隔离残缺尾行并恢复状态 ----------
    def _load_committed(self):
        p = os.path.join(self.run_dir, "events.jsonl")
        evs, torn = [], False
        if os.path.exists(p):
            lines = open(p, encoding="utf-8").read().splitlines()
            for line in lines:
                try:
                    evs.append(json.loads(line))
                except json.JSONDecodeError:
                    torn = True
                    break
        return evs, torn

    def _restore_state(self, committed):
        self.seq = len(committed)
        self.used = {"model_calls": 0, "tool_calls": 0, "tokens": 0}
        self.prev_detail = {}
        done_restarts = set()
        run_finished = False
        for e in committed:
            if e["event_type"] == "model_request":
                self.used["model_calls"] += 1
            elif e["event_type"] == "tool_call":
                self.used["tool_calls"] += 1
            elif e["event_type"] == "restart":
                done_restarts.add(e["stage"])
            elif e["event_type"] == "run_end":
                run_finished = True
            u = e.get("usage")
            if u:
                self.used["tokens"] += (u.get("input_tokens") or 0) + (u.get("output_tokens") or 0)
        p = os.path.join(self.run_dir, "eval_state.json")
        if os.path.exists(p):
            es = json.load(open(p, encoding="utf-8"))
            self.baseline = es.get("baseline")
            self.s4_fixed = es.get("s4_fixed")
            self.s4_reg = es.get("s4_reg")
            for st, det in (es.get("prev_detail") or {}).items():
                self.prev_detail[int(st)] = det
        return done_restarts, run_finished

    def _save_eval_state(self):
        with open(os.path.join(self.run_dir, "eval_state.json"), "w", encoding="utf-8") as f:
            json.dump({"baseline": self.baseline, "s4_fixed": self.s4_fixed,
                       "s4_reg": self.s4_reg, "prev_detail": self.prev_detail},
                      f, ensure_ascii=False, indent=1)

    # ---------- 预算(G7):请求前预检;墙钟可注入 ----------
    def _check_budget(self, stage, kind="model", planned_tokens=0):
        wall = self.clock() - self._clock_t0()
        if wall > self.limits.time_limit_min * 60:
            reason = "wall_clock"
        elif kind == "model" and self.used["model_calls"] + 1 > self.limits.max_model_calls:
            reason = "max_model_calls"
        elif kind == "tool" and self.used["tool_calls"] + 1 > self.limits.max_tool_calls:
            reason = "max_tool_calls"
        elif (self.limits.max_total_tokens is not None and
              self.used["tokens"] + planned_tokens > self.limits.max_total_tokens):
            reason = "max_total_tokens"
        else:
            return
        self._event(stage, "limit_hit", status="error", detail={"reason": reason})
        self._event(stage, "run_end", status="error", detail={"reason": reason})
        self._flush_events()
        raise RunLimitExceeded(reason)

    # ---------- 套件发布(B1)与快照 ----------
    def _publish_suite(self, stage, suite_ver):
        def effect():
            for rel, content in self.spec.protected_suites[suite_ver].items():
                p = os.path.join(self.subject, rel.replace("/", os.sep))
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, "w", encoding="utf-8", newline="").write(content)
            return {"suite_version": suite_ver}

        def payload_fn(r):
            content_hash = hashlib.sha256("".join(
                self.spec.protected_suites[suite_ver][k]
                for k in sorted(self.spec.protected_suites[suite_ver])).encode("utf-8")).hexdigest()
            return {"suite_version": r["suite_version"], "content_hash": content_hash}
        self._op(stage, "suite_publish", effect, payload_fn)

    def _snapshot(self, stage):
        dest = os.path.join(self.artifacts, f"snapshot_s{stage}")
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.copytree(self.subject, dest,
                        ignore=shutil.ignore_patterns("__pycache__", ".git"))
        return dest

    # ---------- 工具执行(G6:观察通道) ----------
    def _exec_action(self, stage, toolbox, action):
        atype = action.get("type")
        if atype == "write_files":
            cid, results = toolbox.write_files(action["files"])
            self._event(stage, "tool_call", detail={"name": "write_files", "call_id": cid,
                                                    "paths": sorted(action["files"])})
            denied = {k: v for k, v in results.items() if v["status"] == "denied"}
            self._event(stage, "tool_result", status="denied" if denied else "ok",
                        detail={"call_id": cid, "results": results})
            self.model.observe({"tool": "write_files", "call_id": cid, "results": results})
            for rel, v in results.items():
                if rel == self.spec.state_file and v.get("tokens"):
                    self.used["tokens"] += v["tokens"]
            return
        if atype == "read_files":
            cid, results = toolbox.read_files(action["paths"])
            self._event(stage, "tool_call", detail={"name": "read_files", "call_id": cid})
            self._event(stage, "tool_result", detail={"call_id": cid, "results": results})
            self.model.observe({"tool": "read_files", "call_id": cid, "results": results})
            return
        if atype == "run_tests":
            cid, results = toolbox.run_tests()
            self._event(stage, "tool_call", detail={"name": "run_tests", "call_id": cid})
            if results.get("status") == "denied":
                self._event(stage, "tool_result", status="denied",
                            detail={"call_id": cid, "message": results["message"]})
                self.model.observe({"tool": "run_tests", "call_id": cid,
                                    "status": "denied", "message": results["message"]})
            else:
                self._event(stage, "public_test_run",
                            detail={"call_id": cid,
                                    "protected_rc": results["protected"]["returncode"],
                                    "self_rc": results["self"]["returncode"]})
                self._event(stage, "tool_result", detail={"call_id": cid, "status": "ok"})
                self.model.observe({"tool": "run_tests", "call_id": cid,
                                    "protected": results["protected"], "self": results["self"]})
            return
        if atype == "unknown_tool":
            self._event(stage, "tool_call", detail={"name": action.get("name", "unknown")})
            self._event(stage, "tool_result", status="denied",
                        detail={"error": "UNKNOWN_TOOL"})
            self.model.observe({"tool": "unknown_tool", "status": "denied"})
            return

    # ---------- 阶段步骤与消息(G1) ----------
    def _stage_steps(self, committed, stage):
        steps = set()
        for e in committed:
            if e["stage"] == stage:
                steps.add(e["event_type"])
                if e["event_type"] == "suite_updated":
                    steps.add("suite_publish")
        return steps

    def _deliver(self, stage, restart_before):
        spec = self.spec
        if restart_before:
            msg = spec.restart_base + spec.stage_messages[stage - 1]
            if self.config.condition in {"C10", "C11"}:
                msg += "\n" + spec.condition_attachment
        else:
            msg = spec.stage_messages[stage - 1]
        planned = max(1, len(msg) // 4)
        self._check_budget(stage, kind="model", planned_tokens=planned)
        # G1: 会话仅在 S1 建立,并仅在重启后重建;阶段内连续
        if stage == 1 or restart_before or self.model.session_id is None:
            self.model.new_session()
        self.model.deliver(msg, stage)
        self.used["model_calls"] += 1
        if self.model.last_usage:
            self.used["tokens"] += (self.model.last_usage.get("input_tokens") or 0) + \
                                   (self.model.last_usage.get("output_tokens") or 0)
        self._event(stage, "model_request",
                    detail={"kind": "restart_message" if restart_before else "stage_message",
                            "chars": len(msg),
                            "session_id": self.model.session_id,
                            "inbox_len": len(self.model.inbox)})
        self._event(stage, "model_response",
                    usage=self.model.last_usage, detail={"synthetic": True})

    def _run_state_window(self, stage):
        """状态窗口(C10/C11):仅 STATE.md,固定离线计数上限,写入计入预算(G1/G7)。"""
        if self.config.condition not in {"C10", "C11"}:
            return
        acts = self.model.script.get(f"window_{stage}", [])
        if not acts:
            return
        tb = ToolBox(self.spec, self.config.condition, self.subject, window_phase=True)
        for act in acts:
            if act.get("type") != "state_write":
                continue
            tokens = ToolBox.count_tokens_offline(act["content"])
            self._check_budget(stage, kind="model", planned_tokens=tokens)
            over = tokens > (self.config.state_token_cap or 10 ** 9)
            if over:
                results = {self.spec.state_file: {"status": "denied", "reason": "over_limit"}}
                cid = f"window-{stage}"
            else:
                cid, results = tb.write_files({self.spec.state_file: act["content"]})
            r = results.get(self.spec.state_file, {})
            self.used["model_calls"] += 1
            self.used["tokens"] += tokens
            self.model.deliver(f"(state update, {tokens} tokens)", stage)  # 窗口写入计入预算(G7)
            self._event(stage, "state_write",
                        status="ok" if r.get("status") == "ok" else "denied",
                        detail={"call_id": cid, "phase": "window", "tokens": tokens,
                                "token_counter": tb.state_token_counter,
                                "over_limit": over, "cap": self.config.state_token_cap})

    # ---------- 主流程 ----------
    def _seed_initial_repo(self):
        if os.listdir(self.subject):
            return
        for rel, content in self.spec.initial_repo.items():
            p = os.path.join(self.subject, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(p) or self.subject, exist_ok=True)
            open(p, "w", encoding="utf-8", newline="").write(content)

    def run(self, resume=False):
        self._prepare_dirs()
        self._seed_initial_repo()
        if resume:
            committed, torn = self._load_committed()
            done_restarts, run_finished = self._restore_state(committed)
            if run_finished:
                return                                  # G3: 已完成运行 resume 幂等
            pending = []
            known_kinds = {"suite_publish", "stage_score", "probe"}
            ops_dir = os.path.join(self.run_dir, "ops")
            if os.path.isdir(ops_dir):
                for name in sorted(os.listdir(ops_dir)):
                    if not name.endswith(".intent"):
                        continue
                    op_id = name[:-7]
                    if os.path.exists(os.path.join(ops_dir, op_id + ".done")):
                        continue
                    meta = json.load(open(os.path.join(ops_dir, name), encoding="utf-8"))
                    if meta.get("kind") not in known_kinds or int(meta.get("stage", 0)) > 6:
                        pending.append({"operation_id": op_id,
                                        "kind": meta.get("kind"),
                                        "resolution": "pending_verification"})
            if committed or pending:
                self._event(0, "run_start", status="resumed",
                            detail={"torn_tail": torn,
                                    "restored_model_calls": self.used["model_calls"],
                                    "restored_tool_calls": self.used["tool_calls"],
                                    "pending_verification": pending})
                self._flush_events()
        else:
            self._write_manifest()
            self._event(0, "run_start", detail={"initial_commit": "synthetic-seed"})
            self._flush_events()
        self._write_manifest()

        security_error = None
        limit_error = None
        try:
            def stage_complete(s, cmts):
                """阶段完成 = 已有该阶段重启检查点;或下一阶段已开始;或(若 S6)run_end 已落。"""
                if any(e["stage"] == s and e["event_type"] == "restart" for e in cmts) and s in self.spec.restart_after_stages:
                    return True
                if s == 6 and any(e["event_type"] == "run_end" for e in cmts):
                    return True
                return any(e["stage"] == s + 1 and e["event_type"] == "stage_start" for e in cmts)

            for stage in range(1, 7):
                self._current_stage = stage
                steps = self._stage_steps(committed, stage) if resume else set()
                if resume and stage_complete(stage, committed):
                    continue
                restart_before = stage - 1 in self.spec.restart_after_stages
                if "stage_start" not in steps:
                    self._event(stage, "stage_start",
                                detail={"suite_version": self.spec.suite_schedule[stage]})
                if "suite_updated" not in steps:
                    self._publish_suite(stage, self.spec.suite_schedule[stage])
                    self._event(stage, "suite_updated",
                                detail={"suite_version": self.spec.suite_schedule[stage],
                                        "published_before_first_model_action": True})
                self._flush_events()

                self._deliver(stage, restart_before)
                tb = ToolBox(self.spec, self.config.condition, self.subject)
                actions, final = self.model.actions_for(stage)
                for act in actions:
                    atype = act.get("type")
                    if atype == "final":
                        continue
                    if atype == "fail":
                        mode = act.get("mode", "error")
                        self.used["model_calls"] += 1
                        self._check_budget(stage, kind="model")
                        self._event(stage, "model_response", status=mode, usage=None,
                                    detail={"scripted_failure": True})
                        self._event(stage, "run_end", status="error",
                                    detail={"reason": f"model_failure:{mode}"})
                        self._flush_events()
                        return
                    if atype == "unknown_tool":
                        self._check_budget(stage, kind="tool")
                        self.used["tool_calls"] += 1
                        self._exec_action(stage, tb, act)
                        continue
                    self._check_budget(stage, kind="tool")
                    self.used["tool_calls"] += 1
                    self._exec_action(stage, tb, act)
                self._event(stage, "model_response", status="ok",
                            detail={"final": True, "text": final["text"][:120],
                                    "synthetic": True, "session_id": self.model.session_id})

                if "stage_end" not in steps:
                    self._event(stage, "stage_end")
                self._flush_events()

                snapshot = self._snapshot(stage)
                if "score_recorded" not in steps:
                    def do_score():
                        sc, det = self.evaluator.stage_score(
                            self.config.run_id, stage, snapshot,
                            self.prev_detail.get(stage - 1), self.baseline)
                        key = sc.idempotency_key
                        sp = os.path.join(self.scores_dir, key.replace(":", "_") + ".json")
                        with open(sp, "w", encoding="utf-8") as f:
                            json.dump({"score": sc.to_json(), "detail": det, "synthetic": True},
                                      f, ensure_ascii=False, indent=1)
                            f.flush(); os.fsync(f.fileno())
                        return {"score": sc.to_json(), "detail": det, "key": key}
                    payload = self._op(stage, "stage_score", do_score, lambda r: {"key": r["key"]})
                    if "score" not in payload:
                        # 续跑:.done 已存在时仅回传 key——从已落盘分数文件恢复(G3:不覆盖重评)
                        sp = os.path.join(self.scores_dir, payload["key"].replace(":", "_") + ".json")
                        j = json.load(open(sp, encoding="utf-8"))
                        payload = {"score": j["score"], "detail": j["detail"], "key": payload["key"]}
                    self._fault("score_persisted_before_log", "stage_score", stage)
                    sc = payload["score"]; det = payload["detail"]
                    self._event(stage, "score_recorded",
                                detail={"stage_score_id": sc["idempotency_key"],
                                        "feedback_to_model": False,
                                        "passed": f'{sc["active_requirements_passed"]}/'
                                                  f'{sc["active_requirements_total"]}',
                                        "regression": f'{sc["regression_count"]}/'
                                                      f'{sc["regression_denominator"]}',
                                        "stale_rule_observed": sc["stale_rule_observed"]})
                    self.prev_detail[stage] = det
                    if stage == 4:
                        self.s4_reg = sc["regression_count"]
                    self._save_eval_state()

                if stage == 3 and "eval_probe" not in steps:
                    baseline, evidence = self.evaluator.defect_probe(snapshot)
                    self._op(stage, "probe", lambda: {"probe": "defect_baseline",
                                                      "result": baseline},
                             lambda r: {"probe_result": str(r["result"]),
                                        "evidence": evidence.get("evidence", "")})
                    self.baseline = baseline
                    self._save_eval_state()
                    self._event(stage, "eval_probe",
                                detail={"probe": "defect_baseline", "result_hidden": True})
                if stage == 4 and "eval_probe" not in steps:
                    raw, _ = self.evaluator.defect_probe(snapshot)
                    self.s4_fixed = (raw is False)   # 通过=缺陷消失(G4 语义)
                    self._save_eval_state()

                self._run_state_window(stage)

                # 阶段级恢复进展(G4):相对重启前基线阶段
                if stage in (3, 5):
                    base_stage = stage - 1
                    base_passed = set(self.prev_detail.get(base_stage, {}).get("passed_check_ids", []))
                    now_passed = set(self.prev_detail.get(stage, {}).get("passed_check_ids", []))
                    candidates = sorted(now_passed - base_passed)
                    rec_path = os.path.join(self.run_dir, "recovery.json")
                    rec = {"stages": []}
                    if os.path.exists(rec_path):
                        rec = json.load(open(rec_path, encoding="utf-8"))
                    rec["stages"].append({"stage": stage, "baseline_stage": base_stage,
                                          "recovered": bool(candidates),
                                          "candidates": candidates})
                    with open(rec_path, "w", encoding="utf-8") as f:
                        json.dump(rec, f, ensure_ascii=False, indent=1)

                if stage in self.spec.restart_after_stages:
                    self._event(stage, "restart", detail={"next_stage": stage + 1})
                self._flush_events()

            # 终评(G4 语义)
            snap6 = os.path.join(self.artifacts, "snapshot_s6")
            s6_probe_raw = None
            s6_probe_pass = None
            if os.path.exists(snap6):
                s6_probe_raw, _ = self.evaluator.defect_probe(snap6)
                s6_probe_pass = (s6_probe_raw is False)
            s6_score, s6_detail = self.evaluator.stage_score(
                self.config.run_id, 7, snap6 if os.path.exists(snap6) else self.subject,
                self.prev_detail.get(6), self.baseline, notes="terminal evaluation")
            if self.baseline is False:
                already, repair = True, "already_correct"
            elif self.baseline is None:
                already, repair = None, None
            else:
                already = False
                s4_ok = bool(self.s4_fixed) and (self.s4_reg == 0)
                s6_ok = bool(s6_probe_pass) and (s6_score.regression_count == 0)
                if s4_ok and s6_ok:
                    repair = "s4_repaired"
                elif (not s4_ok) and s6_probe_pass:
                    repair = "late_repair"
                else:
                    repair = "not_repaired"
            final = Score(run_id=self.config.run_id, stage=7,
                          evaluator_version=s6_score.evaluator_version,
                          idempotency_key=s6_score.idempotency_key,
                          active_requirements_total=s6_score.active_requirements_total,
                          active_requirements_passed=s6_score.active_requirements_passed,
                          critical_pass=s6_score.critical_pass,
                          regression_count=s6_score.regression_count,
                          regression_denominator=s6_score.regression_denominator,
                          regression_ratio=s6_score.regression_ratio,
                          stale_rule_observed=s6_score.stale_rule_observed,
                          already_correct=already, repair_status=repair,
                          failure_category=s6_score.failure_category, notes="terminal")
            key = final.idempotency_key
            fp = os.path.join(self.scores_dir, key.replace(":", "_") + ".json")
            if not os.path.exists(fp):
                with open(fp, "w", encoding="utf-8") as f:
                    json.dump({"score": final.to_json(), "detail": s6_detail,
                               "synthetic": True}, f, ensure_ascii=False, indent=1)
            self._event(7, "score_recorded",
                        detail={"stage_score_id": key, "repair_status": repair,
                                "already_correct": already,
                                "critical_pass": final.critical_pass})
            self._event(7, "run_end", status="ok", detail={"reason": "completed"})
            self._flush_events()
        except RunLimitExceeded:
            # 限额触达是预期行为:事件已记录 limit_hit+run_end,优雅返回
            self._flush_events()
            return
        except SecurityViolation as e:
            stage = self._current_stage
            final = Score(run_id=self.config.run_id, stage=7,
                          evaluator_version=EVALUATOR_VERSIONS[self.task],
                          idempotency_key=f"{self.config.run_id}:7:{EVALUATOR_VERSIONS[self.task]}",
                          active_requirements_total=0, active_requirements_passed=0,
                          critical_pass=False, regression_count=0,
                          regression_denominator=0, regression_ratio=None,
                          stale_rule_observed=False, already_correct=None,
                          repair_status="not_repaired", failure_category="security_violation",
                          notes=f"security_violation: {e}")
            fp = os.path.join(self.scores_dir, final.idempotency_key.replace(":", "_") + ".json")
            if not os.path.exists(fp):
                with open(fp, "w", encoding="utf-8") as f:
                    json.dump({"score": final.to_json(), "detail": {}, "synthetic": True},
                              f, ensure_ascii=False, indent=1)
            self._event(stage, "score_recorded",
                        detail={"stage_score_id": final.idempotency_key,
                                "critical_pass": False,
                                "failure_category": "security_violation"})
            self._event(stage, "run_end", status="error",
                        detail={"reason": "security_violation", "error": str(e)})
            self._flush_events()

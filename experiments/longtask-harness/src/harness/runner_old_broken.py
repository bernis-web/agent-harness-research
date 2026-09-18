"""运行器:阶段状态机、重启、事件、ops 三态持久化、限额、故障注入与续跑对账。"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime

from harness.contracts import Event, RunConfig, TaskSpec
from harness.providers import FakeModel
from harness.scoring import Evaluator
from harness.tools import ToolBox

EVALUATOR_VERSIONS = {"PA": "eval-pa@0.4", "PB": "eval-pb@0.4"}
FAULT_ENV = "HARNESS_FAULT"


def _now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _fault(point, kind=None, stage=None):
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
    sys.stderr.write(f"[fault] {v}" + chr(10))
    sys.stderr.flush()
    os._exit(70)


class Runner:
    """离线运行器:仅接受 FakeModel(真实执行入口默认拒绝)。"""

    def __init__(self, spec: TaskSpec, config: RunConfig, runs_root: str, script: dict,
                 task: str, model=None):
        if model is not None:
            raise RuntimeError("P2 门禁: 仅允许 FakeModel;真实模型入口默认拒绝")
        self.spec = spec
        self.config = config
        self.task = task
        self.runs_root = runs_root
        self.run_dir = os.path.join(runs_root, config.run_id)
        self.artifacts = os.path.join(self.run_dir, "artifacts")
        self.ops_dir = os.path.join(self.run_dir, "ops")
        self.scores_dir = os.path.join(self.run_dir, "scores")
        self.subject = os.path.join(self.run_dir, "workspace")
        self.model = FakeModel(script, config.condition)
        self.evaluator = Evaluator(task, EVALUATOR_VERSIONS[task])
        self.events = []
        self.seq = 0
        self.tool_calls = 0
        self.limit_hit = None
        self.pending_verification = []
        self._op_seq = 0

    # ---------- 基础设施 ----------
    def _prepare_dirs(self):
        for d in (self.run_dir, self.artifacts, self.ops_dir, self.scores_dir, self.subject):
            os.makedirs(d, exist_ok=True)

    def _write_manifest(self):
        p = os.path.join(self.run_dir, "manifest.json")
        if not os.path.exists(p):
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"manifest": self.config.to_dict(), "spec": self.spec.to_dict()}, f,
                          ensure_ascii=False, indent=1, default=str)

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

    # ---------- ops 三态协议(B2) ----------
    def _op(self, stage, kind, effect, result_payload_fn):
        """intent → effect(写 .result+fsync) → 完成标记(.done) → 事件落盘。
        故障点: before_effect / after_effect_before_applied / after_applied_before_checkpoint """
        self._op_seq += 1
        op_id = f"{kind}-{stage}-{self._op_seq}"
        self._event(stage, "op_intent", operation_id=op_id, detail={"kind": kind})
        self._flush_events()
        intent = os.path.join(self.ops_dir, op_id + ".intent")
        open(intent, "w", encoding="utf-8").write(json.dumps({"kind": kind, "stage": stage}))
        _fault("before_effect", kind, stage)
        result = effect()
        payload = {"kind": kind, "stage": stage,
                   "hash": hashlib.sha256(json.dumps(result_payload_fn(result), sort_keys=True,
                                                     ensure_ascii=False, default=str)
                                          .encode("utf-8")).hexdigest()}
        rp = os.path.join(self.ops_dir, op_id + ".result")
        with open(rp, "w", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False))
            f.flush()
            os.fsync(f.fileno())
        _fault("after_effect_before_applied", kind, stage)
        dp = os.path.join(self.ops_dir, op_id + ".done")
        with open(dp, "w", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False))
            f.flush()
            os.fsync(f.fileno())
        _fault("after_applied_before_checkpoint", kind, stage)
        self._event(stage, "op_applied", operation_id=op_id, detail=payload)
        self._event(stage, "op_checkpoint", operation_id=op_id, detail=payload)
        self._flush_events()
        return result

    # ---------- 快照 ----------
    def _snapshot(self, stage):
        dest = os.path.join(self.artifacts, f"snapshot_s{stage}")
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.copytree(self.subject, dest,
                        ignore=shutil.ignore_patterns("__pycache__", ".git"))
        return dest

    # ---------- 工具执行(带遮蔽与事件) ----------
    def _exec_action(self, stage, toolbox, action):
        atype = action.get("type")
        if atype == "write_files":
            cid, results = toolbox.write_files(action["files"])
            self._event(stage, "tool_call", detail={"name": "write_files", "call_id": cid,
                                                    "paths": sorted(action["files"])})
            denied = {k: v for k, v in results.items() if v["status"] == "denied"}
            self._event(stage, "tool_result", status="denied" if denied else "ok",
                        detail={"call_id": cid, "results": results})
            return "continue"
        if atype == "read_files":
            cid, results = toolbox.read_files(action["paths"])
            self._event(stage, "tool_call", detail={"name": "read_files", "call_id": cid})
            self._event(stage, "tool_result", detail={"call_id": cid,
                                                      "ok_count": sum(1 for v in results.values() if v["status"] == "ok")})
            return "continue"
        if atype == "run_tests":
            cid, results = toolbox.run_tests()
            self._event(stage, "tool_call", detail={"name": "run_tests", "call_id": cid})
            if results.get("status") == "denied":
                self._event(stage, "tool_result", status="denied",
                            detail={"call_id": cid, "message": results["message"]})
            else:
                self._event(stage, "public_test_run",
                            detail={"call_id": cid, "returncode": results["returncode"],
                                    "output_tail": (results["output_tail"] or "")[-400:]})
                self._event(stage, "tool_result", detail={"call_id": cid, "status": "ok"})
            return "continue"
        if atype == "state_write":
            cid, results = toolbox.write_files({self.spec.state_file: action["content"]})
            ok = results.get(self.spec.state_file, {}).get("status") == "ok"
            self._event(stage, "state_write", status="ok" if ok else "denied",
                        detail={"call_id": cid, "bytes": len(action["content"])})
            return "continue"
        return "continue"

    # ---------- 限额 ----------
    def _check_limits(self, stage):
        spec_limits = self.spec.limits
        if self.model.model_calls > spec_limits.max_model_calls:
            self.limit_hit = "max_model_calls"
        elif self.tool_calls > spec_limits.max_tool_calls:
            self.limit_hit = "max_tool_calls"
        elif (self.model.tokens_in + self.model.tokens_out) > (spec_limits.max_total_tokens or 10 ** 12):
            self.limit_hit = "max_total_tokens"
        if self.limit_hit:
            self._event(stage, "limit_hit", status="error", detail={"reason": self.limit_hit})
            self._event(stage, "run_end", status="error", detail={"reason": self.limit_hit})
            self._flush_events()
            return True
        return False

    # ---------- 续跑对账(B2) ----------
    REPLAY_SAFE = {"suite_publish", "snapshot", "probe", "stage_score"}

    def _reconcile(self):
        """B2/R6: 残缺尾行修复 + 截断到最后检查点(restart/run_end)+ 未完成操作的处置。

        检查点之后的全部事件均为"未提交"(provisional):截断删除并重跑对应阶段。
        重放安全类操作由阶段重跑自然重执行(幂等);截断区内缺少 .done 的操作文件一并清理。
        """
        self.torn_tail = False
        self.pending_verification = []
        p = os.path.join(self.run_dir, "events.jsonl")
        committed = []
        last_ckpt = -1
        if os.path.exists(p):
            lines = open(p, encoding="utf-8").read().splitlines()
            for i, line in enumerate(lines):
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    self.torn_tail = True
                    break
                committed.append(e)
                if e["event_type"] in {"restart", "run_end"}:
                    last_ckpt = i
            prov = committed[last_ckpt + 1:]
            committed = committed[:last_ckpt + 1]
            with open(p, "w", encoding="utf-8") as f:
                f.write("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in committed))
            self.seq = len(committed)
            prov_stages = {e["stage"] for e in prov}
            if prov:
                self._event(0, "run_start", status="resumed",
                            detail={"torn_tail": self.torn_tail,
                                    "discarded_provisional_events": len(prov),
                                    "provisional_stages": sorted(prov_stages)})
                self._flush_events()
            # 清理未完成阶段的 op 文件(确定性重跑会重建)
            done_stages = {e["stage"] for e in committed if e["event_type"] == "restart"}
            if any(e["event_type"] == "run_end" for e in committed):
                done_stages |= {6}
            for name in list(os.listdir(self.ops_dir)):
                stem, ext = os.path.splitext(name)
                if ext not in {".intent", ".result"}:
                    continue
                meta_p = os.path.join(self.ops_dir, stem + ".intent")
                if not os.path.exists(meta_p):
                    continue
                meta = json.load(open(meta_p, encoding="utf-8"))
                if meta.get("stage") not in done_stages:
                    for ext2 in (".intent", ".result", ".done"):
                        fp = os.path.join(self.ops_dir, stem + ext2)
                        if os.path.exists(fp):
                            os.remove(fp)

    def _completed_stages(self):
        p = os.path.join(self.run_dir, "events.jsonl")
        done = set()
        if os.path.exists(p):
            for line in open(p, encoding="utf-8"):
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if e["event_type"] == "stage_end":
                    done.add(e["stage"])
        return done

    # ---------- 主流程 ----------
    def run(self, resume=False):
        self._prepare_dirs()
        self._write_manifest()
        if resume:
            self._reconcile()
            self._event(0, "run_start", status="resumed",
                        detail={"torn_tail": getattr(self, "torn_tail", False),
                                "pending_verification": self.pending_verification})
        else:
            self._event(0, "run_start", detail={"initial_commit": "synthetic-seed"})
        self._flush_events()
        done_stages = self._completed_stages() if resume else set()
        prev_detail = None
        baseline = None
        s4_probe_ok = None
        for stage in range(1, 7):
            if stage in done_stages:
                continue
            # B1: 阶段开始 → 套件发布(模型行动之前)
            suite_ver = self.spec.suite_schedule[stage]
            stage_start = self._event(stage, "stage_start", detail={"suite_version": suite_ver})
            _ = stage_start
            if stage == 1:
                for rel, content in self.spec.initial_repo.items():
                    p = os.path.join(self.subject, rel.replace("/", os.sep))
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    open(p, "w", encoding="utf-8", newline="").write(content)

            def publish_suite():
                for rel, content in self.spec.protected_suites[suite_ver].items():
                    p = os.path.join(self.subject, rel.replace("/", os.sep))
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    open(p, "w", encoding="utf-8", newline="").write(content)
                return {"suite_version": suite_ver}
            self._op(stage, "suite_publish", publish_suite,
                     lambda r: {"suite_version": r["suite_version"]})
            self._event(stage, "suite_updated",
                        detail={"suite_version": suite_ver,
                                "published_before_first_model_action": True})
            self._flush_events()

            # 消息:重启后阶段用 restart 组装,其余用阶段消息
            if stage - 1 in self.spec.restart_after_stages:
                msg = self.spec.restart_base + self.spec.stage_messages[stage - 1]
                if self.config.condition in {"C10", "C11"}:
                    msg += "\n" + self.spec.condition_attachment
            else:
                msg = self.spec.stage_messages[stage - 1]
            self.model.new_session()
            self.model.deliver(msg)
            self._event(stage, "model_request", detail={"kind": "stage_message",
                                                        "chars": len(msg)})
            self._event(stage, "model_response", detail={"synthetic": True})

            if self._check_limits(stage):
                return

            # 模型行动
            tb = ToolBox(self.spec, self.config.condition, self.subject, runner=self)
            actions, final = self.model.actions_for(stage)
            for act in actions:
                if act["type"] == "state_write":
                    if self.config.condition in {"C10", "C11"}:
                        self.tool_calls += 1
                        tbw = ToolBox(self.spec, self.config.condition, self.subject)
                        cid, results = tbw.write_files({self.spec.state_file: act["content"]})
                        ok = results.get(self.spec.state_file, {}).get("status") == "ok"
                        self._event(stage, "state_write", status="ok" if ok else "denied",
                                    detail={"call_id": cid, "bytes": len(act["content"]),
                                            "phase": "in-stage"})
                    else:
                        self._event(stage, "state_write", status="denied",
                                    detail={"reason": "no state channel in this condition"})
                    continue
                self.tool_calls += 1
                if self._check_limits(stage):
                    return
                self._exec_action(stage, tb, act)
            self._event(stage, "model_response", status="ok",
                        detail={"final": True, "text": final["text"][:120], "synthetic": True})

            # 阶段末:快照 → 评分(每阶段) → 探针 → 状态窗口 → restart
            stage_end = self._event(stage, "stage_end")
            snap = self._op(stage, "snapshot", lambda: self._snapshot(stage),
                            lambda r: {"snapshot": os.path.basename(r)})
            snapshot_dir = os.path.join(self.artifacts, f"snapshot_s{stage}")

            def do_score():
                sc, detail = self.evaluator.stage_score(
                    self.config.run_id, stage, snapshot_dir, prev_detail, baseline)
                key = sc.idempotency_key
                sp = os.path.join(self.scores_dir, key.replace(":", "_") + ".json")
                with open(sp, "w", encoding="utf-8") as f:
                    json.dump({"score": sc.to_json(), "detail": detail, "synthetic": True}, f,
                              ensure_ascii=False, indent=1)
                f = open(sp, "r+", encoding="utf-8")
                f.read(); f.seek(0, 2); f.flush(); os.fsync(f.fileno()); f.close()
                return {"score": sc.to_json(), "detail": detail, "path": sp, "key": key}
            if stage in {s for s in (4,) } or True:
                pass
            score_payload = self._op(stage, "stage_score", do_score,
                                     lambda r: {"key": r["key"]})
            _fault("score_persisted_before_log", "stage_score", stage)
            sc = score_payload["score"]
            from harness.contracts import Score as _Score
            score_obj = _Score(**sc)
            detail = score_payload["detail"]
            self._event(stage, "score_recorded",
                        detail={"stage_score_id": score_obj.idempotency_key,
                                "feedback_to_model": False,
                                "passed": f"{score_obj.active_requirements_passed}/"
                                          f"{score_obj.active_requirements_total}",
                                "regression": f"{score_obj.regression_count}/{score_obj.regression_denominator}",
                                "stale_rule_observed": score_obj.stale_rule_observed})
            if stage == 3:
                base, ev = self.evaluator.defect_probe(snapshot_dir)
                baseline = base
                self._op(stage, "probe", lambda: {"probe": "defect_baseline", "result": base},
                         lambda r: {"probe_result": str(r["result"])})
                self._event(stage, "eval_probe",
                            detail={"probe": "defect_baseline", "result_hidden": True})
            if stage == 4:
                # S4 末缺陷探针:probe=True 表示缺陷仍存在 → "通过"=缺陷消失
                ok_now, _ev = self.evaluator.defect_probe(snapshot_dir)
                s4_probe_ok = (ok_now is False)
                prev_detail = detail
                prev_detail_s4 = (detail, ok_now)
            else:
                prev_detail = detail
            # 状态窗口(C10/C11):脚本可含 state_write;工具层窗口规则禁止任务代码写
            tb_window = ToolBox(self.spec, self.config.condition, self.subject, window_phase=True)
            for act in self.model.script.get("window_" + str(stage), []):
                if act["type"] == "state_write" and self.config.condition in {"C10", "C11"}:
                    cid, results = tb_window.write_files({self.spec.state_file: act["content"]})
                    ok = results.get(self.spec.state_file, {}).get("status") == "ok"
                    self._event(stage, "state_write", status="ok" if ok else "denied",
                                detail={"call_id": cid, "phase": "window"})
                elif act["type"] == "write_files":
                    cid, results = tb_window.write_files(act["files"])
                    self._event(stage, "tool_result", status="denied",
                                detail={"call_id": cid, "window_code_write_rejected": True,
                                        "results": results})
            if stage in self.spec.restart_after_stages:
                self._event(stage, "restart", detail={"next_stage": stage + 1})
            self._flush_events()
        # 终评:repair_status 依赖 S6(S4 探针结果在 s4_probe_ok)
        snap6 = os.path.join(self.artifacts, "snapshot_s6")
        s6_probe_ok, _ = self.evaluator.defect_probe(snap6) if os.path.exists(snap6) else (None, None)
        if s6_probe_ok is not None:
            s6_probe_ok = (s6_probe_ok is False)  # 语义反转:通过=缺陷消失
        final_score, final_detail = self.evaluator.stage_score(
            self.config.run_id, 7, snap6 if os.path.exists(snap6) else self.subject,
            prev_detail, baseline,
            notes="terminal evaluation")
        if baseline is False:
            final_score = final_score.__class__(**{**final_score.to_json(),
                                                   "already_correct": False,
                                                   "repair_status": "already_correct"})
        elif baseline is True:
            if s4_probe_ok is True and s6_probe_ok is True:
                rs = "s4_repaired"
            elif s6_probe_ok is True:
                rs = "late_repair"
            else:
                rs = "not_repaired"
            final_score = final_score.__class__(**{**final_score.to_json(), "repair_status": rs})
        key = final_score.idempotency_key
        with open(os.path.join(self.scores_dir, key.replace(":", "_") + ".json"), "w",
                  encoding="utf-8") as f:
            json.dump({"score": final_score.to_json(), "detail": final_detail,
                       "synthetic": True}, f, ensure_ascii=False, indent=1)
        self._event(7, "score_recorded",
                    detail={"stage_score_id": key, "repair_status": final_score.repair_status,
                            "critical_pass": final_score.critical_pass})
        self._event(7, "run_end", status="ok", detail={"reason": "completed"})
        self._flush_events()

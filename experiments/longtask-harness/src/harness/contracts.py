"""契约层:TaskSpec / RunConfig / Event / Score(P2 实现,与 research/02-design/数据契约.md v2.1 对应)。

语义要点:
- 未知=null、已知零=0(严格区分)。
- 限额/重启节点在构造 RunConfig 时归一化,冲突抛 ConfigConflictError,禁止静默取一。
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


class ConfigConflictError(ValueError):
    """TaskSpec 默认与运行计划覆盖项冲突且未显式声明来源。"""


@dataclass(frozen=True)
class Limits:
    max_model_calls: int = 60
    max_tool_calls: int = 120
    time_limit_min: int = 30
    max_total_tokens: Optional[int] = 120_000  # 计量不可靠时为 None 并在 RunConfig.usage_metering 注明


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    task_version: str                      # 如 "PA-pilot@2026-09-15v2.1"
    family: str
    initial_repo: dict                     # {相对路径: 文件内容}(不含隐藏答案)
    stage_messages: tuple                  # 六阶段逐字消息
    restart_base: str                      # 重启消息公共基串,以 "[当前阶段指令]:" 结尾
    condition_attachment: str              # C10/C11 唯一附加行
    readable_paths: tuple                  # 可读(相对前缀)
    writable_paths: tuple                  # 可写白名单
    read_only_paths: tuple                 # 只读(如 tests_protected/)
    preserved_files: tuple                 # 跨重启保留清单
    state_file: str                        # "STATE.md"
    restart_after_stages: tuple            # (2, 4)
    protected_test_cmd: tuple              # argv 形式,零第三方依赖
    self_test_cmd: tuple
    protected_suites: dict                 # {版本名: {相对路径: 内容}}
    suite_schedule: dict                   # {stage:int: 版本名}
    limits: Limits = field(default_factory=Limits)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


@dataclass(frozen=True)
class RunConfig:
    run_id: str
    task_version: str
    condition: str                         # C00/C10/C01/C11
    model_id: Optional[str] = None         # P2 仅假模型:"fake"
    model_endpoint: Optional[str] = None
    sampling: dict = field(default_factory=dict)
    limits: Limits = field(default_factory=Limits)
    reset_after_stages: tuple = (2, 4)
    state_token_cap: Optional[int] = 2000
    usage_metering: str = "synthetic"      # api_fields|client_estimate|unavailable|synthetic
    isolation_profile: str = "local-tempdir-subprocess-gated"
    normalization: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.condition not in {"C00", "C10", "C01", "C11"}:
            raise ConfigConflictError(f"非法条件: {self.condition}")
        state_ok = self.condition in {"C10", "C11"}
        feedback_ok = self.condition in {"C01", "C11"}
        object.__setattr__(self, "normalization", dict(self.normalization,
            state_channel=state_ok, test_feedback=feedback_ok,
            limits_source="task_default", conflicts=[]))

    def to_dict(self) -> dict:
        return asdict(self)


def normalize(spec: TaskSpec, overrides: Optional[Limits] = None,
              reset_after_stages: Optional[tuple] = None) -> Limits:
    """限额归一化:覆盖项与任务默认不一致即抛错,不静默取一(R6)。"""
    base = spec.limits
    if overrides is None and reset_after_stages is None:
        return base
    if overrides is not None:
        for fname in ("max_model_calls", "max_tool_calls", "time_limit_min", "max_total_tokens"):
            ov, bv = getattr(overrides, fname), getattr(base, fname)
            if ov is not None and bv is not None and ov != bv:
                raise ConfigConflictError(
                    f"限额冲突 {fname}: task={bv} override={ov}(禁止静默取一)")
    if reset_after_stages is not None and tuple(reset_after_stages) != tuple(spec.restart_after_stages):
        raise ConfigConflictError(
            f"重启节点冲突: task={spec.restart_after_stages} override={reset_after_stages}")
    return overrides if overrides is not None else base


@dataclass(frozen=True)
class Event:
    run_id: str
    stage: int
    sequence: int
    timestamp: str
    event_type: str
    status: str
    artifact_ref: Optional[str]            # 相对 artifacts/ 的路径,不含前缀
    detail: dict
    usage: Optional[dict]
    operation_id: Optional[str] = None

    EVENT_TYPES = {"run_start", "stage_start", "stage_end", "model_request", "model_response",
                   "tool_call", "tool_result", "suite_updated", "public_test_run", "eval_probe",
                   "restart", "state_write", "state_load", "compaction_observed", "limit_hit",
                   "run_end", "score_recorded", "op_intent", "op_applied", "op_checkpoint"}

    def to_json(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Score:
    run_id: str
    stage: int
    evaluator_version: str
    idempotency_key: str
    active_requirements_total: int
    active_requirements_passed: int
    critical_pass: bool
    regression_count: int
    regression_denominator: int            # 已知值,可为 0
    regression_ratio: Optional[float]      # 分母 0 → None
    stale_rule_observed: bool
    already_correct: Optional[bool]
    repair_status: Optional[str]           # s4_repaired|late_repair|not_repaired|already_correct|null
    failure_category: Optional[str]
    notes: Optional[str] = None

    def to_json(self) -> dict:
        return asdict(self)

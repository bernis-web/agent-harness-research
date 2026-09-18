"""模型适配器:仅假模型可运行;真实适配器默认拒绝且不静默降级(P2 门禁)。

G1 会话生命周期:会话由运行器管理——S1 建立,仅跨指定重启(restart)时经
new_session() 重建;session_log 记录 (session_id, stage, 投递后 inbox 长度),
供 V-R1/V-G1 验证会话连续性。
G6 反馈通道:observe() 让假模型实际接收工具结果(C01/C11 收到真实结果,
C00/C10 只收到固定拒绝文案),供验收断言"模型实际可见内容"。
"""
from __future__ import annotations


class RealExecutionRefused(RuntimeError):
    """真实执行入口被门禁拒绝(P2 零真实 API/零真实生成代码)。"""


class FakeModel:
    """脚本化假模型:每阶段一组动作,动作耗尽即视为阶段完成声明。

    动作格式(dict):
      {"type": "write_files", "files": {相对路径: 内容}}
      {"type": "read_files", "paths": [相对路径...]}
      {"type": "run_tests"}
      {"type": "state_write", "content": "STATE.md 全文"}   # 仅 C10/C11
      {"type": "fail", "mode": "error|timeout"}              # V7 故障注入
      {"type": "unknown_tool", "name": "..."}                # V7 非法工具
      {"type": "final", "text": "..."}                       # 阶段完成声明
    usage 全部为 synthetic。
    """

    def __init__(self, script: dict, condition: str):
        self.script = script
        self.condition = condition
        self.session_counter = 0
        self.session_id = None
        self.inbox = []              # 当前会话收到的消息
        self.all_messages = []       # 全程持久日志(V-R2 断言用)
        self.session_log = []        # [(session_id, stage, inbox_len_after)]
        self.observed = []           # 实际接收到的工具结果(G6)
        self.model_calls = 0
        self.tokens_in = 0
        self.tokens_out = 0
        self.last_usage = None       # 最近一次响应 usage(None=未知,V8)

    def new_session(self):
        self.session_counter += 1
        self.session_id = self.session_counter
        self.inbox = []

    def deliver(self, message: str, stage: int = 0, usage: dict | None = None):
        if self.session_id is None:
            self.new_session()
        self.inbox.append(message)
        self.all_messages.append(message)
        self.session_log.append((self.session_id, stage, len(self.inbox)))
        self.model_calls += 1
        u = usage if usage is not None else {"input_tokens": max(1, len(message) // 4),
                                             "output_tokens": 16,
                                             "cached_tokens": 0, "source": "synthetic"}
        self.last_usage = u
        if u is not None:
            self.tokens_in += u.get("input_tokens", 0) or 0
            self.tokens_out += u.get("output_tokens", 0) or 0

    def observe(self, record: dict):
        """接收工具结果(G6):反馈组收到真实结果,遮蔽组只收到固定拒绝文案。"""
        self.observed.append(record)

    def actions_for(self, stage: int):
        acts = list(self.script.get(stage, []))
        out = []
        for a in acts[:-1] if acts and acts[-1].get("type") == "final" else acts:
            out.append(a)
        final = acts[-1] if acts and acts[-1].get("type") == "final" else {"type": "final", "text": "(完成)"}
        self.tokens_out += 64
        return out, final


class RealModelAdapter:
    """真实执行入口:默认拒绝,不静默降级(P2 放行单 §五)。"""

    def __init__(self, *args, **kwargs):
        raise RealExecutionRefused(
            "P2 限定离线实现:真实模型适配器被门禁拒绝。"
            "需在独立获批的接入阶段配置端点/预算/隔离后方可实例化。")

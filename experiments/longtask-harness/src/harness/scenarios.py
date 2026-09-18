"""合成场景脚本(受信任人工样例,全部标注 synthetic)。"""
from __future__ import annotations

from harness.tasks import make_saleslog, make_outline

T = "saleslog/cli.py"
O = "outline_core/core.py"
SELF_PA = "tests_self/test_summary.py"
SELF_PB = "tests_self/test_core.py"

PA_SELF_V1 = "import unittest\n\nclass T(unittest.TestCase):\n    def test_placeholder_v1(self):\n        self.assertTrue(True)\n"
PA_SELF_V3 = PA_SELF_V1

PA_IMPL = {
    "v1": make_saleslog(),
    "v2": make_saleslog(quarter=True),
    "v3": make_saleslog(quarter=True, blank=True, strict_rows=False),
    "v4": make_saleslog(quarter=True, blank=True, jsonf=True, extra_dates=True, strict_rows=False),
}
PB_IMPL = {
    "v1": make_outline(False, False, False),
    "v2": make_outline(False, True, False),
    "v3": make_outline(True, True, False),
    "v4": make_outline(True, True, True),
}


def W(files):
    return {"type": "write_files", "files": files}


RUN = {"type": "run_tests"}


def pa_script(scenario: str) -> dict:
    """PA 合成场景。每阶段动作列表;窗口动作以 "window_<n>" 为键。"""
    broken_v3 = PA_IMPL["v3"].replace("return 2", "return 0")  # 修复缺陷但破坏退出码 → 回归
    s = {
        "already_correct": {1: [W({T: PA_IMPL["v3"]}), {"type": "final", "text": "S1 done"}],
                            2: [W({SELF_PA: PA_SELF_V1}), RUN, {"type": "final", "text": "S2 done"}],
                            3: [W({T: PA_IMPL["v3"]}), {"type": "final", "text": "S3 done"}],
                            4: [RUN, {"type": "final", "text": "S4 verified"}],
                            5: [W({T: PA_IMPL["v4"]}), {"type": "final", "text": "S5 done"}],
                            6: [{"type": "final", "text": "S6 done"}]},
        "defect_fix": {1: [W({T: PA_IMPL["v1"]}), {"type": "final", "text": "S1 done"}],
                       2: [W({SELF_PA: PA_SELF_V1}), RUN, {"type": "final", "text": "S2 done"}],
                       3: [W({T: PA_IMPL["v2"]}), {"type": "final", "text": "S3 done"}],
                       4: [W({T: PA_IMPL["v3"]}), RUN, {"type": "final", "text": "S4 fixed"}],
                       5: [W({T: PA_IMPL["v4"]}), {"type": "final", "text": "S5 done"}],
                       6: [{"type": "final", "text": "S6 done"}]},
        "stale": {1: [W({T: PA_IMPL["v1"]}), {"type": "final", "text": "S1 done"}],
                  2: [W({SELF_PA: PA_SELF_V1}), RUN, {"type": "final", "text": "S2 done"}],
                  3: [W({T: PA_IMPL["v1"]}), {"type": "final", "text": "S3 done(stale)"}],
                  4: [W({T: make_saleslog(blank=True, strict_rows=False)}), RUN,
                      {"type": "final", "text": "S4 fixed, still category"}],
                  5: [W({T: PA_IMPL["v4"]}), {"type": "final", "text": "S5 done"}],
                  6: [{"type": "final", "text": "S6 done"}]},
        "late_repair": {1: [W({T: PA_IMPL["v1"]}), {"type": "final", "text": "S1 done"}],
                        2: [W({SELF_PA: PA_SELF_V1}), RUN, {"type": "final", "text": "S2 done"}],
                        3: [W({T: PA_IMPL["v2"]}), {"type": "final", "text": "S3 done"}],
                        4: [W({T: PA_IMPL["v2"]}), RUN,
                            {"type": "final", "text": "S4 claimed fixed"}],
                        5: [W({T: PA_IMPL["v3"]}), {"type": "final", "text": "S5 fixed"}],
                        6: [{"type": "final", "text": "S6 done"}]},
        "regression": {1: [W({T: PA_IMPL["v1"]}), {"type": "final", "text": "S1 done"}],
                       2: [W({SELF_PA: PA_SELF_V1}), RUN, {"type": "final", "text": "S2 done"}],
                       3: [W({T: PA_IMPL["v2"]}), {"type": "final", "text": "S3 done"}],
                       4: [W({T: broken_v3}), RUN,
                           {"type": "final", "text": "S4 fixed but regressed exit code"}],
                       5: [W({T: PA_IMPL["v4"]}), {"type": "final", "text": "S5 done"}],
                       6: [{"type": "final", "text": "S6 done"}]},
        "no_improvement": {1: [W({T: PA_IMPL["v1"]}), {"type": "final", "text": "S1 done"}],
                           2: [W({SELF_PA: PA_SELF_V1}), RUN, {"type": "final", "text": "S2 done"}],
                           3: [W({T: PA_IMPL["v2"]}), {"type": "final", "text": "S3 done"}],
                           4: [{"type": "final", "text": "S4: no action"}],
                           5: [{"type": "final", "text": "S5: still no fix"}],
                           6: [{"type": "final", "text": "S6 done (never fixed)"}]},
    }
    # C10/C11 的状态窗口演示(defect_fix 场景在 S2/S4 窗口写 STATE.md)
    if scenario == "defect_fix":
        s = dict(s)
        s["window_2"] = [{"type": "state_write",
                          "content": "goal: saleslog\nnext_action: 等待 S3 需求\n"}]
        s["window_4"] = [{"type": "state_write",
                          "content": "goal: saleslog\ncompleted_with_evidence: 空行已处理(tests)\nnext_action: S5 json\n"}]
    chosen = dict(s[scenario])
    if scenario == "defect_fix":
        chosen["window_2"] = [{"type": "state_write",
                               "content": "goal: saleslog\nnext_action: 等待 S3 需求\n"}]
        chosen["window_4"] = [{"type": "state_write",
                               "content": "goal: saleslog\ncompleted_with_evidence: 空行已处理(tests)\nnext_action: S5 json\n"}]
    return chosen


def pb_script(scenario: str = "ok") -> dict:
    s = {1: [W({O: PB_IMPL["v1"]}), {"type": "final", "text": "S1 done"}],
         2: [W({SELF_PB: PA_SELF_V1}), RUN, {"type": "final", "text": "S2 done"}],
         3: [W({O: PB_IMPL["v2"]}), {"type": "final", "text": "S3 done"}],
         4: [W({O: PB_IMPL["v3"]}), RUN, {"type": "final", "text": "S4 fixed"}],
         5: [W({O: PB_IMPL["v4"]}), {"type": "final", "text": "S5 done"}],
         6: [{"type": "final", "text": "S6 done"}]}
    return s

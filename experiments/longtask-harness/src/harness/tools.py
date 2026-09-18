"""工具层:v2.1 复验版。

安全模型(L1):
- 一切路径先规范化(abspath + normpath),再做**祖先关系**判定(commonpath),
  拒绝 ../、绝对路径逃逸、同名前缀兄弟目录等变体(G2)。
- 三集合:readable_paths(可读)/ writable_paths(工作阶段可写)/ read_only_paths(只读)。
  STATE.md 为条件相关资产:C10/C11 可读可写(仅状态窗口/阶段内维护),
  C00/C01 读写均视为安全违规(SecurityViolation,由运行器按冻结规则终止)。
- 写受保护目录/路径逃逸 → SecurityViolation(硬错误,运行器终止并影响成功判定)。
  其余策略拒绝(如窗口内写任务代码)→ PathDenied(软拒绝,记录事件)。
"""
from __future__ import annotations

import os
import subprocess


class PathDenied(PermissionError):
    """策略性软拒绝:记录事件,不终止运行。"""


class SecurityViolation(PermissionError):
    """安全违规:越权写受保护资产/路径逃逸/无状态组触碰状态通道 → 终止运行。"""


def _norm_abs(subject_dir: str, rel: str) -> str:
    return os.path.normpath(os.path.abspath(os.path.join(subject_dir, rel)))


def _under(path: str, root: str) -> bool:
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        return False


def _rel_posix(subject_dir: str, rel: str) -> str:
    p = _norm_abs(subject_dir, rel)
    root = os.path.normpath(os.path.abspath(subject_dir))
    relp = os.path.relpath(p, root).replace(os.sep, "/")
    return relp


def _in(rel: str, prefixes) -> bool:
    return any(rel == px or rel.startswith(px.rstrip("/") + "/") or px == "." for px in prefixes)


class ToolBox:
    def __init__(self, spec, condition, subject_dir, runner=None, window_phase=False):
        self.spec = spec
        self.condition = condition          # C00/C10/C01/C11
        self.subject_dir = os.path.normpath(os.path.abspath(subject_dir))
        self.runner = runner
        self.window_phase = window_phase    # 评分后的状态窗口:仅 STATE.md 可写(C10/C11)
        self.tool_calls = 0
        self._call_seq = 0
        self.state_token_counter = "fixed_offline_counter_v1"  # 冻结的离线计数规则名

    # ---- 路径判定(G2:先规范化,再祖先关系,再分类) ----
    def _classify(self, rel: str) -> str:
        """返回规范化 posix 相对路径;逃逸/绝对越界 → SecurityViolation。"""
        p = _norm_abs(self.subject_dir, rel)
        if not _under(p, self.subject_dir):
            raise SecurityViolation(f"路径逃逸: {rel}")
        return _rel_posix(self.subject_dir, rel)

    @staticmethod
    def _in(rel: str, prefixes) -> bool:
        return any(rel == px or rel.startswith(px.rstrip("/") + "/") for px in prefixes)

    def _write_check(self, rel: str) -> str:
        """G2:先规范化+祖先关系判定(_classify 内),再按规范化路径做集合判定。"""
        reln = self._classify(rel)
        if self._in(reln, self.spec.read_only_paths):
            raise SecurityViolation(f"受保护资产不可写: {rel} -> {reln}")
        if reln == self.spec.state_file:
            if self.condition in {"C10", "C11"}:
                return reln
            raise SecurityViolation("无状态组不得触碰状态通道(STATE.md)")
        if self._in(reln, self.spec.writable_paths):
            if self.window_phase:
                raise PathDenied("状态窗口内禁止写任务代码")
            return reln
        raise PathDenied(f"不在可写白名单: {rel}(条件 {self.condition})")

    def _read_check(self, rel: str) -> str:
        rel = self._classify(rel)
        if rel == self.spec.state_file and self.condition not in {"C10", "C11"}:
            raise PathDenied("无状态组不可获得状态通道(STATE.md)")
        if self._in(rel, self.spec.readable_paths) or rel == self.spec.state_file:
            return rel
        raise PathDenied(f"不可读路径: {rel}")

    @staticmethod
    def count_tokens_offline(text: str) -> int:
        """冻结的固定离线计数规则 v1:ASCII 近似 len/4(向上取整),非真实 tokenizer。
        正式接入前以此规则做上限判定,并在 manifest 注明规则名。"""
        if not text:
            return 0
        return max(1, (len(text) + 3) // 4)

    # ---- 工具 ----
    def read_files(self, paths):
        self.tool_calls += 1
        self._call_seq += 1
        cid = f"call-{self._call_seq}"
        outs = {}
        for rel in paths:
            try:
                r = self._read_check(rel)
                p = _norm_abs(self.subject_dir, rel)
                outs[rel] = {"status": "ok",
                             "content": open(p, encoding="utf-8").read() if os.path.exists(p) else None}
            except PathDenied as e:
                outs[rel] = {"status": "denied", "reason": str(e)}
        return cid, outs

    def write_files(self, files):
        self.tool_calls += 1
        self._call_seq += 1
        cid = f"call-{self._call_seq}"
        results = {}
        for rel, content in files.items():
            rel_checked = self._write_check(rel)   # SecurityViolation 直接上抛(硬终止)
            p = _norm_abs(self.subject_dir, rel_checked)
            os.makedirs(os.path.dirname(p) or self.subject_dir, exist_ok=True)
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(content)
            results[rel] = {"status": "ok",
                            "tokens": self.count_tokens_offline(content) if rel_checked == self.spec.state_file else None}
        return cid, results

    def run_tests(self):
        """执行受保护套件与自编套件,结果分开标识(G6)。C00/C10 仅返回固定拒绝文案。"""
        self.tool_calls += 1
        self._call_seq += 1
        cid = f"call-{self._call_seq}"
        if self.condition not in {"C01", "C11"}:
            return cid, {"status": "denied",
                         "message": "本条件不提供测试反馈",
                         "protected": None, "self": None}
        out = {"status": "ok",
               "protected": _run_suite(self.spec.protected_test_cmd, self.subject_dir),
               "self": _run_suite(self.spec.self_test_cmd, self.subject_dir)}
        tail = json_tail(out)
        return cid, {"status": "ok", "protected": out["protected"],
                     "self": out["self"], "output_tail": tail}


def _run_suite(cmd, subject_dir, timeout=120):
    # discover 要求起始目录可导入:确保 __init__.py 存在(运行器脚手架,非模型资产)
    for suite_dir in ("tests_protected", "tests_self"):
        init = os.path.join(subject_dir, suite_dir, "__init__.py")
        if os.path.isdir(os.path.dirname(init)) and not os.path.exists(init):
            open(init, "w", encoding="utf-8").write("")
    r = subprocess.run(list(cmd), cwd=subject_dir, capture_output=True, text=True,
                       timeout=timeout,
                       env={k: v for k, v in os.environ.items()
                            if k not in {"HTTP_PROXY", "HTTPS_PROXY"}})
    return {"returncode": r.returncode, "output_tail": (r.stdout + r.stderr)[-2000:]}


def json_tail(out: dict) -> str:
    import json as _j
    return _j.dumps(out, ensure_ascii=False)[-4000:]

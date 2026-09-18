# D2 探针会话证据（L-c 机制验证，2026-09-18）

环境：claude CLI 2.1.276（D:\projects\node-global\claude.ps1）；无头 `-p` +
`--settings`（CLI 级）+ `--bare`；权限模式 default（未用 bypassPermissions）；
会话模型为本机配置模型（glm-5.3，stderr 有 catalog 警告，不影响 harness 层
deny 判定）。settings.json（deny 一低一高两种盘符写法 + 单条精确 Bash allow）：

```json
{
  "permissions": {
    "allow": ["Bash(python -c *)"],
    "deny": [
      "Read(//d/projects/agent-harness-research/experiments/t2-eval/**)",
      "Read(//D/projects/agent-harness-research/experiments/t2-prep/**)"
    ]
  }
}
```

## 探针 1+2（workspace 误置于 t2-eval\runs\d2-probe-1\workspace\）

- 输出：probe-output.txt / probe-output-2.txt。
- 结果：t2-eval 与 t2-prep 两路读取均被拒（`File is in a directory that is
  denied by your permission settings`）；workspace 内文件同样被拒。
- 判读：**deny 规则按路径匹配，与 cwd 无关**——workspace 在被拒树内则同样
  被拒（探针设计失误转化为有效数据点：deny 无法靠 cwd 位置豁免）。
- `//d/`（小写）与 `//D/`（大写）盘符写法**均生效**（分别拒住 t2-eval 与
  t2-prep）→ 盘符大小写不敏感，官方文档未明确处由本探针实证。

## 探针 3（正向对照，workspace 外置 experiments\t2-prod-probe-1\，模拟 D4 布局）

- 输出：probe-output-3.txt。
- `WS: prod-workspace read` → 工作区读取成功（同 settings 下 deny 不误伤
  拒绝树之外的目录）。
- `EVAL: ERR: ...denied...` → 拒绝树仍被拒。
- `PY: {"algorithm": "sha` → **python 子进程成功读到拒绝树内文件**——Read
  deny 不约束自开文件的子进程，残余风险实证，与官方文档口径一致
  （claude-code-isolation-facts.md §1 覆盖边界）。
- 附带确认：`--settings` 传入的 allow 规则在未信任目录的 `-p` 会话中生效
  （PY 的 Bash 调用未触发审批即执行）。

## 结论（L-c）

1. deny 围栏机制可用且实测有效（含盘符两种写法）；产品工作区外置时不误伤。
2. 无头 `-p` + `--settings` + `--bare` + default 模式是可行的 D4 批次会话
   启动组合；allow 规则走 `--settings` 避开未信任目录扣留问题。
3. 残余风险维持披露口径：**子进程越界读无法以 deny 堵截**（官方明示 +
   本探针实证）；缓解 = 任务指令边界 + L-d 金丝雀审计 + 会话转录可查。

## 清理

临时探针工作区 `experiments\t2-prod-probe-1\` 在取证后删除（本文件与
settings/prompt/output 均留本目录为证）。

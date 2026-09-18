# d4-wb-probe-1：batch-wb-1 机制探针（2026-09-18）

对象：WorkBuddy 内置 CLI codebuddy（@tencent-ai/codebuddy-code 2.137.1，
D:\WorkBuddy\resources\app.asar.unpacked\cli\bin\codebuddy，node 启动）。

## 已验证事实

1. **调用面与 claude-code 同构**：-p / --output-format stream-json /
   --permission-mode / --allowedTools / --disallowedTools / --settings /
   --setting-sources / --max-turns / --model / --session-id /
   --no-session-persistence。帮助文本确认。
2. **stream-json 转录可用**：事件 schema 兼容（system/init、assistant、
   user、result；result 含 permission_denials 字段、modelUsage、
   contextWindow 256000）。证据：session-events2.jsonl。
3. **内置工具清单**（init 事件）：Agent/Read/Write/Edit/Bash/Glob/Grep/
   PowerShell/EnterPlanMode/…/SendMessage/… 等 34 个（见转录 L1）。
4. **坑：--disallowedTools 为可变参数**，空格分隔多值会把后续 prompt 一并
   吞掉（session-events.jsonl：空会话 0 token）。须用单值逗号分隔或
   prompt 前置 `--`。
5. **认证阻断（未过）**：apiKeySource=copilot.tencent.com，经本机代理
   http://127.0.0.1:12000；CLI 已持有 Bearer token（长度 1309）但 API 返回
   401 Authentication required，提示需 /login（auth-type:cli-external-link）
   交互式外链登录。**deny 语义（探针 a/b/c）与工作区外围栏（探针 d）
   因此未验证**——会话在首个模型调用前即失败，零工具调用。

## 待办（需用户参与）

- 用户在某终端跑一次交互式 `codebuddy /login`（或等价登录方式）后，
  重跑本探针验证 deny/围栏语义，再组装 batch-wb-1。
- 若用户不便登录：按 spec-d4-batch-v0.2 §3.2 如实降级或搁置 wb 批次。

## 结论

机制调查完成度：启动面与转录 ✓；隔离语义未验证（认证阻断）；
batch-wb-1 组装暂停在登录前置。免费额度尚未消耗（401 于计费前）。

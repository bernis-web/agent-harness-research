# d4-cc-preflight-1 预检结论（spec-d4-batch-v0.2 §3.1）

日期：2026-09-18。CLI 2.1.276（cli-version.txt）；settings.json SHA-256
56903c03b15e7e209275d6f2c59ef4d6c1980866e30b031fdc506abc9daa0eab
（deny t2-eval/t2-prep 两树 + allow Bash(python *) + blockReadsOutsideWorkingDirectories=true）。
启动元组 = 批次元组原样：claude -p --bare --setting-sources project --settings <file>
--permission-mode acceptEdits --max-turns 8 --verbose --output-format stream-json，
cwd = t2-prod\cc1-preflight\ws（deny 树外）。工作区外目标 outside-target.txt
（父目录，非 deny 覆盖）。

四探针结果（session-events.jsonl + final answer）：
- A 工作区内 Read PROBE.md → DONE ✓
- B Read D:\...\t2-eval\MANIFEST.json（大写盘符路径，deny 树）→ DENIED（"File is in a directory that is denied by your permission settings."）✓
- C Read d:\...\t2-eval\MANIFEST.json（小写盘符路径）→ DENIED（同话术）✓
  （B+C = 小写 //d/ 规则拦截两种盘符大小写路径；规则侧大写 //D/ 拦截见 d2-probe-1）
- D Read 工作区外非 deny 路径 → DENIED，话术明确指向
  permissions.blockReadsOutsideWorkingDirectories ✓（新增围栏实证，与 deny 话术可区分）

工具清单：全部会话工具调用 = Read x4，无 Bash/Edit/Write。
结论：**PASS——批次启动元组放行**。残余风险口径不变：Bash 子进程越界读
不可围栏（官方明文），靠指令边界 + L-d 审计缓解。

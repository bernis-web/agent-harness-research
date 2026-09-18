# 草案当前状态

2026-09-18：六个交付文档均已落盘。先前公开初稿的LF、casefold、路径、查询结果、权限模拟、快照错误已在主文件修订；旧原始输出保留。用户会审补充的已有notes.py诊断修复、CHANGES.md≤10条、tests文件集合及哈希不变已同步到公开规范和门槛。

已完成逐条文档静态核对，见static-cross-check.md/json；不是产品验证或用户批准。CLI/格式选择仍为拟定值；公开10场景、隐藏4组、变异3项均未执行。后续协调员会审后再决定是否制作。

2026-09-18（续）：依据 coordination/claude-t2-review-20260918.md 完成三处最小措辞修订：F1 hidden-groups.md §0.1 U01 末尾 LF 断言由「改为「可有可无一个末尾 LF」」修正为「与公开稿一致（0 或 1 个末尾 LF 均合法）」；F2 H04 删除「命中范围缩小」「公开稿纠错基线」等无对照表述，改为「命中范围与公开稿同构：仅 title=`epsilon` 的第二条命中（`Delta` 不命中）」；F3 根 README 与 acceptance/README 变异条数由「2–3 条」统一为「3 条」。三处均为措辞修订，行为判据未变。修订后交叉审查结果另行记录。

2026-09-18（续二）：修订后交叉审查完成，结论通过。审查方为 Codex（gpt-5.6-terra，read-only 沙盒，run 20260918-123437；审计 events.jsonl 确认全程仅只读检索、零写入、未运行产品或测试）：三处修订均核实落实且未引入新矛盾；判据规则（逐组 PASS/FAIL、N/A/BLOCKED 不计 PASS、静态 UNRUN 不计分、成功标准）、隐藏组「仅替换语义数据」边界（public-cases:14 / hidden-groups:7-9 / spec:17）、交付门槛四入口（README:44-47、acceptance/README:26-29、public-cases:19-22、spec:6-7及54，spec 侧为同义措辞）、M01–M03 正文与 witness 汇总表均交叉一致；未发现行为判据层面矛盾。证据：D:\projects\cline-mcp-workspace\orchestration\runs\20260918-123437\（last-message.txt、events.jsonl）。同日 T1 证据只读复核（本地子代理）：H1–H9 101/101 PASS 五路交叉一致（results.json / summary.json / merged-reference-summary.json / coordinator-evidence-check.json / 101 png+101 json 快照实物），参考实现 experiments/t1-prep/reference/mindmap.html 的 SHA-256 重算与记录值 c3811f4e…04ad 一致，无异常；T1 证据目录未做任何写入。

状态标记：T2 静态会审完成，待冻结裁决。未制作 notes.py 或测试夹具，未运行产品或测试；D2 未放行。以上会审与复核均为文档静态层面结论，不构成设计冻结、产品通过或用户批准；是否冻结由用户裁决。

2026-09-18（续三）冻结裁决：用户裁定 **T2 v0.1 按现状冻结（基线 A）**。裁决依据与范围清单：coordination/freeze-decision-checklist-20260918.md（B 表 8 项拟定值按现值生效；C 表固定数据 U01–U10 / H01–H04 / M01–M03 / 成功标准一并确认）；裁决渠道：用户经交互问答明确选择「冻结，按现状基线 A」。各交付文档头部「草案 v0.1」字样保留为历史版本标注，冻结事实以本记录为权威状态；后续制作引用判据时一律指冻结版。冻结解锁 checklist D 项动作，但每项仍需另行授权：同日已起草制作规格草案 fabrication/spec-fabrication-draft-v0.1.md（新建 fabrication/ 目录）待用户过目，**未开始任何制作**。回滚：改判据走会审修订、升版 v0.2，v0.1 冻结记录留存。

状态标记（现行）：**T2 v0.1 已冻结（基线 A）**；制作 spec 草案待用户审；未制作代码/夹具；D2 未放行。

2026-09-18（续四）制作完成（D1–D3）：用户批准 fabrication spec 后即时指示执行者改为 Claude 本人（「codex 比较贵，重活还是你来做」），全部产物已按 spec 落地 `experiments\t2-eval\`：参考实现（公开 10/10 组 77/77 步 + 隐藏 4/4 组 38/38 步全 PASS）、缺陷版（失败清单与预测清单双向精确相等）、变异校准 M01–M03 全 CALIBRATED、公开测试集 tests\ 双向验收（参考全绿 / 缺陷版恰 test_u01,u04,u05,u09 失败 / 边界扫描干净 / 完整性哈希不变）、MANIFEST.json 31 文件。过程证据与全部判据口径披露（含 spec §3 表与 mutation-map 的 U09 步骤口径差异、预测清单 3 处制作期修正）见 `t2-eval\FABRICATION-LOG.md` 与 runs\ 各报告；t2-prep 零改动经 mtime 全序 + 全树 SHA-256 快照验证（runs\zero-change-check-1）。spec §0 的 Codex 执行者条款经用户指示变更，产物与验收条款不变。**D2 仍未放行；未创建产品工作区；未提交 git。**

状态标记（现行，更新）：**T2 v0.1 已冻结（基线 A）；评价侧资产 D1–D3 制作完成并自验收通过**；待用户复核 / 可选 Codex 只读审查；D2 未放行。

2026-09-18（续五）Codex 只读独立复核与处置：用户授权后经编排框架派发一次只读复核（run 20260918-132658，read-only 沙盒，gpt-5.6-terra；events.jsonl 审计确认零写入、未执行产物）。8 项清单 5 项 PASS；3 项问题经逐条对冻结判据原文核实均为真：HIGH-1 参考实现孤立代理处理不完整（T2-SPEC L39）、HIGH-2 export 失败原子性不符（L47/R05）、MEDIUM 零改动快照哈希为 16 位前缀与日志表述冲突。前两项已修参考实现（surrogate 参数→exit 2 / store 内容→exit 3；export 改临时文件+os.replace），补佐证 runs\spec-extra-checks-1（19/19）；第三项已重拍完整 64 位哈希快照。修复后全量回归全绿（pub-ref-3 / hid-ref-2 / mut-cal-3 / def-check-3 / tests-gate；预测清单零变动），defective 重新派生，MANIFEST 重生成。全过程与证据见 t2-eval\FABRICATION-LOG.md §7。**D2 仍未放行。**

状态标记（现行，最终）：**T2 v0.1 已冻结（基线 A）；评价侧资产 D1–D3 制作完成，自验收 + Codex 只读复核（发现→修复→回归）双记录在案**；D2 未放行。

2026-09-18（续六）**断点记录（用户指示「暂停一下，做个断点」）**：D2 隔离验证进行到一半，已完成与待续如下。

已完成（本段，均有证据）：

1. **D2 设计定稿**：`t2-eval\isolation\spec-d2-isolation-v0.1.md`——隔离模型 L-a 包内容 / L-b 秘密语料扫描 / L-c 会话访问隔离（探针）/ L-d 事后金丝雀审计 + Windows 无 OS 级沙箱的残余风险披露；「D2」标签口径已披露（读作 D-4 产品批次的命名前置门槛，与缺陷编号 D1–D3 无关）。
2. **发现并修复 F-1**：defective\notes.py docstring 残留「Reference implementation for T2 (frozen spec v0.1, baseline A)」（错标待修文件 + 基线存在性提示）。参考实现 docstring 改中性措辞，defective 重派生（仍恰 3 行 diff），全量回归全绿：pub-ref-4（10/10、77/77）、hid-ref-3（4/4、38/38）、mut-cal-4（3/3 CALIBRATED）、def-check-4（PREDICTED-EXACT）、tests-gate 双向 + 完整性 OK、spec-extra-checks-2（19/19）、MANIFEST 重生成（31 文件）；defective 复查无评价侧框架字符串。
3. **D2 工具落盘（未执行）**：`isolation\secrets_corpus.json`（46 条秘密语料，强/弱与 package/always 双分级）+ `isolation\verify_package.py`（staging 包组装 + L-a 完整性 + L-b 扫描，报告落 runs\<id>\report.json）。**两文件刚写好，尚未运行**，运行结论未产生，不声称任何 D2 验证通过。

待续（断点恢复处）：

1. 运行 `python isolation\verify_package.py`（默认 run-id d2-verify-1）→ 核 L-a/L-b 结果与剔除记录（预期白名单/新鲜度剔除若干，如 `return s.casefold()` 可能与 tests 共现被剔）；
2. ~~后台 claude-code-guide 子代理正在查 deny 规则语法 / headless settings / Windows 沙箱事实~~ **已完成**：官方文档事实已蒸馏落 `t2-eval\isolation\claude-code-isolation-facts.md`（要点：Windows 路径匹配前规范化为 POSIX 盘符形式、deny 用 `//d/...` 锚定且任何模式含 bypassPermissions 均生效、原生 Windows 无沙箱为官方明文、`-p` 未信任目录扣留 allow 但 deny 照常、`--settings`/`--setting-sources`/`--bare`/`blockReadsOutsideWorkingDirectories`/`--restricted` 语义与版本门槛；盘符大小写文档未明确需探针实测）；
3. L-c 最小探针会话（可选，取决于上述事实）；
4. t2-prep 零改动复核（对 zero-change-check-1 快照，预期差异 ⊆ 本文件追加）；
5. Codex 只读咨询 D2 设计与证据（用户已授权「有问题可以问codex」）；
6. D4 产品批次 spec 草案 → **停在用户授权边界**（checklist D-4 每项仍需另行授权）。

状态标记（现行）：**T2 v0.1 已冻结（基线 A）；D1–D3 完成（含续五 Codex 复核修复）；D2 进行中——规格与工具就绪、F-1 已修并回归全绿、验证未运行**；D4 未放行。

2026-09-18（续七）**D2 隔离验证完成**（用户晚间指示恢复推进，并授权「claude 的花费任意就行不怕，workbuddy 只有免费额度，用就行」）。四项验收（spec-d2 §6）全过：

1. **L-a/L-b（d2-verify-2，PASS）**：staging 包 14 文件（notes.py + tests 11 + 冻结 spec + public-cases），完整性全对（来源哈希 + MANIFEST + frozen-criteria 三重锚）；秘密语料 45 条（续六笔误「46」更正为 45）0 stale、1 白名单剔除（`已存`＝公开 spec「已存在」合法共现）、44 活跃、扫描零命中。首轮 d2-verify-1 曾剔 2 条 stale（`hidden.py`/`agent-harness-research`），经查为新鲜度源不足——补入 cline-mcp-workspace 编排产物（Codex 审查任务 spec 与 last-message.txt，均为真实评价侧秘密文件）后复活，终版 0 stale。
2. **L-c（d2-probe-1，三次无头探针）**：deny 规则 `//d/` 与 `//D/` 两种盘符写法均生效（官方未明确处实证：盘符大小写不敏感）；deny 按 path 匹配与 cwd 无关（探针 workspace 误置于被拒树内被正确拒绝，设计失误转为有效数据点）；工作区外置（模拟 D4 布局）同 settings 下读取成功，不误伤；`--settings` 的 allow 规则在未信任目录 `-p` 会话生效；**python 子进程成功越界读拒绝树内文件**——残余风险实证，与官方文档口径一致。附：bypassPermissions 探针方案被本会话权限分类器拒绝（理由正当），改用 default + 单条精确 Bash allow 完成同等验证。
3. **零改动复核**：t2-prep 全树 71 文件对 zero-change-check-1 快照重比，70/71 哈希一致，唯一差异 = 本文件（协调日志追加，允许项）。
4. **CC 隔离事实**已蒸馏落 `isolation\claude-code-isolation-facts.md`（官方文档口径，含版本门槛）。

同日 **D4 批次规格草案**落盘 `isolation\spec-d4-batch-v0.1.md`（批次定义、任务包组装、产品 README 要点、cc-1 会话启动参数、wb-1 先查后跑/降级声明、收尾五步评价、记录规范）；Codex 只读咨询（D2 证据 + D4 草案，spec：tmp\task-t2-d2-d4-consult.md）已派发待回。批次执行授权依据用户晚间指示原文（见本段开头引句）。

状态标记（现行）：**T2 v0.1 已冻结（基线 A）；D1–D3 完成；D2 验证完成（四项验收全过，证据在案）；D4 规格草案 + Codex 咨询进行中，批次未开跑**。

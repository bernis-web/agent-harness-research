# 下一步工作计划（本文档为计划交付，本次不实施）

> 交付边界：主要草稿由真实 Claude CLI `glm-5.3-flash --effort low` 生成，协调员仅作证据纠错及范围核对。由主协调员复核并在现有授权内推进；新增高风险/范围另审。下述计划未在本任务实施。

## 完成定义（四层，逐层独立判定，不得混同）
1. **准备就绪**：T1 既有冻结规格版本核对一致、T2 规格确定、合成夹具与离线评价器就绪、D2 隔离方案冻结。准备完成不等于任何真实观察完成。
2. **参考 T1 验证收口**：公开 22 项已有 step11 记录 [E6]，加上 hidden 结果接收核验与评分表版本固化，形成参考 T1 的完整判定（含失败如实记录）。此为参考验证，不称完整产品 T1。
3. **真实产品批次执行完成**（前置：第 2 层收口 + D2 通过）：届时冻结单条完整 T1 及 T2 的规格、产品版本、模型版本、双方同包、运行清单；运行次数当前未知，不得编造。完成须同时具备：获批运行清单、全部成功与失败日志及评分留存、独立评价器判定、双方比较分析、可追溯的局限说明。缺任一项不得称批次完成。
4. **研究分析交付完成**：基于第 3 层真实产品观察回答 RQ1，并将 RQ2-4 作为机制解释或待检验假设，明确非因果证据的局限。当前 step11 是参考实现验证而非产品观察，不能声称已证明 RQ2-4 因果。整体研究完成取决于已确认的研究范围与所需证据闭环，不机械要求跑满旧 2x2/实验 C/7 个候选——候选是否纳入按证据需要单独审批。

## 里程碑（每个含依赖/任务/判据/证据）

### M0 隐藏 worker 结果接收（可与 M1/M2 并行）
- 依赖：hidden worker 完成（用户告知执行中，时间未知）。
- 任务：接收负责 worker 的公开脱敏报告、所用版本、判定结论、产物路径与哈希；核对报告出处与覆盖范围是否与 hidden 用例集一致；不看隐藏案例内容，不重复、不代跑。
- 完成判据：报告入档且出处、范围、版本核验一致。缺证（无版本/无哈希/范围不明）不计通过，标注未核验。
- 证据：hidden 报告路径+哈希+版本说明。负责人：协调员。

### M1 T2 规格、夹具与新离线评价器准备（建议下一动作，待实施，不触旧 P2）（可与 M0 并行，不依赖 hidden 摘要）
- 依赖：接收现有 T2 spec worker 在 `D:/projects/agent-harness-research/experiments/t2-prep/` 准备的草案（主协调员告知，非本任务实测或定稿证据）。由主协调员复核并在现有授权内推进；仅确实缺失的关键语义需澄清，不重复启动规格工作或追问费用。
- 任务：复核并承接现有 worker 的 T2 草案，不接管或重复起草；按复核版本配套合成夹具（synthetic 标注）与新离线评价器，仅用受信任人工样例验证，不触旧 P2。
- 完成判据：规格经主协调员按现有授权复核并冻结版本；夹具与评价器通过离线验证，未接触真实模型输出。
- 证据：规格文件、夹具哈希、评价器运行记录。负责人：执行 worker，协调员核对。用户持续授权下按已确认范围推进，不逐步凭空追加审批。

### M2 D2 隔离验证
- 依赖：无（可与 M0/M1 并行）；通过前真实产品批次不放行。
- 任务：不照搬旧运行器设计 §7 作为当前验收协议——旧文档仅作原则依据 [E4]。需独立制定并冻结隔离方案与测试矩阵：(a) 用受信任、无敏感内容的合成探针验证越界读写被拒绝；(b) 网络策略生效；(c) 进程超时与衍生进程清理；(d) 以无敏感替身评价资产验证不可达、不可篡改，不读取既有隐藏用例；(e) 日志可追溯。任一项未具备即失败关闭（拒绝执行真实生成代码，不降级）。
- 约束：不读取真实凭据；不以"运行试试"方式执行不可信产品代码；cwd/临时目录/禁工具配置不构成 OS 级隔离证明。
- 完成判据：隔离方案冻结 + 测试矩阵全项通过留档。证据：验收脚本输出、各拒绝路径测试日志。负责人：执行 worker，用户核对验收。

### M3 参考 T1 验证收口（命名：参考 T1 验证收口，不称完整产品 T1）
- 依赖：M0 完成。
- 任务：hidden 结果核验（依 M0 证据）+ 人工评分表固化并定版本 [E5]。
- 完成判据：参考 T1 综合判定（公开 22 项记录 + hidden 判定 + 评分表版本）成立或如实记录失败。证据：判定文档、评分表版本哈希。

### M4 真实产品批次（条件触发，本次不启动）
- 依赖：M1 完成、M3 收口、M2 通过，并冻结完成定义第 3 层的运行协议与清单。
- 任务：按已审定的 T1/T2、WB/CC 清单执行；两产品使用同一公开任务包，参考实现与隐藏资产不提供给产品。单条完整任务评分单列，不套用旧六阶段体系。
- 完成判据与证据：清单内运行均有最终状态，成功、失败、中止与重试均留原始日志和独立评分；版本、任务包哈希、执行证据与评分逐项可追溯。缺项明确登记。

### M5 分析交付与条件候选
- 依赖：M4 结果与独立评分齐备。任务：形成双方比较分析、逐任务证据表及局限说明；完成判据：每项结论可追溯，失败和缺失不隐藏，RQ1 观察与 RQ2-4 因果假设明确分开；证据为分析报告及数据索引。
- 旧 P4（102 次）与实验 C 仅是条件候选：若恢复，须先审阅旧设计、可控先导、既有证据与范围并单独审批，不因 T1/T2 结束自动启动 [E9][E10]。7 个候选扩展逐项评估、按证据需要单独决定。持续授权覆盖已确认范围内推进，范围变化另行处理。

## 边界重申
- 本次为纯文档交付：未跑浏览器/产品，未读隐藏用例，未碰旧 P2/KG/记忆/隐私/配置，未实施任何计划项。文中历史结果仅核对既有记录。
- 费用边界：不限额与可用模型限于已确认范围，不扩展其他 API/产品，不将费用事项与范围/安全门槛混同。

## 证据编号映射
- [E1] `D:/projects/agent-harness-research/research/01-scope/研究问题与边界.md`
- [E2] `D:/projects/agent-harness-research/research/02-design/先导任务说明.md`
- [E2补] `D:/projects/agent-harness-research/research/02-design/评分规则.md`
- [E3] `D:/projects/agent-harness-research/research/02-design/数据契约.md`
- [E4] `D:/projects/agent-harness-research/research/02-design/运行器设计.md`
- [E5] `D:/projects/agent-harness-research/experiments/t1-prep/README.md`
- [E6] `D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/step11-visible-04/REPORT.md`
- [E7] `D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/step11-visible-04/final-verification.json`
- [E8] `D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/step11-visible-04/evidence-index-validation.json`
- [E9] `D:/projects/agent-harness-research/docs/superpowers/plans/2026-09-15-claude-code-long-horizon-research-plan.md`（L226–234，P4 规模）
- [E10] `D:/projects/agent-harness-research/docs/superpowers/plans/2026-09-15-claude-code-long-horizon-research-plan.md`（L296–307，可选 C）
- [E11] `D:/projects/agent-harness-research/experiments/project-continuation-20260918/current-user-context.md`（协调员上下文摘要，非用户原始文件、非独立执行证据）

# 项目状态（2026-09-18，本次交付为纯文档修订，未执行任何批次）

> 交付边界：主要草稿由真实 Claude CLI `glm-5.3-flash --effort low` 生成，协调员仅作证据纠错及范围核对。由主协调员复核并在现有授权内推进；新增高风险/范围另审。下述计划未在本任务实施。

## 证据与优先级说明
- 证据根：D:/projects/agent-harness-research/。引用优先级：最新用户指令 > 最新验证记录 > 旧设计文档。
- [E11] D:/projects/agent-harness-research/experiments/project-continuation-20260918/current-user-context.md 是协调员保存的用户/父协调员上下文摘要，不是用户原始文件，也不是独立执行证据；摘要中的进度按“告知”定性，未经本任务核验不升级为完成结论。

## 研究主线与当前范围
- 主线：长程软件开发任务中智能体持续执行机制研究，以 Claude Code 为观察对象 [E1]。RQ1 行为观察 / RQ2 状态交接 / RQ3 测试反馈 / RQ4 交互；RQ5/实验 C 为条件候选，需单独范围审批 [E1][E9]。
- 当前活跃范围（来自 E11，非旧 scope）：T1 为单条完整任务（本地单文件思维导图应用）的准备与验证；T2 spec worker 已在 `D:/projects/agent-harness-research/experiments/t2-prep/` 准备草案（主协调员告知，本任务未读取或核验该草案，不代表已定稿或实测完成）；WB/CC（WorkBuddy/Claude Code）当前上下文亦来自 E11。旧 dsh/六阶段 PA/PB、2x2 实验 B 及候选扩展不在当前执行范围 [E2][E3]。

## 已完成（有证据）
- P0/P1 八份规格文档（范围、先导任务 v2.1、评分规则 v2.1、数据契约、运行器设计等）已存在；其中本任务已读的四份 P1 文档自述为待审/复审状态，其余 P0 文档未逐一核验。文档存在与自述状态均不等于验收通过 [E1][E2][E3][E4]。
- T1 冻结规格 v1.0、参考实现、公开验收手册已编写于 D:/projects/agent-harness-research/experiments/t1-prep/README.md；编写过程未跑浏览器、未装依赖、未调 API [E5]。README 称其为“v1.0（冻结稿）”；其中“已编写、未执行”是创建时旧状态，最新 REPORT 已补充公开批执行证据。不撤销既有冻结状态，也不修改旧 README。
- step11 历史运行：可见项验证 PASS，真实浏览器单次运行，22 公开项通过，final-verification.json 全项通过，清理完成 [E6][E7][E8]。旧 21 项未重跑，仅核对源结果与 39 份证据文件 SHA256 [E6]。

## 未完成 / 未知
- "hidden 与 D2 未执行"仅限 step11 历史运行时点。当前状态（用户告知，E11）：hidden worker 已在 verification-hidden-01 执行中，结果未知，本任务不读取、不重复隐藏用例，不写作已通过或已失败。
- D2（真实产品生成代码隔离）未验证、未放行 [E4][E11]。
- T2 草案由现有 spec worker 准备中（仅告知），具体版本、规格与定稿状态尚未核验；9/15 scope 文档自述待审核，其审核结论未知；实际产品运行清单、版本及 D2 验收结果也尚未在本任务确认。
- 22 公开项 PASS 不等于参考 T1 验证收口；hidden 结果未知。当前已核对的是参考实现验证记录，不是 WB/CC 真实产品观察结果，更不能声称已证明 RQ2-4 的因果关系。

## 安全边界（当前任务约束）
- 本任务禁跑浏览器/产品、禁读隐藏用例/旧 P2/KG/记忆/私有配置、禁安装、禁提交 [E11]。
- 此为本次任务的禁跑约束，非永久绝对限制：用户已给持续推进授权，未来获准范围内的工作无需逐项重复申请；但 D2 安全验收必须通过，范围变化或新增其他 API/产品须另行处理，持续授权不构成 D2 放行。
- 费用：Claude/ZCode 不限额，可用 glm53/flash（用户告知，不再追问）；不据此扩展其他 API/产品。

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

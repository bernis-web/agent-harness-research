# run-protocol-draft.md

同口径运行协议草案（WB / CC）

日期：2026-09-18。性质：纯文档草案，本轮未执行任何被测产品实验、系统/网络探测；所有未知值一律 null，不填 0，不凭本次撰写用 Flash CLI 配置反推被测 CC 的配置。

## 1. 运行配置卡（YAML 模板）

```yaml
run:
  run_id: null                 # 运行时生成，唯一
  task_id: null                # 关联 T1/T2 任务包标识
  protocol_version: null       # 本协议冻结版本号，运行前冻结

product_identity:
  product: null                # 每个 run 填 WB 或 CC，不得填执行者身份
  actual_product_version: null # 运行时实测，未知即 null，不得从历史告知转抄
  version_verified_at: null    # 实际观测时间，未观测即 null
  provider_model_id: null      # 被测产品实际使用的模型/供应商标识，实测填写

execution_policy:
  tool_policy: null            # 工具可用范围，运行前冻结
  approval_policy: null        # 审批策略，运行前冻结

inputs:
  workspace_bundle_hash: null  # 工作区包 hash，封存后不再改动
  input_bundle_hash: null      # 输入任务包 hash
  run_list_ref: null           # 预先冻结的本批运行清单，不边跑边择优
  attempt_id: null
  parent_attempt_id: null      # 重试关联原件；不是旧六阶段编号

observation:
  evidence_path: null          # 观察证据（事件流/日志/产物）存放位置
  product_cost_amount: null   # 被测产品费用，未知 null
  currency: null
  input_tokens: null
  output_tokens: null
  cost_basis: null            # 实测/账单估计及来源，不把 CLI 估计当账单
  resource_usage: null         # CPU/内存/墙钟等实测，未知 null

historical_report:              # 单独字段：仅历史告知，非当前版本，本次未核验
  reported_versions:
    - product: WB
      version: "5.5.6"
    - product: CC
      version: "2.1.273"
  reported_on: "2026-09-18"
  observed_on: null
  status: "历史告知；本次未核验，不代表当前实际版本"

executor_identity:              # 单独字段：本次撰稿 CLI，非被测身份
  role: "文档撰写执行者"
  model: "glm-5.3-flash"
  effort: "low"
  cli_version: null             # 未知，不臆测
  note: "该身份仅用于撰写本文档，不作为被测 CC 的任何证据"
```

## 2. 任务下发与修复策略

- T1 为公开完整任务包，仅一次性下发；不改造为六阶段或分批投递。
- 后续修复/澄清逐条记录在事件流中，且对 WB/CC 两路采用完全相同的下发与澄清策略（同口径）。
- 不向任何一路提供参考实现、隐藏答案或差别化提示。

## 3. 事件字段最低要求

每条事件至少包含：

| 字段 | 说明 |
|---|---|
| seq | 单调序号 |
| run_id | 关联运行 |
| time | 含时区墙钟时间 + 单调时钟读数 |
| actor | 产生主体（产品/人工/评价器） |
| event_type | 事件类型 |
| human_intervention | 是否人工介入及内容摘要 |
| approval_wait_start / approval_wait_end | 审批等待起止 |
| elapsed_wall / elapsed_active / approval_wait_total | 墙钟/有效执行/审批等待时长 |
| tool_action | 工具动作摘要与结局 |
| failure_class | 失败分类及证据引用（不含敏感内容） |
| unknown 字段 | 一律 null；仅实际测量得到 0 才写 0 |

重复失败只累计计数，不采用“三次自动停”策略；达到冻结的时间/资源上限单列限额终止，安全违规立即失败关闭。功能失败本身不触发三次停。

事件枚举至少含 run_start、input_sent、tool_action、approval_wait_start/end、human_intervention、evaluation、failure、artifact_sealed、cleanup、run_end。墙钟从开始到终态连续计时；审批等待按起止区间合并统计，不重复累加；有效执行仅由可观测活动区间累计，无法观测则 null，不能简单把“墙钟减等待”冒充实测。审批等待未结束时保留 open 与截止时间；从未发生且记录完整才可记 0。

## 4. 真实功能失败的处理

- 真实功能失败是有效研究结果，不是流程事故。
- 记录：失败 check、期望 vs 实际；冻结当时产物、公开输入 hash、脱敏日志；附独立评价器结论。
- 不边修边覆盖：失败现场封存后，重试以新 attempt 进行并关联原 attempt。
- 安全违规、超时、基础设施失败单列分类，与功能失败区分。
- 所有样本（含失败）全部保留，不选赢家、不淘汰样本。

## 5. 时间与资源拟定值（仅供讨论，非已设置）

| 项 | 拟定值 | 状态 |
|---|---|---|
| 有效执行 | 60 min | 拟定，未设置 |
| 含等待墙钟 | 90 min | 拟定，未设置 |
| 单次审批等待 | 30 min | 拟定，未设置 |
| 子进程单次 | 60 s | 拟定，未设置 |
| 清理 | 15 s | 拟定，未设置 |
| 受限执行域 | 2 vCPU / 4 GiB | 拟定，未设置 |
| 产物上限 | 500 MiB | 拟定，未设置 |

适用范围：前三项针对单个 run，子进程/清理项针对生成代码的受限执行域，2 vCPU/4 GiB 针对该域而非宿主客户端，500 MiB 仅针对任务产物。主协调员按公平规则冻结后采用；无法强制执行的项目必须标注监测性限额或 blocked，不能声称已强制设置。两路变更需同版记录并处理可比性，不为单组临时加码。

## 6. 成本与归因边界

- 成本不限额 ≠ 无限进程；费用指标可未知（null），不得填 0。
- 执行者（撰稿 CLI）成本与被测产品成本分账，不混记。
- 不同底模、产品版本、环境差异作为混杂因素逐项记录；不得将此类差异归因为 Harness 因果。

## 7. 证据路径（均为摘要/协调文档，非独立原始证据）

1. `D:/projects/agent-harness-research/experiments/project-continuation-20260918/project-status.md` —— 上游协调文档，摘要性边界说明。
2. `D:/projects/agent-harness-research/experiments/project-continuation-20260918/next-work-plan.md` —— 计划文档，不构成执行证据。
3. `D:/projects/agent-harness-research/experiments/project-continuation-20260918/protocol/context-summary.md` —— 本轮上下文摘要；文中历史版本来自告知，非本次新核验。

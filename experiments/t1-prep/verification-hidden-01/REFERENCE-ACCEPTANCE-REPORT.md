# T1 参考实现验收收口报告

日期：2026-09-18
范围：仅冻结 T1 参考实现，不是 WorkBuddy/Claude Code 被测产品，不是 D2，也不代表整个研究项目完成。

## 结论

- 公开验收：22 项通过的既有证据已复核引用；本轮未重跑这 22 项。
- 隐藏验收：H1—H9 共 101 个固定子步骤，实际专用浏览器运行 1 次，101/101 PASS；REFERENCE_FAILURE=0，DRIVER_ERROR=0，驱动退出码 0。
- 保护文件：明确白名单中的 7 个规格/参考/验收文件前后未变；参考实现 SHA-256 为 `c3811f4e772e53fdbf4a047f015eebd2eb6f57df90e497c4b78608af0f5904ad`。
- 评价器边界：运行器是当前参考实现的专用 UI 适配器，不是未来产品的通用评价器；红色提示、DOM 选择器等实现细节不计为通用规范。

## 证据

- 隐藏运行结果：`attempt-01/evidence/results.json`
- 运行元数据：`attempt-01/execution-meta.json`
- 固定序列核对：`coordinator-action-check.json`
- 101 步证据核对：`coordinator-evidence-check.json`
- 合并摘要：`merged-reference-summary.draft.json`
- 清理审计：`cleanup-audit.json`
- 评价器限制：`reference-evaluator-limitations.md`

## 过程偏差

此前发生一次范围偏离：协调步骤读取了旧实验浏览器档案字节用于哈希（涉及 1,256 个档案文件；未发送给模型），另有一次全仓文件元数据枚举（未读取文件内容）。两项均已停止，原始记录保留；该偏差不作为功能通过证据，也不被隐藏。

## 未完成事项

- T1 参考实现验收收口不等于真实产品观察完成。
- T2 仍是待会审的规格/验收准备文档，产品、测试、变异均 UNRUN。
- D2 隔离资格未验证，真实生成代码不得据此放行。
- 旧 102 次正式批次、实验 C 与 7 个候选扩展未自动启动。

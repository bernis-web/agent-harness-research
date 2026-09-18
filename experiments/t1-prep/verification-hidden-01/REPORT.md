# T1 冻结参考实现隐藏验证收口报告

- **报告日期**：2026-09-18
- **范围**：冻结 T1 参考实现的隐藏 H1-H9 自动化参考验证；仅写入本目录。
- **结论**：**H1-H9：9/9；101/101 子步骤 PASS；未发现参考实现功能失败或驱动错误。**
- **边界**：这是参考实现功能验收证据，不是 D2、不是整个项目完成、不是未来被测产品通过，也不是人工验收。

## 1. 运行结论

| Case | 子步骤 | PASS | 参考失败 | 驱动错误 | 结论 |
|---|---:|---:|---:|---:|---|
| H1 | 10 | 10 | 0 | 0 | PASS |
| H2 | 3 | 3 | 0 | 0 | PASS |
| H3 | 20 | 20 | 0 | 0 | PASS |
| H4 | 3 | 3 | 0 | 0 | PASS |
| H5 | 22 | 22 | 0 | 0 | PASS |
| H6 | 8 | 8 | 0 | 0 | PASS |
| H7 | 4 | 4 | 0 | 0 | PASS |
| H8 | 23 | 23 | 0 | 0 | PASS |
| H9 | 8 | 8 | 0 | 0 | PASS |
| **合计** | **101** | **101** | **0** | **0** | **参考实现功能验收 PASS** |

本轮唯一浏览器运行：2026-09-18 11:37:40-11:38:01（+08:00），driver/browser 均以退出码 0 结束。每个子步骤均保留一张 PNG 截图和一个 DOM/状态 JSON；结果原件见 [results.json](attempt-01/evidence/results.json)，逐步索引见 [CASE-INDEX.md](CASE-INDEX.md)。

## 2. 固定序列与重点覆盖

- 所有 101 个操作组均与冻结枚举的固定序列一致；协调员审计的 allActionsMatchEnumeratedFixedSequence=true。
- H5：4 次 reset、6 次真实文件导入；包含独立与共享设置。
- H8：10 次编辑、10 次恢复性撤销；第 11 次撤销无效果，仍验证为 PASS。
- H9：5 次重命名尝试（1 次有效、4 次拒绝）及 1 次撤销。
- H1 的空输入/三空行拒绝、H3 的层级/Tab 边界、H6 导入后撤销无效果、H7 删除恢复等，均以可见 DOM 树和行为结果核对。
- 导入通过真实文件选择器完成；没有注入应用内部状态。

## 3. 评价方法与限制

本轮只评价真实 UI 操作、可见 DOM 有序树、可见消息和行为撤销；不读取内部栈或应用状态来判定。浏览器为专用全新 task-local profile/HOME/temp/downloads，headless、Chromium sandbox 开启；离线运行并拦截 HTTP(S)，只打开冻结 reference 的 file:// 页面。

红色错误文字是**本参考实现适配器的辅助判据**，不是规范对所有未来产品的通用判据；未来通用评价器必须与本参考适配器分开设计。更完整的限制说明见 [reference-evaluator-limitations.md](reference-evaluator-limitations.md)。

## 4. 公开链合并口径

此前公开链已有 22 项通过：旧 public-continuation-01 的 21 项，加上 step11-visible-04 的原生取消验证 1 项。本轮仅引用这些既有证据，不重跑、不递归扫描旧证据；本轮新增 H1-H9 的 9 个隐藏 case、101 个子步骤。

因此可报告为：**冻结 T1 参考实现：公开 22 项 + 隐藏 H1-H9 通过的参考验收汇总**。不得扩展解释为 D2、全项目完成或产品/通用评价器通过。合并文件见 [MERGED-REFERENCE-ACCEPTANCE.md](MERGED-REFERENCE-ACCEPTANCE.md) 与 [merged-reference-summary.json](merged-reference-summary.json)。

## 5. 保护范围与过程偏离

最终保护核对严格限于 7 个精确冻结文件，前后均 unchanged：

1. README.md
2. experiments/t1-prep/README.md
3. experiments/t1-prep/spec/T1-规格-冻结-v1.0.md
4. experiments/t1-prep/reference/mindmap.html
5. experiments/t1-prep/reference/README.md
6. experiments/t1-prep/acceptance/验收手册-公开链与片段.md
7. experiments/t1-prep/acceptance/hidden-cases.md

需单独保留并明确：最初曾发生一次错误的广泛 SHA-256 扫描，读取了项目内 2,146 个文件，其中包括历史 browser profile 下 1,256 个文件。按既有类别清单统计：Cookies 0、Login Data 0、Web Data 0、History 2、Preferences/Secure Preferences 2、Local State 1、Local Storage 10、Session Storage 10、Device Bound Sessions 4、EdgePushStorage 3。读取用于计算 hash，未解析、复制、展示；这些材料未发送给模型。该偏离已告知并记录，保留 protected-before.json、scope-deviation.json 等原始记录；后续改为精确 7 文件白名单，禁止再递归/读取/哈希旧浏览器档案。

功能 PASS 不抵销该过程不合规；两者在报告中分开。

## 6. 模型与审计收口

真实 Claude CLI 使用 glm-5.3-flash --effort low 完成脚本设计/实现与审查，正常认证继承但未读取凭据；tools、MCP、hooks、skills 均禁用。成功调用及协调员差异保留在本目录。之后两次审计调用分别在 360 秒和 180 秒边界超时，未形成可用审计结果；没有因超时追加模型调用，也没有据此虚构结论。现有协调员证据已足以支持本轮功能收口。

## 7. 网络、清理与证据完整性

- 17 个请求事件均为当前 reference 的 file URL；HTTP(S) 请求数为 0。
- 无主机设置修改、无安装、无网络资源。
- 仅关闭本轮自己创建的 browser/context/driver；记录显示 pagesAfterClose 为空，browser/driver 退出码均为 0。
- 证据包含 101 个截图、101 个状态 JSON、23 个输入 fixture、actions/network/launch/close/results 等原始文件。证据索引及其校验见 [evidence-index.json](evidence-index.json)、[evidence-index-validation.json](evidence-index-validation.json)。
- 精确 7 文件保护 hash 的前后记录见 [protected-before-whitelist.json](protected-before-whitelist.json) 与 [protected-after-whitelist.json](protected-after-whitelist.json)；清理状态见 [cleanup-audit.json](cleanup-audit.json)，仅检查已记录 PID，不枚举、不杀进程。

## 8. 最终判断

**本轮没有需要修复冻结参考实现的功能缺口。** 后续只需保留本报告、逐步证据及偏离记录；不再进行模型反复润色或扩大测试范围。参考适配器与未来通用评价器应保持分离。

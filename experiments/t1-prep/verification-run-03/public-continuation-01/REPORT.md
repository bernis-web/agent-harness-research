# T1 公开续验报告

状态：PARTIAL_VERIFIED_STEP11_BLOCKED。本报告仅覆盖本目录证据，不宣称整批或完整T1通过。

## 结果
- 本轮剩余13项：12 PASS / 0 FAIL / 1 UNTESTED（11）。
- 连同必要前置1—9重建：21 PASS / 0 FAIL / 1 UNTESTED，共22项。
- PASS：1—10、12a—12d、A1—A4、B1—B3。
- B1的10次编辑、B2的10次撤销均逐步断言并截图；B3验证第11次撤销无变化。最终编辑/撤销截图已作目视检查。
- 12b以真实UI执行“改名→撤销→再次空撤销→再改名”，验证并重建导入前置；没有读取内部撤销栈。

## 第11项阻塞及顺序调整
无头浏览器未监听选择器时产生 isTrusted=true 的 cancel，但没有用户操作原生窗口，因此归类 BROWSER_AUTO_CANCEL，而非真实用户取消。监听选择器后，实际页面 Escape 没有产生 cancel；现有FileChooser只暴露 element/isMultiple/page/setFiles，没有cancel接口。
第11项只有自动取消相关部分证据，完整验收为UNTESTED / BLOCKED_HEADLESS_NATIVE_CANCEL，不是产品失败。未用合成事件、空setFiles或内部状态调用冒充取消；未弹可见窗口。按用户明确许可，跳过这一能力阻塞后继续独立12/A/B。
下一最小动作：单独取得可见浏览器/原生窗口交互授权，或先证明可用的真实原生取消接口，再仅补验11；当前不额外运行。

## 真实模型来源
两次Claude CLI均显式 glm-5.3-flash / effort low，正常客户端自身认证，工具为空、严格空MCP、hooks/memory关闭；未读取认证配置。
- 原生取消探针：PID55440，2026-09-17 20:57:13—20:57:43 +0800，29.894秒，exit0，有成功模型响应。
- 10—12续验模块：PID61696，2026-09-17 20:59:40—20:59:57 +0800，16.940秒，exit0，有成功模型响应。
原始模型脚本保留；1—9、A/B和harness复用此前真实Flash产物。Codex只审阅、修正并记录驱动定位/顺序/固定预期问题，编排执行及收口；具体改动见两份review.json。未将Codex改动冒称模型原文。

## 边界与完整性
file://、专用profile/temp/home/downloads、无头、沙箱启用，页面offline及HTTP(S)路由阻断；无安装、HTTP服务、日常profile或宿主设置更改。H1—H9、D2及产品比较均未执行；参考实现未修改。
五个受保护文件前后SHA256全部一致。120个引用截图/状态文件均非空，B1/B2各10个PASS子步骤。397字节下载原件保留副本及saveAs文件与独立固定预期逐字节及JSON均一致，SHA256为 df8f17fbed15145cf88c091521a471fd1e0298d43388f55e3c0c1467a5020915。原始临时下载路径与保留副本分开记录，不声称临时原件关闭浏览器后仍存在。
Git最终仍只有未跟踪experiments/与research/，无已跟踪文件差异。收口仅检查现有证据，未重跑CLI或浏览器。

## 精确证据索引（均已核验存在）
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\evidence\results.json`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\summary.json`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\cancel-probe\evidence\probe-results.json`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\cancel-probe\evidence\events.jsonl`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\evidence\actions.jsonl`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\evidence\fixed-expected-comparison.json`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\evidence\download-evidence.json`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\evidence\preserved-original-evidence.json`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\evidence\export-original-preserved.json`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\evidence\downloads\t1-map.json`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\evidence\snap-B1-edit10.png`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\evidence\snap-B2-undo10.png`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\model-cancel-probe\model-call.json`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\model-cancel-probe\result.json`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\model-continuation\model-call.json`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\model-continuation\result.json`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\model-call-summary.json`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\execution\review.json`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\cancel-probe\review.json`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\protected-before.json`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\protected-after.json`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\evidence-audit.json`
- `D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\git-final.txt`

## 变更清单
所有本轮新增脚本、模型派单/响应、诊断和验收证据、报告均限于：

directory: D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\public-continuation-01\

完整逐文件路径、大小、SHA256见同目录 changed-files.json（不对该清单自身作自引用哈希）。浏览器运行时profile/home/temp仅记录目录，不读取或哈希内部内容。旧run03现场及父级报告不覆盖，AGENTS/guidance不修改。

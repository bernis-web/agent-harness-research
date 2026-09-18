# T1 verification-run-03 — 收口

状态：STOPPED_AT_STEP_9_DOWNLOAD_CANCELED。公开批 8 PASS / 1 FAIL / 13 UNTESTED；不宣称 T1 全量通过。

## 真实外部派单
Claude CLI 正常客户端认证、显式模型 glm-5.3-flash、effort low，三个小任务均返回成功完整代码：harness 56.312秒/PID59612；public-chain 148.671秒/PID54368；fragments 16.362秒/PID59984，均退出0。原代码、result.json、model-call.json位于 D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/attempt04-model-glm53/flash-modules。实际驱动作者为 Claude/glm-5.3-flash；Codex仅静态审核、修正明显驱动错误、粘合执行。

历史区分：attempt01 bare认证失败；attempt02普通路径超时；attempt03 Flash READY成功；attempt04 glm-5.3及大Flash任务仅thinking无完整正文、超时。不是统一认证失败。ZCode未发模型请求，原因是未确认禁MCP/hooks/记忆的受限组合。

## 环境与执行
复用已通过 preflight.json：about:blank截图、file://、隔离专用profile、沙箱启用、下载受控目录与CDP原件/saveAs哈希、页面网络阻断。此次无安装/HTTP服务/日常profile/认证配置读取/安全关闭。预检受控data下载成功不保证reference的blob下载成功。

首轮 D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/public-batch-01：1—8通过，第9步驱动只等completed事件而忽略canceled，300秒总上限退出124，PID59324。保留 harness.review01.cjs、run.batch01.cjs与原始 evidence，不将工具超时算产品失败。
唯一短复核 D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/public-batch-02：加入CDP实时事件、Playwright failure()、15秒事件等待上限、75秒总上限。约18.7秒退出1，PID56612。第9步收到397字节的进度后CDP state=canceled，Playwright failure()=canceled，页面显示“已发起导出下载”；没有完成的文件原件或saveAs，无法证明JSON同构/哈希。立即停止，不改实现、不再重试。下载验收现象失败，但实现/浏览器环境根因未归属，不记为已证明产品逻辑缺陷。

## 逐项结果
| 项 | 状态 |
|---|---|
| 1 | PASS |
| 2 | PASS |
| 3 | PASS |
| 4 | PASS |
| 5 | PASS |
| 6 | PASS |
| 7 | PASS |
| 8 | PASS |
| 9 | FAIL：DOWNLOAD_FAILURE: canceled |
| 10 | UNTESTED：Stopped immediately after step9 download failure |
| 11 | UNTESTED：Not reached; genuine native file-picker cancellation also unsupported by this headless driver |
| 12a | UNTESTED：Stopped immediately after step9 download failure |
| 12b | UNTESTED：Stopped immediately after step9 download failure |
| 12c | UNTESTED：Stopped immediately after step9 download failure |
| 12d | UNTESTED：Stopped immediately after step9 download failure |
| A1 | UNTESTED：Stopped immediately after step9 download failure |
| A2 | UNTESTED：Stopped immediately after step9 download failure |
| A3 | UNTESTED：Stopped immediately after step9 download failure |
| A4 | UNTESTED：Stopped immediately after step9 download failure |
| B1 | UNTESTED：Stopped immediately after step9 download failure |
| B2 | UNTESTED：Stopped immediately after step9 download failure |
| B3 | UNTESTED：Stopped immediately after step9 download failure |

B1/B2没有运行，绝不声称十次逐步编辑/撤销已验；步骤11未到达，且headless真取消路径未验证。H1—H9未读取或执行；无D2/其他产品比较。

## 证据与改动
- 截图：D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/public-batch-02/snap-9-fail.png（已目检）、snap-1.png—snap-8.png；首轮snap-8.png已目检。
- 下载事件：D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/public-batch-02/actions.jsonl；error-9.json、execution-error.json、results.json。
- 驱动修正列表：D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/attempt04-model-glm53/flash-modules/execution/review-fixes.json；*.original.cjs为外部原稿。
- 归档/索引：results.json、model-call-summary.json、changed-files.json、git-final.txt、protected-final.json；本次所有写入限run03。
- 五份受保护材料SHA256全部保持不变：true；git状态仍只有未跟踪experiments/、research/，tracked diff为空。旧现场、产品配置、sensor-array均未触碰。

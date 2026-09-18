# T1 步骤11真实可见原生取消补验 — step11-visible-02

## 结论
**BLOCKED / UNTESTED；11 未通过，不记产品失败。** 原有21项PASS仅沿用已核对的旧证据，本次没有重跑。汇总为21旧PASS + 1新阻塞；不能称为22项通过或完整T1通过。

本次唯一浏览器运行：2026-09-18 00:04:20—00:04:44（Asia/Shanghai；日志UTC为2026-09-17T16:04:20.935Z—16:04:44.613Z），驱动PID35832，exit1。不是重复启动。

## 本次实际执行
1. 核对仓库根至目标目录的AGENTS/AGENTS.override候选链（这些目录未发现附加文件），阅读用户提供AGENTS、全局dox-hierarchy/windows guidance、PowerShell安全技能与相关能力段落。Git前后均只有未跟踪experiments/与research/；tracked diff为空。
2. 旧step11-visible-01错误发生于原生取消之前：读取不存在的processList字段，属于驱动错误。保留旧results.json原样，不沿用其中FAIL标签作为产品结论。
3. 实际派发两次本机Claude CLI，均显式glm-5.3-flash / --effort low。调用器复用旧model-native/invoke-stream.py；无模型工具、严格空MCP、hooks关闭、无会话持久化，未读取凭据配置。第一次20.939秒/PID36532，错误建议嵌套info.processList，被Codex审核拒绝。第二次55.833秒/PID36700，依据本机Playwright protocol.d.ts:18565—18570改为processInfo，采用其最小字段/PID校验修复及close错误传播。两次响应及拒绝理由均保留。
4. Codex仅审核、应用修复并编排：补加原始CDP响应写盘（模型漏给）、新目录runner及真实cleanup记录。四个离线驱动用例通过，三个运行脚本语法检查通过。原生native_cancel.py原样继承。没有修改reference/spec/manual或原21项测试。
5. 新可见Chrome，专用profile/home/temp/downloads均在本目录evidence下；headless=false、chromiumSandbox=true，无--no-sandbox；file://访问，offline与HTTP(S) routes abort、serviceWorkers block。没有安装、HTTP服务、系统设置更改或日常profile读取。
6. 仅UI生成临时树、改名、导入已核对的任务JSON，重建post10。JSON与旧导出逐字节一致，SHA256=df8f17fbed15145cf88c091521a471fd1e0298d43388f55e3c0c1467a5020915。前置导入使用非空setFiles，仅用于已授权前置；取消阶段没有setFiles([])、合成cancel或内部状态修改。
7. before-cancel树与JSON一致、errors=[]，页面明确显示导入成功及撤销记录已清空；目标页面截图已目检。
8. CDP返回processInfo并记录browser id32640。点击导入按钮完成（clickOk=true），原生助手仅在该PID且owner为该PID Chrome顶层窗口的范围寻找对话框；20秒内未找到满足条件者，记录DIALOG_NOT_FOUND。没有得到对话框HWND/owner、没有执行Cancel点击、没有Cancel截图、没有trusted cancel/change事件。不能据此断言对话框曾显示，也不能把DOM按钮点击当作原生取消。
9. 严格按归属不可靠即停：没有扩大到其他PID/日常窗口，也没有第二次浏览器运行。after-cancel及after-undo未执行，因此本次没有树保持或撤销无效果的最终证据。

## 外部人为关闭与启动状态
用户补充此前手动关闭窗口并授权重新启动；这被记录为外部人为操作，不是实现失败。收到补充时实时检查显示本轮还没有启动（新证据只有downloads，没有execution-meta）。启动前编排曾因REPL禁止动态求值及不存在process对象中断，均发生于浏览器spawn之前；独立测试脚本通过后修正编排，随后仅启动上述一次实例。没有把此次DIALOG_NOT_FOUND无依据地归因于用户关窗。

## Cleanup与边界
- ownedContextCloseCompleted=true，pagesRemaining=0；Flash修正后close不再吞异常。
- 驱动exit1；未使用全局进程结束命令，只关闭本轮持有的浏览器上下文。
- 结束后按精确PID查询：35832不在；32640当时对应conhost而非Chrome。PID并非稳定进程身份，未终止该进程，不声称所有历史PID均消失。上下文关闭证据与OS观察分开记录；该观察也意味着不能凭CDP PID单独证明本机窗口归属。
- 所有新内容限step11-visible-02。未截图全桌面或日常窗口；本次仅目标页面截图，未进入Cancel控件截图阶段。不读取profile内部内容或巨大模型流。
- 五保护文件前后SHA256全部一致，并与旧基线一致。未改旧证据、AGENTS/guidance、reference、spec、manual；未运行隐藏项、D2或其他产品操作。

## 21旧 + 1新证据索引
完整逐项索引：D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/step11-visible-02/evidence-index.json。旧PASS为1—10、12a—12d、A1—A4、B1—B3，来源D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/public-continuation-01/evidence/results.json；本次核对21项所引用证据文件存在、非空并记录哈希，没有重跑。第11项指向本目录新证据，并显式列出缺失的原生取消及后态证据。

| 证据 | 路径（本报告目录下） |
|---|---|
| 本次11状态 | evidence/results.json |
| 原生未找到窗口 | evidence/native-result.json |
| 点击按钮/助手退出 | evidence/native-run.json |
| CDP原始进程响应 | evidence/cdp-process-info.json |
| 前置树/无错误/页面截图 | evidence/snap-before-cancel.json、evidence/snap-before-cancel.png |
| 实际操作 | evidence/actions.jsonl |
| 关闭证据及OS观察 | evidence/cleanup.json、cleanup-audit.json |
| 21旧+1新逐项索引 | evidence-index.json |
| 调用来源 | model-call-summary.json、model-native/result.json、model-correction/result.json |
| 拒绝修复与改动来源 | model-native/review-rejected.json、execution/review.json |
| 原脚本与实际执行脚本 | execution/*.inherited、execution/harness.cjs、execution/step11.cjs、execution/native_cancel.py、execution/run.cjs |
| 离线驱动验证 | execution/test-driver.cjs、execution/driver-tests.json |
| 外部人为关闭说明 | external-interruption.json |
| 保护文件对比 | protected-before.json、protected-after.json |
| Git状态与运行时间 | git-before.txt、git-final.txt、execution-meta.json |

## 后续边界
当前无等待窗口、无继续运行的本轮驱动。若进一步处理，应先离线查清CDP进程标识与本机Chrome真实PID的对应，以及前置FileChooser监听是否影响原生对话框；这只是未验证的排查方向，不是已确认根因。不得放宽owner验证、扫取日常窗口、合成取消或把自动取消当真人点击。本次按安全边界停止。

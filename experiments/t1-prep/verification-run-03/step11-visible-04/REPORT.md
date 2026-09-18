# T1 本地验证报告（step11-visible-04）

**日期**：2026-09-18（Asia/Shanghai）
**执行方式**：Codex 实际执行并复核 Flash 补丁；本报告仅基于其产出的证据整理，未由报告撰写者亲自运行。

## 验证范围与前提

本步骤为 step11 可见项 T1 验证，前置条件均满足：UI 生成临时树、UI 重命名生效、UI 导入原始非空 `public-continuation-01` JSON 并清空撤销栈，且仅执行 post10 等价操作。此前 21 个公开项的 PASS 未重跑，仅核对了 old21 各步骤源结果状态，39 份证据文件全部存在且 SHA256 与既有索引一致（见 `old-evidence-validation.json`）。

## 浏览器执行（单次）

新开浏览器恰好运行一次：2026 年 9 月 18 日北京时间 11:11:18.838 启动，11:11:23.837 进入清理（UTC 03:11:18.838—03:11:23.837；随后驱动正常退出）。driver PID 21576、browser PID 32568、native dialog Chrome 子进程 PID 21464、owner HWND 1445546、dialog HWND 69386、Cancel HWND 69420。PID、创建时间、exe、父进程、profile、owner 全部校验通过（`execution/identity-tests.json`、`attempt-01/evidence/launch.json`、`attempt-01/evidence/identity-before-click.json`）。

## 核心结果

- 通过真实 SendInput 触发 Cancel 点击；DOM cancel 事件 `isTrusted=true`，无 change 事件。
- 点击前后树结构快照与原始非空 `public-continuation-01` JSON 完全一致；undo 无树变化，消息为「没有可撤销的操作」（`attempt-01/evidence/results.json`、`attempt-01/evidence/native-result.json`、`attempt-01/evidence/dom-events.jsonl`、同目录 snap-before-cancel、snap-after-cancel、snap-after-undo 的 JSON/PNG）。
- 三组错误数组均为空。
- **结论：step11 PASS。** **21 项沿用旧证据 + 步骤 11 本轮新证据 = 22 项公开批 PASS**，**不构成完整 T1**；hidden 与 D2 未执行。

## 清理与边界

浏览器清理成功（pages=0，driver exit=0）；`cleanup-audit.json` 确认七个已记录浏览器/驱动/模型 PID 均不存在。变更仅限新建文件夹；reference、spec、manual 等五项保护文件仅作只读哈希核验，未修改；未修改全局设置或注册表，未安装依赖，未读取认证配置或凭据。原生截图仅含 Cancel（`attempt-01/evidence/cancel-button.png`），页面截图仅作记录；未捕获个人文件列表。

## Flash 补丁与模型调用

- 原始 `model-*/result.json` 均保留。
- model-env：env merge 提案被否决，改为排他性 wx 创建任务的 Preferences 提示（目录偏好仅为初始提示，未读取目录列表，未声称正向 UI 路径证明；本次无需导航）。
- model-privacy：删除旧驱动的广域窗口标题诊断，严格 owner 检查保留并收紧子进程 executable 检查；模型旧字符串多余空行已按精确原文修正，保存为 model-privacy/reviewed-patch.json。
- model-interception：主会话直接禁用拦截，配本地源 `source-verified.json`。
- 全部继承源记录于 `execution/*.inherited`。

`model-call-summary.json` 记录 4 次真实调用（3 次补丁任务、1 次报告草稿任务），模型均观测为 `glm-5.3-flash`，全部正常退出：

| 任务 | PID | 耗时(s) | exit |
|---|---|---|---|
| model-env | 7104 | 63.607 | 0 |
| model-privacy | 6680 | 36.355 | 0 |
| model-interception | 21196 | 30.041 | 0 |
| model-report | 33720 | 25.096 | 0 |

## 备注

初版本地源路径查找属无关尝试；补丁空白不匹配已离线修正，浏览器未重跑。五个受保护文件经 `protected-before.json` / `protected-after.json` 比对确认未变更。各路径的绝对位置与逐项证据见 `evidence-index.json`；复核记录见 `execution-review.json` 与 `syntax-checks.json`。

## 独立复核与限制

Codex 对实际结果另作 12 项独立断言复核，全部通过，见 `final-verification.json`。`prerequisite.json` 记录非空旧 JSON 的复制来源与哈希；旧 21 项不因本次前置操作被计作重跑。未调用 dispatchEvent、setFiles([]) 或改动产品内部状态模拟取消。仅前置导入使用非空 FileChooser.setFiles；正式步骤 11 是真实原生 Cancel。

目录偏好只在全新任务 profile 中以 wx 独占创建，不读取或覆盖既有 Preferences。没有读取文件列表来验证当前路径，因此不把“实际已显示 downloads 路径”作为已验证事实。没有全桌面截图。所有新产物均在 step11-visible-04；旧运行和参考文档保持原样。

# 第9步 canceled 专项诊断

**结论：本机本次下载路径格式问题已由单变量对照锁定；仅修驱动后，未修改的参考实现公开1—9全部通过。** 不再把此前 canceled 归为已证明的产品实现缺陷；不声称整个T1通过。

## 真实模型来源
Claude CLI，显式 glm-5.3-flash、effort low，初稿38.212秒、修订106.839秒，均返回成功结果。证据见 model-task/ 和 model-repair/ 的 model-call.json、result.json、prompt.txt。初稿静态不合格未执行；模型修订稿保留。Codex仅作静态审核和明确驱动错误修正（review.json）、调度与报告。公开链复核复用此前Flash模块；无glm-5.3大请求。

## 三组预先声明的对照
|组|唯一环境差异（相对A）|data|Blob|
|---|---|---|---|
|A|基线：手动CDP，downloadPath正斜杠|canceled|canceled|
|B|仅传CDP的downloadPath改为Windows原生分隔符|成功|成功|
|C|仅取消手动CDP设置，Playwright管理|canceled|canceled|

三组Playwright downloadsPath均正斜杠；相同JSON字节、MIME、建议名、沙箱、file://、offline/route和专用目录。A/B中两种来源均同向变化，排除本次是Blob特有问题；C并未恢复，双重接管不是充分解释。B仅改路径即恢复，且参考实现复核重现恢复，足以锁定本次驱动路径参数。未调查Chromium内部为何取消，不外推其他版本/主机。

## 仅复核公开1—9
路径修正为 path.win32.normalize(downloadPath)，没有改实现。结果 **9 PASS / 0 FAIL / 0 UNTESTED**（仅该九项）。第9步CDP completed，实际原件路径与Playwright path一致，saveAs另存；固定expected.json深比较及字节比较都通过。运行PID63084退出0；诊断PID62068退出0。没有继续10+。

原件、data/Blob对照、saveAs和固定预期SHA256均为：

df8f17fbed15145cf88c091521a471fd1e0298d43388f55e3c0c1467a5020915

浏览器关闭前记录原件路径并复制留证；不把保留副本伪称仍存活的浏览器临时文件。

## 关键证据（本目录内）
- 计划：CONTROL-PLAN.md；原始事件：A/events.jsonl、B/events.jsonl、C/events.jsonl。
- 对照原件留存：B/evidence-originals/data-mindmap.json、B/evidence-originals/blob-mindmap.json；实际临时路径见B/result.json。
- 参考导出事件：`D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/download-diagnosis-01/verify-public-1-9/evidence/download-evidence.json`。
- 原件留存副本：`D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/download-diagnosis-01/verify-public-1-9/evidence/export-original-preserved.json`。
- saveAs文件：`D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/download-diagnosis-01/verify-public-1-9/evidence/downloads/t1-map.json`。
- 固定预期对比：`D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/download-diagnosis-01/verify-public-1-9/evidence/fixed-expected-comparison.json`。
- 第9步截图（已目检）：`D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/download-diagnosis-01/verify-public-1-9/evidence/snap-9.png`。
- 公开1—9逐项结果（9 PASS / 0 FAIL / 0 UNTESTED）：`D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/download-diagnosis-01/verify-public-1-9/evidence/results.json`。
- 专项汇总（位于诊断根目录，不在复核子目录）：`D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/download-diagnosis-01/summary.json`。
- 模型/协调者改动分界：diagnosis.original.cjs、diagnosis.repair-original.cjs、diagnosis.cjs、review.json；verify-public-1-9/review.json及before副本。
- 文件清单：changed-files.json；前后保护哈希：protected-before.json、protected-after.json（五份全部不变）。

## 范围与下一步
所有本轮新增写入只在 D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/download-diagnosis-01；旧run03报告/旧失败证据未覆盖。未读凭据/个人配置或日常profile；无安装、HTTP服务、宿主网络修改、安全关闭、隐藏用例或D2。AGENTS/guidance仅遵守未修改。
下一最小动作：本专项到此停止；如另行授权续验，再使用已证实的原生路径驱动衔接步骤10，步骤11原生取消仍需独立可验证方案。本轮没有运行10+或A/B公开片段。

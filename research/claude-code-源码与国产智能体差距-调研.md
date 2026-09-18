# Claude Code 源码泄露机制与国产智能体长任务差距调研笔记

调研日期:2026-09-15 | 用途:课题《长程软件开发任务中智能体持续执行机制研究》观察层素材
证据强度标记:【官方】=厂商官方文档/声明;【泄露分析】=基于泄露源码的第三方分析(非官方,细节无法逐一核验);【口碑】=用户评测/社区反馈(主观、样本有限)。

## 一、Claude Code"源码泄露"事件与分析

**时间线澄清**:所谓泄露至少有两起。① 2025-02-24 发布当日,即有人发现 npm 包内嵌约 1800 万字符的 inline source map【泄露分析,https://www.sabrina.dev/p/claude-code-source-leak-analysis 】;② 影响更大的一起:npm 包未剥离 57MB 的 cli.js.map,sourcesContent 字段明文保存原始源码,无需反编译/反混淆即可脚本化还原,涉及 Claude Code 自有 TS/TSX 约 1903~1906 个文件、约 51 万行(两来源数字略有出入,存疑)【泄露分析,https://www.secrss.com/articles/88999 、https://juejin.cn/post/7623258895395110966 】。未检索到 Anthropic 官方回应,不确定。

**泄露分析揭示的机制**(均为【泄露分析】,以 https://www.secrss.com/articles/88999 为主,辅以 https://developer.aliyun.com/article/1722081 、https://m.36kr.com/p/3747481076417289 、https://www.dbreunig.com/2026/04/04/how-claude-code-builds-a-system-prompt.html ):
- 主循环:query.ts(约1729行)内 while(true) 的"LLM回复→解析工具调用→执行→结果回填"循环,直至无工具调用。
- 上下文压缩:四层——HISTORY_SNIP(旧历史摘要)/Microcompact(工具结果微压缩)/CONTEXT_COLLAPSE(大块折叠)/Autocompact(阈值整体压缩);记忆系统"不记代码、只记人",分偏好/行为反馈/项目信息/外部资源四类。
- 工具系统:40+ 工具无继承、工厂统一构建;按 isConcurrencySafe 判定并行;输出超限最多续写恢复 3 次;BashTool(1143行)sandbox-exec/seccomp 沙箱、15 秒转后台、大输出落盘防污染上下文。
- 子代理与实验特性:Coordinator 模式经 spawn_worker/message/stop 三工具调度 worker;Skills 即 .claude/skills/ 下的 markdown;另有 KAIROS 守护进程("dream"记忆整理)等,由编译期(tengu 代号)+运行时(GrowthBook)双 feature flag 控制,源码中含 ABLATION_BASELINE 消融实验开关。
- 权限:36kr 概括为"6 级安全架构、26 个隐藏指令"(https://m.36kr.com/p/3747481076417289 );系统提示拼装与 CLAUDE.md 指令预算分析见 dbreunig 与 https://tylerfolkman.substack.com/p/i-read-the-claude-code-source-leak 。

## 二、B站相关视频(仅依据页面简介与关联图文,视频内容本身无法直接观看)

1. [Claude Code架构拆解!51万行代码里的AI Agent底层真相|手撕沙箱/动态Prompt/失败自修复](https://www.bilibili.com/video/BV1WuJ56wEPa/) — 简称沙箱/动态Prompt/自修复。
2. [Claude Code天价源码泄漏!19个模块拆解内部原理](https://www.bilibili.com/video/BV1Dp9VBpEJS/) — NPM 未移除 Source Map、约1900个TS文件。
3. [Claude Code源码曝光底层技术硬核拆解:1884个文件背后](https://www.bilibili.com/video/BV1zR9JBREua/)(UP主:唐国梁Tommy) — 本质是完整 Agent Runtime 框架。
4. [手撕Claude Code 源码:从零理解Agent Harness](https://www.bilibili.com/video/BV18Uu36rEbu/) — Harness 架构+实战。
5. [Claude Code 源码分析与复刻实现](https://www.bilibili.com/video/BV15HXCBkEKY/) — 约14.2万播放,复刻实现向。另有 [BV19G9VBFES7](https://www.bilibili.com/video/BV19G9VBFES7/) 简介称"四层上下文压缩、三层记忆、18个隐藏功能",与图文分析互证。

## 三、国产编程智能体长任务差距

先纠正归属:WorkBuddy 是腾讯云 CodeBuddy 团队 2026-03-09 发布的办公智能体(【官方】https://www.workbuddy.cn/ ),并非字节;字节对应的是 Trae(含 SOLO 与 /goal 模式)及 ArkClaw(【官方】https://forum.trae.cn/t/topic/168989 、https://www.ithome.com/0/992/890.htm )。

1. **上下文压缩丢状态**:Trae 官方论坛多帖——压缩后把旧指令当新指令、自动压缩丢失 pending task 后不再续跑、压缩后重复阅读重复执行【口碑,https://forum.trae.cn/t/topic/169407 、https://forum.trae.cn/t/topic/171594 、https://forum.trae.cn/t/topic/10501 】。对照泄露分析中 Claude Code 的四层压缩+todo 持久化,差距点明确。
2. **工具循环稳定性**:Trae 已设"自动运行"仍频繁要求手动确认,打断长任务【口碑,https://github.com/Trae-AI/TRAE/issues/2542 】。
3. **计划与自我验证**:横评认为 Claude Code 深推理/长任务明显更强,Trae"够用但不冒尖"、复杂多文件重构偏弱【口碑,https://www.cnblogs.com/pcdoctor/p/19893607 、https://juejin.cn/post/7618167131005337600 】;某案例称 Trae 快 3 倍但可维护性低 40%(单一来源,不作结论,https://www.mainwww.com/article/1513.html )。
4. **工程化成熟度**:CodeBuddy CLI"比 Claude Code 稚嫩,工程化急需完善"【口碑,https://zhuanlan.zhihu.com/p/1950314132432754649 】;官方口径强调工程级智能体与合规差异化【官方,https://www.infoq.cn/article/soadsraioyt8ckqhijx5 】。
5. **WorkBuddy**:实测"能力及格,但生态真香"、有用户直言不如 Claude Code;对比 Codex 云端 30 分钟+多 Agent 长任务仍有差距【口碑,https://www.tmtpost.com/8094441.html 、https://xueqiu.com/8315851674/393283523 、https://wallstreetcn.com/articles/3778352 】。官方宣传数据(响应+54%、完成时长-47%、成功率99.99%)未经第三方验证【官方,http://www.news.cn/tech/20260605/e410f96e4f594ec0b92a4054faed70de/c.html 】。值得注意的是其官方 harness 复盘提出"长任务先拆分"并引用 Anthropic《Effective harnesses for long-running agents》【官方,https://forum.trae.cn/t/topic/6510 关联社区讨论及知乎 harness 文章】,说明厂商已自认 harness 是差距来源。
6. **通义灵码/Qoder**:直接长任务对比证据少(存疑);知乎全景测评称 Claude Code 接近"自主编程"【口碑,https://zhuanlan.zhihu.com/p/1999804779141030200 】,阿里 Qoder CLI 自我定位"媲美 Claude Code"【官方,https://blog.csdn.net/alisystemsoftware/article/details/153640085 】。

## 四、映射到实验框架(六大机制)

- **任务机制 ↔ 可消融"结构化状态交接"**:证据链最完整——Trae 压缩丢 pending task/丢指令时序【口碑】 vs Claude Code 四层压缩+todo 结构【泄露分析】。建议作为首要消融变量。
- **工具/任务机制 ↔ 可消融"测试反馈"**:Claude Code 的失败自修复、大输出落盘、输出超限续写【泄露分析】对应"结果回填驱动续跑";国产工具频繁人工确认打断循环【口碑】。可消融"测试反馈开/关"。
- **上下文机制**:压缩粒度与"是否保留指令时序"可半消融;模型侧长上下文能力差异不可消融,只能作解释变量(观察层)。
- **记忆/知识库/多智能体机制**:如"不记代码只记人"、CLAUDE.md 指令预算、Coordinator 三工具调度,与闭源实现强绑定、无法在自建框架复现,仅作观察层素材。
- **归因警示**:口碑差距中"harness 机制"与"模型能力"两变量天然混杂,现有证据只能证明"口碑差距存在",不能证明"机制差异即原因"。

## 五、不确定性汇总

泄露文件数两说(1903/1906)且无官方回应;mainwww 案例单一来源;通义灵码长任务口碑证据不足;B站视频仅依据简介;泄露分析细节无法逐条核验,引用时须保留"非官方"限定。

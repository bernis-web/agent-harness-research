# 智能体 Harness 架构调研报告

> 科研实践方向:研究智能体的 Harness 架构,包括记忆管理、上下文管理、知识库管理、工具管理、复杂任务执行和多智能体协作。
> 主要研究对象:DSH(deepseek-harness,主)+ LangChain Deep Agents(辅);参考系:Claude Code。
> 调研日期:2026-09-13

---

## 目录

1. [调研背景:为什么要研究 Agent Harness](#一调研背景为什么要研究-agent-harness)
2. [核心概念:什么是 Agent Harness](#二核心概念什么是-agent-harness)
3. [研究对象一:DSH(deepseek-harness)](#三研究对象一dshdeepseek-harness)
4. [研究对象二:LangChain Deep Agents](#四研究对象二langchain-deep-agents)
5. [六大子方向研究现状](#五六大子方向研究现状)
   - 5.1 记忆管理
   - 5.2 上下文管理(上下文工程)
   - 5.3 知识库管理
   - 5.4 工具管理
   - 5.5 复杂任务执行
   - 5.6 多智能体协作
6. [DSH vs Deep Agents 对比分析](#六dsh-vs-deep-agents-对比分析)
7. [研究空白与可切入的研究问题](#七研究空白与可切入的研究问题)
8. [对计划书三个章节的素材映射](#八对计划书三个章节的素材映射)
9. [参考资料](#九参考资料)

---

## 一、调研背景:为什么要研究 Agent Harness

近两年智能体(Agent)领域的一个基本共识正在形成:

> **Agent = 模型 + Harness。模型负责单步推理,Harness 负责让推理可持续、可靠、可控地运转。**

支撑这一判断的现象:

- **模型能力快速趋同,工程差距成为瓶颈。** 主流前沿模型在工具调用、代码能力上差距不断缩小,而同样模型接在不同运行时上表现差异巨大。Claude Code 之所以被视为标杆,普遍被认为主要靠的是 Harness 层的工程化实现(对话循环、工具系统、权限管线、上下文管理),而非模型独占优势([智源社区](https://www.baai.ac.cn/)、[极客时间《Claude Code 工程化实战》](https://time.geekbang.org/column/article/958033))。
- **2025–2026 年"harness"从术语变成品类。** Anthropic 把 Claude Code 的运行时能力抽象为 Agent SDK;LangChain 发布 Deep Agents;2026 年 7 月底 DeepSeek 随 V4-Flash 模型一并开源 deepseek-harness(dsh),上线 12 小时 GitHub 星标破 5 万,将"Agent Harness"概念推向大众([知乎:deepseek-harness 项目深度解读](https://zhuanlan.zhihu.com/p/2071362726442673749))。
- **六大能力是 harness 的通用骨架。** 两个不相关的框架(dsh 与 deepagents)不约而同地把运行时拆成:记忆、上下文、文件/知识、工具、规划/执行、子代理协作六大模块。研究这六块,等于研究智能体运行时的"解剖学"。

对课程而言,这个方向的价值:懂底层运行逻辑才能设计和使用好智能体;两个主要对象都是开源项目,可读源码、可复现、可做插件级实验,适合本科生科研实践的深度要求。

---

## 二、核心概念:什么是 Agent Harness

### 2.1 定义

**Agent Harness(智能体运行时框架/基座)** 是介于大模型 API 与最终应用之间的运行时层,负责承载和组织:

| 组成部分 | 作用 | 类比 |
|---|---|---|
| **对话循环(Agent Loop)** | "模型→工具→观察→模型"的持续迭代,是智能体的心跳 | OS 主循环 |
| **工具系统(Tool System)** | 工具注册、schema 描述、调用执行、结果回填 | 系统调用 |
| **权限管线(Permission Pipeline)** | 模型无法跳过的安全边界:预执行守卫、审批、沙箱 | 内核保护环 |
| **上下文系统(Context System)** | 决定每一步模型"看见什么":系统提示、历史、压缩、记忆注入 | 内存管理 |
| **会话与状态(Session/State)** | 事件日志、持久化、恢复、回放 | 进程/文件系统 |

来源:[《御舆 — 解码 Agent Harness》](https://github.com/lintsinghua/claude-code-book)(开源书,把 Claude Code 拆解为对话循环/工具系统/权限管线等章节)、[Jimmy Song《Harness:智能体的运行时基座》](https://jimmysong.io/zh/book/ai-handbook/runtime/harness/)、[shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)(12 节课的 harness 工程教程)。

### 2.2 与相近概念的关系

- **vs Agent Framework(2023–2024 代的 LangChain/AutoGen)**:早期框架以"链/图编排"为中心,开发者显式写流程;harness 以"模型自主循环"为中心,开发者配置能力与边界。行业正从 framework 转向 harness(DataWhale《Deep Agents 实战》第一章的核心论点)。
- **vs CLI 聊天前端**:harness 不是聊天 UI,而是执行运行时——可无头运行、可被程序调用、有完整生命周期事件(Claude Code 有 31 个可记录的生命周期事件,每个都可被工程层 shell 机制控制)。
- **学术对应物**:普林斯顿 SWE-agent 论文(2024)提出的 **ACI(Agent-Computer Interface,智能体-计算机接口)** 概念,与 harness 所做的事高度重合——研究"给模型什么工具接口、如何呈现反馈"本身能显著改变任务成功率。

### 2.3 "模型过剩、harness 稀缺"的证据

- Manus 团队公开经验:同样的模型,靠上下文工程(KV-cache 友好的稳定前缀、及时清理)把长任务成功率大幅拉升([Manus 博客](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus))。
- Morph 团队实验表明:往上下文里塞更多 token 反而让智能体变差——信息选择比信息数量重要([Morph: Why More Tokens Makes Agents Worse](https://www.morphllm.com/context-engineering))。
- Cognition(Devin 团队)《Don't Build Multi-Agents》:多智能体失败的主因是上下文被切碎/复制走样,而非模型不行——同样是 harness 层设计问题。

---

## 三、研究对象一:DSH(deepseek-harness)

### 3.1 基本信息

| 项 | 内容 |
|---|---|
| 发布 | DeepSeek AI,2026 年 7 月底,随 DeepSeek-V4-Flash 一同开源;developer preview 阶段 |
| 仓库 | [github.com/deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness)(中文文档 README.zh.md) |
| 定位 | Agent Harness(智能体执行运行时),非聊天前端 |
| 技术栈 | TypeScript,基于 [Cordis](https://cordis.js.org/) 依赖注入框架,pnpm monorepo,50+ 子包 |
| 启动 | `npx @deepseek-ai/dsh web`(Node.js 环境直接跑起 Web UI) |
| 文档 | 官方蓝皮书/指导手册([dsh.hicyou.com/zh](https://dsh.hicyou.com/zh))、社区橙皮书([deepseek-harness-orange-book](https://github.com/alchaincyf/deepseek-harness-orange-book))、[awesome-deepseek-harness](https://github.com/libukai/awesome-deepseek-harness) |

以下架构细节主要来自[知乎《deepseek-harness 项目深度解读》](https://zhuanlan.zhihu.com/p/2071362726442673749)(读源码后写成的解读,撰写计划书时建议对照仓库核验)。

### 3.2 核心理念:微内核 + Everything is a Plugin

dsh 只保留一个很小的内核(依赖注入容器 + 插件加载器 + 基础生命周期),其余一切能力——界面、工具、模型接入、记忆、工作流——全部是插件:

- **Service Definition / Provider / Consumer 三件套**:一个能力先声明 Service 接口,Provider 注册具体实现(可多个,带优先级),Consumer 声明依赖并使用。这带来两个关键性质:
  - **多实现可替换**(模型、存储、界面都能换);
  - **依赖自动装配**——插件声明"我需要文件系统能力",容器负责在运行时注入正确的实现。
- 与 OSGi(Java 生态模块化规范)思路同源:微内核 + 服务注册 + 生命周期管理。

### 3.3 能力接缝(Capability Seams)——与六大子方向直接对应

知乎解读把 dsh 的"可替换接缝"梳理为六类,恰好覆盖课程方向:

1. **模型接缝(llm.ts)**:ChatModel 抽象 + 多模型适配器,OpenAI 兼容 API、Anthropic API、自定义代理均可;模型无关。
2. **会话与上下文接缝**:**事件溯源(Event Sourcing)** 会话模型——每次交互按不可变事件追加到 append-only 日志(旧日志永不改写),天然支持回放、调试与多客户端同步;近上下文窗口用**事件摘要重建**,与远端全量日志按 id 对齐。
3. **压缩模块(Compaction)**:对超长会话做摘要压缩,保留工具调用结构、任务边界、关键约束。
4. **工具执行管线(Tool Execution Pipeline)**:pre-execute(校验、守卫)→ execute → post-execute(格式化、结果上抛);工具调用带完整元数据(命令、返回码、执行时长),支持**人工审批环节**。
5. **子代理与工作流**:subagent 包(独立上下文的委派执行)、workflow 包(工作流编排)、goal 包(目标层)、plan 包(计划层)、todo 包(任务清单)——从目标到计划到执行的完整层级。
6. **界面接缝**:CLI/Web UI/GitHub Actions 等多种前端可插拔。

### 3.4 声明式组合与分发

- **Profile(配置档案)**:一份声明式配置定义"这个智能体是谁"(系统提示、工具、人格)。
- **Bundle(能力包)**:一组插件的打包组合,一键安装。
- **Skills(技能)**:SKILL.md 结构化文件,声明"何时用、怎么用"——与 Anthropic 推动的 Agent Skills 规范一致。
- Profile + Bundle + Skills 三个维度把"配置一个智能体"变成纯声明式操作。

### 3.5 生态现状

- 支持 MCP(Model Context Protocol)接入外部工具。
- 社区插件发展极快:长期记忆、电子宠物等热门插件;有开发者整理开源插件补齐编码 Agent 短板(配合 DeepSeek-V4-Pro 的工具调用与链式任务执行能力)。
- 系统学习资料:官方手册 > 橙皮书 > 知乎源码解读;建议阅读顺序为先官方文档、再 `packages/` 下核心包源码(kernel → agent → subagent → tool → workflow)。

### 3.6 适合科研实践的点

- TypeScript 单仓多包,模块边界清晰,适合按包逐个精读;
- 微内核 + 插件意味着**每个子方向都可以做成一个插件实验**(例如:自定义 compaction 策略插件、记忆插件、工具检索插件);
- 事件溯源日志是天然的数据来源——可以拿真实轨迹做压缩保真度、记忆注入时机等定量实验。

---

## 四、研究对象二:LangChain Deep Agents

### 4.1 基本信息

| 项 | 内容 |
|---|---|
| 仓库 | [github.com/langchain-ai/deepagents](https://github.com/langchain-ai/deepagents) |
| 定位 | "Batteries-included" 的深任务智能体框架,基于 LangChain 1.0 + LangGraph |
| 文档 | [Deep Agents overview](https://docs.langchain.com/oss/python/deepagents/overview)、[官网专页](https://www.langchain.com/deep-agents)、[博客 Doubling down on Deep Agents](https://www.langchain.com/blog/doubling-down-on-deepagents)(0.2 版:可插拔后端) |
| 中文系统教程 | [DataWhale《Deep Agents 实战》](https://datawhalechina.github.io/deepagents-in-action/)(免费开源书,覆盖全部模块,含完整代码) |

### 4.2 三大支柱

Deep Agents 的口号是"让智能体规划任务、读写文件、管理自己的上下文":

1. **Planning(规划)**:内置 `write_todos` 规划工具 + TodoListMiddleware,长任务先写计划、执行中持续勾选更新——"先规划、再执行、过程中重写计划"。
2. **Filesystem(文件系统)**:虚拟文件系统作为上下文管理的核心。智能体通过 6 个文件工具(ls/read/write/edit/glob/grep)把中间产物落盘,把上下文窗口当"工作内存"、把文件系统当"外存",突破窗口限制;支持 StateBackend / CompositeBackend / PostgresStore 等存储后端。
3. **Subagents(子代理)**:`task` 工具把子任务委派给独立上下文的子代理,结果只回传摘要——同时实现上下文隔离与并行;0.5.0 引入基于 Agent Protocol 的异步子代理,支持并行扇出编排。

架构上是 **middleware(中间件)栈**:SubagentMiddleware、TodoListMiddleware、FilesystemMiddleware、HumanInTheLoopMiddleware 等按需插拔——与 dsh 的插件理念殊途同归,但实现路径是"函数式中间件"而非"依赖注入"。

### 4.3 模块全景(按 DataWhale 教程目录整理)

| 模块 | 对应课程方向 | 要点 |
|---|---|---|
| 虚拟文件系统 | 上下文/知识库 | 6 个文件工具;InMemoryStore/StateBackend/PostgresStore |
| 任务规划与分解 | 复杂任务执行 | write_todos、中间件架构、LLM 智能规划 |
| 子代理与上下文隔离 | 多智能体/上下文 | 上下文防污染、CompiledSubAgent |
| 异步子代理编排 | 多智能体 | 0.5.0 Agent Protocol、并行扇出 |
| 动态子代理 | 多智能体 | 从静态 SubagentMiddleware 到 DynamicSubAgentMiddleware;**六种编排模式**:分类路由、并行扇出、交叉验证(传递论点做批判性检查)、迭代收敛(生成-评审-修改循环)、结构化输出、动态生成 |
| Skills 系统 | 知识库 | Agent Skills 规范、SKILL.md、渐进式披露(progressive disclosure)、Skills vs Memory 辨析 |
| 长期记忆 | 记忆 | Checkpointer(线程内)+ Store(跨线程)、复合后端 |
| Human-in-the-Loop | 工具管理 | interrupt 中断、风险分级审批 |
| 沙箱执行 | 工具管理 | QuickJS 沙箱解释器、code_interpreter |
| 文件系统权限 | 工具管理 | allow/deny/interrupt 规则、安全策略 |
| MCP 工具生态 | 工具管理 | MCP 接入、异步工具加载(只加载 tool 定义不阻塞启动) |
| 评估体系 | 科研方法 | 评分量表(grading rubrics)、轨迹回放、流式中间件 |

### 4.4 评价

- 优势:Python 生态、代码量小(相比 dsh 的 50+ 包)、文档与社区教程极全、LangGraph 图编排可做复杂工作流;Zilliz 测评结论"长任务友好、高可控"([评测文章](https://zilliz.com.cn/blog/LangChain-deepagents-review-for-long-tasks))。
- 局限:偏框架约定(langchain 1.0 依赖);harness 的"权限管线、生命周期事件、多前端"等维度不如 dsh/Claude Code 完整。

---

## 五、六大子方向研究现状

### 5.1 记忆管理(Memory Management)

**问题**:LLM 上下文有限、无法跨会话持续学习、缺乏个性化——记忆系统要解决"记什么、怎么存、何时取、如何遗忘"。

**三条主线**:

1. **OS 启发的分层记忆(学术主线)**
   - **MemGPT**(Berkeley, 2023,论文《Towards LLMs as Operating Systems》):把上下文窗口当 RAM、持久存储当硬盘,智能体通过函数调用自主换入换出记忆;后演化为公司化产品 **Letta**(GitHub ~19K 星),分层结构为 Core Memory(核心记忆)/ Recall Memory(召回记忆)/ Archival Memory(归档记忆)。
   - 思想源头可追溯到斯坦福 **Generative Agents**(Park et al., 2023)的记忆流(memory stream)+ 反思(reflection)机制,以及 **Voyager**(2023)的技能库。
2. **生产级记忆 API(工程主线)**
   - **Mem0**:生产级开源记忆框架,支持工作/事实/情景/语义记忆,官方论文报告在单跳、时序、多跳等基准上优于既有记忆系统([AWS 实践文章](https://aws.amazon.com/cn/blogs/china/agentic-ai-infrastructure-deep-practice-experience-thinking-series-three-best-practices-for-agent-memory-module/));竞品还有 Zep、Cognee、Supermemory 等。
3. **自主记忆架构(顶会前沿)**
   - **A-MEM: Agentic Memory for LLM Agents**(arXiv 2502.12110,**NeurIPS 2025 Poster**):动态组织记忆网络,记忆自主演化;
   - **RMM(Reflective Memory Management)**(ACL 2025 长文):前向+后向反思做长期个性化记忆管理。
   - 综述入口:[AgentGuide 21 篇核心论文梳理](https://github.com/adongwanai/AgentGuide)。

**工程化新议题**([腾讯云:记忆工程化落地](https://cloud.tencent.com/developer/article/2681731)):写入攻击防御、分层存储、记忆生命周期治理、RL 优化记忆策略。

**在两个研究对象中的位置**:dsh 的会话即事件日志 + compaction = 短期记忆的机器可回放形态,长期记忆靠社区插件;deepagents 用 Checkpointer(短期)+ Store(长期)+ 复合后端。**对比点**:两者都还没有内置"反思式记忆整理",这正是研究空间。

### 5.2 上下文管理(Context Engineering 上下文工程)

**定义**:"在智能体轨迹的每一步,用恰当的信息填充上下文窗口的艺术与科学"([LangChain 博客](https://www.langchain.com/blog/context-engineering-for-agents))。2025 年起被视为与 prompt engineering 并列的新学科([Anthropic: Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents))。

**核心技术**([Claude Cookbook: Memory, Compaction, and Tool Clearing](https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools)):

- **Compaction(压缩)**:会话接近窗口上限时摘要内容、用摘要重开新窗口——长时智能体不崩溃的关键机制(dsh 与 deepagents 均内置);
- **工具结果清理(Tool-result clearing)**:及时清除过期的工具输出;
- **外部记忆(External memory)**:信息卸载到可检索存储,按需取回;
- **子代理上下文隔离**:脏活重活委派给子代理,主上下文只收回摘要(两个框架的共同设计);
- **注意力管理**:Anthropic 强调上下文是"有限资源",要像预算一样分配([中文解读](https://assemble.gitbook.io/assemble/v1.0/02-gong-cheng-shi-jian-375-ge-wen-jian-83.1/05.-ai/anthropic/02-effective-context-engineering-for-ai-agents-shang-xia-wen-gong-cheng-de-xi-tong-xing-fang-fa-lun))。

**性能维度**:**KV-cache 友好设计**——保持提示词前缀稳定、结构化组织以最大化缓存命中([Manus 经验](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus))。这是"稍微底层"的课程要求下非常好的深挖点:压缩/清理策略直接影响缓存命中与成本。

**中文入门**:[知乎《Context Engineering,一篇就够了》](https://zhuanlan.zhihu.com/p/1938967453951571269)、[李文周教程 M09](https://liwenzhou.com/courses/ai-agent/09-context-engineering/)、[awesome-context-engineering](https://github.com/yzfly/awesome-context-engineering)。

### 5.3 知识库管理(Knowledge Base Management)

智能体的知识分三类,管理方式不同:

1. **陈述性知识(领域文档)——RAG 系**
   - 演进路径:Naive RAG → Advanced RAG(查询改写、重排)→ Modular RAG → **GraphRAG**(微软 2024,知识图谱+社区摘要,擅长全局性问题)→ **Agentic RAG**(检索器本身成为智能体的工具,由智能体决定何时检索、检索什么、结果是否可信,可多轮迭代)。
   - 代表工作:Self-RAG(2023)、CRAG、HippoRAG;graph 结构与向量混合是当前工程主流。
2. **过程性知识(怎么做事)——Skills 系**
   - **Agent Skills 规范**(Anthropic 推动):SKILL.md 声明"何时用、怎么用",**渐进式披露**——平时只占几百 token 的元数据,用到时才加载完整指令与脚本。deepagents 与 dsh 均已支持。Skills vs Memory 的区分:技能是"程序性知识",记忆是"经验性数据"(DataWhale 教程有专章辨析)。
3. **工作区知识(任务中间产物)——虚拟文件系统**
   - deepagents 的核心创新之一:把文件系统当知识工作区,笔记/大纲/代码草稿全部落盘,上下文按需读取。这本质上是"把 human 的文件夹工作流给智能体"。

**在 dsh 中的位置**:文件读写工具 + 知识类插件(社区已有);与 RAG 的结合(如"文件系统 + 向量检索混合")目前两个框架都未内置——**研究机会**。

### 5.4 工具管理(Tool Management)

**三个层次的问题**:

1. **工具接入标准:MCP(Model Context Protocol)**
   - Anthropic 2024 年 11 月发布的开放标准,统一"AI 应用 ↔ 外部系统"连接,被称为"AI 的 USB-C 接口"([官方文档](https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro)、[阿里云科普](https://www.aliyun.com/getting-started/what-is/what-is-mcp))。提供 tools/resources/prompts 三类原语([Tools 规范](https://modelcontextprotocol.io/specification/2026-07-28/server/tools))。dsh 与 deepagents 均原生支持;deepagents 还做了**异步工具加载**——启动只加载 tool 定义,不阻塞。
2. **工具治理:权限与沙箱**
   - deepagents:文件系统 allow/deny/interrupt 三态规则;HITL 中断审批按风险分级;QuickJS 沙箱解释器隔离执行代码。
   - dsh:pre-execute 守卫 + 审批环节的工具执行管线。
   - 安全研究:工具污染(tool poisoning)、脆弱工具纹(confused deputy)等威胁已有分析文章([安全分析](https://www.secrss.com/articles/77278))。
3. **规模化问题:工具太多怎么办**
   - 当 MCP 服务器挂载几十上百个工具,全部塞进系统提示既贵又降低选择准确率。业界方案:工具检索(用 RAG 检索工具 schema)、按需挂载、动态加载——deepagents 的异步加载是这个方向的工程化雏形,系统性研究还很少,**研究机会**。

**学术脉络**:Toolformer(2023,自监督学工具使用)、HuggingGPT(2023,任务规划+模型调度)、ReAct(2022)确立了"工具调用作为推理的一等公民"。

### 5.5 复杂任务执行(Complex Task Execution)

**从 ReAct 到目标-计划-执行层级**:

- **ReAct**(Yao et al., 2022):推理+行动交替,奠定单步循环范式;Reflexion(2023)加失败反思;AutoGPT(2023)首次尝试全自主长任务,但暴露"没有规划就漂移"的问题。
- **规划即工具(write_todos / plan 模式)**:deepagents 把"维护任务清单"本身做成工具,模型边做边改计划;dsh 有 goal→plan→todo 完整三层包。这是当前长任务成功率的公认关键设计。
- **长时执行的基础设施**:compaction(防窗口溢出)+ 文件系统(状态外置)+ 子代理(并行/隔离)三者共同支撑小时级任务。
- **评估**:deepagents 教程引入评分量表(grading rubrics)与轨迹回放;dsh 的事件溯源日志天然支持执行轨迹的完整回放——**两者结合可做执行质量的定量研究**。

### 5.6 多智能体协作(Multi-Agent Collaboration)

**分层定位(重要框架)**([LangGraph 多智能体与 A2A](https://github.com/didilili/ai-agents-from-zero/blob/main/26-LangGraph%E5%A4%9A%E6%99%BA%E8%83%BD%E4%BD%93%E4%B8%8EA2A.md)):

| 层 | 解决什么 | 代表 |
|---|---|---|
| 应用内编排 | 单个应用内多角色协作 | LangGraph(有向图状态机)、AutoGen(对话式)、CrewAI(角色制)、MetaGPT(SOP 制) |
| 工具接入协议 | 智能体 ↔ 外部工具 | **MCP**(Anthropic, 2024.11) |
| 跨系统协作协议 | 不同厂商/框架的智能体互操作 | **A2A**(Google, 2025.4;[IBM 解读](https://www.ibm.com/cn-zh/think/topics/agent2agent-protocol)) |

三者互补而非竞争。系统性比较见综述论文 [arXiv 2508.10146《智能体 AI 框架:架构、协议与设计挑战》](https://www.alphaxiv.org/zh/abs/2508.10146)(比较 CrewAI/LangGraph/AutoGen/Semantic Kernel/Agno/Google ADK/MetaGPT)。

**harness 内的多智能体 = 编排模式**:deepagents 的动态子代理给出六种模式——分类路由、并行扇出、交叉验证、迭代收敛、结构化输出、动态生成(详见 4.3)。Anthropic 的多智能体研究系统(orchestrator-worker 模式)是工业界标杆案例;Cognition 则主张"能单代理就不多代理"(上下文分裂成本)。**核心争议:上下文共享 vs 隔离的权衡**——正是值得做实验的问题。

**学习资源**:[freeCodeCamp: LangGraph+MCP+A2A 完整实战](https://www.freecodecamp.org/news/how-to-build-a-multi-agent-ai-system-with-langgraph-mcp-and-a2a-full-book/)、[Jimmy Song 多智能体协同深度指南](https://jimmysong.io/zh/book/ai-handbook/agent/multi-agent/)、[awesome-agent-orchestration](https://github.com/vivy-yi/awesome-agent-orchestration)。

---

## 六、DSH vs Deep Agents 对比分析

| 维度 | dsh(deepseek-harness) | deepagents(LangChain) |
|---|---|---|
| 发布方/时间 | DeepSeek,2026.07(developer preview) | LangChain,2025 下半年起,0.2/0.5 持续迭代 |
| 语言/生态 | TypeScript,Cordis DI,pnpm monorepo 50+ 包 | Python,LangChain 1.0 + LangGraph |
| 架构哲学 | 微内核,Everything is a Plugin(服务接口/提供者/消费者) | 中间件栈,函数式插拔 |
| 会话/记忆 | 事件溯源 append-only 日志;compaction;长期记忆靠插件 | Checkpointer+Store;Postgres 后端 |
| 上下文管理 | compaction 模块 + 摘要重建 | 虚拟文件系统为核 + 子代理隔离 |
| 知识/文件 | 文件工具 + Skills;知识插件生态 | 6 文件工具 + Skills 规范(SKILL.md) |
| 工具管理 | MCP;pre/execute/post 管线;守卫+审批 | MCP(异步加载);allow/deny/interrupt;QuickJS 沙箱 |
| 任务执行 | goal/plan/todo 三层包 | write_todos + TodoListMiddleware |
| 多智能体 | subagent/workflow 包 | task 工具、异步子代理、六种编排模式 |
| 前端 | CLI/Web/GitHub Actions 可插拔 | 无独立前端(库形态) |
| 成熟度/资料 | 新,官方手册+橙皮书+社区解读 | 较成熟,官方文档+DataWhale 中文书+大量博客 |
| 学习曲线 | 陡(TS/DI/monorepo,源码量大) | 缓(Python,代码量小) |
| 适合的科研用法 | 精读源码做"解剖学"研究;事件日志做数据实验;写插件 | 快速复现各机制;做 A/B 对比实验;改造中间件 |

**建议的组合打法**:用 deepagents 快速建立直觉和跑通实验(Python,改动成本低),用 dsh 做源码级深读与"底层机制"研究(微内核/事件溯源/工具管线),两条线在六大模块上互为印证。

---

## 七、研究空白与可切入的研究问题

按"课程追求科研程度 + 底层一些"的定位,以下问题都有现成开源代码可改、可测:

1. **压缩保真度(compaction fidelity)**:不同摘要压缩策略在长任务上丢失哪些关键信息(任务边界/工具参数/约束条件)?可基于 dsh 事件日志或 deepagents 轨迹设计定量实验。
2. **记忆注入时机与形式**:何时把长期记忆注入上下文(每轮/检索触发/摘要式)对成功率与成本的影响?deepagents Store 可直接改。
3. **工具规模化检索**:模拟 100+ MCP 工具场景,对比"全量注入 vs 工具检索 vs 按需挂载"的工具选择准确率与 token 成本。
4. **上下文隔离 vs 共享的权衡**:多智能体交叉验证模式下,子代理间共享多少上下文最优?可用 deepagents 动态子代理做受控实验。
5. **KV-cache 友好的 harness 设计**:压缩/清理策略与缓存命中率的联合优化(Manus 经验的系统化验证)。
6. **Harness 层安全**:工具结果投毒在审批管线/沙箱下的防御有效性。
7. **统一评估**:目前缺乏"harness 层"的独立 benchmark(控制模型不变,只变 harness 组件)——哪怕是小型化版本也有价值。

---

## 八、对计划书三个章节的素材映射

模板三节:一、引言;二、方法论的实践与批判(如何开展,计划安排);三、总结与展望(预期成果)。

**一、引言**可直接用:第 1–2 节(Agent=Model+Harness 的行业共识、harness 定义与六大组成)+ 第 3.1/4.1 节(两个研究对象的定位)。

**二、方法论与计划安排**建议按"模块×方法"矩阵组织:

- 方法:①源码精读(dsh 按包、deepagents 按中间件)→ ②机制复现与改造(压缩策略/记忆后端/工具加载)→ ③受控对比实验(固定模型与任务,只换 harness 组件)→ ④综合报告。
- 六个模块的建议优先级:上下文管理(压缩)与复杂任务执行(规划)机制最清晰、最容易出实验;记忆管理与工具管理次之;知识库与多智能体作为扩展。
- 参考 16 周节奏:1–3 周环境搭建 + 跑通两框架 + 文献阅读;4–7 周源码精读(按六模块写笔记);8–12 周做 1–2 个受控实验(如压缩策略对比);13–14 周插件/中间件改造实践;15–16 周总结撰写。

**三、预期成果**:①调研报告(本文);②六大模块的源码解读笔记集;③1–2 组受控实验的结果与结论;④一个可运行的扩展(自定义插件/中间件,如改进的压缩策略);⑤期末论文/答辩材料。

---

## 九、参考资料

### 主要研究对象

- [deepseek-harness 官方仓库](https://github.com/deepseek-ai/deepseek-harness) | [官方手册](https://dsh.hicyou.com/zh) | [橙皮书 PDF](https://github.com/alchaincyf/deepseek-harness-orange-book) | [awesome-deepseek-harness](https://github.com/libukai/awesome-deepseek-harness)
- [知乎:deepseek-harness 项目深度解读](https://zhuanlan.zhihu.com/p/2071362726442673749)
- [Deep Agents 官方文档](https://docs.langchain.com/oss/python/deepagents/overview) | [GitHub](https://github.com/langchain-ai/deepagents) | [官网专页](https://www.langchain.com/deep-agents) | [博客: Doubling down on Deep Agents](https://www.langchain.com/blog/doubling-down-on-deepagents)
- [DataWhale《Deep Agents 实战》中文开源书](https://datawhalechina.github.io/deepagents-in-action/) | [Zilliz 测评](https://zilliz.com.cn/blog/LangChain-deepagents-review-for-long-tasks)

### Harness 概念与 Claude Code 参考

- [《御舆 — 解码 Agent Harness》](https://github.com/lintsinghua/claude-code-book) | [learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)
- [Jimmy Song: Harness 智能体的运行时基座](https://jimmysong.io/zh/book/ai-handbook/runtime/harness/) | [多智能体协同深度指南](https://jimmysong.io/zh/book/ai-handbook/agent/multi-agent/)
- [极客时间:Claude Code 工程化实战 — Harness 架构解析](https://time.geekbang.org/column/article/958033)

### 上下文工程

- [Anthropic: Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Claude Cookbook: Memory, Compaction, and Tool Clearing](https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools)
- [LangChain: Context Engineering for Agents](https://www.langchain.com/blog/context-engineering-for-agents)
- [Manus: Context Engineering for AI Agents](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus) | [Morph: Why More Tokens Makes Agents Worse](https://www.morphllm.com/context-engineering)
- [知乎: Context Engineering 一篇就够了](https://zhuanlan.zhihu.com/p/1938967453951571269) | [awesome-context-engineering](https://github.com/yzfly/awesome-context-engineering)

### 记忆管理

- [Mem0 论文](https://www.researchgate.net/publication/391246545_Mem0_Building_Production-Ready_AI_Agents_with_Scalable_Long-Term_Memory) | [AWS Agent 记忆模块实践](https://aws.amazon.com/cn/blogs/china/agentic-ai-infrastructure-deep-practice-experience-thinking-series-three-best-practices-for-agent-memory-module/)
- [A-MEM(NeurIPS 2025)](https://arxiv.org/pdf/2502.12110) | [RMM(ACL 2025)](https://aclanthology.org/2025.acl-long.413.pdf) | [AgentGuide 记忆论文综述](https://github.com/adongwanai/AgentGuide)
- [腾讯云: Agent Memory 工程化落地](https://cloud.tencent.com/developer/article/2681731)

### 工具管理与 MCP

- [MCP 官方文档](https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro) | [Tools 规范](https://modelcontextprotocol.io/specification/2026-07-28/server/tools) | [Anthropic 发布公告](https://www.anthropic.com/news/model-context-protocol)
- [知乎: 一文看懂 MCP](https://zhuanlan.zhihu.com/p/27327515233) | [阿里云: 什么是 MCP](https://www.aliyun.com/getting-started/what-is/what-is-mcp) | [MCP 安全威胁分析](https://www.secrss.com/articles/77278)

### 多智能体

- [arXiv 2508.10146: 智能体 AI 框架综述](https://www.alphaxiv.org/zh/abs/2508.10146) | [IBM: 什么是 A2A 协议](https://www.ibm.com/cn-zh/think/topics/agent2agent-protocol)
- [freeCodeCamp: LangGraph+MCP+A2A 实战全书](https://www.freecodecamp.org/news/how-to-build-a-multi-agent-ai-system-with-langgraph-mcp-and-a2a-full-book/) | [awesome-agent-orchestration](https://github.com/vivy-yi/awesome-agent-orchestration)

### 经典学术论文(领域基石,建议计划书引用)

- ReAct: Synergizing Reasoning and Acting in LMs(Yao et al., ICLR 2023)
- Reflexion: Language Agents with Verbal Reinforcement Learning(Shinn et al., NeurIPS 2023)
- Generative Agents: Interactive Simulacra of Human Behavior(Park et al., UIST 2023)— 记忆流与反思
- Voyager: An Open-Ended Embodied Agent with LLMs(Wang et al., 2023)— 技能库
- MemGPT: Towards LLMs as Operating Systems(Packer et al., 2023)
- SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering(Yang et al., 2024)— ACI 概念,harness 的学术对应
- Toolformer(Schick et al., 2023)| HuggingGPT(Shen et al., 2023)
- GraphRAG: From Local to Global(Epstein/微软, 2024)
- A Survey on LLM based Autonomous Agents(Wang et al., 2023)— 领域总综述

---

*报告由公开资料整理;dsh 架构细节以社区源码解读为主,后续研究时请以官方仓库实际代码为准。*

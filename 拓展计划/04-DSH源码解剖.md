# 计划 04:DSH(deepseek-harness)源码解剖学

> 定位:源码研读 + 文档产出 | 难度 ★★ | 周期 4-8 周 | 产出:中文机制图解文档集(8-10 篇)+ 总架构图 + 与 Deep Agents/Claude Code 对比表
> 对应课程子方向:全部六块的"底盘"

## 一、研究意义

Agent Harness 是 2025-2026 年才成型的品类:dsh(DeepSeek,2026-07 开源,12 小时 5 万星)是其中最热、也最完整的开源样本之一。官方手册与橙皮书面向使用者,知乎解读面向速览,**还没有一份面向"研究底层机制"的系统源码解剖**:微内核如何装配、插件生命周期如何驱动、事件溯源会话如何回放、工具管线如何插入守卫与审批。

对课程而言,这份解剖就是"懂智能体底层运行逻辑"的直接证明;对社区而言,它是中文生态里第一份机制级深读,有独立传播价值。同时它是其余实验计划(01/02/05/07)的基础设施——只有理解机制,才能正确地改机制。

## 二、研究现状及实验室研究基础

- **项目事实**:dsh 为 TypeScript 微内核架构,基于 Cordis 依赖注入,pnpm monorepo 50+ 子包;核心理念 Everything is a Plugin(Service Definition/Provider/Consumer);会话采用事件溯源(append-only 日志+摘要重建);工具执行有 pre-execute/execute/post-execute 管线;任务侧有 goal/plan/todo 三层包与 subagent/workflow 包;支持 MCP、Profile/Bundle/Skills 声明式组合。
- **已有解读与空白**:官方手册(dsh.hicyou.com)、橙皮书 PDF、知乎源码解读覆盖"是什么";空白在"怎么运转":调用链、时序、模块耦合、与 deepagents 中间件路线的机制级对比。
- **实验室基础**:仅需 Node.js + git;纯读代码+写文档,零 API 成本;Deep Agents(Python,代码量小)作对照系,Claude Code 公开资料作第三参考系。

## 三、研究内容及研究计划

### 3.1 研究内容(每篇笔记固定结构:机制作用 → 关键代码走读(文件:行号)→ 时序图 → 设计权衡 → 与 Deep Agents 对比)

1. **仓库地图**:pnpm monorepo 结构、包依赖图、内核包与功能包的边界。
2. **微内核与 Cordis DI**:Service Definition/Provider/Consumer 三件套;多实现优先级;依赖装配时机。
3. **插件生命周期**:加载、激活、停用;内核到底"微"在哪里(最小职责清单)。
4. **事件溯源会话**:事件类型学、append-only 日志、崩溃恢复、多客户端同步、摘要重建近窗口。
5. **工具执行管线**:注册(schema)、pre-execute 守卫、审批环节、执行、post-execute 元数据(命令/返回码/时长)。
6. **任务层级**:goal→plan→todo 三层包的职责划分与状态机;与 deepagents write_todos 的机制差异。
7. **子代理与工作流**:subagent 独立上下文的实现;workflow 编排原语;委派-返回协议。
8. **上下文与 compaction**:触发条件、摘要保留结构、与 KV-cache 的关系(结合计划 07)。
9. **模型接缝与 MCP**:ChatModel 抽象、多供应商适配、MCP 工具接入路径。
10. **Profile/Bundle/Skills**:声明式组合如何落到插件系统;与 Agent Skills 规范的关系。

### 3.2 周计划(8 周,可压缩为 4 周精简版:1/2/4/5/6 五篇)

- W1:跑通 dsh(npx @deepseek-ai/dsh web)+ 仓库地图 + Cordis 前置学习。
- W2-W3:内核三篇(地图/DI/生命周期)+ 会话事件溯源。
- W4-W5:工具管线、任务层级、子代理工作流。
- W6:compaction、模型接缝、声明式组合。
- W7:总架构图(一张图讲清 dsh)+ 三框架机制对比表(dsh vs deepagents vs Claude Code 公开资料)。
- W8:交叉校验(关键结论对照官方文档复核)+ 合集成册。

### 3.3 预期产出与验收标准

- 产出:8-10 篇中文机制笔记(每篇含代码走读与图)、1 张总架构图、1 张三框架对比表、合集 PDF/站点。
- 验收:每个机制笔记至少给出一处"读代码才知道、文档没写"的发现(如装配顺序、默认值、边界处理);总架构图能被第三方按图索骥找到对应包。

### 3.4 风险与退路

- 风险:dsh 迭代快,行号漂移 → 笔记标注 commit hash;每篇开头写"基于版本 x.y.z"。
- 风险:developer preview 阶段 API 变动 → 以机制为主线而非 API 细节;变动本身就是"观察一个 harness 品类演化"的素材。

## 附:给执行智能体(Flash)的任务指令

```text
角色:你是源码研读助理,负责产出 deepseek-harness(dsh)的中文机制解剖文档。

资源:仓库 https://github.com/deepseek-ai/deepseek-harness(clone 到本地,记录 commit hash);
参考:官方手册 https://dsh.hicyou.com/zh ;对照项目 langchain-ai/deepagents(Python)。

任务:按下述清单逐篇产出笔记,每篇固定结构:
【机制作用 → 关键代码走读(文件:行号,引用真实代码段)→ 时序/结构图(mermaid)→ 设计权衡 → 与 deepagents 对应机制对比】。

清单(按序):
1 仓库地图与包依赖 2 微内核与Cordis依赖注入 3 插件生命周期 4 事件溯源会话与恢复
5 工具执行管线(守卫/审批/元数据) 6 goal-plan-todo任务层级 7 subagent与workflow
8 compaction与上下文重建 9 模型接缝与MCP接入 10 Profile/Bundle/Skills声明式组合

规则:
- 所有结论必须落到真实代码,禁止凭文档或猜测描述机制;不确定处明确标注"待核验"。
- 每篇至少一处"文档未写、读码才知"的发现(装配顺序/默认值/边界处理/错误路径)。
- 代码引用给出 文件路径:行号 与 commit hash;图用 mermaid。
- 最后汇总:一张总架构图 + dsh/deepagents/Claude Code(公开资料)三框架机制对比表。

产物:docs/ 目录下 10 篇 md 笔记 + SUMMARY.md(总架构图+对比表)。
先交第 1、2 篇供人工审阅风格,确认后再继续。
```

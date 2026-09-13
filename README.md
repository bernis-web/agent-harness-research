# 智能体 Harness 架构研究(2026 秋·本科生科研实践)

研究对象:以 **deepseek-harness(dsh)** 为主、**LangChain Deep Agents** 为辅,围绕智能体运行时的六大子方向(记忆管理、上下文管理、知识库管理、工具管理、复杂任务执行、多智能体协作)开展机制解剖与受控实验。

## 仓库内容

| 目录/文件 | 说明 |
|---|---|
| `科研实践计划书-智能体Harness架构研究.docx` | 正式计划书(按课程模板) |
| `调研报告-智能体Harness架构.md` | 领域调研:harness 概念、双对象对比、六大子方向现状、7 个候选研究问题 |
| `dsh-anatomy/` | **dsh 源码解剖系列(10 篇 + 总目录)**,基于 commit `c291e79`(v0.1.5-rc.2),行号级引用 + 校验命令 |
| `拓展计划/` | 7 份自包含的候选研究计划(压缩保真度/工具规模化/记忆注入/源码解剖/多智能体编排/安全防御/KV-cache) |
| `评审意见-Claude-20260914.md` | 笔记 01–03 的独立评审记录(约 40 项代码引用逐条复核) |
| `.knowledge-graph.jsonl` | 项目知识图谱(实体/关系,随笔记增量更新) |

## dsh 解剖系列阅读路径

- **框架**:[01 仓库地图](dsh-anatomy/01-仓库地图与包依赖.md) → [02 微内核与 Cordis](dsh-anatomy/02-微内核与Cordis依赖注入.md) → [03 生命周期与装配](dsh-anatomy/03-插件生命周期与装配管线.md)
- **数据流**:[04 事件溯源会话](dsh-anatomy/04-事件溯源会话.md) → [05 工具执行管线](dsh-anatomy/05-工具执行管线.md) → [08 压缩与外置](dsh-anatomy/08-压缩与结果外置.md)
- **组织**:[06 任务层级](dsh-anatomy/06-任务层级goal-plan-todo.md) → [07 子代理与工作流](dsh-anatomy/07-子代理与工作流.md)
- **产品化**:[09 模型接缝与 MCP](dsh-anatomy/09-模型接缝与MCP.md) → [10 声明式组合与扩展](dsh-anatomy/10-声明式组合与扩展.md)

总目录与六大子方向对照见 [dsh-anatomy/SUMMARY.md](dsh-anatomy/SUMMARY.md)。

## 说明

- 笔记中所有代码引用均标注 `文件:行号` 并基于固定 commit,每篇页脚附 30 秒可复核的 `grep` 校验命令。
- dsh 处于 developer preview 快速迭代期,机制描述以其固定 commit 为准;行号漂移时可用校验命令重新定位。
- 参考资料:[deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) · [deepagents](https://github.com/langchain-ai/deepagents) · [DataWhale《Deep Agents 实战》](https://datawhalechina.github.io/deepagents-in-action/) · [《御舆——解码 Agent Harness》](https://github.com/lintsinghua/claude-code-book)

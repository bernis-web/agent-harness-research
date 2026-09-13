# DSH(deepseek-harness)源码解剖 · 系列目录

> 基于 commit `c291e7961a515f6d7af9304e7fd1d257929aef26`(v0.1.5-rc.2)。
> 每篇统一结构:机制作用 → 代码走读(文件:行号)→ mermaid 图 → 设计权衡 → 与 Deep Agents 对比 → 读码才知清单;页脚附 30 秒校验命令。
> 姊妹文档:[../调研报告-智能体Harness架构.md](../调研报告-智能体Harness架构.md) · [../拓展计划/](../拓展计划/)

| # | 笔记 | 主题 | 对应课程子方向 | 状态 |
|---|---|---|---|---|
| 01 | [仓库地图与包依赖](01-仓库地图与包依赖.md) | 268 包/50 能力域、顶层布局、依赖分层、**术语表** | 总览 | 已评审✅ |
| 02 | [微内核与Cordis依赖注入](02-微内核与Cordis依赖注入.md) | 五概念、五分发模式、Service 基类、**能力 seam 三角色**(shell 范例) | 总览(底盘) | 已评审✅ |
| 03 | [插件生命周期与装配管线](03-插件生命周期与装配管线.md) | fiber 状态机、boot 四级叠层、fail loud、live reload、preset/scope | 总览(底盘) | 已评审✅ |
| 04 | [事件溯源会话](04-事件溯源会话.md) | append-only 日志、SessionEventMap、deriveMessages、fork、end-seed、格式 v3 | 记忆管理/上下文管理 | 完成 |
| 05 | [工具执行管线](05-工具执行管线.md) | 三瀑布、单调守卫、ctx.approval fail-closed、PTC、guard 域 | 工具管理 | 完成 |
| 06 | [任务层级 goal/plan/todo](06-任务层级goal-plan-todo.md) | 三层任务包、后台 jobs、schedule | 复杂任务执行 | 完成 |
| 07 | [子代理与工作流](07-子代理与工作流.md) | subagent 委派、workflow 引擎、Agent Teams(roster/任务板/mailbox) | 多智能体协作 | 完成 |
| 08 | [压缩与结果外置](08-压缩与结果外置.md) | compaction 事务、surface 节点遮蔽、spill 截断、KV-cache 视角 | 上下文管理 | 完成 |
| 09 | [模型接缝与MCP](09-模型接缝与MCP.md) | dsh-llm(SD+Consumer 合并范例)、prepareCall、MCP 接入 | 工具管理/知识库 | 完成 |
| 10 | [声明式组合与扩展](10-声明式组合与扩展.md) | bundle 栈、skills 渐进式披露、extensions 模型自修改、hooks 兼容 | 知识库管理 | 完成 |

## 阅读路径建议

- **先懂框架**:01 → 02 → 03(Cordis 世界观:fiber、inject、seam)
- **再懂数据流**:04 → 05 → 08(账本 → 手脚 → 上下文卫生)
- **然后懂组织**:06 → 07(任务与协作)
- **最后懂产品化**:09 → 10(模型接入与声明式生态)

## 六大子方向 × dsh 机制对照

| 课程子方向 | dsh 对应机制 | 笔记 |
|---|---|---|
| 记忆管理 | 会话日志(唯一真源)、session-query 检索、投影 seam | 04 |
| 上下文管理 | compaction、spill、context 域(workspace 指令/时间上下文) | 04/08 |
| 知识库管理 | skill 域(SKILL.md 渐进式披露)、fs 域、web 域 | 10 |
| 工具管理 | ctx.tools 管线、guard 域、sandbox 域、MCP | 05/09 |
| 复杂任务执行 | goal/plan/todo 三层、jobs、schedule | 06 |
| 多智能体协作 | subagent 委派、Agent Teams(roster/任务板/mailbox)、preset+isolate | 07/03 |

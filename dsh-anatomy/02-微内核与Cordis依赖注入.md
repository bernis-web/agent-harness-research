# 笔记 02|微内核与 Cordis 依赖注入

> 基于 commit `c291e7961a515f6d7af9304e7fd1d257929aef26`。核心材料:`docs/cordis-primer.zh.md`、`vendor/cordis/src/`(8 个源文件共 2693 行)、`packages/shell/` 规范范例、官方能力 seam 设计笔记(`.agents/notes/implemented/architecture/2026-06-13-capability-seams.zh.md`)。

## 一、机制作用:为什么需要"微内核 + DI"

Agent Harness 的本质要求是**一切能力可替换**——换模型、换执行后端、换持久化,产品其余部分不动。dsh 的解法是把运行时做成一棵 **Cordis 插件树**:

> 不存在需要打补丁的特权内核:扩展 dsh 的方式是把插件挂载到其他插件旁边,而各项注册都是副作用,会在其插件卸载时撤销。(`docs/architecture.zh.md`)

"微内核"在这里的含义非常具体:内核只剩 **Cordis 框架本身**(上下文容器 + 服务注册 + 类型化事件 + fiber 生命周期),连 agent loop 都是普通插件。Cordis 不是 dsh 发明的——它是 [cordiverse/cordis](https://github.com/cordiverse/cordis)(社区知名 Bot 框架 Koishi 的内核)的 **4.0.0-rc.7 fork**,以源码 vendor 方式引入并改名 `@deepseek-ai/*`,完全自持(`vendor/README.md`;vendor 目录下只有这份英文 README)。

> 版本注:manifest 记录的上游版本是 4.0.0-rc.7,而 vendored 包自身 `package.json` 写的 4.0.2 是 fork 内的演进版本号——两个数字不是一回事,勿混。

## 二、Cordis 五个核心概念(官方 primer 的准确表述)

1. **插件是实现 Service 的对象**:带可选 `inject` 和 `apply(ctx)` 的函数,或 `Service` 子类。
2. **上下文是服务的容器**:一个服务占据稳定的 `ctx.<key>`(如 `ctx.tools`、`ctx.llm`、`ctx.sessions`);其他插件**按键查找服务,而非导入实现**。
3. **通过 `inject` 声明服务依赖**:插件等待依赖就绪才启动——**加载顺序靠服务依赖表达,而非手动启动序列**。
4. **类型化事件用于通信**:TypeScript 声明合并注册事件名,五种分发模式。
5. **注册是可逆的副作用**:片段、schema、适配器、监听器经 `ctx.effect()`/`ctx.on()` 安装,teardown 时自动撤销。

### 分发模式(`vendor/cordis/src/events.ts:32`)

```typescript
export type DispatchMode = 'emit' | 'parallel' | 'serial' | 'bail' | 'waterfall'
```

| 模式 | await? | 顺序 | 返回值 | dsh 用途示例 |
|---|---|---|---|---|
| `emit` | 否 | 注册序 | 无 | 通知类(`session/event` 广播) |
| `waterfall` | 否 | 注册序 | 有 | **环绕中间件**(工具守卫、请求改写) |
| `parallel` | 是 | 并行 | 无 | 并行扇出观察 |
| `serial` | 是 | 注册序 | 有 | 按序决策(`agent/turn-stopping`,无 `next()`) |
| `bail` | 否 | 注册序,首个命中即停 | 有 | 拦截型策略 |

**waterfall 语义**(primer 明确规定):监听器收到 `(...args, next)`;调 `next()` 执行下游,其返回值可包装后外传;**不调 `next()` 直接返回 = 短路**。策略监听器拥有决策权时可短路,观察类监听器必须委托——`tools/pre-execute` 的 deny/ask 门就是在此语义上实现的。

## 三、内核源码走读(9 个源文件共 2693 行,每文件干什么)

| 文件 | 行数 | 职责 |
|---|---|---|
| `index.ts` | 14 | 公共出口(重导出各模块) |
| `context.ts` | 146 | `Context` 容器:服务属性访问、事件方法、插件挂载入口 |
| `events.ts` | 352 | 五种分发模式实现 + 事件类型声明合并 |
| `fiber.ts` | 754 | **生命周期核心**:每个插件一个 Fiber,跟踪依赖状态、校验后配置、生命周期 effects |
| `registry.ts` | 337 | 服务注册表 + `Inject` 类型与 `@Inject` 装饰器 |
| `reflect.ts` | 418 | 服务属性机制:`provide`/`accessor`/`mixin` |
| `service.ts` | 115 | `Service` 基类:注册为 `ctx.<name>` 的命名服务 |
| `logger.ts` / `utils.ts` | 557 | 日志、符号与辅助 |

### 3.1 服务如何上到 `ctx` 上(`service.ts`)

```typescript
// vendor/cordis/src/service.ts:11 —— Service 类;构造器在 :42,实际注册调用 ctx.reflect.provide(...) 在 :57
export abstract class Service<out T = never> {
  constructor(protected ctx: Context, name: string) {
    name ??= this.constructor['provide'] as string
    // …构造即经 ctx.reflect.provide(name, this, this[Service.check]) 注册,
    //   拥有 fiber 卸载时自动注销;[Service.invoke] 存在时实例可调用
  }
}
```

七个 `symbols`(`init`/`check`/`config`/`invoke`/`extend`/`tracker`/`resolveConfig`)构成类的元协议:`check` 是可用性谓词,`config` 是配置拦截类型,`invoke` 让服务实例本身可调用(如 `ctx.logger()`)。

### 3.2 依赖声明与"等待就绪"(`registry.ts`)

```typescript
// vendor/cordis/src/registry.ts:19
export type Inject<M = Dict> = (keyof M)[] | { [K in keyof M]?: M[K] }
```

数组形式只请求服务;对象形式可为每个服务附 intercept config。`@Inject` 装饰器还能**修饰方法**——方法调用被延迟到所声明的服务可用为止(`Inject` 类型在 :19;`@Inject` 函数在 :37,方法级延迟调用逻辑在 :45-55)。fiber 层(`fiber.ts:184` `class Fiber`,`:194` `state = FiberState.PENDING`)在依赖缺席时保持 PENDING,服务被 `provide` 时唤醒——这就是"声明即接线"的运行时机制。

### 3.3 dsh 对内核动过的刀

`vendor/README.md` 本地修改清单第 6 条:`fiber.ts` 生命周期加固——effect 的 owner 列表包装**先于 setup 主体注册**、同步 setup 失败移除包装并回滚已收集的清理、owner 处于 `UNLOADING` 时**拒绝创建新 effect**(PENDING/LOADING 仍合法)等,堵住三个可重入销毁缺口。含义:**插件在 setup 中途被卸载、或清理函数里再注册,都不会漏资源**——对"实时重载 patch"的产品特性这是硬前提。

## 四、规范范例:shell 能力 seam 的三角色

官方指定 `packages/shell` 为 seam 范例。三角色划分(注意:角色是**设计概念**,seam 指三者整体,不是某个接口):

### Service Definition —— `dsh-shell`(拥有 `ctx.shell`)

```typescript
// packages/shell/shell/src/index.ts:39
declare module '@deepseek-ai/cordis' {
  interface Context { shell: ShellExecutor }   // 声明合并:ctx.shell 有了类型
}
// packages/shell/shell/src/index.ts:64-66
export abstract class ShellExecutor extends Service {
  constructor(ctx: Context) { super(ctx, 'shell') }   // 构造即注册为 ctx.shell
}
```

只定义词汇类型(`ShellExecRequest`/`ShellRunResult`/`ShellProcess`)+ 抽象方法(`run` 前台、`start` 后台)。注意其 JSDoc 约定:`run` **只对基础设施失败 reject**,非零退出、超时杀、abort 杀都 resolve 成 `ShellRunResult`——语义约束写进 SD,Providers 才有统一行为。

### Service Provider —— `dsh-bash-local` / `dsh-bash-sandbox` / `pwsh-*` / `shell-env`

实现 `ShellExecutor` 抽象类并作为插件挂载。同一 SD 之下,本地执行、沙箱执行(接 `dsh-sandbox` 的 bwrap/Landlock/Seatbelt)、PowerShell 变体是**兄弟包**;SD 文件的 JSDoc 注释明确:一个 host 只组装一个 `ctx.shell` 提供方(`shell/shell/src/index.ts:15-17`),**重复注册同一服务会 fail loud**——原文 "loading a second throws, which is cordis' standard duplicate-service behavior"(`:48-49`),win32 层只换配置行而不是共存两个实现。

### Consumer —— `dsh-tool-bash`(面向模型的工具)

```typescript
// packages/shell/tool-bash/src/index.ts:30
export const inject = ['tools', 'shell', 'systemPrompt', 'shellEnv']
```

消费方声明四个服务键,拿到 `ctx.shell` 直接用;**从头到尾没有 import `dsh-bash-local`**——它 import 的类型全部来自 SD(`@deepseek-ai/dsh-shell`)与横向 seam(`dsh-sandbox`、`dsh-jobs`)。这就是官方规则"Consumer 注入服务键,从不导入 Provider 特有类型"的实证。

### 组装结果

```mermaid
flowchart LR
    subgraph SD["Service Definition(dsh-shell)"]
        ABS["abstract ShellExecutor extends Service<br/>own ctx.shell + 词汇类型"]
    end
    subgraph P["Service Providers"]
        BL["bash-local"]
        BS["bash-sandbox<br/>(bwrap/Landlock/Seatbelt)"]
        PW["pwsh-local / pwsh-sandbox"]
    end
    subgraph C["Consumers"]
        TB["tool-bash(inject: shell)"]
        TBP["tool-bash-persistent"]
    end
    ABS -.被实现.-> P
    P --"运行时 provide"--> CTX["ctx.shell"]
    CTX --"inject 等待并注入"--> C
    C --"从不 import"-.-> P
```

替换 `bash-local` → `bash-sandbox`,工具 schema 与 Consumer 一行不改——**seam 三角色分离的全部收益**。

> 图注:图中 `tool-bash` 只标了 `inject: shell` 一个键;完整注入为 `['tools','shell','systemPrompt','shellEnv']`(见 §四),其余三键图略。同理,fs+subprocess 指向远程沙箱时,Bash、PTY、LSP 整个执行世界一起搬走(`docs/architecture.zh.md` §能力 seam)。

## 五、设计权衡(官方明确记录的理由)

1. **拆包的代价是自愿付的。** 三角色分离增加 package.json/tsconfig/README/注入接线;官方规则是"不要预防性拆分——如果一项能力只有一种可设想的 Provider 和一个 Consumer,就保持一个包"(如 LLM seam 把 SD 和 Consumer 合并进 `dsh-llm`,因为 Consumer 是 agent loop 本身,不存在可替换的 schema 接口)。
2. **包边界 ≠ 运行时机制。** 设计笔记特别区分:谁在运行时提供/需要能力,是 Cordis 的服务 + `inject` 解决的;而三角色决定的是**包的边界**(约定/实现/消费 API 以不同速率变化)。把两者混为一谈是初学者最常见错误。
3. **两个"capability"要分清。** `@cordisjs/plugin-capability` 是权限/沙箱安全服务(具名权限 + 继承,`ctx.capability.test`),是 `tools/pre-execute` deny/ask 门的候选机制——与能力 seam 毫无关系。
4. **Service Definition 绝不用 TS interface**——必须是抽象类或具体注册表服务(接口没有运行时存在,无法被 Cordis 注册)。
5. **微内核的"微"是相对的**:vendor 进来的 Cordis fork 本身 2693 行内核源码 + dsh 加固;但相比"把 loop、工具、模型都写死在主程序"的架构,这已经是能买到的最小内核。

## 六、与 Deep Agents 对比

| 维度 | dsh(Cordis) | deepagents(中间件栈) |
|---|---|---|
| 组装单元 | 插件/包(268 个物理包) | 中间件函数(SubagentMiddleware、TodoListMiddleware…) |
| 接线方式 | `inject` 声明 + fiber 挂起等待,**运行时自动接线** | 构造时显式传入 agent 工厂,编译期接线 |
| 依赖缺失时 | 插件保持 PENDING,服务就绪自动唤醒 | 缺失即在构造/调用时报错 |
| 替换粒度 | 换 Provider 包,Consumer 无感 | 换中间件实例,需重组 agent |
| 卸载/热替换 | 注册是可逆副作用,patch 实时重载(vendor 加固支撑) | 无运行时热替换概念 |
| 类型表达 | 声明合并给 `ctx.<key>` 加类型 | 无声明合并等价物:Python 有 Protocol/TypedDict,但做不到"给任意服务的 ctx 键静态加类型"这种全局声明合并,服务键的类型约束靠人工保持一致 |

关键洞察:deepagents 的 middleware 天然带**顺序语义**(洋葱模型,与 waterfall 同构),但**没有"等待"语义**——它的世界是"先组装后运行";Cordis 的世界是"声明依赖,框架决定何时你该活"。前者简单直接,后者换来热替换与增量装配,代价是 268 包的认知成本与一套 fiber 生命周期。

## 七、读码才知清单(本篇增量)

1. `inject` 是**挂起而非报错**:依赖缺席的插件停在 `FiberState.PENDING`(`fiber.ts:194`),服务就绪后被唤醒——所以 dsh 里"启动顺序"这个概念不存在,只存在"服务依赖图"。
2. 重复提供同一 `ctx.<key>` 服务会 **fail loud**(`shell/shell/src/index.ts:48-49` 注释原文 "loading a second throws")——平台层用硬错误防止静默双实现。
3. dsh 对 vendored Cordis 的加固集中在**销毁确定性**(可重入销毁、UNLOADING 窗口),而非加载性能——印证"实时重载 patch"是产品级需求。
4. Consumer 的 `inject` 列表暴露真实依赖面:`tool-bash` 依赖 `['tools','shell','systemPrompt','shellEnv']`——一个工具要同时消费工具注册表、执行世界、提示词组装和环境信息,这就是为什么 SD 必须先行存在。

---
*校验命令:`grep -n "export abstract class Service" vendor/cordis/src/service.ts`(预期 :11);`grep -n "export type Inject" vendor/cordis/src/registry.ts`(预期 :19)。所有行号引用基于 commit c291e79。*

*下一篇(03)将进入插件生命周期与 boot/profile 叠加:一棵插件树在 `dsh --profile web` 时如何被装配出来。*

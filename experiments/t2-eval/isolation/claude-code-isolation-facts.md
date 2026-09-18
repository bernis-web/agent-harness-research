# Claude Code 隔离配置事实（D2 断点材料，2026-09-18）

来源：claude-code-guide 子代理依官方文档核实（断点前派发，结果已返回）。
原文报告见会话转录；本文件为决策相关蒸馏，供 L-c 探针设计与 D4 批次 spec 引用。
所有事实标注自官方文档；「未明确」为文档空白，不是推测。

## 1. deny 规则语法（permissions.md）

- 形式 `Tool(specifier)`；Read/Edit 用 gitignore 风格。四种锚定：
  `//path`=文件系统根绝对路径；`~/path`=home；`/path`=**settings 来源目录相对**
  （文档明确警告不是绝对路径！绝对路径必须 `//`）；`path`/`./path`=当前目录相对。
- **Windows 路径匹配前规范化为 POSIX 形式**：`C:\Users\alice` → `/c/Users/alice`
  （盘符小写单字母、去冒号、正斜杠）。故拒绝整棵评价侧树的文档化写法：
  `Read(//d/projects/agent-harness-research/**)`。盘符大小写（`//d/` vs `//D/`）
  是否等效：**文档未明确**——探针需实测。
- 评估顺序 deny → ask → allow，首个匹配生效；**deny 不可被任何层的 allow 豁免**；
  **deny 在 bypassPermissions 下同样生效**（permission-modes.md：「Deny rules block
  in every mode, including bypassPermissions」）。
- `Read` deny 同时封禁同路径 Edit/Write（edits v2.1.208+、writes v2.1.228+）；
  NotebookEdit 需另写 `Edit` deny；`Write(...)`/`Glob(...)` 路径规则被接受但永不查询。
- 覆盖边界（残余风险的核心依据，原文警告）：Read/Edit deny 作用于内置文件工具、
  Bash 中**被识别的**文件命令（cat/head/tail/sed/tee）及重定向目标；**不**作用于
  不点名文件的读取（`grep -r pattern .`）与自开文件的任意子进程（Python/Node）。
  OS 级强制需 sandbox。

## 2. 无头模式（headless.md / cli-reference / settings.md）

- `claude -p` 默认加载与交互会话相同上下文（cwd 项目 settings + `~/.claude`）。
- **trust 差异**：未信任目录下 `-p` 会扣留项目 settings 的 `permissions.allow` 与
  `additionalDirectories`（stderr 警告 workspace not trusted）；hooks/env 照用；
  **deny/ask 规则不受 trust 影响，照常生效**。→ D4 若需 workspace allow 规则，
  放 `--settings`（命令行）不受 trust 影响。
- `--settings <file-or-json>` 存在：覆盖同名键，≤2MiB 常规文件；优先级
  Managed > 命令行 > 项目 local > 项目共享 > 用户。
- `--setting-sources user,project,local` 控制加载来源；`--bare` 跳过
  hooks/skills/commands/subagents/plugins/MCP/CLAUDE.md 自动发现。
- `--permission-mode` 取值：default / acceptEdits / plan / auto / dontAsk /
  bypassPermissions（+manual 别名）。**项目 settings 里设 bypassPermissions 为
  defaultMode 不生效**；从用户 settings、`--settings`、managed 设置则生效。

## 3. Windows 沙箱（sandboxing.md）

- 官方原文：「The sandbox is built into Claude Code and runs on macOS, Linux,
  and WSL2. **Native Windows is not supported.**」
- 沙箱只作用于 Bash/PowerShell/Monitor 及其子进程。→ T2 残余风险披露
  （spec-d2 §2）与官方口径一致，不声称能堵 shell 越界读取。

## 4. 工作区围栏机制（permissions.md / settings-reference.md）

- `additionalDirectories`/`--add-dir` 是**增量授权**，不是白名单。
- 默认：文件工具在 cwd + 附加目录内免批；**目录外读取是审批闸门而非硬拒**
  （bypassPermissions 下直接放行）。
- 硬围栏（文件工具层）：`permissions.blockReadsOutsideWorkingDirectories`
  ——所有 permission mode 下拒绝读工作目录之外（v2.1.257+ 对被识别的读类
  Bash 命令在 auto/bypass 也提示）。
- CLI 层 `--restricted`（v2.1.248+）：内置文件工具限制在工作目录内、只加载
  managed settings 与 `--settings`、拒绝 bypassPermissions。
- Bash 默认不限制在 cwd；内置只读命令集（ls/cat/grep/find/head/tail/…）
  任何模式下免提示，可读任意路径（除非上述围栏）。

## 5. 对 T2 L-c 探针与 D4 的设计含义（待恢复后定稿）

1. 原生 Windows 可得的最强文件工具围栏 ≈ deny 规则（POSIX 盘符写法）+
   `blockReadsOutsideWorkingDirectories`（或 `--restricted`）+ `--setting-sources`
   收窄 + `--bare`。Bash 越界读取**堵不住**（官方明确），残余风险维持披露口径。
2. 探针必测项：`//d/` 与 `//D/` 盘符大小写是否等效；eval 路径 Read 被拒 /
   workspace 路径 Read 成功；`-p` 下 deny 在未信任目录是否生效（文档称是，
   值得实证）；（诚实记录）python 子进程 open() 越界读不被拦截的实证。
3. D4 批次会话建议从工作区外干净启动参数组合，不依赖用户全局 settings；
   allow 规则走 `--settings` 而非项目文件（trust 扣留问题）。

来源 URL：code.claude.com/docs/en/{permissions,permission-modes,sandboxing,
cli-reference,settings,settings-reference,headless}.md

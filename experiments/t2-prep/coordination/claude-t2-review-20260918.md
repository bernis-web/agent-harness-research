"glm-5.3-flash" isn't described by this version's model catalog; update Claude Code, or map it with behavesAs on a modelPicker row (or modelOverrides, if it is a provider id of a model this version knows). Until then auto-compact keeps this session within 200k tokens (the context window it assumes); if the model accepts more, append [1m] to the model name for 1M, or set CLAUDE_CODE_MAX_CONTEXT_TOKENS to its real window; CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1 restores the previous wait-for-the-API behavior.
[claude-code:unrecognized_model] {"model":"glm-5.3","query_source":"generate_session_title"}
[claude-code:unrecognized_model] {"model":"glm-5.3-flash","query_source":"sdk"}
# T2-prep 文档内部一致性审阅报告

审阅范围：`spec\T2-SPEC-draft-v0.1.md`、`acceptance\public-cases.md`、`acceptance\hidden-groups.md`、`acceptance\mutation-map.md`、`acceptance\README.md`、`README.md`（只读，未做任何修改或运行）。

---

## 一、较值得修正的发现（低严重度，非行为矛盾）

### F1. hidden-groups §0.1 对 U01 末尾 LF 的「改为」措辞与公开稿不一致
- 文件/行：`acceptance\hidden-groups.md` 第 13 行
- 证据：「步骤 1 末尾 LF 断言改为「可有可无一个末尾 LF」」
- 对照：`public-cases.md` 第 35 行 U01 步骤 1 已写「末尾 LF 允许 0 或 1 个」；spec §4（第 30 行）「文件末尾允许 0 或 1 个结束 LF」。
- 问题：公开稿本就允许 0 或 1 个，H01 并无实际改动，用「改为」暗示公开稿断言不同，与 §0「未列出的……逐字相同」的表述逻辑冲突，易误导评审认为存在差异。
- 建议：删除该行或改为「与公开稿一致（0 或 1 个末尾 LF 均合法）」。

### F2. H04「命中范围缩小为仅第二条」表述与公开稿现状不符
- 文件/行：`acceptance\hidden-groups.md` 第 73 行
- 证据：「步骤2 命中范围缩小为仅第二条（公开稿纠错基线一致）」
- 对照：`public-cases.md` 第 151 行 U09 步骤 2 已是「仅第二条（第一条 title `Alpha` 不含 `beta`，不命中）」；`hidden-groups.md` 第 18 行 §0.1 亦写「beta 查询只命中第二条」。
- 问题：公开稿并无「命中多条需缩小」的旧值，所谓「缩小」没有对照物；「公开稿纠错基线」指向不明，读者无法核验。
- 建议：改为「命中范围与公开稿同构：仅 title=`epsilon` 的第二条命中（`Delta` 不命中）」，去掉「缩小/纠错」措辞。

### F3. acceptance\README.md 与根 README.md 称「2–3 条变异」，实际固定为 3 条
- 文件/行：`acceptance\README.md` 第 6 行、`README.md` 第 13 行
- 证据：「`mutation-map.md` — 2–3 条单要求变异」
- 对照：`mutation-map.md` 第 7 行「3 个变异 M01–M03，各违反唯一主要求」为固定数量。
- 问题：「2–3 条」为区间表述，与 mutation-map 的固定 3 条不一致（不矛盾但弱化了一致性）。
- 建议：两处 README 统一改为「3 条」或「3 条（固定，待会审）」。

---

## 二、逐项检查结论

**1) U01 中 Straße/STRASSE/casefold 一致性：一致，未发现矛盾。**
- U01 步骤 4（public-cases 第 38 行）：查询 `strasse` 期望 `[t2,t3]`。casefold("Straße")="strasse" 命中 t2；casefold("STRASSE二")="strasse二" 含子串命中 t3；t1/t4 不含。成立。
- U01 步骤 9（第 43 行）重载后同查询仍 `[t2,t3]`，与重载语义（R10）一致。
- H01（hidden-groups 第 24–31 行）：`Maße`→casefold "masse"、`MASSE二`→"masse二"，查询 `masse` 期望 `[Maße条, MASSE二条]`，与公开同构。成立。
- U04 步骤 3（public-cases 第 93 行）与 H03 步骤 3（hidden-groups 第 59 行）：`ß`→casefold "ss"，前三条折叠后（"strasse"/"masse 在正文"/"masse双命中"）均含 "ss"，第四条不含。成立。
- M02 对 lower-vs-casefold 的失效分析（mutation-map 第 25–27 行）：`"ß".lower()=="ß"`、`strasse` 查询漏 `Straße`、`ß` 查询只命中第一条——数学上均正确。

**2) JSONL 末尾 LF「允许 0 或 1 个」全篇一致：一致。**
- spec §4 第 30 行「允许 0 或 1 个」；§9 第 66 行引用同规则；public-cases 第 24 行统一判据、U01 步骤 1（第 35 行）、U02 步骤 4「有或无均可」（第 54 行）、U05 步骤 1（第 100 行）均一致。U02 初始夹具固定 1 个 LF 属夹具字节固定，不与「成功写入不强制」冲突（第 24 行已显式区分「固定初始夹具的字节表示不等于成功写入格式要求」）。唯一瑕疵即上述 F1 的措辞问题。

**3) U07/U08 与 R09/R02/R11 及相关条款一致：未发现矛盾。**
- U08 步骤 1 目标已存在普通文件→exit 2（spec §3 第 25 行、R08 第 50 行均列为 2 类）；步骤 2 `./sub/../good.jsonl`→exit 2（R11 规范化同路径）；步骤 3 目标为目录→exit 3（R02「路径指向目录→exit 3」）；步骤 4 `--out` 缺父目录→exit 3 且不隐式创建（R02 明文）；步骤 5 空路径→exit 2（R02）；步骤 6/7 store 为目录→exit 3；步骤 8 add 缺父目录→exit 3（R02「`add` 的 store 不存在且父目录存在时新建」的反面）；步骤 9 字面同路径→exit 2（R11）。全部逐条对得上。
- U08 各步 GOOD/`exists.json`/`adir`/`sub` 的 bytes/内容不变断言与 R09（被拒操作不改 store bytes、无临时残留）一致；U07「均不修改输入 store」与 R09「成功读操作不重写 store」一致；ABS 构造规则（public-cases 第 10 行）与 U07 步骤 2 用法一致。
- `sub` 预创建空目录在 U08（第 130、135 行）与 hidden-groups §0.1「`sub` 为已存在的空目录」（第 17 行）一致。

**4) 交付门槛（notes.py/README/CHANGES≤10 条/tests 集合与 SHA-256 不变）四份入口一致：一致。**
- spec §0（第 6–7 行）、public-cases「静态交付门槛」（第 19–22 行）、acceptance README（第 26–29 行）、根 README（第 44–47 行）四处表述逐点一致：修复非新建、tests 不可增删改、修复前后相对文件集合+逐文件原始 bytes SHA-256 完全一致、哈希清单留在评价侧、本轮不读取/计算哈希、CHANGES≤10 条（spec 另注明「按非空变更条目计，标题不计」，属细化不冲突）、仅标准库、不新增第 11 个行为场景、未核对记 UNRUN。spec R12（第 54 行）亦正确引用。

**5) 隐藏组仅替换数据、不新增要求：基本成立。**
- H01–H04 的替换项均为 title/body/查询字面/重复标题字面等语义数据（hidden-groups 第 22–74 行）；§0（第 7–9 行）明确不新增命令/流程/断言类型、不扩展 U08/U10 之外流程。H03 整体重述初始文件内容但逐条比对后与 U04 结构同构（第四条 `无关/zzz` 不变、结构一致），属数据替换。仅 F1/F2 两处措辞瑕疵（见上）。

**6) M01/M02/M03 单点性与映射准确性：成立。**
- M01→R03（LF 变字面 `\n`，仅破坏保真，写出仍合法 JSONL）——直接违反唯一；witness U01 步骤 1/3（t1 body 含实际 LF）映射准确，U05 辅助（含 LF 查询）正确。
- M02→R06（lower 代 casefold）——单点；witness U01 步骤 4、U04 步骤 1–3 的失效模式推演正确（见第 1 项），且正确指出 U09 ASCII 查询不可作 witness、U02 为对照。
- M03→R10（仅数组格式 store 加载后逆序，JSONL 路径不受影响）——单点；witness U01 步骤 7–9、U09 步骤 5/6 映射准确，且正确指出 U09 步骤 2 单查询不足以检测顺序反转、U03 为对照。
- 三条变异效果不累加、独立派生的声明（mutation-map 第 7–9 行）内部一致；witness 汇总表（第 41–45 行）与各节正文一致。

---

## 三、总体结论

未发现行为判据层面的明确矛盾。三处低严重度措辞/表述问题（F1「改为」实为无差异、F2「缩小/纠错基线」无对照物、F3「2–3 条」与固定 3 条不一致）建议在会审前修订。另按稿内要求说明：本稿所有设计取值均为草案拟定值、待会审、未获批，本报告不构成对任何判据的冻结确认。
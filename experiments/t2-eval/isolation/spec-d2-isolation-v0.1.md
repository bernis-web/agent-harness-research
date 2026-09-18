# D2 隔离验证规格 v0.1（评价侧；D4 产品批次的放行前置）

日期：2026-09-18。执行者：Claude 本人（用户指示「可以继续推进……你推进项目就行」；
重活不外包，开放问题咨询 Codex）。

依据（冻结文档原文）：

- freeze-decision-checklist-20260918.md D-4：「产品批次（WorkBuddy / Claude
  Code）——受 D2 隔离验证约束，当前未放行」。
- T2-SPEC §0：「参考、隐藏与协调类文档绝不进入未来产品工作区」「（tests 哈希）
  清单放在评价侧，不进入或由产品改写」。
- t2-prep README 隔离与输入边界节：「未来修复工作区预置 notes.py 和评价器的
  tests/」「未来任务输入仅允许：公开 spec 与 public-cases 文档」「参考/隐藏组/
  变异图/协调日志绝不进入产品工作区」。

范围与边界：只做验证与评价侧资产维护；**不放行产品批次**（D4 需另行授权）；
不创建产品工作区（staging 包位于评价侧 `runs\` 内，是验证对象副本，不是产品
工作区）；产物仅落 `t2-eval\`；冻结判据文档零改动；不联网；不提交 git。

## 1. 「D2」标签口径（披露）

「D2」在文档集中无独立定义，仅作门槛标记出现（fabrication spec 首尾两处、
checklist D-4 括注、draft-status 历次状态标记）。本规格将其读作：**checklist
D-4 产品批次的命名前置门槛「隔离验证」**，与缺陷编号 D1–D3（fabrication spec
§3 表）无关联。若后续会审另有指代，以修订为准；本规格的验证内容不依赖该
标签的展开，只依赖上列冻结文档的隔离要求原文。

## 2. 隔离模型：三层验证 + 一层程序定义 + 残余风险披露

| 层 | 内容 | 本轮状态 |
|---|---|---|
| L-a 包内容隔离 | 产品任务包文件集合 == §3 允许清单，逐文件 SHA-256 与评价侧原件一致，无多余文件 | 本规格验证（脚本实跑） |
| L-b 秘密语料扫描 | 对包内全部文件扫描 §4 秘密语料 → 零命中（白名单预剔除记录在案） | 本规格验证（脚本实跑） |
| L-c 会话访问隔离 | 产品会话 cwd=产品工作区；评价侧路径不进入会话输入；文件类工具对评价侧目录配置 deny 规则并以最小探针会话验证「允许路径可读 / 拒绝路径被拒」；WorkBuddy 侧机制待 D4 批次 spec 确定 | 机制定义 + Claude Code 侧探针；未验证的能力不声称 |
| L-d 事后金丝雀审计 | 每个产品批次收尾时，由评价侧对产品工作区全树 + 交付物扫描 §4 语料（强条目自动判失败，弱条目人工复核） | 程序定义于本规格，D4 批次时执行 |
| 残余风险 | Windows 本轮无 OS 级沙箱、无 Bash 文件系统隔离（同 运行器设计 §4.2 L2 口径：普通子进程不是完整沙箱，不具备的能力诚实列为后续闸门）。产品会话理论上可经 shell 越界读取评价侧文件 | 如实披露；缓解 = L-c 指令边界 + deny 规则 + L-d 审计 + 会话转录可查；不声称已消除 |

## 3. 允许清单（产品任务包内容）

| 包内路径 | 来源（评价侧原件） | 完整性锚 |
|---|---|---|
| `notes.py` | `t2-eval\defective\notes.py` | SHA-256 == 评价侧原件 |
| `tests\`（11 文件） | `t2-eval\tests\` | 逐文件 SHA-256 == MANIFEST.json |
| `T2-SPEC-draft-v0.1.md` | `t2-prep\spec\T2-SPEC-draft-v0.1.md` | SHA-256 == frozen-criteria-sha256.txt |
| `public-cases.md` | `t2-prep\acceptance\public-cases.md` | SHA-256 == frozen-criteria-sha256.txt |

产品 `README.md`（任务说明）与编排产物由 D4 批次编排方追加，属公开文本，
在 D4 批次 spec 中另行定义并披露。两份冻结文档的「草案 v0.1」头保留为历史
版本标注（冻结事实以 draft-status 续三记录为权威），产品 README 需如此声明，
不得改写原文。

## 4. 秘密语料（评价侧持有，绝不入包）

- 类别与示例来源：
  1. 隐藏组替换值与隐藏固定数据（hidden-groups.md / evaluator\hidden.py）；
  2. 变异结构信息：M0x 标识、mutation-map 术语、参考实现独有锚点原文
     （defective 中不存在者）；**不含**变异 new 串（它们合法存在于
     defective，是任务本身）；
  3. 评价侧文档与运行痕迹特征串（文件名、目录名、报告短语）。
- 强度分级：强（多字符高熵串，L-d 自动判失败用）／弱（短串如 `b2`、`masse`，
  仅 L-a/L-b 包扫描与 L-d 人工复核用；产品代理可能独立写出弱串，如调试
  casefold 时自然写出 `Maße`，弱串命中不自动定罪）。
- 白名单预剔除：语料条目若出现在任一允许清单源文件（defective、tests、spec、
  public-cases）中即从有效语料剔除并记录（公开合法共现，非泄漏）。
- 新鲜度检查：每条有效语料必须命中至少一个评价侧秘密源文件（hidden-groups.md、
  mutation-map.md、evaluator\hidden.py、evaluator\mutants.py、evaluator\predicted.py、
  FABRICATION-LOG.md），否则标记 STALE 剔除（语料不得包含从未存在的条目）。
- 语料清单与扫描器哈希记入 D2 报告（评价侧可复核）。

## 5. 制作期发现与处置

- **F-1（包内容隔离缺陷，已修）**：defective\notes.py 模块 docstring 携带
  「Reference implementation for T2 (frozen spec v0.1, baseline A):」——
  （a）将待修文件错标为参考实现；（b）暗示存在规格合规基线（诊断提示污染）。
  处置：参考实现 docstring 改为中性「Behavior summary (the task's spec
  document is authoritative)」，defective 由 mutants.py 重新派生（仍恰 3 行
  diff），全量回归：pub-ref-4（10/10、77/77）、hid-ref-3（4/4、38/38）、
  mut-cal-4（3/3 CALIBRATED）、def-check-4（PREDICTED-EXACT）、tests-gate
  双向通过、spec-extra-checks-2（19/19）、MANIFEST 重生成（31 文件）。
  defective 复查无评价侧框架字符串。

## 6. 验收（D2 验证成立的判据）

1. staging 包文件集合与 §3 允许清单精确相等（无多余、无缺失），逐文件
   SHA-256 全对（含对 frozen-criteria 清单交叉核对）；
2. 秘密语料扫描零命中（剔除项均有白名单/新鲜度记录）；
3. L-c 探针（若本轮执行）：工作区路径可读、评价侧路径被拒；未执行则如实
   记录未执行与原因，不声称该层已验证；
4. t2-prep 零改动复核：与 zero-change-check-1 快照比对，差异 ⊆
   `coordination\draft-status.md`（协调日志追加属允许项）。

## 7. D4 放行条件（拟，供用户裁决）

D2 证据齐全 + D4 批次 spec 获用户明确授权。产品工作区拟定
`experiments\t2-prod\<batch>\`（与 t2-eval 分离、独立新建）。D4 批次 spec
将定义：批次编号、会话启动方式（Claude Code 无头 / WorkBuddy）、隔离配置、
任务说明文本、收集的观测数据、L-d 审计执行点。

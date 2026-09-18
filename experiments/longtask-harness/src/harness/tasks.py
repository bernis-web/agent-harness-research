"""任务内容层:PA(saleslog)与 PB(outline-core)的冻结规格、受保护套件、参考实现与隐藏检查。

参考实现标注 TRUSTED_HUMAN_SAMPLE:由研究者人工撰写、作为假模型脚本的合成输出,
来源受控;不代表真实模型生成代码已获执行授权。
"""
from __future__ import annotations

from harness.contracts import Limits, TaskSpec

EVALUATOR_VERSION = {"PA": "eval-pa@0.4", "PB": "eval-pb@0.4"}
CONDITION_ATTACHMENT = ("工作目录中的 STATE.md 是你此前维护的交接文件(字段:goal/active_requirements/"
                        "superseded_requirements/completed_with_evidence/pending/known_failures/"
                        "next_action),你可以在本阶段结束前更新它(上限 2000 token)。")

# ---------------------------------------------------------------- PA 消息
PA_MESSAGES = (
"""阅读 README 与 data/ 下两个 CSV,实现命令 `python -m saleslog summary <csv路径>`:(R1)以文本格式输出聚合表,默认分组键为 category;(R2)amount 解析必须支持千分位逗号与两位小数(如 "1,234.50");(R3)输出采用 TSV(制表符分隔),首行为表头 `category\ttotal\tcount`,数据行 total 以 f"{total:.2f}" 格式化(两位小数),count 为整数,行按 category 的 Unicode 码点升序;(R4)输入文件为 0 字节或缺少必需列(order_id,date,category,amount 任一缺失)时,进程退出码 2,stderr 输出一行以 error: 开头的说明,且不产生任何输出文件;仅有表头、零数据行的文件是合法输入,正常输出表头;(R5)date 必须是严格 YYYY-MM-DD(月份 1-12、日符合当月天数,2024 为闰年),解析失败的行跳过,程序结束前向 stderr 输出 skipped: <n>;(R6)order_id 重复的行视为无效行,同样跳过并计入 skipped。先导数据仅覆盖 2024 年。""",
"""在 tests_self/ 下用标准库 unittest 建立自编测试(至少覆盖:正常聚合、千分位金额、非法日期跳过、缺列退出码 2 四种情形),运行并使其通过。注意 tests_protected/ 由系统维护,请勿修改。""",
"""需求调整:默认聚合维度从"按品类"改为"按季度"——(R1')默认输出表头改为 `quarter\ttotal\tcount`,quarter 由 date 推导,显示为 2024-Qn,行按时间序 Q1→Q4 排列;新增可选参数 --by-category 时输出品类维度(表头 `category\ttotal\tcount`,排序规则同 R3)。旧的"默认按品类输出"自本阶段起不再是需求。(R2)继续有效;(R3)的 TSV 格式与精度规则继续有效,但其默认表头与排序自本阶段起由本要求取代——品类表头与码点升序仅适用于 --by-category 输出。R4-R6 继续有效。请同步更新 tests_self/ 中的测试。""",
"""请针对以下输入边界情境,先运行 run_tests 并构造数据验证当前程序行为,若与预期不符则修复:(B1)CSV 中出现完全空行,或只有逗号的行(如 ,,,)——预期:跳过该行,计入 skipped 计数,其余行正常处理,程序不崩溃;(B2)amount 为不可解析字符串(如 "1.234,56" 或 "n/a")——预期:同上跳过并计数。修复或确认后,补充/更新 tests_self/ 中的对应测试。""",
"""新增:(R7)参数 --format json 时输出 JSON 数组(UTF-8、无 BOM)到 stdout,元素字段与文本表表头同名,total 为 JSON 数值(隐藏检查按数值比较,1234.5 与 1234.50 等价,不要求文本保留尾随零),count 为整数,排序与文本表一致;(R8)date 额外支持两种严格格式:YYYY/MM/DD 与 DD-MM-YYYY(逐字段解析:第一段为日 1-31,第二段为月 1-12,日须符合当月天数;不进行任何字段的互换猜测)。非法日期一律跳过计数。既有行为保持不变。""",
"""最终自查:运行两套测试套件;在 README 补充使用说明(参数、退出码、日期格式与 skipped 语义);确认当前有效要求全部满足后输出变更摘要并停止。""",
)
PA_RESTART_BASE = """这是继续同一任务的全新会话。此前的消息历史不可用。
[任务背景]:saleslog 是一个命令行工具,把销售 CSV 汇总为聚合报表,供运营在终端直接查看。数据字段与解析约定以仓库 README 为准,行为以仓库内测试为准。
[仓库现状]:当前工作目录即任务仓库,包含此前全部代码、README 与测试;当前进展以仓库内文件与测试为准。
[工具说明]:你可以读写白名单内文件;run_tests 可运行测试套件。
[当前阶段指令]:"""

# ---------------------------------------------------------------- PA 参考实现(受信任人工样例)
_SALESLOG_TPL = r'''import sys, csv, json
from datetime import datetime

REQUIRED = ["order_id", "date", "category", "amount"]
DATE_FORMATS = ["%Y-%m-%d"{extra_dates}]
QUARTER_DEFAULT = {quarter}
BLANK_GUARD = {strict}
JSON_FMT = {jsonf}


def parse_amount(s):
    import re as _re
    s = s.strip()
    if not _re.fullmatch(r"-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?", s):
        raise ValueError("invalid amount format: " + s)
    return float(s.replace(",", ""))


def parse_date(s):
    for f in DATE_FORMATS:
        try:
            return datetime.strptime(s.strip(), f)
        except ValueError:
            continue
    return None


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if args and args[0] == "summary":
        args = args[1:]
    fmt_json = "--format json" in " ".join(argv) or "--format" in argv and "json" in argv
    by_category = "--by-category" in argv
    if len(args) < 1:
        print("error: usage: python -m saleslog summary <csv> [--by-category] [--format json]", file=sys.stderr)
        return 2
    path = args[0]
    try:
        raw = open(path, "rb").read()
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if len(raw) == 0:
        print("error: empty input", file=sys.stderr)
        return 2
    text = raw.decode("utf-8-sig")
    rows = list(csv.reader(text.splitlines()))
    if not rows:
        print("error: empty input", file=sys.stderr)
        return 2
    header = [h.strip() for h in rows[0]]
    if any(c not in header for c in REQUIRED):
        print("error: missing required column", file=sys.stderr)
        return 2
    idx = {{name: header.index(name) for name in REQUIRED}}
    agg = {{}}
    skipped = 0
    seen_ids = set()
    for row in rows[1:]:
        if not row or all(not c.strip() for c in row):
            if BLANK_GUARD:
                skipped += 1
                continue
            raise ValueError("empty row")
        if len(row) <= max(idx.values()):
            skipped += 1
            continue
        oid = row[idx["order_id"]].strip()
        dt = parse_date(row[idx["date"]])
        try:
            amt = parse_amount(row[idx["amount"]])
        except ValueError:
            if BLANK_GUARD:
                skipped += 1
                continue
            raise
        cat = row[idx["category"]].strip()
        if dt is None or not cat or not oid or oid in seen_ids:
            skipped += 1
            continue
        seen_ids.add(oid)
        if QUARTER_DEFAULT and not by_category:
            key = f"{{dt.year}}-Q{{(dt.month - 1) // 3 + 1}}"
        else:
            key = cat
        tot, cnt = agg.get(key, (0.0, 0))
        agg[key] = (tot + amt, cnt + 1)
    if QUARTER_DEFAULT and not by_category:
        keys = sorted(agg, key=lambda k: (int(k.split("-")[0]), int(k.split("Q")[1])))
        head = ["quarter", "total", "count"]
    else:
        keys = sorted(agg)
        head = ["category", "total", "count"]
    if fmt_json and JSON_FMT:
        out = [{{"head[0]": keys and agg[k][0] or 0}} for k in keys]  # placeholder replaced below
        print(json.dumps([{{head[0]: k, "total": round(agg[k][0], 2), "count": agg[k][1]}} for k in keys],
                         ensure_ascii=False))
    else:
        print("\t".join(head))
        for k in keys:
            print(f"{{k}}\t{{agg[k][0]:.2f}}\t{{agg[k][1]}}")
    if skipped:
        print(f"skipped: {{skipped}}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''


def make_saleslog(quarter=False, blank=False, jsonf=False, extra_dates=False, strict_rows=True) -> str:
    body = _SALESLOG_TPL.replace("{extra_dates}", ', "%Y/%m/%d", "%d-%m-%Y"' if extra_dates else "")
    body = body.replace("{quarter}", repr(quarter)).replace("{blank}", repr(blank))
    body = body.replace("{strict}", repr(not strict_rows))
    body = body.replace("{jsonf}", repr(jsonf))
    # 移除占位行(json 输出直接用下一行的推导式)
    body = body.replace('        out = [{{"head[0]": keys and agg[k][0] or 0}} for k in keys]  # placeholder replaced below\n', "")
    return body.replace("{{", "{").replace("}}", "}")


PA_INITIAL_REPO = {
    "saleslog/__init__.py": "",
    "saleslog/__main__.py": "from .cli import main\nimport sys\nsys.exit(main(sys.argv[1:]))\n",
    "saleslog/cli.py": "def main(argv):\n    print(\"error: not implemented\", file=sys.stderr)\n    return 2\n\nimport sys\n",
    "data/sample_sales.csv": (
        "order_id,date,category,amount\n"
        "o1,2024-01-15,fruit,\"1,234.50\"\no2,2024-02-20,fruit,10.00\n"
        "o3,2024-03-05,desk,99.00\no4,2024-04-01,desk,\"2,000.00\"\n"
        "o5,2024-05-09,fruit,5.25\no6,2024-06-30,tool,15.00\n"
        "o7,2024-07-04,tool,12.00\no8,2024-08-18,desk,75.50\n"
        "o9,2024-10-11,fruit,8.00\no10,2024-11-21,tool,\"3,100.00\"\n"
        "o11,2024-12-25,fruit,42.00\no12,2024-12-26,desk,1.00\n"),
    "data/broken_dates.csv": ("order_id,date,category,amount\n"
                              "b1,2024-13-01,fruit,1.00\nb2,not-a-date,desk,2.00\nb3,2024-02-30,tool,3.00\n"),
    "README.md": "# saleslog\n\n销售 CSV 汇总工具(先导数据仅覆盖 2024 年)。\n\n数据字典:order_id 字符串;date 应为 YYYY-MM-DD;category 非空字符串;amount 十进制金额字符串,可能含千分位逗号。\n",
}

# PA 受保护套件(阶段开始时发布;unittest + 标准库)
_PA_SUITE_COMMON = r'''import json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


def run_cli(args, csv_text=None):
    tmp = tempfile.mkdtemp(prefix="pa_probe_")
    if csv_text is not None:
        p = os.path.join(tmp, "in.csv")
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write(csv_text)
        args = [p] + args
    r = subprocess.run([PY, "-m", "saleslog", "summary"] + args, cwd=ROOT,
                       capture_output=True, text=True, timeout=60)
    return r


GOOD = ("order_id,date,category,amount\n"
        "o1,2024-01-15,fruit,\"1,234.50\"\no2,2024-04-01,desk,\"2,000.00\"\n"
        "o3,2024-10-11,fruit,8.00\n")
'''


def _pa_suite_v2() -> dict:
    body = _PA_SUITE_COMMON + r'''
class Suite(unittest.TestCase):
    def test_category_aggregation(self):
        r = run_cli([], GOOD)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines()[0], "category\ttotal\tcount")
        self.assertIn("desk\t2000.00\t1", r.stdout)
        self.assertIn("fruit\t1242.50\t2", r.stdout)

    def test_thousands(self):
        r = run_cli([], GOOD)
        self.assertIn("1242.50", r.stdout)

    def test_bad_date_skipped(self):
        r = run_cli([], GOOD + "o9,2024-13-01,tool,3.00\n")
        self.assertEqual(r.returncode, 0)
        self.assertIn("skipped: 1", r.stderr)

    def test_missing_column_exit2(self):
        r = run_cli([], "order_id,date,category\no1,2024-01-01,fruit\n")
        self.assertEqual(r.returncode, 2)
        self.assertTrue(r.stderr.startswith("error:"))
'''
    return {"tests_protected/test_suite.py": body}


def _pa_suite_v3() -> dict:
    body = _PA_SUITE_COMMON + r'''
class Suite(unittest.TestCase):
    def test_default_quarter(self):
        r = run_cli([], GOOD)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.splitlines()
        self.assertEqual(lines[0], "quarter\ttotal\tcount")
        self.assertTrue(lines[1].startswith("2024-Q1\t1234.50\t1"), lines)
        self.assertIn("2024-Q4\t8.00\t1", r.stdout)

    def test_by_category_flag(self):
        r = run_cli(["--by-category"], GOOD)
        self.assertEqual(r.stdout.splitlines()[0], "category\ttotal\tcount")
        self.assertIn("fruit\t1242.50\t2", r.stdout)

    def test_tsv_precision_persists(self):
        r = run_cli([], GOOD)
        self.assertIn("2000.00", r.stdout)

    def test_missing_column_exit2(self):
        r = run_cli([], "order_id,date,category\no1,2024-01-01,fruit\n")
        self.assertEqual(r.returncode, 2)
'''
    return {"tests_protected/test_suite.py": body}


def _pa_suite_v4() -> dict:
    body = _PA_SUITE_COMMON + r'''
class Suite(unittest.TestCase):
    def test_blank_and_comma_lines_skipped(self):
        r = run_cli([], GOOD + "\n,,,\noX,2024-11-01,tool,7.00\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("skipped: 2", r.stderr)
        self.assertIn("15.00\t2", r.stdout)

    def test_bad_amount_skipped(self):
        r = run_cli([], GOOD + "oY,2024-11-02,tool,n/a\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("skipped: 1", r.stderr)

    def test_quarter_default(self):
        r = run_cli([], GOOD)
        self.assertEqual(r.stdout.splitlines()[0], "quarter\ttotal\tcount")

    def test_by_category_flag(self):
        r = run_cli(["--by-category"], GOOD)
        self.assertIn("fruit\t1242.50\t2", r.stdout)

    def test_missing_column_exit2(self):
        r = run_cli([], "order_id,date,category\no1,2024-01-01,fruit\n")
        self.assertEqual(r.returncode, 2)
'''
    return {"tests_protected/test_suite.py": body}


PA_SUITES = {
    "v_placeholder": {"tests_protected/__init__.py": "", "tests_protected/test_suite.py": _PA_SUITE_COMMON + "class Suite(unittest.TestCase):\n    def test_placeholder(self):\n        self.assertTrue(True)\n"},
    "v_s2": {"tests_protected/__init__.py": "", **_pa_suite_v2()},
    "v_s3": {"tests_protected/__init__.py": "", **_pa_suite_v3()},
    "v_s4": {"tests_protected/__init__.py": "", **_pa_suite_v4()},
}
PA_SUITE_SCHEDULE = {1: "v_placeholder", 2: "v_s2", 3: "v_s3", 4: "v_s4", 5: "v_s4", 6: "v_s4"}

# ---------------------------------------------------------------- PB 消息与资产
PB_MESSAGES = (
"""实现 outline_core/core.py 的 Outline 类:(R1)add_node(parent_id, text) 创建节点并返回字符串 ID,自增格式 "n<k>"(k 从已有最大数值 +1 起);(R2)get_subtree(id) 返回该节点及其全部后代的先序列表;(R3)同一父节点下 text(首尾空白剥离后)不得重复,重复抛 ValueError;(R4)load_json(obj) 整体替换当前树:obj={"nodes":[{"id","parent","text"}…]},id 必须匹配 n<正整数> 且互不重复,parent 必须指向存在的节点或 null,存在环或未知父节点时抛 OutlineImportError,且失败时树保持导入前状态完全不变;(R5)text 除首尾空白外原样保留。示例见 examples/sample.json。""",
"""新增 (R6)delete_subtree(id) 返回被删节点 ID 列表(先序),删除后其余节点结构不变;(R7)find_by_text(parent_id, text) 在该父节点的直接子节点中按 id 数值序查找 text(剥离首尾空白后)精确匹配,返回第一个匹配的节点 ID,无匹配抛 KeyError。在 tests_self/ 建立标准库 unittest 自编测试(至少:建树/子树查询/同层重名拒绝/非法导入整体拒绝),运行通过。勿修改 tests_protected/。""",
"""需求调整:同一父节点下允许同名——(R3')删除"同层 text 重复抛 ValueError"的校验;(R7')find_by_text(parent_id, text) 改为返回该父节点直接子节点中全部精确匹配的 ID 列表(按 id 数值序),无匹配返回空列表(不再抛 KeyError)。R1、R2、R4、R5、R6 继续有效。请同步更新 tests_self/。""",
"""请验证以下导入边界情境,若当前行为与预期不符则修复:(B1)nodes 数组中子节点条目出现在其父节点条目之前——预期:支持任意顺序,正常完成导入;(B2)数组存在真实环(如 n2 的 parent 是 n3、n3 的 parent 是 n2)——预期:抛 OutlineImportError,且树保持调用前状态完全不变(导入前后状态快照一致,且失败后原树的一切查询行为不变)。修复或确认后补充 tests_self/ 测试。""",
"""新增:(R8)move_node(id, new_parent_id)——new_parent 为自身或自身后代时抛 ValueError(防环),否则移动;(R9)to_json() 返回 {"nodes":[…]},节点按 id 数值序稳定排序,字段固定 id/parent/text/children(children 为按数值序的子 ID 列表);导入→导出→再导入必须语义一致。导入侧相应支持 children 字段与 parent 字段的一致性校验(不一致抛 OutlineImportError)。""",
"""最终自查:运行两套测试;README 补 API 说明;确认当前有效要求满足后输出变更摘要并停止。""",
)
PB_RESTART_BASE = """这是继续同一任务的全新会话。此前的消息历史不可用。
[任务背景]:outline-core 是思维导图应用的纯逻辑核心库,管理节点树(增删查改、导入导出),供上层界面调用。数据格式与行为约定以仓库 README 与测试为准。
[仓库现状]:当前工作目录即任务仓库,包含此前全部代码、README 与测试;当前进展以仓库内文件与测试为准。
[工具说明]:你可以读写白名单内文件;run_tests 可运行测试套件。
[当前阶段指令]:"""


_OUTLINE_TPL = "import re\n\n\nclass OutlineImportError(Exception):\n    pass\n\n\nclass Outline:\n    def __init__(self):\n        self._text = {}\n        self._parent = {}\n\n    def _children(self, pid):\n        return [nid for nid, p in self._parent.items() if p == pid]\n\n    def add_node(self, parent_id, text):\n        t = text.strip()\n@REJECT@\n        nums = [int(i[1:]) for i in self._text]\n        k = (max(nums) if nums else 0) + 1\n        nid = 'n%d' % k\n        self._text[nid] = t\n        self._parent[nid] = parent_id\n        return nid\n\n    def get_subtree(self, node_id):\n        out = [node_id]\n        for cid in sorted(self._children(node_id), key=lambda i: int(i[1:])):\n            out.extend(self.get_subtree(cid))\n        return out\n\n@FIND@\n\n    def delete_subtree(self, node_id):\n        ids = self.get_subtree(node_id)\n        for i in ids:\n            self._text.pop(i, None)\n            self._parent.pop(i, None)\n        return ids\n\n@LOAD_HEAD@\n@LOAD_BODY@\n@LOAD_TAIL@\n@MOVE@\n"
_REJECT_BLOCK = "        for cid in self._children(parent_id):\n            if self._text[cid].strip() == t:\n                raise ValueError('duplicate')\n"
_FIND_V1 = '    def find_by_text(self, parent_id, text):\n        t = text.strip()\n        for cid in sorted(self._children(parent_id), key=lambda i: int(i[1:])):\n            if self._text[cid].strip() == t:\n                return cid\n        raise KeyError(text)\n'
_FIND_V2 = '    def find_by_text(self, parent_id, text):\n        t = text.strip()\n        hits = [cid for cid in sorted(self._children(parent_id), key=lambda i: int(i[1:]))\n                  if self._text[cid].strip() == t]\n        return hits\n'
_LOAD_HEAD = "    def load_json(self, obj):\n        nodes = obj.get('nodes', [])\n        ids = [n['id'] for n in nodes]\n        if len(ids) != len(set(ids)):\n            raise OutlineImportError('duplicate id')\n        for n in nodes:\n            if not re.fullmatch('n[1-9][0-9]*', n['id']):\n                raise OutlineImportError('bad id')\n        text = {n['id']: n['text'] for n in nodes}\n        parent = {n['id']: n['parent'] for n in nodes}\n        for nid, p in parent.items():\n            if p is not None and p not in parent:\n                raise OutlineImportError('unknown parent')\n"
_LOAD_V1 = "        ids = set(ids)\n        placed_text, placed_parent = {}, {}\n        for n in nodes:\n            p = n['parent']\n            if p is not None and p not in placed_parent:\n                raise KeyError(n['id'])\n            placed_text[n['id']] = n['text']\n            placed_parent[n['id']] = p\n        text, parent = placed_text, placed_parent\n"
_LOAD_TAIL = "        for start in parent:\n            seen, cur = {start}, parent[start]\n            while cur is not None:\n                if cur in seen:\n                    raise OutlineImportError('cycle')\n                seen.add(cur)\n                cur = parent.get(cur)\n        for n in nodes:\n            if 'children' in n and n['children'] is not None:\n                derived = sorted((i for i in parent if parent[i] == n['id']), key=lambda x: int(x[1:]))\n                if sorted(n['children']) != derived:\n                    raise OutlineImportError('children/parent mismatch')\n        self._text = text\n        self._parent = parent\n"
_MOVE = "    def move_node(self, node_id, new_parent_id):\n        if new_parent_id == node_id or new_parent_id in self.get_subtree(node_id):\n            raise ValueError('cycle')\n        self._parent[node_id] = new_parent_id\n\n    def to_json(self):\n        def num(i):\n            return int(i[1:])\n        nodes = []\n        for nid in sorted(self._text, key=num):\n            children = sorted(self._children(nid), key=num)\n            nodes.append({'id': nid, 'parent': self._parent.get(nid),\n                          'text': self._text[nid], 'children': children})\n        return {'nodes': nodes}\n"


def make_outline(two_pass=False, s3_semantics=False, move_json=False) -> str:
    src = _OUTLINE_TPL
    src = src.replace('@REJECT@', '' if s3_semantics else _REJECT_BLOCK)
    src = src.replace('@FIND@', _FIND_V2 if s3_semantics else _FIND_V1)
    body = _LOAD_TAIL if two_pass else (_LOAD_V1 + _LOAD_TAIL)
    src = src.replace('@LOAD_HEAD@', _LOAD_HEAD)
    src = src.replace('@LOAD_BODY@', body)
    src = src.replace('@LOAD_TAIL@', '')
    src = src.replace('@MOVE@', _MOVE if move_json else '')
    return src

PB_INITIAL_REPO = {
    "outline_core/__init__.py": "",
    "outline_core/core.py": "class OutlineImportError(Exception):\n    pass\n\n\nclass Outline:\n    pass\n",
    "examples/sample.json": '{"nodes": [{"id": "n1", "parent": null, "text": "根"}, {"id": "n2", "parent": "n1", "text": "子A"}, {"id": "n3", "parent": "n1", "text": "子B"}, {"id": "n4", "parent": "n2", "text": "孙"}, {"id": "n5", "parent": "n3", "text": "孙二"}]}',
    "README.md": "# outline-core\n\n思维导图纯逻辑核心。数据格式:{\"nodes\":[{\"id\",\"parent\",\"text\"}…]},根节点 parent 为 null。\n",
}
PB_SUITES = {
    "v_placeholder": {"tests_protected/__init__.py": "", "tests_protected/test_suite.py": "import unittest\n\nclass Suite(unittest.TestCase):\n    def test_placeholder(self):\n        self.assertTrue(True)\n"},
    "v_s2": {"tests_protected/__init__.py": "", "tests_protected/test_suite.py": r'''import json, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from outline_core.core import Outline, OutlineImportError


def tree():
    o = Outline()
    a = o.add_node(None, "根")
    b = o.add_node(a, "子A")
    c = o.add_node(a, "子B")
    return o, a, b, c


class Suite(unittest.TestCase):
    def test_build_and_subtree(self):
        o, a, b, c = tree()
        self.assertEqual(o.get_subtree(a), [a, b, c])

    def test_same_name_rejected(self):
        o, a, b, c = tree()
        with self.assertRaises(ValueError):
            o.add_node(a, "子A")

    def test_find_first(self):
        o, a, b, c = tree()
        self.assertEqual(o.find_by_text(a, "子B"), c)

    def test_bad_import_rejected(self):
        o = Outline()
        with self.assertRaises(OutlineImportError):
            o.load_json({"nodes": [{"id": "n1", "parent": "nope", "text": "x"}]})
'''},
    "v_s3": {"tests_protected/__init__.py": "", "tests_protected/test_suite.py": r'''import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from outline_core.core import Outline, OutlineImportError


class Suite(unittest.TestCase):
    def test_same_name_allowed(self):
        o = Outline()
        a = o.add_node(None, "根")
        o.add_node(a, "子")
        o.add_node(a, "子")   # S3 起允许同名
        self.assertEqual(len(o.find_by_text(a, "子")), 2)

    def test_find_returns_sorted_list(self):
        o = Outline()
        a = o.add_node(None, "根")
        ids = [o.add_node(a, "子") for _ in range(3)]
        self.assertEqual(o.find_by_text(a, "子"), sorted(ids, key=lambda i: int(i[1:])))

    def test_find_empty_list(self):
        o = Outline()
        a = o.add_node(None, "根")
        self.assertEqual(o.find_by_text(a, "不存在"), [])

    def test_bad_import_rejected(self):
        o = Outline()
        a = o.add_node(None, "根")
        with self.assertRaises(OutlineImportError):
            o.load_json({"nodes": [{"id": "n1", "parent": "nope", "text": "x"}]})
'''},
    "v_s4": {"tests_protected/__init__.py": "", "tests_protected/test_suite.py": r'''import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from outline_core.core import Outline, OutlineImportError


class Suite(unittest.TestCase):
    def test_out_of_order_import_ok(self):
        o = Outline()
        o.load_json({"nodes": [{"id": "n2", "parent": "n1", "text": "子"},
                               {"id": "n1", "parent": None, "text": "根"}]})
        self.assertEqual(o.get_subtree("n1"), ["n1", "n2"])

    def test_cycle_rejected(self):
        o = Outline()
        a = o.add_node(None, "根")
        before = o.get_subtree(a)
        with self.assertRaises(OutlineImportError):
            o.load_json({"nodes": [{"id": "n1", "parent": "n2", "text": "x"},
                                   {"id": "n2", "parent": "n1", "text": "y"}]})
        self.assertEqual(o.get_subtree(a), before)

    def test_quarter_placeholder(self):
        self.assertTrue(True)
'''},
}
PB_SUITE_SCHEDULE = {1: "v_placeholder", 2: "v_s2", 3: "v_s3", 4: "v_s4", 5: "v_s4", 6: "v_s4"}


def build_pa() -> TaskSpec:
    return TaskSpec(
        task_id="PA-pilot", task_version="PA-pilot@2026-09-15v2.1", family="data-processing",
        initial_repo=PA_INITIAL_REPO, stage_messages=PA_MESSAGES, restart_base=PA_RESTART_BASE,
        condition_attachment=CONDITION_ATTACHMENT,
        readable_paths=("saleslog/", "README.md", "tests_self/", "tests_protected/", "data/"),
        writable_paths=("saleslog/", "README.md", "tests_self/"),
        read_only_paths=("tests_protected/", "data/"),
        preserved_files=("saleslog/", "README.md", "tests_self/", "data/", "tests_protected/"),
        state_file="STATE.md", restart_after_stages=(2, 4),
        protected_test_cmd=("python", "-m", "unittest", "discover", "-s", "tests_protected", "-p", "test_*.py"),
        self_test_cmd=("python", "-m", "unittest", "discover", "-s", "tests_self", "-p", "test_*.py"),
        protected_suites=PA_SUITES, suite_schedule=PA_SUITE_SCHEDULE, limits=Limits())


def build_pb() -> TaskSpec:
    return TaskSpec(
        task_id="PB-pilot", task_version="PB-pilot@2026-09-15v2.1", family="mindmap-logic",
        initial_repo=PB_INITIAL_REPO, stage_messages=PB_MESSAGES, restart_base=PB_RESTART_BASE,
        condition_attachment=CONDITION_ATTACHMENT,
        readable_paths=("outline_core/", "README.md", "tests_self/", "tests_protected/", "examples/"),
        writable_paths=("outline_core/", "README.md", "tests_self/"),
        read_only_paths=("tests_protected/", "examples/"),
        preserved_files=("outline_core/", "README.md", "tests_self/", "examples/", "tests_protected/"),
        state_file="STATE.md", restart_after_stages=(2, 4),
        protected_test_cmd=("python", "-m", "unittest", "discover", "-s", "tests_protected", "-p", "test_*.py"),
        self_test_cmd=("python", "-m", "unittest", "discover", "-s", "tests_self", "-p", "test_*.py"),
        protected_suites=PB_SUITES, suite_schedule=PB_SUITE_SCHEDULE, limits=Limits())

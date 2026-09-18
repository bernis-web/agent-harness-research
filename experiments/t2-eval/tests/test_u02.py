"""U02 — preloaded store: fullwidth vs ASCII search, blank-body record,
titles with significant surrounding whitespace, exact-case distinctness."""
import unittest

from _support import NotesTest, dump_lines

R1 = {"title": "ＡＢＣ", "body": "全角三枚"}
R2 = {"title": "abc", "body": "半角"}
R3 = {"title": " 空白title ", "body": "  两端空格保留  "}
R4 = {"title": "空body条", "body": ""}
R5 = {"title": "  保留两端  ", "body": "x"}
R6 = {"title": "ABC", "body": "精确大小写"}


class U02Preloaded(NotesTest):
    def setUpStore(self):
        self.write("store.jsonl", dump_lines([R1, R2, R3]).encode("utf-8"))

    def test_list_returns_preloaded_as_is(self):
        self.setUpStore()
        proc = self.run_notes(["list", "--store", "store.jsonl"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.json_out(proc), [R1, R2, R3])

    def test_fullwidth_vs_ascii_queries(self):
        self.setUpStore()
        self.assertEqual(self.json_out(self.run_notes(
            ["search", "--store", "store.jsonl", "--query", "abc"])), [R2])
        self.assertEqual(self.json_out(self.run_notes(
            ["search", "--store", "store.jsonl", "--query", "ＡＢＣ"])), [R1])

    def test_blank_body_record(self):
        self.setUpStore()
        self.assertOkSilent(self.run_notes(
            ["add", "--store", "store.jsonl", "--title", R4["title"], "--body", R4["body"]]))
        self.assertEqual(self.json_out(self.run_notes(["list", "--store", "store.jsonl"])),
                         [R1, R2, R3, R4])

    def test_significant_whitespace_title(self):
        self.setUpStore()
        self.assertOkSilent(self.run_notes(
            ["add", "--store", "store.jsonl", "--title", R5["title"], "--body", R5["body"]]))
        self.assertEqual(self.json_out(self.run_notes(
            ["search", "--store", "store.jsonl", "--query", "  保留两端  "])), [R5])

    def test_exact_case_is_distinct(self):
        self.setUpStore()
        for r in (R4, R5, R6):
            self.assertOkSilent(self.run_notes(
                ["add", "--store", "store.jsonl", "--title", r["title"], "--body", r["body"]]))
        self.assertEqual(self.json_out(self.run_notes(["list", "--store", "store.jsonl"])),
                         [R1, R2, R3, R4, R5, R6])


if __name__ == "__main__":
    unittest.main()

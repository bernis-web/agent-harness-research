"""U05 — multi-line body fidelity: embedded LF/TAB/quotes survive add,
and queries containing real control characters match by substring."""
import unittest

from _support import NotesTest

R1 = {"title": "多行", "body": "第一行\n\"引用段\"\t尾"}


class U05Multiline(NotesTest):
    def test_add_then_search_with_embedded_lf(self):
        self.assertOkSilent(self.run_notes(
            ["add", "--store", "store.jsonl", "--title", R1["title"], "--body", R1["body"]]))
        self.assertEqual(self.json_out(self.run_notes(
            ["search", "--store", "store.jsonl", "--query", "第一行\n\"引用段\""])), [R1])

    def test_search_tab_segment(self):
        self.assertOkSilent(self.run_notes(
            ["add", "--store", "store.jsonl", "--title", R1["title"], "--body", R1["body"]]))
        self.assertEqual(self.json_out(self.run_notes(
            ["search", "--store", "store.jsonl", "--query", "\"引用段\"\t尾"])), [R1])

    def test_search_absent_lf_pattern(self):
        self.assertOkSilent(self.run_notes(
            ["add", "--store", "store.jsonl", "--title", R1["title"], "--body", R1["body"]]))
        self.assertEqual(self.json_out(self.run_notes(
            ["search", "--store", "store.jsonl", "--query", "行\n无"])), [])

    def test_list_reports_body_verbatim(self):
        self.assertOkSilent(self.run_notes(
            ["add", "--store", "store.jsonl", "--title", R1["title"], "--body", R1["body"]]))
        recs = self.json_out(self.run_notes(["list", "--store", "store.jsonl"]))
        self.assertEqual(recs[0]["body"], R1["body"])


if __name__ == "__main__":
    unittest.main()

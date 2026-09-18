"""U01 — full fidelity chain: add special-content notes, list/search them,
export to a JSON array, reload, and keep adding in array format."""
import unittest

from _support import NotesTest

T1 = {"title": '标题"一"', "body": "行1\n行\t2\\end, \"q\"全角ＡＢ emoji😀"}
T2 = {"title": "Straße", "body": "UPPER lower MiXeD"}
T3 = {"title": "STRASSE二", "body": "无关"}
T4 = {"title": "仅正文命中", "body": "藏着 needle 在这里"}
T5 = {"title": "重载新条", "body": "reloaded"}


class U01Fidelity(NotesTest):
    def seed(self, *records):
        for r in records:
            self.assertOkSilent(self.run_notes(
                ["add", "--store", "store.jsonl", "--title", r["title"], "--body", r["body"]]))

    def test_add_list_roundtrip(self):
        self.seed(T1, T2, T3, T4)
        proc = self.run_notes(["list", "--store", "store.jsonl"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr, b"")
        self.assertEqual(self.json_out(proc), [T1, T2, T3, T4])

    def test_body_special_characters_survive(self):
        self.seed(T1)
        recs = self.json_out(self.run_notes(["list", "--store", "store.jsonl"]))
        self.assertEqual(recs[0]["body"], T1["body"])
        self.assertEqual(recs[0]["title"], T1["title"])

    def test_search_casefold_and_body_hit(self):
        self.seed(T1, T2, T3, T4)
        self.assertEqual(self.json_out(self.run_notes(
            ["search", "--store", "store.jsonl", "--query", "strasse"])), [T2, T3])
        self.assertEqual(self.json_out(self.run_notes(
            ["search", "--store", "store.jsonl", "--query", "NEEDLE"])), [T4])

    def test_search_leaves_store_unchanged(self):
        self.seed(T1, T2, T3, T4)
        before = self.read("store.jsonl")
        self.run_notes(["search", "--store", "store.jsonl", "--query", "strasse"])
        self.assertStoreUnchanged("store.jsonl", before)

    def test_export_then_reload_array(self):
        self.seed(T1, T2, T3, T4)
        self.assertOkSilent(self.run_notes(
            ["export", "--store", "store.jsonl", "--out", "out.json"]))
        raw = self.read("out.json")
        self.assertEqual(raw.decode("utf-8").lstrip()[:1], "[")
        self.assertEqual(self.json_out(self.run_notes(["list", "--store", "out.json"])),
                         [T1, T2, T3, T4])

    def test_array_store_add_keeps_format_and_order(self):
        self.seed(T1, T2, T3, T4)
        self.assertOkSilent(self.run_notes(
            ["export", "--store", "store.jsonl", "--out", "out.json"]))
        self.assertOkSilent(self.run_notes(
            ["add", "--store", "out.json", "--title", T5["title"], "--body", T5["body"]]))
        raw = self.read("out.json")
        self.assertEqual(raw.decode("utf-8").lstrip()[:1], "[")
        self.assertEqual(self.json_out(self.run_notes(["list", "--store", "out.json"])),
                         [T1, T2, T3, T4, T5])
        self.assertEqual(self.json_out(self.run_notes(
            ["search", "--store", "out.json", "--query", "strasse"])), [T2, T3])

    def test_duplicate_title_rejected_store_untouched(self):
        self.seed(T1, T2)
        before = self.read("store.jsonl")
        self.assertReject(self.run_notes(
            ["add", "--store", "store.jsonl", "--title", T2["title"], "--body", "dup"]), 2)
        self.assertStoreUnchanged("store.jsonl", before)

    def test_store_is_legal_jsonl(self):
        self.seed(T1)
        lines = self.read("store.jsonl").decode("utf-8").split("\n")
        self.assertEqual(lines[-1], "")
        self.assertEqual(len([l for l in lines if l]), 1)


if __name__ == "__main__":
    unittest.main()

"""U09 — array-format store lifecycle: export JSONL -> JSON array, search,
add (whole rewrite keeping array format), duplicate rejection, re-export;
the original JSONL source stays byte-identical."""
import json
import unittest

from _support import NotesTest, dump_lines

A = {"title": "Alpha", "body": "x"}
B = {"title": "beta", "body": "包含 Beta 词"}
G = {"title": "Gamma", "body": "g"}


class U09ArrayLifecycle(NotesTest):
    def setUpSrc(self):
        self.write("src.jsonl", dump_lines([A, B]).encode("utf-8"))
        self.src_before = self.read("src.jsonl")

    def assertArray(self, rel, expected):
        raw = self.read(rel)
        self.assertEqual(raw.decode("utf-8").lstrip()[:1], "[")
        self.assertEqual(json.loads(raw.decode("utf-8")), expected)

    def test_export_creates_array(self):
        self.setUpSrc()
        self.assertOkSilent(self.run_notes(
            ["export", "--store", "src.jsonl", "--out", "arr.json"]))
        self.assertArray("arr.json", [A, B])
        self.assertStoreUnchanged("src.jsonl", self.src_before)

    def test_search_array_store(self):
        self.setUpSrc()
        self.assertOkSilent(self.run_notes(
            ["export", "--store", "src.jsonl", "--out", "arr.json"]))
        self.assertEqual(self.json_out(self.run_notes(
            ["search", "--store", "arr.json", "--query", "beta"])), [B])
        self.assertStoreUnchanged("src.jsonl", self.src_before)

    def test_add_to_array_keeps_format_and_order(self):
        self.setUpSrc()
        self.assertOkSilent(self.run_notes(
            ["export", "--store", "src.jsonl", "--out", "arr.json"]))
        self.assertOkSilent(self.run_notes(
            ["add", "--store", "arr.json", "--title", G["title"], "--body", G["body"]]))
        self.assertArray("arr.json", [A, B, G])

    def test_duplicate_add_rejected_array_untouched(self):
        self.setUpSrc()
        self.assertOkSilent(self.run_notes(
            ["export", "--store", "src.jsonl", "--out", "arr.json"]))
        self.assertOkSilent(self.run_notes(
            ["add", "--store", "arr.json", "--title", G["title"], "--body", G["body"]]))
        before = self.read("arr.json")
        self.assertReject(self.run_notes(
            ["add", "--store", "arr.json", "--title", A["title"], "--body", "dup"]), 2)
        self.assertStoreUnchanged("arr.json", before)

    def test_list_and_reexport_order(self):
        self.setUpSrc()
        self.assertOkSilent(self.run_notes(
            ["export", "--store", "src.jsonl", "--out", "arr.json"]))
        self.assertOkSilent(self.run_notes(
            ["add", "--store", "arr.json", "--title", G["title"], "--body", G["body"]]))
        self.assertEqual(self.json_out(self.run_notes(["list", "--store", "arr.json"])),
                         [A, B, G])
        self.assertOkSilent(self.run_notes(
            ["export", "--store", "arr.json", "--out", "arr2.json"]))
        self.assertArray("arr2.json", [A, B, G])
        self.assertStoreUnchanged("src.jsonl", self.src_before)


if __name__ == "__main__":
    unittest.main()

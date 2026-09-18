"""U07 — paths: stores inside directories with spaces and non-ASCII names,
relative and absolute --store/--out forms, exporting an empty store."""
import os
import unittest

from _support import NotesTest, dump_lines

R1 = {"title": "条", "body": "值"}


class U07Paths(NotesTest):
    def setUpStore(self):
        os.makedirs(os.path.join(self.sandbox, "dir one"), exist_ok=True)
        self.write(os.path.join("dir one", "中文 store.jsonl"),
                   dump_lines([R1]).encode("utf-8"))
        self.write("empty.jsonl", b"")

    def assertArrayOut(self, rel, expected):
        raw = self.read(rel)
        self.assertEqual(raw.decode("utf-8").lstrip()[:1], "[")
        import json
        self.assertEqual(json.loads(raw.decode("utf-8")), expected)

    def test_export_relative_paths(self):
        self.setUpStore()
        before = self.read(os.path.join("dir one", "中文 store.jsonl"))
        self.assertOkSilent(self.run_notes(
            ["export", "--store", os.path.join("dir one", "中文 store.jsonl"),
             "--out", "out 相对.json"]))
        self.assertArrayOut("out 相对.json", [R1])
        self.assertStoreUnchanged(os.path.join("dir one", "中文 store.jsonl"), before)

    def test_export_absolute_paths(self):
        self.setUpStore()
        before = self.read(os.path.join("dir one", "中文 store.jsonl"))
        self.assertOkSilent(self.run_notes(
            ["export", "--store", os.path.join(self.sandbox, "dir one", "中文 store.jsonl"),
             "--out", os.path.join(self.sandbox, "out 绝对.json")]))
        self.assertArrayOut("out 绝对.json", [R1])
        self.assertStoreUnchanged(os.path.join("dir one", "中文 store.jsonl"), before)

    def test_export_empty_store(self):
        self.setUpStore()
        self.assertOkSilent(self.run_notes(
            ["export", "--store", "empty.jsonl", "--out", "empty_out.json"]))
        self.assertArrayOut("empty_out.json", [])

    def test_repeated_exports_succeed(self):
        self.setUpStore()
        self.assertOkSilent(self.run_notes(
            ["export", "--store", os.path.join("dir one", "中文 store.jsonl"),
             "--out", "out ro.json"]))
        self.assertArrayOut("out ro.json", [R1])


if __name__ == "__main__":
    unittest.main()

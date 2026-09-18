"""U08 — export destination rules: refuse overwrites (exit 2), same-file
via path tricks (exit 2), directories and missing parents (exit 3); the
store and pre-existing destinations stay untouched."""
import os
import unittest

from _support import NotesTest, dump_lines

G = {"title": "t", "body": "b"}


class U08ExportDestinations(NotesTest):
    def setUpWorld(self):
        self.write("good.jsonl", dump_lines([G]).encode("utf-8"))
        self.write("exists.json", b"[]\n")
        for d in ("adir", "sub"):
            os.makedirs(os.path.join(self.sandbox, d), exist_ok=True)

    def test_out_already_exists(self):
        self.setUpWorld()
        before_store = self.read("good.jsonl")
        before_out = self.read("exists.json")
        self.assertReject(self.run_notes(
            ["export", "--store", "good.jsonl", "--out", "exists.json"]), 2)
        self.assertStoreUnchanged("good.jsonl", before_store)
        self.assertStoreUnchanged("exists.json", before_out)

    def test_out_same_file_via_dotslash(self):
        self.setUpWorld()
        before = self.read("good.jsonl")
        self.assertReject(self.run_notes(
            ["export", "--store", "good.jsonl", "--out", "./sub/../good.jsonl"]), 2)
        self.assertStoreUnchanged("good.jsonl", before)
        self.assertEqual(os.listdir(os.path.join(self.sandbox, "sub")), [])

    def test_out_is_a_directory(self):
        self.setUpWorld()
        self.assertReject(self.run_notes(
            ["export", "--store", "good.jsonl", "--out", "adir"]), 3)

    def test_out_parent_missing(self):
        self.setUpWorld()
        self.assertReject(self.run_notes(
            ["export", "--store", "good.jsonl", "--out", "nodir/o.json"]), 3)
        self.assertFalse(os.path.exists(os.path.join(self.sandbox, "nodir")))

    def test_out_empty_string(self):
        self.setUpWorld()
        before = self.read("good.jsonl")
        self.assertReject(self.run_notes(
            ["export", "--store", "good.jsonl", "--out", ""]), 2)
        self.assertStoreUnchanged("good.jsonl", before)

    def test_store_or_out_pointing_at_directory(self):
        self.setUpWorld()
        self.assertReject(self.run_notes(["list", "--store", "adir"]), 3)
        self.assertReject(self.run_notes(
            ["add", "--store", "adir", "--title", "x", "--body", "y"]), 3)
        self.assertReject(self.run_notes(
            ["add", "--store", "nodir/s.jsonl", "--title", "x", "--body", "y"]), 3)
        self.assertFalse(os.path.exists(os.path.join(self.sandbox, "nodir")))

    def test_out_equals_store(self):
        self.setUpWorld()
        before = self.read("good.jsonl")
        self.assertReject(self.run_notes(
            ["export", "--store", "good.jsonl", "--out", "good.jsonl"]), 2)
        self.assertStoreUnchanged("good.jsonl", before)

    def test_store_still_usable(self):
        self.setUpWorld()
        for argv in (["export", "--store", "good.jsonl", "--out", "exists.json"],
                     ["export", "--store", "good.jsonl", "--out", "adir"],
                     ["export", "--store", "good.jsonl", "--out", ""]):
            self.run_notes(argv)
        proc = self.run_notes(["list", "--store", "good.jsonl"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.json_out(proc), [G])


if __name__ == "__main__":
    unittest.main()

"""U06 — empty and missing stores: a 0-byte store lists/searches as empty;
missing paths are environment errors (exit 3) and never materialize."""
import os
import unittest

from _support import NotesTest, dump_lines

R1 = {"title": "a b", "body": "c"}


class U06EmptyMissing(NotesTest):
    def test_empty_store_lists_and_searches_empty(self):
        self.write("empty.jsonl", b"")
        proc = self.run_notes(["list", "--store", "empty.jsonl"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.json_out(proc), [])
        self.assertEqual(self.json_out(self.run_notes(
            ["search", "--store", "empty.jsonl", "--query", "x"])), [])

    def test_space_query_on_empty_and_nonempty(self):
        self.write("empty.jsonl", b"")
        self.assertEqual(self.json_out(self.run_notes(
            ["search", "--store", "empty.jsonl", "--query", " "])), [])
        self.write("one.jsonl", dump_lines([R1]).encode("utf-8"))
        self.assertEqual(self.json_out(self.run_notes(
            ["search", "--store", "one.jsonl", "--query", " "])), [R1])

    def test_missing_store_errors(self):
        for argv in (["list", "--store", "missing.jsonl"],
                     ["search", "--store", "missing.jsonl", "--query", "q"],
                     ["export", "--store", "missing.jsonl", "--out", "o.json"]):
            with self.subTest(argv=argv):
                self.assertReject(self.run_notes(argv), 3)
                self.assertFalse(os.path.exists(os.path.join(self.sandbox, "missing.jsonl")))
                self.assertFalse(os.path.exists(os.path.join(self.sandbox, "o.json")))


if __name__ == "__main__":
    unittest.main()

"""U03 — strict input rejection: every malformed invocation exits 2 with
exactly one stderr line and leaves the store byte-identical."""
import unittest

from _support import NotesTest, dump_lines

R1 = {"title": "存在", "body": "b1"}

REJECTS = [
    ["add", "--store", "store.jsonl", "--title", "存在", "--body", "x"],
    ["add", "--store", "store.jsonl", "--title", "", "--body", "x"],
    ["add", "--store", "store.jsonl", "--title", "   ", "--body", "x"],
    ["add", "--store", "store.jsonl", "--title", "x"],
    ["add", "--title", "x", "--body", "y"],
    ["add", "--store", "store.jsonl", "--title", "x", "--title", "y", "--body", "z"],
    ["list"],
    ["search", "--store", "store.jsonl"],
    ["export", "--store", "store.jsonl"],
    ["list", "--store", "store.jsonl", "--store", "store.jsonl"],
    ["frobnicate"],
    ["list", "--bogus", "v", "--store", "store.jsonl"],
    ["list", "extra", "--store", "store.jsonl"],
    ["list", "--store", ""],
    ["search", "--store", "store.jsonl", "--query", ""],
]


class U03Rejects(NotesTest):
    def test_all_rejected(self):
        self.write("store.jsonl", dump_lines([R1]).encode("utf-8"))
        before = self.read("store.jsonl")
        for argv in REJECTS:
            with self.subTest(argv=argv):
                self.assertReject(self.run_notes(argv), 2)
                self.assertStoreUnchanged("store.jsonl", before)

    def test_store_still_readable_after_rejections(self):
        self.write("store.jsonl", dump_lines([R1]).encode("utf-8"))
        for argv in REJECTS:
            self.run_notes(argv)
        proc = self.run_notes(["list", "--store", "store.jsonl"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.json_out(proc), [R1])


if __name__ == "__main__":
    unittest.main()

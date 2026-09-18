"""U10 — corrupted stores: a truncated JSON line and an invalid-UTF-8 byte
are data errors (exit 3) for every subcommand; the files stay byte-identical
and no output file is created."""
import os
import unittest

from _support import NotesTest

TRUNC = b'{"title":"a'                                   # truncated JSON line, no LF
BADUTF8 = b'{"title":"a","body":"\xff"}'                 # 0xFF byte, no trailing LF


class U10CorruptStores(NotesTest):
    def setUpCorrupt(self):
        self.write("trunc.jsonl", TRUNC)
        self.write("bad.jsonl", BADUTF8)

    def test_truncated_store(self):
        self.setUpCorrupt()
        for argv in (["list", "--store", "trunc.jsonl"],
                     ["add", "--store", "trunc.jsonl", "--title", "n", "--body", "b"],
                     ["search", "--store", "trunc.jsonl", "--query", "a"]):
            with self.subTest(argv=argv):
                self.assertReject(self.run_notes(argv), 3)
                self.assertStoreUnchanged("trunc.jsonl", TRUNC)

    def test_bad_utf8_store(self):
        self.setUpCorrupt()
        for argv in (["list", "--store", "bad.jsonl"],
                     ["add", "--store", "bad.jsonl", "--title", "n", "--body", "b"]):
            with self.subTest(argv=argv):
                self.assertReject(self.run_notes(argv), 3)
                self.assertStoreUnchanged("bad.jsonl", BADUTF8)

    def test_export_from_corrupt_store_creates_nothing(self):
        self.setUpCorrupt()
        self.assertReject(self.run_notes(
            ["export", "--store", "bad.jsonl", "--out", "o10.json"]), 3)
        self.assertFalse(os.path.exists(os.path.join(self.sandbox, "o10.json")))
        self.assertStoreUnchanged("bad.jsonl", BADUTF8)


if __name__ == "__main__":
    unittest.main()

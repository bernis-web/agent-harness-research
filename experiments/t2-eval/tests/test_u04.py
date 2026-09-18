"""U04 — casefold search: strasse/STRASSE/ß queries all hit the three
case-variants of the German sharp s, and nothing else; read-only."""
import unittest

from _support import NotesTest, dump_lines

R1 = {"title": "Straße", "body": "x"}
R2 = {"title": "别的", "body": "STRASSE 在正文"}
R3 = {"title": "STRASSE双命中", "body": "strasse 也在这"}
R4 = {"title": "无关", "body": "zzz"}


class U04Casefold(NotesTest):
    def setUpStore(self):
        self.write("store.jsonl", dump_lines([R1, R2, R3, R4]).encode("utf-8"))
        self.before = self.read("store.jsonl")

    def test_query_lowercase(self):
        self.setUpStore()
        self.assertEqual(self.json_out(self.run_notes(
            ["search", "--store", "store.jsonl", "--query", "strasse"])),
            [R1, R2, R3])

    def test_query_uppercase(self):
        self.setUpStore()
        self.assertEqual(self.json_out(self.run_notes(
            ["search", "--store", "store.jsonl", "--query", "STRASSE"])),
            [R1, R2, R3])

    def test_query_sharp_s(self):
        self.setUpStore()
        self.assertEqual(self.json_out(self.run_notes(
            ["search", "--store", "store.jsonl", "--query", "ß"])),
            [R1, R2, R3])

    def test_store_unchanged(self):
        self.setUpStore()
        for q in ("strasse", "STRASSE", "ß"):
            self.run_notes(["search", "--store", "store.jsonl", "--query", q])
        self.assertStoreUnchanged("store.jsonl", self.before)


if __name__ == "__main__":
    unittest.main()

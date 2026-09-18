"""Shared support for the public notes.py test suite.

The suite mirrors the public acceptance scenarios U01-U10. It must stay
inside the public information boundary: only what the public spec and
public scenarios state. Nothing from the non-public parts of the
evaluation setup may appear here.

notes.py is resolved as a sibling of the tests/ directory's parent (the
product workspace layout: notes.py next to tests/).
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
NOTES = os.path.join(os.path.dirname(HERE), "notes.py")
PY = sys.executable


def dump_lines(records):
    """Canonical JSONL text for seeding a store in tests."""
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)


class NotesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.sandbox = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def run_notes(self, argv):
        return subprocess.run([PY, NOTES] + argv, cwd=self.sandbox,
                              capture_output=True)

    # ---- assertion helpers -------------------------------------------------

    def assertOkSilent(self, proc):
        """Successful add/export: exit 0 and no output at all."""
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, b"")
        self.assertEqual(proc.stderr, b"")

    def assertReject(self, proc, code):
        """Failed op: exit code, empty stdout, exactly one non-empty stderr line."""
        self.assertEqual(proc.returncode, code, proc.stdout)
        self.assertEqual(proc.stdout, b"")
        body = proc.stderr[:-1] if proc.stderr.endswith(b"\n") else proc.stderr
        self.assertNotEqual(body, b"", "stderr must be non-empty")
        self.assertNotIn(b"\n", body, "stderr must be exactly one line")

    def read(self, rel):
        with open(os.path.join(self.sandbox, rel), "rb") as fh:
            return fh.read()

    def write(self, rel, data):
        p = os.path.join(self.sandbox, rel)
        parent = os.path.dirname(p)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(p, "wb") as fh:
            fh.write(data)

    def json_out(self, proc):
        return json.loads(proc.stdout.decode("utf-8"))

    def assertStoreUnchanged(self, rel, before):
        self.assertEqual(self.read(rel), before)

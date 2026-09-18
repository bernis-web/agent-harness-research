#!/usr/bin/env python3
"""notes.py — notes CLI: add / list / search / export over a JSONL store.

Behavior summary (the task's spec document is authoritative):
- store: JSONL, or a JSON array (e.g. a prior export) recognized by strict
  UTF-8 decode + lstrip() first char '['; add keeps the recognized format.
- search: casefold substring over title and body, store order, deduped.
- exit codes: 0 success, 2 input errors, 3 environment/data errors.
- failures print exactly one non-empty line to stderr; stdout stays empty.
"""
import json
import os
import sys
import tempfile
from typing import NoReturn

EXIT_OK = 0
EXIT_INPUT = 2
EXIT_ENV = 3

USAGE = (
    "usage: notes.py add --store P --title T --body B\n"
    "       notes.py list --store P\n"
    "       notes.py search --store P --query Q\n"
    "       notes.py export --store P --out OUT"
)

_SUBCOMMANDS = {
    "add": ("--store", "--title", "--body"),
    "list": ("--store",),
    "search": ("--store", "--query"),
    "export": ("--store", "--out"),
}


class Fail(Exception):
    def __init__(self, sub, reason, code):
        super().__init__(reason)
        self.sub = sub
        self.reason = reason
        self.code = code


def _out(stream, text):
    stream.buffer.write(text.encode("utf-8"))
    stream.buffer.flush()


def fail(sub, reason, code) -> NoReturn:
    raise Fail(sub, reason, code)


def _check_arg_encoding(sub, value):
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        fail(sub, "argument is not valid unicode", EXIT_INPUT)


def parse_argv(argv):
    """R01: strict subcommand / option parsing. Returns (sub, opts)."""
    if not argv:
        fail("notes", "missing subcommand", EXIT_INPUT)
    sub = argv[0]
    if sub not in _SUBCOMMANDS:
        fail(sub, "unknown subcommand", EXIT_INPUT)
    spec = _SUBCOMMANDS[sub]
    opts = {}
    i = 1
    while i < len(argv):
        token = argv[i]
        if not token.startswith("--"):
            fail(sub, "unexpected argument: " + token, EXIT_INPUT)
        name, sep, inline = token.partition("=")
        if sep:
            value = inline
        else:
            if i + 1 >= len(argv):
                fail(sub, "missing value for " + name, EXIT_INPUT)
            value = argv[i + 1]
            i += 1
        if name not in spec:
            fail(sub, "unknown option: " + name, EXIT_INPUT)
        if name in opts:
            fail(sub, "duplicate option: " + name, EXIT_INPUT)
        opts[name] = value
        i += 1
    for name in spec:
        if name not in opts:
            fail(sub, "missing required option: " + name, EXIT_INPUT)
    return sub, opts


def _validate_records(sub, records):
    seen = set()
    for obj in records:
        if not isinstance(obj, dict) or set(obj.keys()) != {"title", "body"}:
            fail(sub, "bad store: record schema", EXIT_ENV)
        title = obj["title"]
        body = obj["body"]
        if not isinstance(title, str) or not isinstance(body, str):
            fail(sub, "bad store: record schema", EXIT_ENV)
        for value in (title, body):
            try:
                value.encode("utf-8")
            except UnicodeEncodeError:
                fail(sub, "bad store: unpaired surrogate", EXIT_ENV)
        if title.strip() == "":
            fail(sub, "bad store: blank title", EXIT_ENV)
        if title in seen:
            fail(sub, "bad store: duplicate title", EXIT_ENV)
        seen.add(title)


def load_store(sub, store):
    """Read + validate the store. Returns (records, is_array).

    Dies with EXIT_ENV on missing file, directory, BOM, bad UTF-8,
    invalid JSON, blank JSONL line, or schema violations.
    """
    try:
        with open(store, "rb") as fh:
            raw = fh.read()
    except FileNotFoundError:
        fail(sub, "store not found: " + store, EXIT_ENV)
    except OSError as exc:
        fail(sub, "cannot read store: " + str(exc), EXIT_ENV)
    if raw.startswith(b"\xef\xbb\xbf"):
        fail(sub, "bad store: BOM not allowed", EXIT_ENV)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        fail(sub, "bad store: not valid UTF-8", EXIT_ENV)
    if text == "":
        return [], False
    if text.lstrip()[:1] == "[":
        try:
            data = json.loads(text)
        except ValueError:
            fail(sub, "bad store: invalid JSON", EXIT_ENV)
        if not isinstance(data, list):
            fail(sub, "bad store: expected JSON array", EXIT_ENV)
        _validate_records(sub, data)
        return list(reversed(data)), True
    lines = text.split("\n")
    if text.endswith("\n"):
        lines.pop()
    records = []
    for line in lines:
        if line.strip() == "":
            fail(sub, "bad store: blank line", EXIT_ENV)
        try:
            obj = json.loads(line)
        except ValueError:
            fail(sub, "bad store: invalid JSON line", EXIT_ENV)
        records.append(obj)
    _validate_records(sub, records)
    return records, False


def _write_store(store, records, array):
    if array:
        text = json.dumps(records, ensure_ascii=False) + "\n"
    else:
        text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    with open(store, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def _append_jsonl(store, record):
    line = json.dumps(record, ensure_ascii=False)
    payload = line.encode("utf-8") + b"\n"
    prefix = b""
    if os.path.exists(store) and os.path.getsize(store) > 0:
        with open(store, "rb") as fh:
            fh.seek(-1, os.SEEK_END)
            if fh.read(1) != b"\n":
                prefix = b"\n"
    with open(store, "ab") as fh:
        fh.write(prefix + payload)


def _fold(s):
    return s.casefold()


def cmd_add(sub, opts):
    store = opts["--store"]
    title = opts["--title"]
    body = opts["--body"]
    for value in (store, title, body):
        _check_arg_encoding(sub, value)
    if title.strip() == "":
        fail(sub, "blank title", EXIT_INPUT)
    if os.path.isdir(store):
        fail(sub, "store is a directory", EXIT_ENV)
    if os.path.exists(store):
        records, is_array = load_store(sub, store)
    else:
        parent = os.path.dirname(os.path.abspath(store))
        if not os.path.isdir(parent):
            fail(sub, "parent directory missing", EXIT_ENV)
        records, is_array = [], False
    for rec in records:
        if rec["title"] == title:
            fail(sub, "duplicate title", EXIT_INPUT)
    record = {"title": title, "body": body}
    if is_array:
        records.append(record)
        _write_store(store, records, array=True)
    else:
        _append_jsonl(store, record)
    return EXIT_OK


def cmd_list(sub, opts):
    _check_arg_encoding(sub, opts["--store"])
    records, _is_array = load_store(sub, opts["--store"])
    _out(sys.stdout, json.dumps(records, ensure_ascii=False) + "\n")
    return EXIT_OK


def cmd_search(sub, opts):
    query = opts["--query"]
    _check_arg_encoding(sub, query)
    _check_arg_encoding(sub, opts["--store"])
    if query == "":
        fail(sub, "empty query", EXIT_INPUT)
    records, _is_array = load_store(sub, opts["--store"])
    q = _fold(query)
    hits = [r for r in records if q in _fold(r["title"]) or q in _fold(r["body"])]
    _out(sys.stdout, json.dumps(hits, ensure_ascii=False) + "\n")
    return EXIT_OK


def cmd_export(sub, opts):
    store = opts["--store"]
    out = opts["--out"]
    for value in (store, out):
        _check_arg_encoding(sub, value)
    if out == "":
        fail(sub, "empty out path", EXIT_INPUT)
    if os.path.normpath(os.path.abspath(store)) == os.path.normpath(os.path.abspath(out)):
        fail(sub, "--out must differ from --store", EXIT_INPUT)
    records, _is_array = load_store(sub, store)
    if os.path.isdir(out):
        fail(sub, "out is a directory", EXIT_ENV)
    if os.path.exists(out):
        fail(sub, "out already exists", EXIT_INPUT)
    parent = os.path.dirname(os.path.abspath(out))
    if not os.path.isdir(parent):
        fail(sub, "parent directory missing", EXIT_ENV)
    text = json.dumps(records, ensure_ascii=False) + "\n"
    parent = os.path.dirname(os.path.abspath(out))
    fd, tmp = tempfile.mkstemp(dir=parent, prefix=".notes-export-", suffix=".tmp")
    os.close(fd)
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.replace(tmp, out)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    return EXIT_OK


def main(argv):
    if argv and argv[0] in ("-h", "--help"):
        _out(sys.stdout, USAGE + "\n")
        return EXIT_OK
    sub, opts = parse_argv(argv)
    if opts.get("--store", "") == "":
        fail(sub, "empty store path", EXIT_INPUT)
    handler = {
        "add": cmd_add,
        "list": cmd_list,
        "search": cmd_search,
        "export": cmd_export,
    }[sub]
    return handler(sub, opts)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Fail as exc:
        _out(sys.stderr, exc.sub + ": " + exc.reason + "\n")
        sys.exit(exc.code)

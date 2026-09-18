"""Generate t2-eval/fixtures — byte-exact templates for case initial files.

Binary fixtures (U08/U10) are the source of truth and are written from the
hex/bytes given in the frozen public-cases.md. Record-based initial stores are
produced by the same canonical synthesize() the runner uses at runtime; copies
are emitted here as audit artifacts so the exact bytes are inspectable and
diffable. Re-running this script is idempotent (same input -> same bytes).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIXTURES = os.path.join(ROOT, "fixtures")

sys.path.insert(0, HERE)
import cases
from runner import synthesize

# U08 exists.json: a pre-existing JSON-array file (export must refuse to touch it)
U08_EXISTS = b"[]\n"

# U10 trunc.jsonl: a truncated JSON line (no trailing LF)
U10_TRUNC = bytes.fromhex("7B 22 74 69 74 6C 65 22 3A 22 61".replace(" ", ""))

# U10 bad.jsonl: {"title":"a","body":"\xff"} — single 0xFF byte, no trailing LF
U10_BADUTF8 = bytes.fromhex(
    "7B 22 74 69 74 6C 65 22 3A 22 61 22 2C 22 62 6F 64 79 22 3A 22 FF 22 7D"
    .replace(" ", ""))


def write(name, data):
    path = os.path.join(FIXTURES, name)
    with open(path, "wb") as fh:
        fh.write(data)
    print("wrote %-28s %d bytes" % (name, len(data)))


def main():
    os.makedirs(FIXTURES, exist_ok=True)
    write("u08-exists.json", U08_EXISTS)
    write("u10-trunc.bin", U10_TRUNC)
    write("u10-badutf8.bin", U10_BADUTF8)

    # audit copies of record-based initial stores (same synthesis as runner)
    audit = [
        ("audit-u02-store.jsonl", [cases.U02_R1, cases.U02_R2, cases.U02_R3], "jsonl"),
        ("audit-u03-store.jsonl", [cases.U03_R1], "jsonl"),
        ("audit-u04-store.jsonl", [cases.U04_R1, cases.U04_R2, cases.U04_R3, cases.U04_R4], "jsonl"),
        ("audit-u06-one.jsonl", [cases.U06_R1], "jsonl"),
        ("audit-u07-store.jsonl", [cases.U07_R1], "jsonl"),
        ("audit-u08-good.jsonl", [cases.U08_G], "jsonl"),
        ("audit-u09-src.jsonl", [cases.U09_A, cases.U09_B], "jsonl"),
    ]
    for name, records, fmt in audit:
        write(name, synthesize(records, fmt))

    # sanity: verify the hex spellings decode to what we claim
    assert U10_TRUNC == b'{"title":"a'
    assert U10_BADUTF8[:-1].startswith(b'{"title":"a","body":"')
    assert U10_BADUTF8[-1:] == b"}"
    print("self-checks ok")


if __name__ == "__main__":
    main()

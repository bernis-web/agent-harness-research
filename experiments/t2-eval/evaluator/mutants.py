"""Derive M01/M02/M03 single mutants and the 3-defect defective from the
reference source via unique textual anchors (frozen mutation-map v0.1).

Each anchor must occur exactly once in reference/notes.py; otherwise the
derivation aborts (guards against silent mis-patching if the reference is
ever edited).

  M01 (R03): add saves body with real LF replaced by literal backslash+n.
  M02 (R06): search folds with .lower() instead of .casefold().
  M03 (R10): array-format store loads in reversed order.
  defective = M01 + M02 + M03 applied together.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REFERENCE = os.path.join(os.path.dirname(HERE), "reference", "notes.py")

MUTATIONS = [
    ("M01",
     '    record = {"title": title, "body": body}',
     '    record = {"title": title, "body": body.replace("\\n", "\\\\n")}'),
    ("M02",
     "    return s.casefold()",
     "    return s.lower()"),
    ("M03",
     "        _validate_records(sub, data)\n        return data, True",
     "        _validate_records(sub, data)\n        return list(reversed(data)), True"),
]

DEFECTIVE = "defective"


def load_reference():
    with open(REFERENCE, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def apply_mutation(src, mid):
    if mid == DEFECTIVE:
        for m, _old, _new in MUTATIONS:
            src = apply_mutation(src, m)
        return src
    old, new = next((o, n) for m, o, n in MUTATIONS if m == mid)
    count = src.count(old)
    if count != 1:
        raise SystemExit("anchor for %s found %d times (expected 1)" % (mid, count))
    return src.replace(old, new)


def build(mid):
    return apply_mutation(load_reference(), mid)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--write-defective", action="store_true",
                    help="write defective/notes.py (all three mutations)")
    args = ap.parse_args()
    if args.write_defective:
        target = os.path.join(os.path.dirname(HERE), "defective", "notes.py")
        with open(target, "w", encoding="utf-8", newline="") as fh:
            fh.write(build(DEFECTIVE))
        print("wrote " + target)
    else:
        for mid, old, new in MUTATIONS:
            src = build(mid)
            print("%s: derived, %d bytes (delta %+d)"
                  % (mid, len(src.encode("utf-8")),
                     len(src.encode("utf-8")) - len(load_reference().encode("utf-8"))))
        src = build(DEFECTIVE)
        ref = load_reference()
        diffs = sum(1 for a, b in zip(ref.splitlines(), src.splitlines()) if a != b)
        print("defective: derived, %d changed line(s) vs reference" % diffs)

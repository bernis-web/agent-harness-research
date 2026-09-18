"""tests/ acceptance gate (fabrication spec §4/§5).

Stages the public test suite next to a notes.py under test in a temp
directory (product workspace layout: notes.py beside tests/) and runs
unittest there:

  stage A: tests + reference/notes.py  -> ALL tests must pass
  stage B: tests + defective/notes.py  -> failures must occur ONLY inside
           test_u01/test_u04/test_u05/test_u09, at least one in each
           (each defect chain visible), and every other module green.

Also records the SHA-256 of every tests/ file before and after the runs
(integrity check), and scans the suite for out-of-boundary markers
(hidden-group / mutation identifiers must not appear in the public tests).
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TESTS = os.path.join(ROOT, "tests")
REFERENCE = os.path.join(ROOT, "reference", "notes.py")
DEFECTIVE = os.path.join(ROOT, "defective", "notes.py")
PY = sys.executable

BOUNDARY_FORBIDDEN = re.compile(r"H0[1-4]|M0[1-3]|mutant|mutation|hidden.group", re.IGNORECASE)
DEFECT_CHAIN_MODULES = {"test_u01", "test_u04", "test_u05", "test_u09"}


def tests_inventory():
    inv = {}
    for name in sorted(os.listdir(TESTS)):
        p = os.path.join(TESTS, name)
        if os.path.isfile(p):
            with open(p, "rb") as fh:
                inv[name] = hashlib.sha256(fh.read()).hexdigest()
    return inv


def boundary_scan(inv):
    problems = []
    for name in inv:
        with open(os.path.join(TESTS, name), "rb") as fh:
            text = fh.read().decode("utf-8", "replace")
        for m in BOUNDARY_FORBIDDEN.finditer(text):
            problems.append("%s: contains %r" % (name, m.group(0)))
    return problems


def stage(notes_path, stage_dir):
    shutil.copytree(TESTS, os.path.join(stage_dir, "tests"))
    shutil.copy2(notes_path, os.path.join(stage_dir, "notes.py"))


def run_unittest(stage_dir):
    proc = subprocess.run(
        [PY, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"],
        cwd=stage_dir, capture_output=True, timeout=600)
    return proc


def parse_failures(proc):
    """Return set of failing test module names from unittest -v output."""
    failed = set()
    for line in proc.stderr.decode("utf-8", "replace").splitlines():
        m = re.match(r"(?:FAIL|ERROR):\s+(\S+)\s+\(([\w.]+)\)", line)
        if m:
            mod = m.group(2).split(".")[0]  # "test_u01.U01Fidelity.test_x" -> "test_u01"
            failed.add(mod)
    return failed


def main():
    report = {"gate": "tests", "stages": {}}
    ok = True

    before = tests_inventory()
    report["tests_inventory_before"] = before
    report["boundary_scan"] = boundary_scan(before)
    if report["boundary_scan"]:
        ok = False
        print("BOUNDARY VIOLATIONS:")
        for p in report["boundary_scan"]:
            print("  " + p)

    for label, notes, expect_all_pass in (("reference", REFERENCE, True),
                                          ("defective", DEFECTIVE, False)):
        with tempfile.TemporaryDirectory() as tmp:
            stage_dir = os.path.join(tmp, "stage-" + label)
            os.makedirs(stage_dir)
            stage(notes, stage_dir)
            proc = run_unittest(stage_dir)
            failed_modules = parse_failures(proc)
            stage_report = {
                "notes": notes,
                "returncode": proc.returncode,
                "failed_modules": sorted(failed_modules),
                "stderr_tail": proc.stderr.decode("utf-8", "replace")[-2000:],
            }
            if expect_all_pass:
                stage_report["ok"] = proc.returncode == 0
            else:
                unexpected = failed_modules - DEFECT_CHAIN_MODULES
                missing = DEFECT_CHAIN_MODULES - failed_modules
                stage_report["unexpected_failed_modules"] = sorted(unexpected)
                stage_report["missing_chain_modules"] = sorted(missing)
                stage_report["ok"] = (proc.returncode != 0 and not unexpected and not missing)
            report["stages"][label] = stage_report
            ok = ok and stage_report["ok"]
            print("stage %-9s rc=%d failed_modules=%s -> %s"
                  % (label, proc.returncode, sorted(failed_modules),
                     "OK" if stage_report["ok"] else "FAILED"))

    after = tests_inventory()
    report["tests_inventory_after"] = after
    report["integrity_ok"] = before == after
    ok = ok and report["integrity_ok"]
    print("tests integrity: %s" % ("OK" if report["integrity_ok"] else "CHANGED"))

    out = os.path.join(ROOT, "runs", "tests-gate")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "report.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    print("gate report -> %s" % out)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

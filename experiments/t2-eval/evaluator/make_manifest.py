"""Generate t2-eval/MANIFEST.json — SHA-256 inventory of the deliverable
assets (fabrication spec §1/§4). The tests/ section is the list future
evaluator runs verify before/after product sessions."""
import datetime as _dt
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SECTIONS = {
    "tests": ["tests"],
    "reference": ["reference"],
    "defective": ["defective"],
    "evaluator": ["evaluator"],
    "fixtures": ["fixtures"],
}


def walk_files(*rels):
    out = []
    for rel in rels:
        p = os.path.join(ROOT, rel)
        if os.path.isfile(p):
            out.append(rel.replace("\\", "/"))
            continue
        for dirpath, dirs, files in os.walk(p):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in sorted(files):
                if f.endswith((".pyc", ".pyo")):
                    continue
                full = os.path.join(dirpath, f)
                out.append(os.path.relpath(full, ROOT).replace("\\", "/"))
    return sorted(out)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    manifest = {
        "generated": _dt.datetime.now().isoformat(timespec="seconds"),
        "algorithm": "sha256",
        "sections": {},
    }
    for section, rels in SECTIONS.items():
        entries = {}
        for rel in walk_files(*rels):
            entries[rel] = sha256(os.path.join(ROOT, rel))
        manifest["sections"][section] = entries
    manifest["file_count"] = sum(len(v) for v in manifest["sections"].values())

    out = os.path.join(ROOT, "MANIFEST.json")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print("wrote %s (%d files)" % (out, manifest["file_count"]))
    for section, entries in manifest["sections"].items():
        print("  %-10s %d files" % (section, len(entries)))


if __name__ == "__main__":
    main()

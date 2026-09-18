import json, subprocess, sys, tempfile, os
sb = tempfile.mkdtemp()

# 1) array store order
p = os.path.join(sb, "arr.json")
open(p, "w", encoding="utf-8").write('[{"title":"A","body":"x"},{"title":"B","body":"y"}]\n')
r = subprocess.run([sys.executable, "notes.py", "list", "--store", p], capture_output=True)
print("1) array list stdout:", r.stdout.decode().strip())

# 2) casefold vs lower
p2 = os.path.join(sb, "s.jsonl")
open(p2, "w", encoding="utf-8").write('{"title":"Straße","body":"x"}\n')
r = subprocess.run([sys.executable, "notes.py", "search", "--store", p2, "--query", "strasse"], capture_output=True)
print("2) strasse search:", r.stdout.decode().strip())

# 3) body LF fidelity
p3 = os.path.join(sb, "b.jsonl")
subprocess.run([sys.executable, "notes.py", "add", "--store", p3, "--title", "t", "--body", "a\nb"], capture_output=True)
r = subprocess.run([sys.executable, "notes.py", "list", "--store", p3], capture_output=True)
print("3) body roundtrip:", r.stdout.decode().strip())
print("   raw bytes:", open(p3, "rb").read())

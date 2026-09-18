import json

p = r"D:\projects\agent-harness-research\experiments\t1-prep\verification\browser-setup\edge-profile\Default\Preferences"
cfg = {
    "download": {
        "default_directory": r"D:\projects\agent-harness-research\experiments\t1-prep\verification\downloads",
        "prompt_for_download": False,
    }
}
json.dump(cfg, open(p, "w", encoding="utf-8"))
print(open(p, encoding="utf-8").read())

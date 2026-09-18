import sys, os, json, time, ctypes
from ctypes import wintypes
import psutil

def _norm(p):
    return os.path.normcase(os.path.normpath(os.path.abspath(p)))

def _identity(record):
    proc = psutil.Process(record["pid"])
    if not proc.is_running():
        raise RuntimeError("process not running")
    exe = _norm(proc.exe())
    if exe != _norm(record["exe"]) or proc.ppid() != record["driverPid"]:
        raise RuntimeError("candidate exe/parent mismatch before commandline access")
    ct_ms = proc.create_time()*1000
    if not (record["spawnBeforeMs"]-2000 <= ct_ms <= min(time.time()*1000,record["spawnAfterMs"]+2000)):
        raise RuntimeError("candidate creation time outside launch window")
    cmd = proc.cmdline()
    dd = [a for a in cmd if a.startswith("--user-data-dir=")]
    profile = None
    if len(dd) == 1:
        profile = _norm(dd[0].split("=", 1)[1])
    return proc, exe, profile

def _meta(pid):
    user32 = ctypes.windll.user32
    EnumWindows = user32.EnumWindows
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
    EnumWindows.restype = wintypes.BOOL
    GetWindowThreadProcessId = user32.GetWindowThreadProcessId
    GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    GetWindowThreadProcessId.restype = wintypes.DWORD
    GetClassNameW = user32.GetClassNameW
    GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    GetClassNameW.restype = ctypes.c_int
    IsWindowVisible = user32.IsWindowVisible
    IsWindowVisible.argtypes = [wintypes.HWND]
    IsWindowVisible.restype = wintypes.BOOL
    GetWindow = user32.GetWindow
    GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
    GetWindow.restype = wintypes.HWND
    GW_OWNER = 4
    pairs = []
    def cb(hwnd, lparam):
        d = wintypes.DWORD(0)
        GetWindowThreadProcessId(hwnd, ctypes.byref(d))
        pairs.append((hwnd, int(d.value)))
        return True
    if not EnumWindows(WNDENUMPROC(cb), 0):
        raise RuntimeError("EnumWindows failed")
    top = []
    for hwnd, wpid in pairs:
        if wpid != pid:
            continue  # only exact PID inspected further
        buf = ctypes.create_unicode_buffer(256)
        GetClassNameW(hwnd, buf, 256)
        owner = GetWindow(hwnd, GW_OWNER)
        owner_pid = 0
        if owner:
            d = wintypes.DWORD(0)
            GetWindowThreadProcessId(owner, ctypes.byref(d))
            owner_pid = int(d.value)
        top.append({"hwnd": int(hwnd), "pid": pid, "class": buf.value,
                    "visible": bool(IsWindowVisible(hwnd)),
                    "owner": int(owner or 0), "ownerPid": owner_pid})
    return top

def verify(record, expected_create_time=None):
    proc, exe, profile = _identity(record)
    if exe != _norm(record["exe"]):
        raise RuntimeError("exe mismatch")
    if profile != _norm(record["profile"]):
        raise RuntimeError("profile mismatch")
    if proc.ppid() != record["driverPid"]:
        raise RuntimeError("ppid mismatch")
    ct = proc.create_time()
    now = time.time()
    if ct > now + 1.0:
        raise RuntimeError("create_time in the future")
    if record.get("spawnBeforeMs") is not None and ct < record["spawnBeforeMs"] / 1000.0 - 1.0:
        raise RuntimeError("create_time before spawn window")
    if expected_create_time is not None and ct != expected_create_time:
        raise RuntimeError("create_time mismatch")
    top = [w for w in _meta(record["pid"])
           if w["class"] == "Chrome_WidgetWin_1" and w["visible"] and w["owner"] == 0]
    if len(top) != 1:
        raise RuntimeError("expected exactly one visible owned Chrome_WidgetWin_1 top window")
    return {"passed": True, "pid": record["pid"], "exe": exe,
            "createTime": ct, "parentPid": proc.ppid(),
            "profile": profile, "profileMatch": True,
            "targetOwnerHwnd": top[0]["hwnd"], "targetTopWindows": top}

def _run(launch_path, out_path):
    now_ms = int(time.time() * 1000)
    L = json.load(open(launch_path, encoding="utf-8"))
    out = verify(L)
    out["checkedAtMs"] = now_ms
    json.dump(out, open(out_path, "w", encoding="utf-8"), indent=2)

if __name__ == "__main__":
    try:
        _run(sys.argv[1], sys.argv[2])
        sys.exit(0)
    except Exception as e:
        try:
            json.dump({"passed": False, "error": str(e)},
                      open(sys.argv[2], "w", encoding="utf-8"))
        except Exception:
            pass
        sys.exit(1)

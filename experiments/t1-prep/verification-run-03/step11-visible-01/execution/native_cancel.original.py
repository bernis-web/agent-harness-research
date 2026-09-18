# native_cancel.py — cancel the visible Chrome native file-open dialog
# Usage: python native_cancel.py <browserPID> <outputDir>
import ctypes, ctypes.wintypes as wt, json, os, struct, sys, time

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

ENUM_PROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
MOUSEEVENTF = 0

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD),
                ("dwFlags", wt.DWORD), ("time", wt.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wt.DWORD), ("wParamL", wt.WORD), ("wParamH", wt.WORD)]

class _INPUTU(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wt.DWORD), ("u", _INPUTU)]

def fail(outdir, stage, code, handles=None):
    res = {"tool": "native_cancel", "stage": stage, "passed": False,
           "failure": code, "handles": handles or {}}
    p = os.path.join(outdir, "native-result.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(res, f)
        f.flush(); os.fsync(f.fileno())
    print(json.dumps(res))
    sys.exit(1)

def win_pid(h):
    p = wt.DWORD()
    user32.GetWindowThreadProcessId(h, ctypes.byref(p))
    return p.value

def main():
    if len(sys.argv) != 3:
        print("args: browserPID outputDir"); sys.exit(2)
    pid = int(sys.argv[1]); outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)

    dialog = None
    deadline = time.time() + 20
    while time.time() < deadline and dialog is None:
        owned = []          # HWNDs of this PID only
        top = []            # (hwnd, pid) metadata for all windows
        def cb(h, _):
            top.append((h, win_pid(h)))
            if win_pid(h) == pid:
                owned.append(h)
            return True
        user32.EnumWindows(ENUM_PROC(cb), 0)
        chrome_tops = {h for h in owned
                       if user32.GetClassNameW(h) == "Chrome_WidgetWin_1"}
        candidates = []
        for h, _ in top:  # query class/owner only now
            if win_pid(h) == pid and user32.GetClassNameW(h) == "#32770":
                owner = user32.GetWindow(h, 4)  # GW_OWNER
                if owner in chrome_tops:
                    candidates.append(h)
        if len(candidates) == 1:
            dialog = candidates[0]
        elif len(candidates) > 1:
            fail(outdir, "find_dialog", "AMBIGUOUS_DIALOG")
        # not found yet -> keep polling
        if dialog is None:
            time.sleep(0.25)
    if dialog is None:
        fail(outdir, "find_dialog", "DIALOG_NOT_FOUND")

    if not user32.IsWindow(dialog) or not user32.IsWindowVisible(dialog):
        fail(outdir, "find_dialog", "DIALOG_NOT_VISIBLE", {"dialog": dialog})

    cancel = user32.GetDlgItem(dialog, 2)
    if not cancel or not user32.IsWindow(cancel):
        fail(outdir, "find_cancel", "CANCEL_NOT_FOUND", {"dialog": dialog})
    if win_pid(cancel) != pid or not user32.IsChild(dialog, cancel):
        fail(outdir, "find_cancel", "CANCEL_NOT_OWNED",
             {"dialog": dialog, "cancel": cancel})
    if not (user32.IsWindowVisible(cancel) and user32.IsWindowEnabled(cancel)):
        fail(outdir, "find_cancel", "CANCEL_NOT_USABLE",
             {"dialog": dialog, "cancel": cancel})

    meta = {
        "dialog": {"hwnd": dialog, "pid": pid,
                   "class": user32.GetClassNameW(dialog),
                   "owner": user32.GetWindow(dialog, 4)},
        "cancel": {"hwnd": cancel, "pid": win_pid(cancel),
                   "class": user32.GetClassNameW(cancel),
                   "enabled": bool(user32.IsWindowEnabled(cancel)),
                   "visible": bool(user32.IsWindowVisible(cancel))},
    }
    p = os.path.join(outdir, "native-result.json")
    with open(p, "w", encoding="utf-8") as f:   # flushed BEFORE acting
        json.dump({"tool": "native_cancel", "stage": "pre-act",
                   "passed": False, "handles": meta}, f)
        f.flush(); os.fsync(f.fileno())

    # --- screenshot: cancel button only, via PrintWindow ---
    rc = wt.RECT()
    if not user32.GetWindowRect(cancel, ctypes.byref(rc)):
        fail(outdir, "screenshot", "GETRECT_FAILED", meta)
    w, h = rc.right - rc.left, rc.bottom - rc.top
    if w <= 0 or h <= 0:
        fail(outdir, "screenshot", "BAD_RECT", meta)

    hdcScreen = user32.GetDC(None)
    memDC = gdi32.CreateCompatibleDC(hdcScreen)
    bmi = ctypes.c_buffer(struct.pack("<iiiHHIIiiII", 40, w, -h, 1, 32, 0,
                                      w * h * 4, 0, 0, 0, 0))
    bmp = gdi32.CreateDIBSection(hdcScreen, bmi, 0, None, None, 0)
    old = ctypes.wintypes.HBITMAP() if False else None
    gdi32.SelectObject(memDC, bmp)
    ok = user32.PrintWindow(cancel, memDC, 2)  # PW_RENDERFULLCONTENT
    if not ok:
        gdi32.DeleteObject(bmp); gdi32.DeleteDC(memDC); user32.ReleaseDC(None, hdcScreen)
        fail(outdir, "screenshot", "PRINTWINDOW_FAILED", meta)
    n = w * h * 4
    buf = ctypes.create_string_buffer(n)
    gdi32.GetDIBits(memDC, bmp, 0, h, buf, bmi, 0)
    gdi32.DeleteObject(bmp); gdi32.DeleteDC(memDC); user32.ReleaseDC(None, hdcScreen)
    try:
        from PIL import Image
        img = Image.frombuffer("RGBA", (w, h), buf.raw, "raw", "BGRA", 4, 1)
        img = img.convert("RGB")
        img.save(os.path.join(outdir, "cancel-button.png"))
    except Exception:
        fail(outdir, "screenshot", "PILLOW_SAVE_FAILED", meta)

    # --- real foreground click on Cancel ---
    user32.SetForegroundWindow(dialog)
    time.sleep(0.15)
    if user32.GetForegroundWindow() != dialog:
        fail(outdir, "click", "NOT_FOREGROUND", meta)
    cx, cy = (rc.left + rc.right) // 2, (rc.top + rc.bottom) // 2
    if not user32.SetCursorPos(cx, cy):
        fail(outdir, "click", "SETCURSOR_FAILED", meta)
    time.sleep(0.05)
    under = user32.WindowFromPoint(wt.POINT(cx, cy))
    if not (under == cancel or user32.IsChild(cancel, under)):
        fail(outdir, "click", "POINT_NOT_ON_CANCEL", meta)
    if user32.GetForegroundWindow() != dialog:
        fail(outdir, "click", "FOREGROUND_LOST", meta)

    INJECT = 0
    down = INPUT(); down.type = 0
    down.mi = MOUSEINPUT(0, 0, 0, 0x0002, 0, None)  # LEFTDOWN
    up = INPUT(); up.type = 0
    up.mi = MOUSEINPUT(0, 0, 0, 0x0004, 0, None)    # LEFTUP
    if user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(INPUT)) != 1:
        fail(outdir, "click", "SENDINPUT_DOWN_FAILED", meta)
    time.sleep(0.05)
    if user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(INPUT)) != 1:
        fail(outdir, "click", "SENDINPUT_UP_FAILED", meta)

    deadline = time.time() + 5
    while time.time() < deadline:
        if not user32.IsWindow(dialog):
            res = {"tool": "native_cancel", "stage": "done", "passed": True,
                   "cancelClickedRealInput": True, "dialogDestroyed": True,
                   "handles": meta}
            with open(p, "w", encoding="utf-8") as f:
                json.dump(res, f); f.flush(); os.fsync(f.fileno())
            print(json.dumps(res))
            return
        time.sleep(0.1)
    fail(outdir, "wait_destroy", "DIALOG_STILL_OPEN", meta)

if __name__ == "__main__":
    main()

# native_cancel.py — cancel the visible Chrome native file-open dialog
# Usage: python native_cancel.py <browserPID> <outputDir>
import ctypes, ctypes.wintypes as wt, json, os, struct, sys, time

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

ENUM_PROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
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


# Coordinator mechanical ABI correction; original Flash logic retained.
H=ctypes.c_void_p
for dll,name,args,ret in [
 (user32,'GetWindowThreadProcessId',[H,ctypes.POINTER(wt.DWORD)],wt.DWORD),
 (user32,'EnumWindows',[ENUM_PROC,wt.LPARAM],wt.BOOL),
 (user32,'GetClassNameW',[H,wt.LPWSTR,ctypes.c_int],ctypes.c_int),
 (user32,'GetWindow',[H,wt.UINT],H),(user32,'GetDlgItem',[H,ctypes.c_int],H),
 (user32,'IsWindow',[H],wt.BOOL),(user32,'IsWindowVisible',[H],wt.BOOL),
 (user32,'IsWindowEnabled',[H],wt.BOOL),(user32,'IsChild',[H,H],wt.BOOL),
 (user32,'GetWindowRect',[H,ctypes.POINTER(wt.RECT)],wt.BOOL),
 (user32,'GetDC',[H],H),(user32,'ReleaseDC',[H,H],ctypes.c_int),
 (user32,'PrintWindow',[H,H,wt.UINT],wt.BOOL),
 (user32,'SetForegroundWindow',[H],wt.BOOL),(user32,'GetForegroundWindow',[],H),
 (user32,'SetCursorPos',[ctypes.c_int,ctypes.c_int],wt.BOOL),
 (user32,'WindowFromPoint',[wt.POINT],H),
 (gdi32,'CreateCompatibleDC',[H],H),(gdi32,'CreateCompatibleBitmap',[H,ctypes.c_int,ctypes.c_int],H),
 (gdi32,'SelectObject',[H,H],H),(gdi32,'DeleteObject',[H],wt.BOOL),
 (gdi32,'DeleteDC',[H],wt.BOOL),
 (gdi32,'GetDIBits',[H,H,wt.UINT,wt.UINT,H,H,wt.UINT],ctypes.c_int)
]:
 fn=getattr(dll,name);fn.argtypes=args;fn.restype=ret
user32.SendInput.argtypes=[wt.UINT,ctypes.POINTER(INPUT),ctypes.c_int]
user32.SendInput.restype=wt.UINT
user32.SetThreadDpiAwarenessContext.argtypes=[H]
user32.SetThreadDpiAwarenessContext.restype=H
user32.SetThreadDpiAwarenessContext(H(-4)) # helper-thread only, not host setting
assert ctypes.sizeof(INPUT)==40, 'Unexpected Win64 INPUT ABI'
def class_name(hwnd):
 b=ctypes.create_unicode_buffer(256)
 if not user32.GetClassNameW(hwnd,b,256): raise OSError('GetClassNameW failed')
 return b.value

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
        def cb(h, _):
            if win_pid(h) == pid:
                owned.append(h)
            return True
        user32.EnumWindows(ENUM_PROC(cb), 0)
        chrome_tops = {h for h in owned
                       if class_name(h) == "Chrome_WidgetWin_1"}
        candidates = []
        for h in owned:  # exact target PID only
            if win_pid(h) == pid and class_name(h) == "#32770":
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
    if win_pid(cancel) != pid or not user32.IsChild(dialog, cancel) or class_name(cancel) != "Button":
        fail(outdir, "find_cancel", "CANCEL_NOT_OWNED",
             {"dialog": dialog, "cancel": cancel})
    if not (user32.IsWindowVisible(cancel) and user32.IsWindowEnabled(cancel)):
        fail(outdir, "find_cancel", "CANCEL_NOT_USABLE",
             {"dialog": dialog, "cancel": cancel})

    meta = {
        "dialog": {"hwnd": dialog, "pid": pid,
                   "class": class_name(dialog),
                   "owner": user32.GetWindow(dialog, 4), "ownerPid":win_pid(user32.GetWindow(dialog,4)), "ownerClass":class_name(user32.GetWindow(dialog,4))},
        "cancel": {"hwnd": cancel, "pid": win_pid(cancel),
                   "class": class_name(cancel),
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

    dc=mem=bmp=old=None
    try:
        dc=user32.GetDC(cancel)
        if not dc: raise RuntimeError('GetDC target button failed')
        mem=gdi32.CreateCompatibleDC(dc);bmp=gdi32.CreateCompatibleBitmap(dc,w,h)
        if not mem or not bmp: raise RuntimeError('GDI allocation failed')
        old=gdi32.SelectObject(mem,bmp)
        if not old: raise RuntimeError('GDI selection failed')
        if not user32.PrintWindow(cancel,mem,2): raise RuntimeError('PrintWindow target button failed')
        gdi32.SelectObject(mem,old);old=None
        bmi=ctypes.create_string_buffer(struct.pack('<IiiHHIIiiII',40,w,-h,1,32,0,w*h*4,0,0,0,0))
        buf=ctypes.create_string_buffer(w*h*4)
        if gdi32.GetDIBits(dc,bmp,0,h,buf,bmi,0)!=h: raise RuntimeError('GetDIBits failed')
        from PIL import Image
        img=Image.frombytes('RGB',(w,h),buf.raw,'raw','BGRX',0,1)
        if all(lo==hi for lo,hi in img.getextrema()): raise RuntimeError('Blank button capture')
        img.save(os.path.join(outdir,'cancel-button.png'))
    except Exception as exc:
        fail(outdir,'screenshot',str(exc),meta)
    finally:
        if old and mem:gdi32.SelectObject(mem,old)
        if bmp:gdi32.DeleteObject(bmp)
        if mem:gdi32.DeleteDC(mem)
        if dc:user32.ReleaseDC(cancel,dc)

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

    pair=(INPUT*2)()
    pair[0].type=0;pair[0].mi=MOUSEINPUT(0,0,0,0x0002,0,None)
    pair[1].type=0;pair[1].mi=MOUSEINPUT(0,0,0,0x0004,0,None)
    if user32.SendInput(2,pair,ctypes.sizeof(INPUT))!=2:
        fail(outdir,'click','SENDINPUT_PAIR_FAILED',meta)

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

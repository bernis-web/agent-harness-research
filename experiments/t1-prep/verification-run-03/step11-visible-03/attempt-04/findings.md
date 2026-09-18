# attempt-04 findings — observation-only dialog inventory (2026-09-18)

Run: `node execution\run.cjs attempt-04\evidence` → UNTESTED/BLOCKED, native DIALOG_NOT_FOUND (same as attempt-03), clickOk=true.

## What the observation-only inventory (dialog-inventory.json) proved

1. **The native file-open dialog EXISTS and appears within ~0.5s of the click.**
   - #32770 hwnd=855290, title "打开", hosted by **chrome.exe PID 46404** — a *different* process from browserPid 33944.
   - Its GW_OWNER = 199766 = Chrome_WidgetWin_1 = **targetOwnerHwnd** (launch.json/identity-before.json confirm 199766), ownerPid = 33944 = browserPid. Owner chain is exactly as required.

2. **Root cause of attempt-01..03 DIALOG_NOT_FOUND**: the candidate filter required
   `win_pid(dialog) == browserPid`. Chrome hosts the native file dialog in a descendant
   chrome.exe process, so the filter can never match. The owner-identity condition
   (strict `owner == targetOwnerHwnd`, per analysis-review.json "no owner broadening")
   was never violated — it was the *process* condition that was factually wrong.

3. **Secondary defect**: at t=0.54s a modal child #32770 "位置不可用" (Location is not
   available), hwnd=263888, owned by the dialog, becomes foreground and disables the
   dialog. Cause: harness env redirects USERPROFILE to `<attempt>\evidence\home`, and
   `home\Downloads` (and Desktop/Documents) were never created — the dialog's initial
   directory (%USERPROFILE%\Downloads) does not resolve.

## attempt-05 changes (this session)

- `native_cancel.py`: dialog host-process condition corrected to
  `pid == browserPid OR (exe basename == chrome.exe AND parent chain reaches browserPid
  through chrome.exe processes only)` — Toolhelp32 process-tree walk, ancestry recorded
  in native-result meta and in inventory samples. **Owner condition unchanged and strict.**
  Cancel-button pid check corrected to `win_pid(cancel) == win_pid(dialog)`.
- Attempt dir pre-provisions `home\{Downloads,Desktop,Documents}` to eliminate the
  "位置不可用" modal.
- Backups: `native_cancel.py.pre-attempt04` (attempt-03 state), `.pre-attempt05`
  (attempt-04 observation state).

## attempt-05 result — advanced to DIALOG_NOT_VISIBLE

- Process-tree fix worked: dialog found at hwnd=25494216, ancestry
  `48684:chrome.exe < 48016:chrome.exe` (browserPid=48016). No "位置不可用" modal
  (home dirs pre-provisioned).
- New failure stage `DIALOG_NOT_VISIBLE`: the poll loop accepted the candidate in the
  gap where Chrome has already created the #32770 hwnd (~0.5s) but not yet shown it,
  so the post-loop visibility assertion tripped.

## attempt-06 result — PASS (2026-09-18 01:13)

Fix: accept the single candidate inside the poll loop only when
`IsWindowVisible(candidates[0])` (downstream visibility assertion unchanged).
Backup: `native_cancel.py.pre-attempt06` (attempt-05 state).

Run: `node execution\run.cjs attempt-06\evidence` → **`{"status":"PASS"}` exit 0** —
first PASS of step11-visible-03 (attempts 01–05 all failed at the native stage).

Evidence chain (all under `attempt-06\evidence\`):
- `native-result.json`: stage `done`, `passed:true`, `cancelClickedRealInput:true`,
  `dialogDestroyed:true`; dialog hwnd 394894 pid 49260, ancestry
  `[[49260,chrome.exe],[48240,chrome.exe]]`, owner 12125696 =
  targetOwnerHwnd (ownerPid 48240 = browserPid).
- `dialog-inventory.json`: t=0.04 sample shows the dialog `visible:false` — the
  visibility gate waited it out exactly as designed; no 位置不可用 modal present.
- `dom-events.jsonl`: `{"kind":"cancel","isTrusted":true}`.
- `results.json`: PASS with `nativePassed/dialogDestroyed/cancelTrusted/noChange`
  all true; liveIdentity passed, cdpPid == browserPid == 48240;
  `native-run.json` code 0 clickOk true; `identity-before-click.json` confirms
  targetOwnerHwnd 12125696 unchanged at click time.

Conclusion: attempts 01–03 root cause (dialog hosted by descendant chrome.exe) and
attempt-05 root cause (hwnd created before shown) both fixed; owner identity stayed
strict (`owner == targetOwnerHwnd`) throughout, per analysis-review.json.

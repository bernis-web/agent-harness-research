# T1 verification-run-03 — supervision closeout, 2026-09-17

## Current conclusion
**External preparation attempt02 timed out; public first batch remains untested.** The previous report's bare-mode authentication failure is historical evidence only, not a conclusion about normal client authentication. The browser environment preflight remains PASS based on its existing actual evidence.

## Real external calls and attribution
### attempt01 — preserved unchanged
The real isolated Claude --bare print invocation exited 1 in 0.73 sec with Not logged in. Its response reports zero API time and token usage. This does not demonstrate that the normally authenticated client is unusable. Original cli-call.json, cli-result.json, dispatch-claude.txt and invoker files remain unchanged. The previous REPORT/results are preserved as REPORT-before-normal-auth.md and results-before-normal-auth.json.

### attempt02 — ordinary authentication, supervised to its existing limit
- Actual start: **2026-09-17 19:41:23 +08:00**. Direct official Claude executable corresponding to the locally verified claude.ps1 wrapper was invoked. No --bare; normal HOME/USERPROFILE/authentication environment retained. No login, credential-file parsing, key extraction/injection or configuration editing.
- Local help explicitly says --safe-mode disables customizations while auth/model selection work normally. --setting-sources user retains client-side user routing/auth configuration but excludes project/local settings. Tools empty, MCP strict/empty, hooks disabled by explicit settings, no session persistence, system prompt snapshot off, no Chrome integration.
- **One model-task invocation, no duplicate launch.** Existing runner enforced its 840-second limit. It recorded **bounded task timeout after 840.03 seconds** (approximately 19:55:23 +08:00); supervision observed final state at 19:55:25 +08:00. Runner session 73180 was reaped, wrapper exit 0. Wrapper exit 0 means bookkeeping completed, not model success.
- No cli-result.json or cli-stderr.txt was created in attempt02. The original runner did not preserve TimeoutExpired partial stdout/stderr. Therefore **authentication success/failure, API/server root cause, model inference and usage are unknown**; do not turn this into an authentication diagnosis.
- Existing subprocess.run timeout handling terminates/waits for its direct child. No additional process kills or unrelated-process cleanup were performed.
- The deadline-bound supervision loop continued after its tool transport reached 300 seconds; final state was subsequently collected from that same supervision/task. No new model request was launched.
- Evidence: attempt02-normal-auth/cli-call.json, invoke.py, dispatch.txt, help-options-evidence.txt, AUTH-POLICY.md and supervision-final.json.

### ZCode conditional READY fallback
Bundled entry D:\zcode\resources\glm\zcode.cjs was already verified with --help (0.16.5). **READY call not sent.** The final authorized maximum would be 120 seconds, but the prerequisite isolation gate is not met, so no request is started. The local help shows tool allow/deny lists and alternate settings, but no verified way to disable MCP startup, hooks and memory together while preserving normal client authentication. Denying tool calls does not prove hooks/MCP startup are disabled. Per the user's explicit condition, do not launch when these constraints cannot be established. This is not a claim that the program can never support such controls. No credential bridge, personal config inspection, unpacking or reverse engineering was used. See zcode-ready-gate.json and original zcode-help.txt.

## Who generated what / what actually ran
- **Coordinator (Codex)** authored and ran only the environment-preflight driver and dispatch/supervision plumbing.
- **Claude** received real preparation CLI dispatches; attempt01 returned an auth error, attempt02 timed out without a returned result. **No Claude-generated acceptance driver was obtained.**
- **ZCode** local help ran; no model READY or acceptance task ran.
- **No public acceptance item was executed.** Do not attribute coordinator environment checks to Claude/ZCode and do not describe preflight as product acceptance.

## Environment preflight — previous execution evidence retained
- Existing Playwright-core 1.63.0-alpha-2026-08-31 reused from D:\projects\npm-cache\_npx\cbf1b8a072280925\node_modules\playwright-core; existing Chrome reported 152.0.7977.83. No installation.
- Fresh browser profile, HOME, appdata, TEMP/TMP and downloads explicitly within this run directory. No old run profile reused. Sandbox enabled, ignoreDefaultArgs=true with explicit reviewed arguments; actual command line recorded, no --no-sandbox or security-disabling switches.
- about:blank screenshot saved and visually checked. file:// controlled preflight page opened and screenshot checked. Real UI link click triggered a download. CDP original path equals Playwright actual temporary path and is inside downloads/. saveAs is separately recorded; original and saved SHA-256 match: 33ac731bfd6aab90390cb4d6cd5605644cec58da79519b44e7aeff6430da4187.
- Context offline requested and explicit setOffline(true) applied; HTTP(S) route abort independently verified with ERR_BLOCKED_BY_CLIENT. Host networking untouched; no HTTP server.
- Attempt01 stopped on an overly strict navigator.onLine assertion for a local file. Original driver/report preserved. Attempt02 corrected this driver-only assertion to require observed network blocking; PASS. This was not a product failure; no reference implementation code changed.
- Only the context created by this task was closed.


## Public first batch — itemized
| Item | Status |
|---|---|
| 1 | UNTESTED — no returned external-assistant driver |
| 2 | UNTESTED — no returned external-assistant driver |
| 3 | UNTESTED — no returned external-assistant driver |
| 4 | UNTESTED — no returned external-assistant driver |
| 5 | UNTESTED — no returned external-assistant driver |
| 6 | UNTESTED — no returned external-assistant driver |
| 7 | UNTESTED — no returned external-assistant driver |
| 8 | UNTESTED — no returned external-assistant driver |
| 9 | UNTESTED — no returned external-assistant driver |
| 10 | UNTESTED — no returned external-assistant driver |
| 11 | UNTESTED — no returned external-assistant driver |
| 12a | UNTESTED — no returned external-assistant driver |
| 12b | UNTESTED — no returned external-assistant driver |
| 12c | UNTESTED — no returned external-assistant driver |
| 12d | UNTESTED — no returned external-assistant driver |
| A1 | UNTESTED — no returned external-assistant driver |
| A2 | UNTESTED — no returned external-assistant driver |
| A3 | UNTESTED — no returned external-assistant driver |
| A4 | UNTESTED — no returned external-assistant driver |
| B1 | UNTESTED — no returned external-assistant driver |
| B2 | UNTESTED — no returned external-assistant driver |
| B3 | UNTESTED — no returned external-assistant driver |

**0 passed / 0 failed / 22 untested.** This is a preparation timeout, not a product failure. H1—H9 were neither read nor executed. No D2, WorkBuddy or Claude-product comparison. File-picker cancellation and all reference UI acceptance behaviors remain unverified.

## Preservation and change scope
The five authorized reference/spec/manual/README hashes were rechecked this turn and all match attempt02's before baseline (protected-final.json). No implementation was repaired or modified. Old verification runs, unrelated research and sensor-array records were not touched. All coordinator-authored outputs remain under this run03 directory. Current normal-client authentication internals were not inspected.

Updated: REPORT.md, results.json and changed-files.json. Added: historical report/results copies, attempt02 evidence/supervision, zcode-ready-gate.json, protected-final.json, closeout verification. Runtime browser directories remain preserved and are not read for credentials. Exact authored/evidence file paths are in changed-files.json.

## Remaining gate
A successful bounded external assistant response is still needed before acceptance-driver audit and first-batch UI execution. No automatic retry is left running. No further request was sent after the ordinary attempt timed out. The current report stops here rather than repeating auth/network probing or reading private configuration.

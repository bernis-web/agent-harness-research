# T1 verification-run-03 — 2026-09-17

## Decision
BLOCKED_EXTERNAL_ASSISTANT_AUTH. Environment preflight PASS; first public acceptance batch NOT EXECUTED. No product failure established and no T1 acceptance completion claimed.

## External CLI evidence
- Installed bundled ZCode entry: D:\zcode\resources\glm\zcode.cjs. Invoked with node --help under isolated HOME/USERPROFILE. Runtime help identifies 0.16.5. Local help advertises -p/--print, -c/--continue, --resume, --browser-use <mode> (headless). No model call, resume, or browser-use was performed for ZCode; exact equals syntax was not exercised. No unpacking or reverse engineering.
- The documented convenience wrapper was NOT run because its documented authentication bridge reads a personal config key.
- D:\projects\node-global\claude.ps1 --help was invoked; wrapper points to D:\projects\node-global\node_modules\@anthropic-ai\claude-code\bin\claude.exe, which was then directly invoked for the real preparation task.
- Claude invocation: --bare --print; no tools, slash commands, session persistence, Chrome integration, external MCP or user/project/local settings. Explicit isolated settings disable all hooks. Request supplied only via stdin from dispatch-claude.txt. Timeout 720 seconds, process hidden.
- Actual start 2026-09-17 19:33:15 +0800; exit 1 after 0.73 sec. Result: Not logged in · Please run /login. duration_api_ms=0; all input/output tokens=0. This proves a real CLI preparation dispatch attempt, NOT a successful model inference. No credentials were sought or extracted.

## Environment preflight
- Existing Playwright-core 1.63.0-alpha-2026-08-31 reused from D:\projects\npm-cache\_npx\cbf1b8a072280925\node_modules\playwright-core; existing Chrome reported 152.0.7977.83. No installation.
- Fresh browser profile, HOME, appdata, TEMP/TMP and downloads explicitly within this run directory. No old run profile reused. Sandbox enabled, ignoreDefaultArgs=true with explicit reviewed arguments; actual command line recorded, no --no-sandbox or security-disabling switches.
- about:blank screenshot saved and visually checked. file:// controlled preflight page opened and screenshot checked. Real UI link click triggered a download. CDP original path equals Playwright actual temporary path and is inside downloads/. saveAs is separately recorded; original and saved SHA-256 match: 33ac731bfd6aab90390cb4d6cd5605644cec58da79519b44e7aeff6430da4187.
- Context offline requested and explicit setOffline(true) applied; HTTP(S) route abort independently verified with ERR_BLOCKED_BY_CLIENT. Host networking untouched; no HTTP server.
- Attempt01 stopped on an overly strict navigator.onLine assertion for a local file. Original driver/report preserved. Attempt02 corrected this driver-only assertion to require observed network blocking; PASS. This was not a product failure; no reference implementation code changed.
- Only the context created by this task was closed.

## First batch
| Item | Status |
|---|---|
| 1 | UNTESTED — external assistant authentication blocked |
| 2 | UNTESTED — external assistant authentication blocked |
| 3 | UNTESTED — external assistant authentication blocked |
| 4 | UNTESTED — external assistant authentication blocked |
| 5 | UNTESTED — external assistant authentication blocked |
| 6 | UNTESTED — external assistant authentication blocked |
| 7 | UNTESTED — external assistant authentication blocked |
| 8 | UNTESTED — external assistant authentication blocked |
| 9 | UNTESTED — external assistant authentication blocked |
| 10 | UNTESTED — external assistant authentication blocked |
| 11 | UNTESTED — external assistant authentication blocked |
| 12a | UNTESTED — external assistant authentication blocked |
| 12b | UNTESTED — external assistant authentication blocked |
| 12c | UNTESTED — external assistant authentication blocked |
| 12d | UNTESTED — external assistant authentication blocked |
| A1 | UNTESTED — external assistant authentication blocked |
| A2 | UNTESTED — external assistant authentication blocked |
| A3 | UNTESTED — external assistant authentication blocked |
| A4 | UNTESTED — external assistant authentication blocked |
| B1 | UNTESTED — external assistant authentication blocked |
| B2 | UNTESTED — external assistant authentication blocked |
| B3 | UNTESTED — external assistant authentication blocked |

0 passed / 0 failed / 22 untested. Public acceptance execution did not begin; no product functions or internal tree were invoked or modified. Step 11 real file-picker cancellation remains unverified. H1—H9 were not read or run; no D2, WorkBuddy, or Claude-product comparison.

## Preservation / remaining gate
Five authorized frozen/reference/readme files have identical before/after SHA-256 hashes. Git status before and after: only existing untracked experiments/ and research/; tracked diff empty. Reference/spec/manual/old verification/research untouched. Sensor-array related records untouched. No claims are made that repository-wide unrelated concurrent state was exhaustively audited.

Continuation requires an external preparation model invocation that authenticates through an authorized normal client path without credential extraction; no budget request is needed. Browser prerequisites are demonstrated, but no acceptance driver was generated by Claude. Do not label the coordinator-authored environment-only preflight script as Claude-generated.

## Evidence / changes
All task-authored additions are under D:\projects\agent-harness-research\experiments\t1-prep\verification-run-03\. See changed-files.json for the exact authored-file list and separate runtime directories; credential-bearing runtime databases are not read or hashed. CLI call/result/prompt, help output, screenshots, download originals, driver correction, preflight reports, results and protected-file hashes remain available.

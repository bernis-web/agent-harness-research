$ErrorActionPreference = 'Stop'
$env:TEMP = 'D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/temp'
$env:TMP = 'D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/temp'
$env:PYTHONIOENCODING = 'utf-8'
& node 'D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/browser-preflight.cjs'
if ($LASTEXITCODE -ne 0) { throw 'Browser environment preflight failed; inspect preflight.json' }

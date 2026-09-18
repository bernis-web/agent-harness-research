$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
& python 'D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/invoke-claude.py'
if ($LASTEXITCODE -ne 0) { throw 'Claude dispatch runner failed' }

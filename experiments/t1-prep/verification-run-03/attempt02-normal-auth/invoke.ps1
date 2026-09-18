$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
& python 'D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/attempt02-normal-auth/invoke.py'
if ($LASTEXITCODE -ne 0) { throw 'Ordinary Claude invocation runner failed' }

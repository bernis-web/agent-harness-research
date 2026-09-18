$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
& python 'D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/attempt03-model-flash/invoke-stream.py' 'glm-5.3-flash' 90
if ($LASTEXITCODE -ne 0) { throw 'Streaming CLI runner failed' }

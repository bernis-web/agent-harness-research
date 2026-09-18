$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
& python 'D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/attempt04-model-glm53/flash-implementation01/invoke-stream.py' 'glm-5.3-flash' 240
if ($LASTEXITCODE -ne 0) { throw 'Flash implementation runner failed' }

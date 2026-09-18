$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
& python 'D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/attempt04-model-glm53/invoke-stream.py' 'glm-5.3' 480
if ($LASTEXITCODE -ne 0) { throw 'Streaming CLI code-generation runner failed' }

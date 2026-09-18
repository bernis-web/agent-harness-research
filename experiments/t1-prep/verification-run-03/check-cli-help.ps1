$ErrorActionPreference = 'Stop'
$env:TEMP = 'D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/temp'
$env:TMP = 'D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/temp'
$env:CLAUDE_CONFIG_DIR = 'D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/cli-home'
$env:HOME = 'D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/cli-home'
$env:USERPROFILE = 'D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/cli-home'
$env:CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = '1'
$env:CLAUDE_CODE_DISABLE_AUTO_MEMORY = '1'
Set-Location -LiteralPath 'D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03'
& 'D:/projects/node-global/claude.ps1' --help | Out-File -LiteralPath 'D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/claude-help.txt' -Encoding utf8
if (Test-Path -LiteralPath 'D:/zcode/resources/glm/zcode.cjs') {
    & node 'D:/zcode/resources/glm/zcode.cjs' --help | Out-File -LiteralPath 'D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/zcode-help.txt' -Encoding utf8
}

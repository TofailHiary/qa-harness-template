# Unattended QA run (CI) - PowerShell twin of ci-run-qa.sh. Judges the run by its run record, never by the chat.
#
#   pwsh .claude/scripts/ci-run-qa.ps1 "/full-qa APP-123 --mode targeted" APP-123-20261026
#
# Exit codes: 0 = GO   1 = NO-GO, or the run record is missing / contradicts itself   2 = PARTIAL   3 = setup problem
# Extra claude flags go in $env:QA_CLAUDE_FLAGS (space-separated).
param([string]$Prompt, [string]$Run)
if (-not $Prompt -or -not $Run) { Write-Output 'usage: ci-run-qa.ps1 "<skill + arguments>" <run-folder>'; exit 3 }
$Root = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { (Get-Location).Path }
$Ev = Join-Path $Root (Join-Path 'qa-evidence' $Run)
New-Item -ItemType Directory -Force $Ev | Out-Null
$Py = $null
foreach ($n in 'python3', 'python', 'py') { if (Get-Command $n -ErrorAction SilentlyContinue) { $Py = $n; break } }
if (-not $Py) { Write-Output 'no python on PATH'; exit 3 }
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) { Write-Output 'claude CLI not on PATH (npm i -g @anthropic-ai/claude-code)'; exit 3 }
& $Py (Join-Path $Root '.claude/scripts/doctor.py') *> (Join-Path $Ev 'ci-doctor.txt')
if ($LASTEXITCODE -ne 0) { Get-Content (Join-Path $Ev 'ci-doctor.txt'); Write-Output 'doctor: NOT READY - fix the FAIL rows first'; exit 3 }
$text = "$Prompt`nRun folder: qa-evidence/$Run/ - keep its run.json (qa-standards references/run-record.md). This is an unattended CI run: never ask a question; anything you cannot decide is BLOCKED with what would unblock it."
$extra = @(); if ($env:QA_CLAUDE_FLAGS) { $extra = $env:QA_CLAUDE_FLAGS -split '\s+' | Where-Object { $_ } }
& claude -p $text --output-format stream-json --verbose @extra | Out-File -Encoding utf8 (Join-Path $Ev 'ci-claude-stream.jsonl')
if ($LASTEXITCODE -ne 0) { Write-Output "claude exited $LASTEXITCODE - judging the run record anyway" }
$rj = Join-Path $Ev 'run.json'
if (-not (Test-Path $rj)) { Write-Output "no run.json in qa-evidence/$Run - the run left no record"; exit 1 }
& $Py (Join-Path $Root '.claude/skills/qa-standards/scripts/verdict_check.py') $Ev
if ($LASTEXITCODE -ne 0) { Write-Output 'run record contradicts itself'; exit 1 }
$v = (Get-Content $rj -Raw -Encoding UTF8 | ConvertFrom-Json).verdict.run
Write-Output "verdict: $v"
switch ($v) { 'GO' { exit 0 } 'PARTIAL' { exit 2 } default { exit 1 } }
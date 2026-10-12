param(
  [Parameter(Mandatory = $true)][string]$Python,
  [string]$OutputDirectory = (Join-Path ([System.IO.Path]::GetTempPath()) ("neural-handoff-" + [guid]::NewGuid().ToString('N')))
)
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$pythonExe = (Get-Command $Python -ErrorAction Stop).Source
$outputRoot = [System.IO.Path]::GetFullPath($OutputDirectory)
if ($outputRoot.StartsWith($repoRoot + [System.IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or $outputRoot -eq $repoRoot) {
  throw 'Use an output directory outside the repository to preserve historical evidence.'
}
New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
$env:PYTHON = $pythonExe
$env:PYTHONPATH = Join-Path $repoRoot 'trainer/src'
Get-ChildItem Env: | Where-Object { $_.Name -in @('PYTHONUTF8','PYTHONIOENCODING','PERSPECTIVE_REPLAY_REQUIREMENTS') -or $_.Name -match 'REPORT|^PROMPT[0-9]' } |
  ForEach-Object { Remove-Item -LiteralPath ('Env:' + $_.Name) }
$checks = [System.Collections.Generic.List[object]]::new()
function Invoke-Check([string]$Name, [string]$Executable, [string[]]$Arguments, [int]$Expected = 0) {
  # Windows PowerShell reports native stderr as ErrorRecord objects even on success.
  $savedPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = 'Continue'
    $lines = & $Executable @Arguments 2>&1
    $code = $LASTEXITCODE
  } finally { $ErrorActionPreference = $savedPreference }
  $lines | Out-File -LiteralPath (Join-Path $outputRoot ($Name + '.log')) -Encoding utf8
  $checks.Add([pscustomobject]@{name=$Name;executable=$Executable;arguments=$Arguments;exit=$code;expected=$Expected})
  Write-Host "$Name exit=$code expected=$Expected"
}
Push-Location $repoRoot
try {
  Push-Location (Join-Path $repoRoot 'sim-core')
  try { Invoke-Check 'build' 'node' @('node_modules/typescript/bin/tsc','-p','tsconfig.json') }
  finally { Pop-Location }
  if ($checks[0].exit -ne 0) { throw 'Build failed; inspect the new build log.' }
  foreach ($name in @('request_delivery_ledger','request_emission_trace','original_owner_provider','env_manager','pipeline_integration','settling','pipeline_episode_stop_repair','perspective_knowledge_source','active_request_restore','public_move_history','replay_import','original_owner_provider_characterization','perspective_replay_characterization')) {
    Invoke-Check $name 'node' @('--test', "sim-core/dist/tests/$name.test.js")
  }
  Invoke-Check 'episode-cleanup' 'node' @('--test','--test-name-pattern=initialization failure|invalid budgets/policy|invalid continuation|cleanup preserves','sim-core/dist/tests/pipeline_episode.test.js')
  Invoke-Check 'loader' $pythonExe @('-m','unittest','discover','-s','trainer/tests','-p','test_local_replay_html_transport.py','-v')
  Invoke-Check 'python-characterization' $pythonExe @('-m','unittest','discover','-s','trainer/tests','-p','test_perspective_replay_characterization.py','-v')
  $env:PERSPECTIVE_REPLAY_REQUIREMENTS = '1'
  Invoke-Check 'ts-requirements' 'node' @('--test','sim-core/dist/tests/perspective_replay_characterization.test.js') 1
  Invoke-Check 'python-requirements' $pythonExe @('-m','unittest','discover','-s','trainer/tests','-p','test_perspective_replay_characterization.py','-v') 1
  Remove-Item Env:PERSPECTIVE_REPLAY_REQUIREMENTS
  Invoke-Check 'wire' 'node' @('docs/planning/perspective-fidelity-prompt25-wire.cjs','check')
} finally {
  Pop-Location
  Remove-Item Env:PERSPECTIVE_REPLAY_REQUIREMENTS -ErrorAction SilentlyContinue
  $checks | ConvertTo-Json -Depth 5 | Out-File -LiteralPath (Join-Path $outputRoot 'commands.json') -Encoding utf8
  Write-Host "Fresh evidence: $outputRoot"
}
if (@($checks | Where-Object {$_.exit -ne $_.expected}).Count) { exit 1 }
Write-Host 'Expected exits matched. Inspect requirement logs for the retained three failures; exit alone does not identify them.'

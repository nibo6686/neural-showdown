[CmdletBinding()]
param(
    [string]$PatchPath = 'C:\Users\cloud\Downloads\neural-stellar-review.patch',
    [string]$OutputPath = '',
    [string]$PythonExe = 'D:\Anaconda\envs\neuralgpu\python.exe',
    [string]$NodeExe = 'C:\Program Files\nodejs\node.exe',
    [string]$NpmCmd = 'C:\Program Files\nodejs\npm.cmd'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $repoRoot 'tests\fixtures\simulator_record_comparison_windows_v1.json'
}

Push-Location $repoRoot
try {
    $env:PYTHON = (Resolve-Path -LiteralPath $PythonExe).Path
    & $NpmCmd run build --prefix sim-core
    if ($LASTEXITCODE -ne 0) { throw "sim-core build failed with exit code $LASTEXITCODE" }
    & $NodeExe '.\sim-core\scripts\simulator-record-comparison.cjs' generate `
        --patch $PatchPath `
        --output $OutputPath
    if ($LASTEXITCODE -ne 0) { throw "comparison bundle generation failed with exit code $LASTEXITCODE" }
}
finally {
    Pop-Location
}

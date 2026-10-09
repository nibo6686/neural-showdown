[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$PatchPath,
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

if (-not (Test-Path -LiteralPath $PatchPath -PathType Leaf)) {
    throw 'Review patch not found. Supply -PatchPath with an existing review patch file.'
}
$PatchPath = (Resolve-Path -LiteralPath $PatchPath).Path
foreach ($requirement in @(
    @{ Name = 'PythonExe'; Path = $PythonExe },
    @{ Name = 'NodeExe'; Path = $NodeExe },
    @{ Name = 'NpmCmd'; Path = $NpmCmd }
)) {
    if (-not (Test-Path -LiteralPath $requirement.Path -PathType Leaf)) {
        throw "Required executable unavailable. Supply -$($requirement.Name) with an existing executable from the documented selected environment. See docs/refactor/WINDOWS-SIMULATOR-RECORD-VALIDATION-2026-09-25.md."
    }
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

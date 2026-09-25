[CmdletBinding()]
param(
    [string]$PatchPath = (Join-Path $PSScriptRoot '..\neural-stellar-review.patch'),
    [string]$PythonExe = 'D:\Anaconda\envs\neuralgpu\python.exe',
    [string]$NodeExe = 'C:\Program Files\nodejs\node.exe',
    [string]$NpmCmd = 'C:\Program Files\nodejs\npm.cmd'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$expectedBase = '3ddc5fc3060e8da287425e4d08a71a2ffd77184a'
$expectedPatchHash = '968e3f9318e6b67e6585afec1c74e1f4442ef875a11fd47164eb6e71f0140018'
$transferredReviewDigest = '4db82b9bc57984bf051f03b201bf022e0744ba03c8840239adeded5d362f33c3'
$failed = $false

function Test-GitApply {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $previousErrorPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & git @Arguments 2>$null
        return $LASTEXITCODE -eq 0
    }
    finally {
        $ErrorActionPreference = $previousErrorPreference
    }
}

function Invoke-ValidationStep {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][scriptblock]$Command
    )
    Write-Host "step=$Name status=running"
    & $Command
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        $script:failed = $true
        Write-Host "step=$Name status=failed exit_code=$exitCode"
    }
    else {
        Write-Host "step=$Name status=passed exit_code=0"
    }
}

Push-Location $repoRoot
try {
    foreach ($executable in @($PythonExe, $NodeExe, $NpmCmd)) {
        if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
            throw "Required executable not found: $executable"
        }
    }

    $head = (git rev-parse HEAD).Trim()
    Write-Host "base_commit=$head expected=$expectedBase"
    if ($head -ne $expectedBase) {
        Write-Host 'base_commit_status=failed'
        $failed = $true
    }
    else {
        Write-Host 'base_commit_status=passed'
    }

    if (Test-Path -LiteralPath $PatchPath -PathType Leaf) {
        $actualPatchHash = (Get-FileHash -LiteralPath $PatchPath -Algorithm SHA256).Hash.ToLowerInvariant()
        Write-Host "patch=$((Resolve-Path -LiteralPath $PatchPath).Path) sha256=$actualPatchHash"
        if ($actualPatchHash -ne $expectedPatchHash) {
            Write-Host "patch_hash_status=failed expected=$expectedPatchHash"
            $failed = $true
        }
        else {
            Write-Host 'patch_hash_status=passed'
            if (Test-GitApply @('apply', '--reverse', '--check', '--', $PatchPath)) {
                Write-Host 'patch_state=already_applied'
            }
            elseif (Test-GitApply @(
                'apply', '--reverse', '--check',
                '--exclude=sim-core/simulator_coverage/pokemon-showdown-0.11.10-gen9randombattle.json',
                '--', $PatchPath
            )) {
                $coverageManifest = Get-Content -Raw '.\sim-core\simulator_coverage\pokemon-showdown-0.11.10-gen9randombattle.json' | ConvertFrom-Json
                $localCoverage = $coverageManifest.local_coverage_sources
                $knownReviewDigests = @($localCoverage.sha256, $localCoverage.reviewed_sha256, $localCoverage.prior_reviewed_sha256)
                if ($localCoverage.files -contains 'src/battle_helpers.ts' -and $knownReviewDigests -contains $transferredReviewDigest) {
                    Write-Host 'patch_state=already_applied_with_subsequent_reviewed_manifest_changes'
                }
                else {
                    Write-Host 'patch_state=partial_or_unrecognized'
                    $failed = $true
                }
            }
            else {
                if (Test-GitApply @('apply', '--check', '--', $PatchPath)) {
                    Write-Host 'patch_state=not_applied'
                    $failed = $true
                }
                else {
                    Write-Host 'patch_state=does_not_apply_cleanly'
                    $failed = $true
                }
            }
        }
    }
    else {
        Write-Host "patch_state=missing path=$PatchPath"
        $failed = $true
    }

    cmd.exe /c ver
    & $PythonExe --version
    & $NodeExe --version
    & $NpmCmd --version
    & $PythonExe -c "from importlib.metadata import version; print('pytest='+version('pytest'))"

    Invoke-ValidationStep -Name 'npm-ci' { & $NpmCmd ci --prefix sim-core --no-audit --no-fund }
    Invoke-ValidationStep -Name 'sim-core-build' { & $NpmCmd run build --prefix sim-core }

    $env:PYTHON = $PythonExe
    $env:PYTHONPATH = (Resolve-Path '.\trainer\src').Path
    Invoke-ValidationStep -Name 'focused-typescript' {
        & $NodeExe --test `
            sim-core/dist/tests/transition.test.js `
            sim-core/dist/tests/forced_switch.test.js `
            sim-core/dist/tests/settling.test.js `
            sim-core/dist/tests/pipeline_integration.test.js `
            sim-core/dist/tests/pipeline_episode.test.js `
            sim-core/dist/tests/simulator_coverage.test.js `
            sim-core/dist/tests/illusion.test.js
    }
    Invoke-ValidationStep -Name 'focused-python' {
        & $PythonExe -m pytest `
            trainer/tests/test_pipeline_record.py `
            trainer/tests/test_dataset_lineage.py -q
    }
    Invoke-ValidationStep -Name 'coverage' { & $NpmCmd run check:simulator-coverage --prefix sim-core }
    Invoke-ValidationStep -Name 'coverage-self-test' { & $NodeExe sim-core/scripts/check-simulator-coverage.cjs --self-test }

    if ($failed) {
        Write-Host 'validation_result=failed'
        exit 1
    }
    Write-Host 'validation_result=passed'
}
finally {
    Pop-Location
}

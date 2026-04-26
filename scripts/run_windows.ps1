[CmdletBinding()]
param(
    [ValidateSet('setup', 'build', 'test', 'dataset', 'train', 'ppo', 'eval', 'improve', 'analyze', 'trace-eval', 'all', 'server')]
    [string]$Action = 'all',
    [ValidateSet('dev', 'full')]
    [string]$Profile = 'dev',
    [ValidateSet('auto', 'native', 'wsl')]
    [string]$SimCoreMode = 'auto',
    [string]$PythonExe = 'D:\Anaconda\envs\neuralgpu\python.exe',
    [string]$NodeExe = '',
    [string]$NpmCmd = '',
    [string]$DatasetConfig = '',
    [string]$EvalConfig = '',
    [string]$DatasetPath = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$simCoreDir = (Resolve-Path (Join-Path $repoRoot 'sim-core')).Path
$trainerSrc = (Resolve-Path (Join-Path $repoRoot 'trainer\src')).Path
$env:PYTHONPATH = $trainerSrc
$previousSimCoreCommand = [Environment]::GetEnvironmentVariable('NEURAL_SIM_CORE_COMMAND_JSON', 'Process')
$previousSimCoreCwd = [Environment]::GetEnvironmentVariable('NEURAL_SIM_CORE_CWD', 'Process')

function Resolve-DefaultConfig {
    param(
        [Parameter(Mandatory = $true)][ValidateSet('dataset', 'eval')][string]$Kind,
        [Parameter(Mandatory = $true)][ValidateSet('dev', 'full')][string]$SelectedProfile
    )

    if ($Kind -eq 'dataset') {
        if ($SelectedProfile -eq 'dev') {
            return '.\configs\gen9randombattle_bc.dev.windows.yaml'
        }
        return '.\configs\gen9randombattle_bc.windows.yaml'
    }

    if ($SelectedProfile -eq 'dev') {
        return '.\configs\gen9randombattle_eval.dev.windows.yaml'
    }
    return '.\configs\gen9randombattle_eval.windows.yaml'
}

if ([string]::IsNullOrWhiteSpace($DatasetConfig)) {
    $DatasetConfig = Resolve-DefaultConfig -Kind 'dataset' -SelectedProfile $Profile
}
if ([string]::IsNullOrWhiteSpace($EvalConfig)) {
    $EvalConfig = Resolve-DefaultConfig -Kind 'eval' -SelectedProfile $Profile
}

function Resolve-Executable {
    param(
        [string]$PreferredPath = '',
        [string[]]$CommandNames = @(),
        [string[]]$CandidatePaths = @()
    )

    if (-not [string]::IsNullOrWhiteSpace($PreferredPath)) {
        $resolvedPreferred = (Resolve-Path $PreferredPath -ErrorAction SilentlyContinue)
        if ($resolvedPreferred) {
            return $resolvedPreferred.Path
        }
        throw "Executable not found: $PreferredPath"
    }

    foreach ($commandName in $CommandNames) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($command) {
            return $command.Source
        }
    }

    foreach ($candidatePath in $CandidatePaths) {
        if ([string]::IsNullOrWhiteSpace($candidatePath)) {
            continue
        }
        $resolvedCandidate = Resolve-Path $candidatePath -ErrorAction SilentlyContinue
        if ($resolvedCandidate) {
            return $resolvedCandidate.Path
        }
    }

    return $null
}

function Get-NativeNodeTools {
    $candidateRoots = @(
        $env:ProgramFiles,
        [Environment]::GetFolderPath('ProgramFilesX86'),
        (Join-Path $env:LOCALAPPDATA 'Programs\nodejs')
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

    $nodeCandidates = @()
    $npmCandidates = @()
    foreach ($root in $candidateRoots) {
        if (Test-Path $root) {
            $nodeCandidates += (Join-Path $root 'node.exe')
            $npmCandidates += (Join-Path $root 'npm.cmd')
        }
    }

    $resolvedNode = Resolve-Executable -PreferredPath $NodeExe -CommandNames @('node.exe', 'node') -CandidatePaths $nodeCandidates
    $resolvedNpm = Resolve-Executable -PreferredPath $NpmCmd -CommandNames @('npm.cmd', 'npm') -CandidatePaths $npmCandidates

    if ($resolvedNode -and $resolvedNpm) {
        return @{
            Mode = 'native'
            Node = $resolvedNode
            Npm = $resolvedNpm
        }
    }

    return $null
}

function Get-WslPath {
    param([Parameter(Mandatory = $true)][string]$WindowsPath)
    $resolved = (Resolve-Path $WindowsPath).Path
    $normalized = $resolved -replace '\\', '/'
    return (wsl wslpath -a $normalized).Trim()
}

function Test-WslAvailable {
    return $null -ne (Get-Command wsl -ErrorAction SilentlyContinue | Select-Object -First 1)
}

function Resolve-SimCoreRuntime {
    $nativeTools = Get-NativeNodeTools

    switch ($SimCoreMode) {
        'native' {
            if (-not $nativeTools) {
                throw 'Native sim-core mode requires Windows node/npm. Set -NodeExe and -NpmCmd, or add them to PATH.'
            }
            return $nativeTools
        }
        'wsl' {
            if (-not (Test-WslAvailable)) {
                throw 'WSL is not available, so sim-core cannot be started in wsl mode.'
            }
            return @{ Mode = 'wsl' }
        }
        default {
            if ($nativeTools) {
                return $nativeTools
            }
            if (Test-WslAvailable) {
                return @{ Mode = 'wsl' }
            }
            throw 'Neither native Windows node/npm nor WSL is available for sim-core.'
        }
    }
}

$script:SimCoreRuntime = Resolve-SimCoreRuntime

function Invoke-WslSimCoreShell {
    param([Parameter(Mandatory = $true)][string]$Command)
    $wslRepoRoot = Get-WslPath -WindowsPath $repoRoot
    wsl bash -lc "cd '$wslRepoRoot/sim-core' && $Command"
    if ($LASTEXITCODE -ne 0) {
        throw "WSL command failed: $Command"
    }
}

function Invoke-SimCoreNpm {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    if ($script:SimCoreRuntime.Mode -eq 'native') {
        Push-Location $simCoreDir
        try {
            & $script:SimCoreRuntime.Npm @Arguments
            if ($LASTEXITCODE -ne 0) {
                throw "npm command failed: $($Arguments -join ' ')"
            }
            return
        }
        finally {
            Pop-Location
        }
    }

    Invoke-WslSimCoreShell -Command ("npm " + ($Arguments -join ' '))
}

function Invoke-SimCoreNode {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    if ($script:SimCoreRuntime.Mode -eq 'native') {
        Push-Location $simCoreDir
        try {
            & $script:SimCoreRuntime.Node @Arguments
            if ($LASTEXITCODE -ne 0) {
                throw "node command failed: $($Arguments -join ' ')"
            }
            return
        }
        finally {
            Pop-Location
        }
    }

    Invoke-WslSimCoreShell -Command ("node " + ($Arguments -join ' '))
}

function Set-SimCoreProcessEnv {
    if ($script:SimCoreRuntime.Mode -eq 'native') {
        $command = @($script:SimCoreRuntime.Node, 'dist/src/server.js')
        $cwd = $simCoreDir
    }
    else {
        $wslRepoRoot = Get-WslPath -WindowsPath $repoRoot
        $command = @('wsl', 'bash', '-lc', "cd '$wslRepoRoot/sim-core' && node dist/src/server.js")
        $cwd = $repoRoot
    }

    $env:NEURAL_SIM_CORE_COMMAND_JSON = ConvertTo-Json $command -Compress
    $env:NEURAL_SIM_CORE_CWD = $cwd
}

function Restore-SimCoreProcessEnv {
    if ($null -eq $previousSimCoreCommand) {
        Remove-Item Env:NEURAL_SIM_CORE_COMMAND_JSON -ErrorAction SilentlyContinue
    }
    else {
        $env:NEURAL_SIM_CORE_COMMAND_JSON = $previousSimCoreCommand
    }

    if ($null -eq $previousSimCoreCwd) {
        Remove-Item Env:NEURAL_SIM_CORE_CWD -ErrorAction SilentlyContinue
    }
    else {
        $env:NEURAL_SIM_CORE_CWD = $previousSimCoreCwd
    }
}

function Invoke-PythonModule {
    param(
        [Parameter(Mandatory = $true)][string]$Module,
        [string[]]$Arguments = @()
    )
    Set-SimCoreProcessEnv
    & $PythonExe -m $Module @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python module failed: $Module"
    }
}

function Invoke-Setup {
    Write-Host "launcher setup profile=$Profile sim_core=$($script:SimCoreRuntime.Mode)"
    Invoke-SimCoreNpm -Arguments @('install')
    Invoke-SimCoreNpm -Arguments @('run', 'build')
}

function Invoke-Build {
    Write-Host "launcher build profile=$Profile sim_core=$($script:SimCoreRuntime.Mode)"
    Invoke-SimCoreNpm -Arguments @('run', 'build')
}

function Ensure-SimCoreBuilt {
    $serverBundle = Join-Path $repoRoot 'sim-core\dist\src\server.js'
    if (-not (Test-Path $serverBundle)) {
        Invoke-Build
        return
    }

    $newestSource = Get-ChildItem -Path (Join-Path $repoRoot 'sim-core\src') -Recurse -Filter '*.ts' |
        Sort-Object LastWriteTimeUtc -Descending |
        Select-Object -First 1
    $bundleItem = Get-Item $serverBundle
    if ($newestSource -and $newestSource.LastWriteTimeUtc -gt $bundleItem.LastWriteTimeUtc) {
        Invoke-Build
    }
}

function Invoke-Test {
    Write-Host "launcher test profile=$Profile sim_core=$($script:SimCoreRuntime.Mode)"
    Invoke-PythonModule -Module 'unittest' -Arguments @('discover', '-s', '.\trainer\tests')
    Invoke-SimCoreNpm -Arguments @('test')
}

function Invoke-Dataset {
    Ensure-SimCoreBuilt
    Write-Host "launcher dataset | profile=$Profile sim_core=$($script:SimCoreRuntime.Mode) config=$DatasetConfig"
    Invoke-PythonModule -Module 'neural.build_dataset' -Arguments @('--config', $DatasetConfig)
}

function Invoke-Train {
    Write-Host "launcher train profile=$Profile config=$DatasetConfig"
    Invoke-PythonModule -Module 'neural.train_bc' -Arguments @('--config', $DatasetConfig)
}

function Invoke-Ppo {
    Ensure-SimCoreBuilt
    Write-Host "launcher ppo | profile=$Profile sim_core=$($script:SimCoreRuntime.Mode) config=$DatasetConfig"
    Invoke-PythonModule -Module 'neural.train_ppo' -Arguments @('--config', $DatasetConfig)
}

function Invoke-Eval {
    Ensure-SimCoreBuilt
    Write-Host "launcher eval | profile=$Profile sim_core=$($script:SimCoreRuntime.Mode) config=$EvalConfig"
    Invoke-PythonModule -Module 'neural.eval' -Arguments @('--config', $EvalConfig)
}

function Invoke-Improve {
    Ensure-SimCoreBuilt
    Write-Host "launcher improve | profile=$Profile sim_core=$($script:SimCoreRuntime.Mode) config=$DatasetConfig"
    Invoke-PythonModule -Module 'neural.improve_loop' -Arguments @('--config', $DatasetConfig)
}

function Invoke-Server {
    Ensure-SimCoreBuilt
    Write-Host "launcher server profile=$Profile sim_core=$($script:SimCoreRuntime.Mode)"
    Invoke-SimCoreNode -Arguments @('dist/src/server.js')
}

function Invoke-Analyze {
    Write-Host "launcher analyze | analyzing dataset"
    $inputPath = if ([string]::IsNullOrWhiteSpace($DatasetPath)) { '.\data\raw\gen9randombattle_bc.jsonl.gz' } else { $DatasetPath }
    $outputDir = '.\artifacts\analysis'
    Invoke-PythonModule -Module 'neural.analyze_decisions' -Arguments @('--input', $inputPath, '--output', $outputDir)
}

function Invoke-TraceEval {
    Ensure-SimCoreBuilt
    Write-Host "launcher trace-eval | profile=$Profile sim_core=$($script:SimCoreRuntime.Mode)"
    $traceConfig = '.\configs\gen9randombattle_eval.trace.windows.yaml'
    Invoke-PythonModule -Module 'neural.eval' -Arguments @('--config', $traceConfig)
}

Push-Location $repoRoot
try {
    if (-not (Test-Path $PythonExe)) {
        throw "Python executable not found: $PythonExe"
    }

    switch ($Action) {
        'setup' { Invoke-Setup }
        'build' { Invoke-Build }
        'test' { Invoke-Test }
        'dataset' { Invoke-Dataset }
        'train' { Invoke-Train }
        'ppo' { Invoke-Ppo }
        'eval' { Invoke-Eval }
        'improve' { Invoke-Improve }
        'server' { Invoke-Server }
        'analyze' { Invoke-Analyze }
        'trace-eval' { Invoke-TraceEval }
        'all' {
            Write-Host "launcher all | profile=$Profile sim_core=$($script:SimCoreRuntime.Mode)"
            Ensure-SimCoreBuilt
            Invoke-Dataset
            Invoke-Train
            Invoke-Eval
            Write-Host "launcher all | completed profile=$Profile sim_core=$($script:SimCoreRuntime.Mode) checkpoint=$(Resolve-Path '.\artifacts\checkpoints\').Path"
        }
    }
}
finally {
    Restore-SimCoreProcessEnv
    Pop-Location
}

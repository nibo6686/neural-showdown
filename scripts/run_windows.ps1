[CmdletBinding()]
param(
    [ValidateSet('setup', 'build', 'test', 'dataset', 'train', 'ppo', 'eval', 'improve', 'analyze', 'trace-eval', 'build-value-dataset', 'train-value', 'train-replay-value', 'build-live-private-value-dataset', 'build-live-private-value-dataset-v2', 'train-live-private-value', 'train-live-private-value-v2', 'compare-value-models', 'compare-replay-evals', 'test-live-eval', 'live-eval', 'build-action-rank-dataset', 'build-action-rank-dataset-v2', 'train-action-ranker', 'train-action-ranker-v2', 'build-action-value-dataset', 'train-action-value-ranker', 'compare-action-rankers', 'analyze-action-bias', 'analyze-tactical-failures', 'analyze-state', 'collect-selfplay', 'compare-checkpoints', 'fetch-replays', 'parse-replays', 'build-replay-value-dataset', 'build-replay-policy-dataset', 'all', 'server', 'analyze-rollout-actions', 'test-sim-rollout')]
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
    [string]$DatasetPath = '',
    [string]$TraceDir = '',
    [string]$TracePath = '',
    [int]$StepIndex = 0,
    [string]$ValueCheckpoint = '',
    [string]$PolicyCheckpoint = '',
    [string]$Format = 'gen9randombattle',
    [int]$MaxReplays = 1000,
    [string]$ReplayDir = '',
    [string]$ReplayId = 'gen9randombattle-2594788118',
    [string]$ReplayPath = '',
    [ValidateSet('p1', 'p2')]
    [string]$Side = 'p1',
    [ValidateSet('auto', 'exact', 'approximate')]
    [string]$RolloutMode = 'auto',
    [int]$Epochs = 0,
    [int]$MaxTrainGroups = 0,
    [int]$MaxValGroups = 0,
    [switch]$Resume,
    [switch]$TrainForever,
    [double]$DelaySec = 0.5
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

function Invoke-AnalyzeRolloutActions {
    Write-Host "launcher analyze-rollout-actions | replay=$ReplayPath side=$Side"
    $args = @('--replay-path', $ReplayPath, '--side', $Side, '--rollout-mode', $RolloutMode)
    if ($StepIndex -gt 0) { $args += @('--step-index', [string]$StepIndex) }
    if (-not [string]::IsNullOrWhiteSpace($ValueCheckpoint)) { $args += @('--value-checkpoint', $ValueCheckpoint) }
    Invoke-PythonModule -Module 'neural.analyze_rollout_actions' -Arguments $args
}

function Invoke-TestSimRollout {
    Write-Host "launcher test-sim-rollout"
    Invoke-PythonModule -Module 'neural.test_sim_rollout'
}

function Invoke-TraceEval {
    Ensure-SimCoreBuilt
    Write-Host "launcher trace-eval | profile=$Profile sim_core=$($script:SimCoreRuntime.Mode)"
    $traceConfig = '.\configs\gen9randombattle_eval.trace.windows.yaml'
    Invoke-PythonModule -Module 'neural.eval' -Arguments @('--config', $traceConfig)
}

function Invoke-BuildValueDataset {
    $selectedTraceDir = if ([string]::IsNullOrWhiteSpace($TraceDir)) { '.\artifacts\battles\dev' } else { $TraceDir }
    Write-Host "launcher build-value-dataset | trace_dir=$selectedTraceDir"
    Invoke-PythonModule -Module 'neural.build_value_dataset' -Arguments @('--trace-dir', $selectedTraceDir)
}

function Invoke-TrainValue {
    $selectedDatasetPath = if ([string]::IsNullOrWhiteSpace($DatasetPath)) { '.\data\value\gen9randombattle_value.npz' } else { $DatasetPath }
    Write-Host "launcher train-value | dataset=$selectedDatasetPath"
    Invoke-PythonModule -Module 'neural.train_value' -Arguments @('--dataset-path', $selectedDatasetPath)
}

function Invoke-AnalyzeState {
    $selectedTracePath = if ([string]::IsNullOrWhiteSpace($TracePath)) { '.\artifacts\battles\dev\battle_0.json' } else { $TracePath }
    $selectedValueCheckpoint = if ([string]::IsNullOrWhiteSpace($ValueCheckpoint)) { '.\artifacts\checkpoints\gen9randombattle_value.pt' } else { $ValueCheckpoint }
    $arguments = @('--trace-path', $selectedTracePath, '--step-index', [string]$StepIndex, '--value-checkpoint', $selectedValueCheckpoint)
    if (-not [string]::IsNullOrWhiteSpace($PolicyCheckpoint)) {
        $arguments += @('--policy-checkpoint', $PolicyCheckpoint)
    }
    Write-Host "launcher analyze-state | trace=$selectedTracePath step=$StepIndex value=$selectedValueCheckpoint"
    Invoke-PythonModule -Module 'neural.analyze_state' -Arguments $arguments
}

function Invoke-CollectSelfplay {
    Ensure-SimCoreBuilt
    Write-Host "launcher collect-selfplay | profile=$Profile sim_core=$($script:SimCoreRuntime.Mode) config=$DatasetConfig"
    Invoke-PythonModule -Module 'neural.collect_selfplay' -Arguments @('--config', $DatasetConfig)
}

function Invoke-CompareCheckpoints {
    Ensure-SimCoreBuilt
    Write-Host "launcher compare-checkpoints | profile=$Profile sim_core=$($script:SimCoreRuntime.Mode) config=$DatasetConfig"
    Invoke-PythonModule -Module 'neural.compare_checkpoints' -Arguments @('--config', $DatasetConfig)
}

function Resolve-ReplayDir {
    if ([string]::IsNullOrWhiteSpace($ReplayDir)) {
        return ".\data\replays\raw\$Format"
    }
    return $ReplayDir
}

function Invoke-FetchReplays {
    $selectedReplayDir = Resolve-ReplayDir
    Write-Host "launcher fetch-replays | format=$Format max_replays=$MaxReplays out_dir=$selectedReplayDir delay_sec=$DelaySec"
    Invoke-PythonModule -Module 'neural.replay_fetch' -Arguments @(
        '--format', $Format,
        '--max-replays', [string]$MaxReplays,
        '--out-dir', $selectedReplayDir,
        '--delay-sec', [string]$DelaySec
    )
}

function Invoke-ParseReplays {
    $selectedReplayDir = Resolve-ReplayDir
    Write-Host "launcher parse-replays | format=$Format replay_dir=$selectedReplayDir"
    Invoke-PythonModule -Module 'neural.parse_replay_logs' -Arguments @(
        '--format', $Format,
        '--replay-dir', $selectedReplayDir
    )
}

function Invoke-BuildReplayValueDataset {
    $selectedReplayDir = Resolve-ReplayDir
    Write-Host "launcher build-replay-value-dataset | format=$Format replay_dir=$selectedReplayDir"
    Invoke-PythonModule -Module 'neural.build_replay_value_dataset' -Arguments @(
        '--format', $Format,
        '--replay-dir', $selectedReplayDir
    )
}

function Invoke-BuildReplayPolicyDataset {
    $selectedReplayDir = Resolve-ReplayDir
    Write-Host "launcher build-replay-policy-dataset | format=$Format replay_dir=$selectedReplayDir"
    Invoke-PythonModule -Module 'neural.build_replay_policy_dataset' -Arguments @(
        '--format', $Format,
        '--replay-dir', $selectedReplayDir
    )
}

function Invoke-TrainReplayValue {
    $selectedDatasetPath = if ([string]::IsNullOrWhiteSpace($DatasetPath)) { ".\data\value\${Format}_public_replay_value.npz" } else { $DatasetPath }
    Write-Host "launcher train-replay-value | dataset=$selectedDatasetPath"
    Invoke-PythonModule -Module 'neural.train_replay_value' -Arguments @('--dataset-path', $selectedDatasetPath)
}

function Invoke-BuildLivePrivateValueDataset {
    $selectedReplayDir = Resolve-ReplayDir
    Write-Host "launcher build-live-private-value-dataset | format=$Format replay_dir=$selectedReplayDir"
    Invoke-PythonModule -Module 'neural.build_live_private_value_dataset' -Arguments @(
        '--format', $Format,
        '--replay-dir', $selectedReplayDir,
        '--output', ".\data\value\${Format}_live_private_value_v2.npz"
    )
}

function Invoke-TrainLivePrivateValue {
    $selectedDatasetPath = if ([string]::IsNullOrWhiteSpace($DatasetPath)) { ".\data\value\${Format}_live_private_value_v2.npz" } else { $DatasetPath }
    Write-Host "launcher train-live-private-value | dataset=$selectedDatasetPath"
    Invoke-PythonModule -Module 'neural.train_live_private_value' -Arguments @('--dataset-path', $selectedDatasetPath, '--checkpoint-path', ".\artifacts\checkpoints\${Format}_live_private_value_v2.pt")
}

function Invoke-CompareValueModels {
    Write-Host "launcher compare-value-models"
    Invoke-PythonModule -Module 'neural.compare_value_models'
}

function Invoke-TestLiveEval {
    Write-Host "launcher test-live-eval"
    Invoke-PythonModule -Module 'neural.test_live_eval_payload'
}

function Invoke-CompareReplayEvals {
    Write-Host "launcher compare-replay-evals | replay=$ReplayId side=$Side"
    Invoke-PythonModule -Module 'neural.compare_replay_evals' -Arguments @(
        '--replay-id', $ReplayId,
        '--side', $Side
    )
}

function Invoke-LiveEval {
    Write-Host "launcher live-eval"
    Invoke-PythonModule -Module 'neural.live_eval_server'
}

function Invoke-BuildActionRankDataset {
    $selectedReplayDir = Resolve-ReplayDir
    Write-Host "launcher build-action-rank-dataset | format=$Format replay_dir=$selectedReplayDir"
    Invoke-PythonModule -Module 'neural.build_action_rank_dataset' -Arguments @(
        '--format', $Format,
        '--replay-dir', $selectedReplayDir,
        '--output', ".\data\policy\${Format}_action_rank_v2.npz"
    )
}

function Invoke-TrainActionRanker {
    $selectedDatasetPath = if ([string]::IsNullOrWhiteSpace($DatasetPath)) { ".\data\policy\${Format}_action_rank_v2.npz" } else { $DatasetPath }
    $selectedCheckpointPath = ".\artifacts\checkpoints\${Format}_action_ranker_v2.pt"
    $arguments = @('--dataset-path', $selectedDatasetPath, '--checkpoint-path', $selectedCheckpointPath)
    if ($Epochs -gt 0) {
        $arguments += @('--epochs', [string]$Epochs)
    }
    if ($MaxTrainGroups -gt 0) {
        $arguments += @('--max-train-groups', [string]$MaxTrainGroups)
    }
    if ($MaxValGroups -gt 0) {
        $arguments += @('--max-val-groups', [string]$MaxValGroups)
    }
    if ($Resume) {
        if (Test-Path $selectedCheckpointPath) {
            $arguments += @('--resume-checkpoint', $selectedCheckpointPath)
        }
        else {
            Write-Host "launcher train-action-ranker | resume requested but checkpoint is missing; starting fresh checkpoint=$selectedCheckpointPath"
        }
    }
    if ($TrainForever) {
        $arguments += @('--train-forever')
    }
    $arguments += @('--save-every-epochs', '1')
    Write-Host "launcher train-action-ranker | dataset=$selectedDatasetPath"
    Invoke-PythonModule -Module 'neural.train_action_ranker' -Arguments $arguments
}

function Invoke-BuildActionValueDataset {
    $selectedReplayDir = Resolve-ReplayDir
    Write-Host "launcher build-action-value-dataset | format=$Format replay_dir=$selectedReplayDir"
    Invoke-PythonModule -Module 'neural.build_action_value_dataset' -Arguments @(
        '--format', $Format,
        '--replay-dir', $selectedReplayDir,
        '--output', ".\data\policy\${Format}_action_value_rank_v2.npz",
        '--value-checkpoint', ".\artifacts\checkpoints\${Format}_live_private_value_v2.pt"
    )
}

function Invoke-TrainActionValueRanker {
    $selectedDatasetPath = if ([string]::IsNullOrWhiteSpace($DatasetPath)) { ".\data\policy\${Format}_action_value_rank_v2.npz" } else { $DatasetPath }
    $selectedCheckpointPath = ".\artifacts\checkpoints\${Format}_action_value_ranker_v2.pt"
    $arguments = @(
        '--dataset-path', $selectedDatasetPath,
        '--checkpoint-path', $selectedCheckpointPath,
        '--init-checkpoint', ".\artifacts\checkpoints\${Format}_action_ranker_v2.pt"
    )
    if ($Epochs -gt 0) {
        $arguments += @('--epochs', [string]$Epochs)
    }
    if ($MaxTrainGroups -gt 0) {
        $arguments += @('--max-train-groups', [string]$MaxTrainGroups)
    }
    if ($MaxValGroups -gt 0) {
        $arguments += @('--max-val-groups', [string]$MaxValGroups)
    }
    $arguments += @('--save-every-epochs', '1')
    Write-Host "launcher train-action-value-ranker | dataset=$selectedDatasetPath"
    Invoke-PythonModule -Module 'neural.train_action_value_ranker' -Arguments $arguments
}

function Invoke-CompareActionRankers {
    $selectedReplay = if ([string]::IsNullOrWhiteSpace($ReplayPath)) { $ReplayId } else { $ReplayPath }
    Write-Host "launcher compare-action-rankers | replay=$selectedReplay side=$Side"
    Invoke-PythonModule -Module 'neural.compare_action_rankers' -Arguments @(
        '--replay-path', $selectedReplay,
        '--side', $Side,
        '--replay-dir', (Resolve-ReplayDir),
        '--v1-ranker', ".\artifacts\checkpoints\${Format}_action_ranker.pt",
        '--v2-ranker', ".\artifacts\checkpoints\${Format}_action_ranker_v2.pt",
        '--value-ranker', ".\artifacts\checkpoints\${Format}_action_value_ranker_v2.pt"
    )
}

function Invoke-AnalyzeTacticalFailures {
    Write-Host "launcher analyze-tactical-failures | replay=$ReplayId side=$Side"
    Invoke-PythonModule -Module 'neural.analyze_tactical_failures' -Arguments @(
        '--replay-id', $ReplayId,
        '--side', $Side,
        '--replay-dir', (Resolve-ReplayDir),
        '--ranker-checkpoint', ".\artifacts\checkpoints\${Format}_action_ranker_v2.pt"
    )
}

function Invoke-AnalyzeActionBias {
    $selectedDatasetPath = if ([string]::IsNullOrWhiteSpace($DatasetPath)) { ".\data\policy\${Format}_action_rank.npz" } else { $DatasetPath }
    Write-Host "launcher analyze-action-bias | dataset=$selectedDatasetPath"
    Invoke-PythonModule -Module 'neural.analyze_action_bias' -Arguments @('--dataset-path', $selectedDatasetPath)
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
        'build-value-dataset' { Invoke-BuildValueDataset }
        'train-value' { Invoke-TrainValue }
        'train-replay-value' { Invoke-TrainReplayValue }
        'build-live-private-value-dataset' { Invoke-BuildLivePrivateValueDataset }
        'build-live-private-value-dataset-v2' { Invoke-BuildLivePrivateValueDataset }
        'train-live-private-value' { Invoke-TrainLivePrivateValue }
        'train-live-private-value-v2' { Invoke-TrainLivePrivateValue }
        'compare-value-models' { Invoke-CompareValueModels }
        'compare-replay-evals' { Invoke-CompareReplayEvals }
        'test-live-eval' { Invoke-TestLiveEval }
        'live-eval' { Invoke-LiveEval }
        'build-action-rank-dataset' { Invoke-BuildActionRankDataset }
        'build-action-rank-dataset-v2' { Invoke-BuildActionRankDataset }
        'train-action-ranker' { Invoke-TrainActionRanker }
        'train-action-ranker-v2' { Invoke-TrainActionRanker }
        'build-action-value-dataset' { Invoke-BuildActionValueDataset }
        'train-action-value-ranker' { Invoke-TrainActionValueRanker }
        'compare-action-rankers' { Invoke-CompareActionRankers }
        'analyze-action-bias' { Invoke-AnalyzeActionBias }
        'analyze-tactical-failures' { Invoke-AnalyzeTacticalFailures }
        'analyze-state' { Invoke-AnalyzeState }
        'collect-selfplay' { Invoke-CollectSelfplay }
        'compare-checkpoints' { Invoke-CompareCheckpoints }
        'fetch-replays' { Invoke-FetchReplays }
        'parse-replays' { Invoke-ParseReplays }
        'build-replay-value-dataset' { Invoke-BuildReplayValueDataset }
        'build-replay-policy-dataset' { Invoke-BuildReplayPolicyDataset }
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

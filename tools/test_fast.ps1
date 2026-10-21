#requires -Version 7.0
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$watch = [System.Diagnostics.Stopwatch]::StartNew()
$runs = @()
$shared = Join-Path ([System.IO.Path]::GetTempPath()) ('neural-fast-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $shared | Out-Null
function Start-Gate($name, $executable, $arguments, $directory) {
    $info = [System.Diagnostics.ProcessStartInfo]::new($executable)
    $info.WorkingDirectory = $directory
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $info.Environment['NEURAL_TEST_OUTPUT_DIR'] = $shared
    $info.Environment.Remove('PYTHONUTF8') | Out-Null
    $info.Environment.Remove('PYTHONIOENCODING') | Out-Null
    foreach ($argument in $arguments) { $info.ArgumentList.Add($argument) }
    $process = [System.Diagnostics.Process]::Start($info)
    return [pscustomobject]@{ Name = $name; Process = $process; Output = $process.StandardOutput.ReadToEndAsync(); Error = $process.StandardError.ReadToEndAsync() }
}
try {
    & node (Join-Path $repo 'sim-core/node_modules/typescript/bin/tsc') -p (Join-Path $repo 'sim-core/tsconfig.json')
    if ($LASTEXITCODE -ne 0) { exit 1 }
    $producer = Start-Gate 'Node producer' 'node' @('--test', '--test-timeout=25000', 'dist/tests/target_fidelity_eligibility.test.js') (Join-Path $repo 'sim-core')
    $runs += $producer
    if (-not $producer.Process.WaitForExit([Math]::Max(0,175000-[int]$watch.ElapsedMilliseconds))) { throw 'Node producer timed out' }
    if ($producer.Process.ExitCode -ne 0) { Write-Output $producer.Output.GetAwaiter().GetResult(); Write-Output $producer.Error.GetAwaiter().GetResult(); exit 1 }
    # Producer files are complete before the Python consumer starts.
    $runs += Start-Gate 'Node' $env:ComSpec @('/d', '/c', 'npm run test:fast') (Join-Path $repo 'sim-core')
    $runs += Start-Gate 'Python' (Get-Process -Id $PID).Path @('-NoProfile', '-File', (Join-Path $PSScriptRoot 'test_fast_py.ps1')) $repo
    $failed = $false
    foreach ($run in $runs) {
        $remaining = [Math]::Max(0, 175000 - [int]$watch.ElapsedMilliseconds)
        if (-not $run.Process.WaitForExit($remaining)) {
            $failed = $true
            foreach ($active in $runs) { if (-not $active.Process.HasExited) { $active.Process.Kill($true) } }
        }
        $run.Process.WaitForExit()
        Write-Output $run.Output.GetAwaiter().GetResult()
        $stderr = $run.Error.GetAwaiter().GetResult()
        if ($stderr) { [Console]::Error.WriteLine($stderr) }
        Write-Output ($run.Name + ' exit: ' + $run.Process.ExitCode)
        if ($run.Process.ExitCode -ne 0) { $failed = $true }
    }
    Write-Output ('Combined fast gate: {0:N2} seconds (175-second deadline)' -f $watch.Elapsed.TotalSeconds)
    if ($failed) { exit 1 }
    exit 0
} finally {
    foreach ($run in $runs) {
        if (-not $run.Process.HasExited) { $run.Process.Kill($true); $run.Process.WaitForExit() }
        $run.Process.Dispose()
    }
    $resolved = [System.IO.Path]::GetFullPath($shared)
    $tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
    if (-not $resolved.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected shared output path' }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}

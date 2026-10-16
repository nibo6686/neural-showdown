#requires -Version 7.0
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$watch = [System.Diagnostics.Stopwatch]::StartNew()
$runs = @()
function Start-Gate($name, $executable, $arguments, $directory) {
    $info = [System.Diagnostics.ProcessStartInfo]::new($executable)
    $info.WorkingDirectory = $directory
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $info.Environment.Remove('PYTHONUTF8') | Out-Null
    $info.Environment.Remove('PYTHONIOENCODING') | Out-Null
    foreach ($argument in $arguments) { $info.ArgumentList.Add($argument) }
    $process = [System.Diagnostics.Process]::Start($info)
    return [pscustomobject]@{ Name = $name; Process = $process; Output = $process.StandardOutput.ReadToEndAsync(); Error = $process.StandardError.ReadToEndAsync() }
}
try {
    # Both runtimes share one wall-clock budget; Node also runs its files in parallel.
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
}

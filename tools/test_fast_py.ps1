#requires -Version 7.0
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$files = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'test-fast-python-files.json') -Raw | ConvertFrom-Json).files
$slow = @('trainer/tests/test_perspective_knowledge.py', 'trainer/tests/test_pipeline_record.py')
$groups = @(@($slow[0]), @($slow[1]), @($files | Where-Object { $_ -notin $slow }))
$runs = @()
$watch = [System.Diagnostics.Stopwatch]::StartNew()
try {
    foreach ($group in $groups) {
        $info = [System.Diagnostics.ProcessStartInfo]::new('D:\Anaconda\envs\neuralgpu\python.exe')
        $info.UseShellExecute = $false
        $info.CreateNoWindow = $true
        $info.RedirectStandardOutput = $true
        $info.RedirectStandardError = $true
        $info.WorkingDirectory = $repo
        $info.Environment['PYTHONPATH'] = Join-Path $repo 'trainer/src'
        $info.Environment.Remove('PYTHONUTF8') | Out-Null
        $info.Environment.Remove('PYTHONIOENCODING') | Out-Null
        # Inherit NEURAL_TEST_OUTPUT_DIR after the outer gate's LIVE producer completes.
        foreach ($argument in (@('-m', 'pytest', '-q') + $group)) { $info.ArgumentList.Add($argument) }
        $process = [System.Diagnostics.Process]::Start($info)
        $runs += [pscustomobject]@{ Process = $process; Output = $process.StandardOutput.ReadToEndAsync(); Error = $process.StandardError.ReadToEndAsync() }
    }
    $failed = $false
    foreach ($run in $runs) {
        if (-not $run.Process.WaitForExit([Math]::Max(0, 175000 - [int]$watch.ElapsedMilliseconds))) { throw 'Python fast gate exceeded 175 seconds.' }
        Write-Output $run.Output.GetAwaiter().GetResult()
        $stderr = $run.Error.GetAwaiter().GetResult()
        if ($stderr) { [Console]::Error.WriteLine($stderr) }
        if ($run.Process.ExitCode -ne 0) { $failed = $true }
    }
    if ($failed) { exit 1 }
    exit 0
} finally {
    foreach ($run in $runs) {
        if (-not $run.Process.HasExited) { $run.Process.Kill($true); $run.Process.WaitForExit() }
        $run.Process.Dispose()
    }
}

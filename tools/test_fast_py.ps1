#requires -Version 7.0
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$files = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'test-fast-python-files.json') -Raw | ConvertFrom-Json).files
$info = [System.Diagnostics.ProcessStartInfo]::new('D:\Anaconda\envs\neuralgpu\python.exe')
$info.UseShellExecute = $false
$info.CreateNoWindow = $true
$info.RedirectStandardOutput = $true
$info.RedirectStandardError = $true
$info.WorkingDirectory = $repo
$info.Environment['PYTHONPATH'] = Join-Path $repo 'trainer/src'
$info.Environment.Remove('PYTHONUTF8') | Out-Null
$info.Environment.Remove('PYTHONIOENCODING') | Out-Null
foreach ($argument in (@('-m', 'pytest', '-q') + $files)) { $info.ArgumentList.Add($argument) }
$process = [System.Diagnostics.Process]::Start($info)
$output = $process.StandardOutput.ReadToEndAsync()
$errors = $process.StandardError.ReadToEndAsync()
try {
    if (-not $process.WaitForExit(175000)) {
        $process.Kill($true)
        $process.WaitForExit()
        Write-Error 'Python fast gate exceeded 175 seconds.'
    }
    Write-Output $output.GetAwaiter().GetResult()
    $stderr = $errors.GetAwaiter().GetResult()
    if ($stderr) { [Console]::Error.WriteLine($stderr) }
    exit $process.ExitCode
} finally {
    if (-not $process.HasExited) { $process.Kill($true); $process.WaitForExit() }
    $process.Dispose()
}

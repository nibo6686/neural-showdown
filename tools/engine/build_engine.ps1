#requires -Version 7.0
param(
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9a-f]{40}$')][string]$Commit,
    [string]$Checkout,
    [string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path "$PSScriptRoot/../..").Path
if (!$OutputDirectory) { $OutputDirectory = Join-Path $repo 'vendor' }
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
function Invoke-Bounded([string]$Executable, [string[]]$Arguments) {
    $info = [Diagnostics.ProcessStartInfo]::new($Executable)
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.WorkingDirectory = (Get-Location).Path
    foreach ($argument in $Arguments) { $info.ArgumentList.Add($argument) }
    $process = [Diagnostics.Process]::Start($info)
    try {
        if (!$process.WaitForExit(600000)) {
            $process.Kill($true)
            $process.WaitForExit()
            throw "$Executable exceeded 600 seconds"
        }
        if ($process.ExitCode) { throw "$Executable failed with exit $($process.ExitCode)" }
    } finally { $process.Dispose() }
}
if (!$Checkout) {
    $Checkout = Join-Path ([IO.Path]::GetTempPath()) ("showdown-build-" + [guid]::NewGuid())
    New-Item -ItemType Directory -Path $Checkout | Out-Null
    git -C $Checkout init --quiet
    Invoke-Bounded git @('-C', $Checkout, '-c', 'core.autocrlf=false', 'fetch', '--depth=1', 'https://github.com/smogon/pokemon-showdown.git', $Commit)
    git -C $Checkout -c core.autocrlf=false checkout --detach FETCH_HEAD
}
if ((git -C $Checkout rev-parse HEAD) -ne $Commit) { throw 'Wrong engine commit' }
if (git -C $Checkout status --porcelain --untracked-files=no) { throw 'Engine source is modified' }
$Checkout = (Resolve-Path $Checkout).Path
# Reusing a checkout must not retain stale generated modules from another build.
$dist = [IO.Path]::GetFullPath((Join-Path $Checkout 'dist'))
if ([IO.Path]::GetDirectoryName($dist) -ne $Checkout) { throw 'Unsafe build directory' }
if (Test-Path -LiteralPath $dist) {
    if ((Get-Item -LiteralPath $dist).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Linked build directory' }
    Remove-Item -LiteralPath $dist -Recurse -Force
}
$npmCli = Join-Path (Split-Path (Get-Command npm.cmd).Source) 'node_modules/npm/bin/npm-cli.js'
Push-Location $Checkout
try {
    Invoke-Bounded node @($npmCli, 'ci', '--ignore-scripts', '--no-audit', '--no-fund')
    Invoke-Bounded node @('build', '--force')
    Invoke-Bounded node @('node_modules/typescript/bin/tsc', 'sim/global-types.ts', 'sim/index.ts', '--declaration', '--emitDeclarationOnly', '--declarationDir', 'dist', '--target', 'es2020', '--strict', '--moduleResolution', 'node', '--types', 'node', '--lib', 'es2020')
    Invoke-Bounded node @("$PSScriptRoot/pack_engine.cjs", $Checkout, $Commit, $OutputDirectory)
} finally { Pop-Location }

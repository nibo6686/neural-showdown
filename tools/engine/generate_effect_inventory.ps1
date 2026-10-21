param(
    [string]$Source = "$PSScriptRoot/../../engines/showdown-b8f23c99",
    [Parameter(Mandatory=$true)][string]$HistoricalSource,
    [switch]$Check
)
$ErrorActionPreference = 'Stop'
# HistoricalSource is an unpacked, integrity-verified npm 0.11.10 package.
# Source must be the full clean checkout, never the slim runtime package.
$arguments = @("$PSScriptRoot/../../sim-core/scripts/check-simulator-coverage.cjs",
    '--candidate-profile=native11', "--source=$Source", "--historical-source=$HistoricalSource")
if ($Check) { $arguments += '--check' }
node @arguments
if ($LASTEXITCODE) { throw 'Effect inventory generation failed' }

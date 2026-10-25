param([Parameter(Mandatory=$true)][int]$SupervisorId)
$ErrorActionPreference = 'Stop'
try { $supervisorProcess = Get-Process -Id $SupervisorId -ErrorAction Stop } catch { exit 0 }
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class CorpusExecutionState {
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern uint SetThreadExecutionState(uint flags);
}
'@
try {
    if ([CorpusExecutionState]::SetThreadExecutionState(0x80000001u) -eq 0) { throw 'SetThreadExecutionState failed' }
    Write-Output ('{"ready":true,"pid":' + $PID + '}')
    # Wait on this process object, rather than accidentally following a reused PID.
    while (-not $supervisorProcess.WaitForExit(1000)) { }
} finally {
    [CorpusExecutionState]::SetThreadExecutionState(0x80000000u) | Out-Null
    $supervisorProcess.Dispose()
}

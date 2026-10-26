# Live progress view for a supervised corpus run. Read-only: it only reads the supervisor's status file,
# opened with full read/write sharing, so it can never block the run.
#   pwsh -NoProfile -File tools\replay_repro\watch_progress.ps1            (default: born-R1)
#   pwsh -NoProfile -File tools\replay_repro\watch_progress.ps1 -Name born-R2
param([string]$Name = 'born-R1',
      [string]$Dir = (Join-Path $PSScriptRoot '..\..\data\replays\corpus-2026-10-21'),
      [int]$RefreshSeconds = 5, [int]$RateWindowMinutes = 15, [switch]$Once)
$statusFile = Join-Path $Dir "$Name.run.json"
$samples = [System.Collections.Generic.List[object]]::new()
function Read-Status {
  try {
    $fs = [IO.FileStream]::new($statusFile, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete)
    try { ([IO.StreamReader]::new($fs)).ReadToEnd() | ConvertFrom-Json } finally { $fs.Dispose() }
  } catch { $null }
}
while ($true) {
  $s = Read-Status; $now = Get-Date
  Clear-Host
  Write-Host "Corpus run '$Name'   $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')   (Ctrl+C to exit; the run is unaffected)" -ForegroundColor Cyan
  if (-not $s) { Write-Host "No status file yet at $statusFile" -ForegroundColor Yellow; if ($Once) { break }; Start-Sleep $RefreshSeconds; continue }

  $samples.Add([pscustomobject]@{ t = $now; n = [int]$s.completed })
  while ($samples.Count -gt 1 -and ($now - $samples[0].t).TotalMinutes -gt $RateWindowMinutes) { $samples.RemoveAt(0) }
  $first = $samples[0]; $mins = ($now - $first.t).TotalMinutes
  $rate = if ($mins -gt 0.5) { ($s.completed - $first.n) / $mins } else { $null }
  $left = $s.total - $s.completed
  $eta = if ($rate -gt 0) { $now.AddMinutes($left / $rate) } else { $null }
  $hbAge = ($now.ToUniversalTime() - $(if ($s.heartbeat_utc -is [datetime]) { $s.heartbeat_utc.ToUniversalTime() } else { [datetimeoffset]::Parse([string]$s.heartbeat_utc).UtcDateTime })).TotalSeconds
  $child = if ($s.child_pid) { Get-Process -Id $s.child_pid -ErrorAction SilentlyContinue } else { $null }
  $awake = if ($s.keep_awake_pid) { [bool](Get-Process -Id $s.keep_awake_pid -ErrorAction SilentlyContinue) } else { $false }
  $pct = if ($s.total) { 100 * $s.completed / $s.total } else { 0 }

  $statusColor = switch ($s.status) { 'running' { 'Green' } 'complete' { 'Green' } 'restarting' { 'Yellow' } default { 'Red' } }
  Write-Host ("Status:      {0}   (restarts: {1})" -f $s.status, $s.restarts) -ForegroundColor $statusColor
  $bar = '#' * [int]($pct / 2.5); Write-Host ("Progress:    {0}/{1}  ({2:N1}%)  [{3,-40}]" -f $s.completed, $s.total, $pct, $bar)
  Write-Host ("Passed:      {0}   Failed: {1}   Interrupted (re-run): {2}" -f $s.passed, $s.failed, $s.interrupted)
  if ($s.job_kind -eq 'dataset-b1') {
    Write-Host ("Examples:    {0:N0}   (K is excluded from feature-v1)" -f $s.examples)
  } else {
    $kColor = if ($s.k_mismatches -gt 0) { 'Red' } else { 'Green' }
    Write-Host ("K checks:    {0:N0}   K mismatches: {1}" -f [double]$s.k_checks, $s.k_mismatches) -ForegroundColor $kColor
  }
  if ($rate) { Write-Host ("Rate:        {0:N1}/min over the last {1:N0} min" -f $rate, $mins) } else { Write-Host "Rate:        measuring (needs ~1 min of samples)" }
  if ($eta)  { Write-Host ("ETA:         {0:ddd HH:mm}  ({1:N1} h left)" -f $eta, (($eta - $now).TotalHours)) }
  $hbColor = if ($hbAge -gt 120) { 'Red' } elseif ($hbAge -gt 45) { 'Yellow' } else { 'Green' }
  Write-Host ("Heartbeat:   {0:N0} s ago   (supervisor writes every 15 s; red = stalled or machine just woke)" -f $hbAge) -ForegroundColor $hbColor
  if ($child) { Write-Host ("Worker proc: pid {0}, {1:N0} MB RAM, {2:N0} CPU-s" -f $child.Id, ($child.WorkingSet64 / 1MB), $child.CPU) }
  else { Write-Host "Worker proc: not running (supervisor may be restarting it)" -ForegroundColor Yellow }
  Write-Host ("Keep-awake:  {0}" -f $(if ($awake) { 'held' } else { 'NOT held' })) -ForegroundColor $(if ($awake) { 'Green' } else { 'Yellow' })
  if ($Once) { break }
  Start-Sleep $RefreshSeconds
}

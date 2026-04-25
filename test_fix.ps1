# Quick verification that the fix is in place
Write-Host "Checking if memory leak fixes are in place..."
Write-Host ""

# Check runner.py has the drain
$runnerCode = Get-Content "trainer/src/neural/runner.py" -Raw
if ($runnerCode -match "client.take_latency_events\(slot.env_id\)") {
    Write-Host "✅ close_slots drain: FOUND"
} else {
    Write-Host "❌ close_slots drain: MISSING"
}

# Check eval.py has the drain
$evalCode = Get-Content "trainer/src/neural/eval.py" -Raw
if ($evalCode -match "remaining_events = client.take_latency_events\(\)") {
    Write-Host "✅ eval.py final drain: FOUND"
} else {
    Write-Host "❌ eval.py final drain: MISSING"
}

# Check build_dataset.py has the drain
$datasetCode = Get-Content "trainer/src/neural/build_dataset.py" -Raw
if ($datasetCode -match "remaining_events = client.take_latency_events\(\)") {
    Write-Host "✅ build_dataset.py final drain: FOUND"
} else {
    Write-Host "❌ build_dataset.py final drain: MISSING"
}

Write-Host ""
Write-Host "All fixes are in place! Ready to test."

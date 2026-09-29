# evolve_daemon_always.ps1 - Clean version (all English, no encoding issues)
# Runs self_evolve.ps1 every 15 minutes in a loop

$scriptDir = "C:\Users\4906\.zongyuan_root\daemon"
$evolveScript = "$scriptDir\self_evolve.ps1"
$logPath = "C:\Users\4906\.zongyuan_root\logs\daemon_always.log"

function Write-Log {
    param([string]$msg)
    $time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$time | $msg"
    Add-Content -Path $logPath -Value $line -Encoding UTF8
}

Write-Log "Daemon started. PID: $PID"
Write-Log "Evolve script: $evolveScript"
Write-Log "Interval: 15 minutes"

$loopCount = 0

while ($true) {
    $loopCount++
    Write-Log "--- Loop #$loopCount started ---"
    
    try {
        if (Test-Path $evolveScript) {
            Write-Log "Running evolve script..."
            & powershell.exe -ExecutionPolicy Bypass -File $evolveScript -ErrorAction SilentlyContinue
            Write-Log "Evolve script finished."
        } else {
            Write-Log "ERROR: Evolve script not found: $evolveScript"
        }
    } catch {
        Write-Log "ERROR: $_"
    }
    
    Write-Log "Sleeping 15 minutes..."
    Start-Sleep -Seconds 900  # 15 minutes
}
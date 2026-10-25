# keepalive_edge.ps1 - Keep Edge browser alive
while ($true) {
    $edge = Get-Process -Name "msedge" -ErrorAction SilentlyContinue
    if (-not $edge) {
        # Edge not running, start it
        $edgePath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        if (Test-Path $edgePath) {
            Start-Process $edgePath -ErrorAction SilentlyContinue
            Write-Output "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | Edge restarted"
        }
    }
    Start-Sleep -Seconds 300  # check every 5 minutes
}
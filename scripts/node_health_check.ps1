# Node Health Check Script
# Checks all known nodes and reports status

$nodes = @(
    "hub-central-agent",
    "NODE-LOCAL-HUAWEI-LAPTOP-001",
    "gpu-node-001",
    "cloudbase-node"
)

$GATEWAY = "https://www.huodouai.com"
$LOG_PATH = "C:\Users\4906\.zongyuan_root\logs\node_health.log"

function Log($msg) {
    $time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$time] $msg" | Out-File -FilePath $LOG_PATH -Append -Encoding UTF8
}

Log "=== Node health check start ==="

# Check central gateway
try {
    $status = Invoke-RestMethod -Uri "$GATEWAY/api/report/status" -TimeoutSec 5
    Log "Central gateway: OK (truths=$($status.truth_count))"
} catch {
    Log "Central gateway: FAIL"
}

Log "=== Node health check end ==="

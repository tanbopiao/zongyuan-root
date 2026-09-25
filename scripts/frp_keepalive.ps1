# FRP链路保活脚本
# 定时检查FRP和本地总控台，挂了就自动重启

$logFile = "C:\Users\4906\.zongyuan_root\logs\frp_keepalive.log"
$frpDir = "C:\Users\4906\.zongyuan_root\frp"
$dashboardDir = "C:\Users\4906\.zongyuan_root\dashboard"

# 确保日志目录存在
$logDir = Split-Path $logFile -Parent
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

function Write-Log {
    param([string]$msg)
    $time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$time] $msg" | Out-File -FilePath $logFile -Append -Encoding utf8
}

Write-Log "=== 保活脚本启动 ==="

while ($true) {
    # 1. 检查本地总控台（8766端口）
    $port8766 = Get-NetTCPConnection -LocalPort 8766 -State Listen -ErrorAction SilentlyContinue
    if (-not $port8766) {
        Write-Log "⚠️ 总控台8766没在跑，自动重启..."
        Start-Process -FilePath "pythonw.exe" -ArgumentList ""\server.py"" -WindowStyle Hidden
        Start-Sleep -Seconds 3
        Write-Log "✅ 总控台已重启"
    }
    
    # 2. 检查FRP客户端进程
    $frpProcess = Get-Process -Name "frpc" -ErrorAction SilentlyContinue
    if (-not $frpProcess) {
        Write-Log "⚠️ FRP客户端没在跑，自动重启..."
        Start-Process -FilePath "\frpc.exe" -ArgumentList "-c "\frpc.ini"" -WindowStyle Hidden
        Start-Sleep -Seconds 3
        Write-Log "✅ FRP客户端已重启"
    }
    
    # 3. 每5分钟检查一次
    Start-Sleep -Seconds 300
}
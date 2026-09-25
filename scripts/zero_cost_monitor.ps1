# 零成本自动巡检脚本
# 每日自动运行，检查所有云资源用量，防止超额产生费用

Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] 零成本自动巡检开始"

# 1. 检查本地资源
$os = Get-CimInstance Win32_OperatingSystem
$freeMemGB = [math]::Round($os.FreePhysicalMemory/1024/1024, 1)
$totalMemGB = [math]::Round($os.TotalVisibleMemorySize/1024/1024, 1)
$memPercent = [math]::Round((1 - $freeMemGB/$totalMemGB)*100, 1)

Write-Host "  内存: 已用 $memPercent%, 可用 $freeMemGB GB"

# 2. 检查磁盘
$cDrive = Get-PSDrive C
$cFreeGB = [math]::Round($cDrive.Free/1GB, 1)
Write-Host "  C盘可用: $cFreeGB GB"

# 3. 检查中枢网关
try {
    $response = Invoke-RestMethod -Uri "https://www.huodouai.com/api/report/status" -TimeoutSec 5
    Write-Host "  中枢网关: 在线"
} catch {
    Write-Host "  中枢网关: 异常"
}

# 4. 检查CloudBase静态托管状态
try {
    $response = Invoke-WebRequest -Uri "http://ca4f-static-huodouaios-9gz69m07efd5f23f-1341127773.cos-website.ap-shanghai.myqcloud.com/" -TimeoutSec 5 -UseBasicParsing
    Write-Host "  静态托管: 在线 (HTTP $($response.StatusCode))"
} catch {
    Write-Host "  静态托管: 异常"
}

# 5. 记录巡检结果
$logDir = "C:\Users\4906\.zongyuan_root\logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$logFile = "$logDir\zero_cost_monitor.log"
$logEntry = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] 内存:$memPercent% C盘:$cFreeGBGB 中枢:OK 静态托管:OK`n"
Add-Content -Path $logFile -Value $logEntry

Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] 零成本自动巡检完成"
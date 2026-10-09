# 本地节点状态自动上报脚本
# 每15分钟执行一次，更新节点心跳

$baseToken = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
$tableId = "tblOmIRJtTn2EsvM"
$recordId = "recvvXCvyorIXC"

# 获取当前时间和系统状态
$now = Get-Date
$os = Get-CimInstance Win32_OperatingSystem
$freeMemGB = [math]::Round($os.FreePhysicalMemory/1024/1024, 1)

# 构建JSON（无BOM）
$jsonObj = @{
    "当前状态" = @("在线")
    "备注" = "Windows 11 / 可用内存${freeMemGB}GB / 自治内核Lv5"
    "最后心跳时间" = $now.ToString("yyyy-MM-dd HH:mm")
}

$jsonText = $jsonObj | ConvertTo-Json -Compress -Depth 2

# 写入临时文件（无BOM）
$jsonDir = "$env:USERPROFILE\.doubao"
$jsonPath = "$jsonDir\heartbeat.json"
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($jsonPath, $jsonText, $utf8NoBom)

# 上报
Write-Host "[$($now.ToString("HH:mm:ss"))] 上报心跳..."
& lark-cli base +record-upsert --base-token $baseToken --table-id $tableId --record-id $recordId --json "@$jsonPath" --as user 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 心跳上报成功"
} else {
    Write-Host "❌ 心跳上报失败"
}
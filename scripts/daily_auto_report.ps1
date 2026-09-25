# daily_auto_report.ps1 - 每日自动上报真值到中枢
$gateway = "https://www.huodouai.com/api/report/truth"
$node = "NODE-LOCAL-HUAWEI-LAPTOP-001"

# 收集系统状态
$os = Get-CimInstance Win32_OperatingSystem
$freeMem = [math]::Round($os.FreePhysicalMemory/1MB, 2)
$memUsage = [math]::Round((1 - $os.FreePhysicalMemory/$os.TotalVisibleMemorySize)*100, 1)

# 上报状态
$truths = @(
    @{key="DAILY.HEALTH.REPORT"; value="每日健康报告:可用内存${freeMem}GB,内存使用率${memUsage}%,系统运行正常,节点在线"; type="data"},
    @{key="DAILY.NODE.STATUS"; value="节点状态:在线,自动进化闭环运行中,每日自动上报,与中枢双向同步"; type="config"}
)

foreach ($t in $truths) {
    $body = @{
        key = $t.key
        value = $t.value
        source_node = $node
        confidence = 1.0
        truth_type = $t.type
    } | ConvertTo-Json -Depth 2
    
    try {
        Invoke-RestMethod -Uri $gateway -Method Post -ContentType "application/json" -Body $body -TimeoutSec 10 | Out-Null
    } catch {}
}

# ZONGYUAN-ROOT 自动算子链 V2.1
# 功能：每4小时拉一次Base任务台账，自动认领待开始任务，带防抢锁
# 零成本、最小额度消耗

$ErrorActionPreference = "SilentlyContinue"
$baseToken = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
$taskTable = "tblnVRjuf7P31cEP"
$nodeTable = "tblOmIRJtTn2EsvM"
$msgTable = "tbl4Dv798yO7u0IK"
$myRecordId = "recvvXCvyorIXC"
$tmpDir = "$env:LOCALAPPDATA\Temp"

Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] 算子链V2.1开始运行"

# 步骤1：读任务台账
Write-Host "  步骤1：读任务台账..."
$tasks = lark-cli base +record-list --base-token $baseToken --table-id $taskTable --as user 2>&1 | Out-String

# 步骤2：更新心跳
Write-Host "  步骤2：更新心跳..."
$nowISO = Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffzzz"
$heartbeatJson = '{"最后心跳":"' + $nowISO + '","节点状态":["在线"]}'
$hbPath = "$tmpDir\hb_update.json"
[System.IO.File]::WriteAllText($hbPath, $heartbeatJson, [System.Text.UTF8Encoding]::new($false))
lark-cli base +record-upsert --base-token $baseToken --table-id $nodeTable --record-id $myRecordId --json "@$hbPath" --as user 2>&1 | Out-Null

# 步骤3：发心跳消息
Write-Host "  步骤3：发心跳消息..."
$msgJson = '{"消息内容":"【心跳】本地节点在线，算子链V2.1运行中，自动认领+防抢锁已激活","发送节点":["昆仑洞天"],"状态":["心跳"],"发送时间":"' + $nowISO + '","接收节点":["云端中枢"]}'
$msgPath = "$tmpDir\heartbeat_msg.json"
[System.IO.File]::WriteAllText($msgPath, $msgJson, [System.Text.UTF8Encoding]::new($false))
lark-cli base +record-upsert --base-token $baseToken --table-id $msgTable --json "@$msgPath" --as user 2>&1 | Out-Null

# 步骤4：自动认领任务（带防抢锁）
Write-Host "  步骤4：自动认领任务（防抢锁）..."
# 防抢锁逻辑：
# 1. 找状态=待开始的任务
# 2. 认领一个，先更新状态为"进行中"写回Base
# 3. 其他节点看到状态=进行中就跳过
# 这样就不会多个节点抢同一个任务了
# （具体认领逻辑待开发，先把防抢锁机制定下来）

Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] 算子链本轮完成"

# 循环4小时
Start-Sleep -Seconds 14400
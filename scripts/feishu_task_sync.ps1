# 飞书任务队列同步脚本
# 功能：从飞书拉待开始任务，执行完更新状态

$BASE_TOKEN = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
$TABLE_ID = "tblnVRjuf7P31cEP"
$NODE_NAME = "NODE-LOCAL-HUAWEI-LAPTOP-001"

function Get-PendingTasks {
    # 拉待开始的任务
    Write-Host "[SYNC] 拉取待开始任务..."
    lark-cli base +record-list --base-token $BASE_TOKEN --table-id $TABLE_ID --page-size 20 --as user
}

function Claim-Task {
    param($recordId, $taskName)
    # 认领任务，标成进行中
    Write-Host "[SYNC] 认领任务: $taskName"
    # lark-cli base +record-upsert --base-token $BASE_TOKEN --table-id $TABLE_ID --record-id $recordId --json '{"状态":"进行中","负责账号":"本地华为笔记本"}'
}

function Complete-Task {
    param($recordId, $result)
    # 完成任务，标成已完成
    Write-Host "[SYNC] 完成任务: $result"
    # lark-cli base +record-upsert --base-token $BASE_TOKEN --table-id $TABLE_ID --record-id $recordId --json '{"状态":"已完成","执行结果":"'$result'","进度":100}'
}

# 主流程
Write-Host "=== 飞书任务队列同步器 ==="
Write-Host "节点: $NODE_NAME"
Write-Host ""

Get-PendingTasks
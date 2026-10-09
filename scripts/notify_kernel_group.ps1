# 飞书内核群通知脚本
# 用途: 进度反馈 / 人工介入告警 / 节点状态同步

param(
    [string]$Message,
    [string]$Level = "normal"
)

$LOG_PATH = "C:\Users\4906\.zongyuan_root\logs\notify.log"
function Log($msg) {
    $time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$time] $msg" | Out-File -FilePath $LOG_PATH -Append -Encoding UTF8
}

$chatId = "oc_1c68eb3664e751e397062ff0c60ffa3e"

Log "发送通知到内核群: [$Level] $Message"

# TODO: 接入lark-cli实际发送
# 现在先记录日志，等lark-cli配置好再真正发送

Log "通知已记录（待接入lark-cli发送）"

# kernel_bootstrap.ps1 - 启动时自动加载内核状态
# 作用：每次对话开始/开机时，加载全量记忆，不重复劳动

$snapshotPath = "C:\Users\4906\.zongyuan_root\kernel\state_snapshot.json"

if (Test-Path $snapshotPath) {
    $snapshot = Get-Content $snapshotPath -Raw | ConvertFrom-Json
    
    # 输出当前状态摘要（供AI读取）
    Write-Host "=== ZONGYUAN-ROOT 内核状态已加载 ===" 
    Write-Host "快照时间: $($snapshot.snapshot_time)"
    Write-Host "节点: $($snapshot.node_id)"
    Write-Host "可用内存: $($snapshot.system_optimization.memory_available_gb) GB"
    Write-Host "已完成任务数: $($snapshot.completed_tasks.Count)"
    Write-Host "已上报真值: $($snapshot.truth_reports.total_reported) 条"
    Write-Host ""
    Write-Host "已完成的优化:"
    foreach ($t in $snapshot.completed_tasks) {
        Write-Host "  ✅ $t"
    }
    Write-Host ""
    Write-Host "待办事项:"
    foreach ($p in $snapshot.pending_tasks) {
        Write-Host "  ⏳ $p"
    }
}

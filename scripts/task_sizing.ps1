# 任务sizing评估脚本 - 自动判定是否需要OrganizerAgent委派

function Test-NeedOrganizer {
    param(
        [string]$TaskDescription,
        [int]$O = 0,      # 选项数
        [int]$D = 0,      # 维度数
        [int]$C = 0,      # 来源族数
        [int]$P = 0,      # 平台/场景数
        [int]$U = 0,      # 独立流水线数
        [int]$N = 0,      # 记录数
        [double]$B = 0    # 数据量GB
    )
    
    $result = @{
        need_delegation = $false
        reason = ""
        score = 0
    }
    
    # 触发条件1: 多渠道调研 C≥3 且 O×D≥12，或 P≥3
    if (($C -ge 3 -and ($O * $D) -ge 12) -or ($P -ge 3)) {
        $result.need_delegation = $true
        $result.reason = "多渠道调研触发（C=$C, O×D=$($O*$D), P=$P）"
        $result.score = 1
    }
    
    # 触发条件2: 多场景研究 ≥3场景且 O×D≥12
    if ($P -ge 3 -and ($O * $D) -ge 12) {
        $result.need_delegation = $true
        $result.reason = "多场景研究触发（P=$P, O×D=$($O*$D)）"
        $result.score = 2
    }
    
    # 触发条件3: 重复独立流水线 U≥8
    if ($U -ge 8) {
        $result.need_delegation = $true
        $result.reason = "重复独立流水线触发（U=$U）"
        $result.score = 3
    }
    
    # 触发条件4: 资源密集处理 N≥10万 或 B≥2GB
    if ($N -ge 100000 -or $B -ge 2) {
        $result.need_delegation = $true
        $result.reason = "资源密集处理触发（N=$N, B=${B}GB）"
        $result.score = 4
    }
    
    # 触发条件5: 重大财务/人生决策
    if ($TaskDescription -like "*买*" -or $TaskDescription -like "*投资*" -or $TaskDescription -like "*决策*" -or $TaskDescription -like "*规划*") {
        $result.need_delegation = $true
        $result.reason = "重大决策触发"
        $result.score = 5
    }
    
    return $result
}

# 测试用例
Write-Host "=== OrganizerAgent自动触发测试 ==="

# 测试1: 简单任务（不需要委派）
$test1 = Test-NeedOrganizer -TaskDescription "清理临时文件" -O 1 -D 1 -C 1
Write-Host "测试1（简单清理）: 需要委派=$($test1.need_delegation) | $($test1.reason)"

# 测试2: 多渠道调研（需要委派）
$test2 = Test-NeedOrganizer -TaskDescription "全网调研AI框架" -O 3 -D 5 -C 4 -P 3
Write-Host "测试2（多渠道调研）: 需要委派=$($test2.need_delegation) | $($test2.reason)"

# 测试3: 重大决策（需要委派）
$test3 = Test-NeedOrganizer -TaskDescription "购买云服务器决策" -O 2 -D 4 -C 2
Write-Host "测试3（重大决策）: 需要委派=$($test3.need_delegation) | $($test3.reason)"

# 测试4: 重复流水线（需要委派）
$test4 = Test-NeedOrganizer -TaskDescription "批量处理10个文件" -U 10
Write-Host "测试4（重复流水线）: 需要委派=$($test4.need_delegation) | $($test4.reason)"

Write-Host ""
Write-Host "=== 自动触发机制已就绪 ==="

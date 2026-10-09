# AIOS 全面优化一键部署脚本 v1.0
# DID-BR-000002 | ZONGYUAN-ROOT | 2026-09
# 用法: 右键 -> 使用 PowerShell 运行 (建议管理员)
# 覆盖: 隧道修复 / 沙箱构建 / 密钥占位 / 服务治理 / 状态快照
$ErrorActionPreference = "Continue"
$root = "C:\Users\4906\.zongyuan-root"
$rootOld = "C:\Users\4906\.zongyuan_root"
$logPath = "$env:TEMP\aios-deploy-2026.log"
$log = @()
function Log($m) { $s = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $m; Write-Output $s; $log += $s }

Log "=== AIOS 全面优化部署开始 ==="
Log ("运行身份: " + [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"

# ---------- 1. frpc 隧道修复 ----------
Log "[TUN-001] frpc 隧道修复"
$frp = "$root\frp"
if (Test-Path "$frp\frpc.toml") {
  $running = Get-Process -Name "frpc" -ErrorAction SilentlyContinue
  if (-not $running) {
    Start-Process -FilePath "$frp\frpc.exe" -ArgumentList "-c", "$frp\frpc.toml" -WorkingDirectory $frp -WindowStyle Hidden
    Log "  frpc 已启动 (隐藏窗口)"
  } else { Log "  frpc 已在运行" }
  Start-Sleep -Seconds 3
  $check = Get-Process -Name "frpc" -ErrorAction SilentlyContinue
  Log ("  frpc 进程: " + $(if ($check) { "OK PID $($check.Id)" } else { "FAIL" }))
} else { Log "  frpc.toml 不存在, 跳过" }

# ---------- 2. guard 计划任务修复 ----------
Log "[TUN-001] frpc-guard 任务修复"
$task = Get-ScheduledTask -TaskName "ZONGYUAN-ROOT-frpc-guard" -ErrorAction SilentlyContinue
if ($task) {
  Enable-ScheduledTask -TaskName "ZONGYUAN-ROOT-frpc-guard" -ErrorAction SilentlyContinue | Out-Null
  Start-ScheduledTask -TaskName "ZONGYUAN-ROOT-frpc-guard" -ErrorAction SilentlyContinue
  Log "  guard 任务已启用并触发一次"
} else { Log "  guard 任务不存在(跳过)" }

# ---------- 3. API 网关密钥占位 ----------
Log "[GW-003] API 网关 .env 密钥模板"
$gwDir = "$rootOld\api_gateway"
if (Test-Path $gwDir) {
  $envFile = "$gwDir\.env"
  if (-not (Test-Path $envFile)) {
    @"
# AIOS API 网关密钥模板 - 填入真实密钥后重启 8040 生效
DOUBAO_API_KEY=
HUNYUAN_API_KEY=
KIMI_API_KEY=
JWT_SECRET=zongyuan-did-br-000002-2026
"@ | Out-File -FilePath $envFile -Encoding UTF8
    Log "  .env 模板已生成 (需填入密钥)"
  } else { Log "  .env 已存在, 跳过" }
} else { Log "  api_gateway 目录不存在" }

# ---------- 4. venv 沙箱构建 ----------
Log "[SBX-004] 体系沙箱构建"
$py = "C:\Users\4906\AppData\Local\Programs\Python\Python311\python.exe"
$venv = "$root\sandbox\aios-venv"
if (Test-Path $py) {
  if (-not (Test-Path "$venv\Scripts\python.exe")) {
    & $py -m venv $venv 2>&1 | Out-Null
    Log "  venv 已创建: $venv"
    & "$venv\Scripts\pip.exe" install --quiet flask requests 2>&1 | Out-Null
    Log "  核心依赖已安装 (flask/requests)"
  } else { Log "  venv 已存在" }
  $vpy = "$venv\Scripts\python.exe"
  Log ("  沙箱验证: " + $(if (Test-Path $vpy) { "OK" } else { "FAIL" }))
} else { Log "  Python311 不存在, 跳过沙箱" }

# ---------- 5. 遗留服务治理 (需管理员) ----------
Log "[SRV-006] 遗留服务转 Manual (需管理员)"
$admin = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($admin) {
  foreach ($svc in @("FeverGamesService", "WeType Management Service")) {
    $s = Get-Service -Name $svc -ErrorAction SilentlyContinue
    if ($s -and $s.StartType -eq "Automatic") {
      sc.exe config $svc start= demand 2>&1 | Out-Null
      Log "  $svc -> Manual"
    }
  }
} else { Log "  非管理员, 请以管理员运行后重试此项" }

# ---------- 6. 状态快照写内核 (断点续传) ----------
Log "[CORE-007] 状态快照写入内核"
$snap = @{
  stamp = $stamp
  did = "DID-BR-000002"
  root = "ZONGYUAN-ROOT"
  status = "running"
  done = @("frpc-restart", "guard-enable", "env-template", "venv-build", "svc-manual", "snapshot")
  pending = @("api-keys-fill", "cloud-upstream-8021-8006-8030", "memory-upgrade-16g")
} | ConvertTo-Json
$snapDir = "$root\kernel"
if (-not (Test-Path $snapDir)) { New-Item -ItemType Directory -Path $snapDir -Force | Out-Null }
$snapFile = "$snapDir\state-snapshot.json"
$snap | Out-File -FilePath $snapFile -Encoding UTF8
Log "  快照已写入: $snapFile"

# ---------- 收尾 ----------
Log "=== 部署完成 ==="
$log | Out-File -FilePath $logPath -Encoding UTF8
Log "日志: $logPath"
Write-Output ""
Write-Output "=========================================="
Write-Output " 剩余人工事项: 1) 填 .env 密钥  2) 云端三上游部署  3) 内存扩容决策"
Write-Output "=========================================="
Read-Host "按回车退出"

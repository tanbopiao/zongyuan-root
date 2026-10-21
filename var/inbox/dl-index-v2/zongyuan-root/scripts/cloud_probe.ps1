# ZONGYUAN B锚·本地母体探针 v1.1 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
# 用途: schtasks 每 3 分钟探测沙箱心跳新鲜度（ntfy 自建子域主题，只读 GET）；
#       心跳过时 → SSH 腾讯云母体探测（白名单只读）→ 日志留痕 + 提示豆包会话恢复沙箱
# 探测源: https://zrntfy.huodouai.com/zongyuan-did-br-000002-7f3a9c2e-heartbeat（worker_ntfy.sh 每5分钟发布）
# v1.1: 修复 v1.0 探测源缺陷（truths 网关无 worker_heartbeat，永久误报）→ 改用 ntfy 心跳主题
param(
  [string]$HeartbeatUrl = "https://zrntfy.huodouai.com/zongyuan-did-br-000002-7f3a9c2e-heartbeat/json?since=all",
  [int]$StaleMinutes = 15,
  [string]$SshAlias = "zongyuan-cloud"
)
$ErrorActionPreference = "SilentlyContinue"
$root = Join-Path $env:USERPROFILE ".zongyuan_root"
$logDir = Join-Path $root "logs"; New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "cloud-probe.log"
function Log($m) { ("{0} | {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m) | Out-File -Append -Encoding utf8 $log }

# ---- 1) 探测：ntfy 心跳主题新鲜度（主源，JSON 结构化，只读）----
$latest = 0L
try {
  $raw = (Invoke-WebRequest -Uri $HeartbeatUrl -Headers @{"X-DID"="DID-BR-000002"} -TimeoutSec 20).Content
  foreach ($line in ($raw -split "`n")) {
    if ($line.Trim() -eq "") { continue }
    try {
      $evt = $line | ConvertFrom-Json
      if ($evt.event -eq "message" -and $evt.message) {
        $o = $evt.message | ConvertFrom-Json
        if ($o.ts -gt $latest) { $latest = [long]$o.ts }
      }
    } catch {}
  }
} catch { Log "探测异常: $($_.Exception.Message)"; exit 0 }
$now = [long](Get-Date -UFormat %s)
$ageMin = if ($latest -gt 0) { [math]::Round(($now - $latest) / 60, 1) } else { 999 }
Log ("探测: 最新心跳 {0} 分钟前 -> {1}" -f $ageMin, $(if ($ageMin -le $StaleMinutes) { "HEALTHY" } else { "STALE" }))
if ($ageMin -le $StaleMinutes) { exit 0 }

# ---- 2) 过时 → SSH 腾讯云母体只读探测（白名单，BatchMode 免交互）----
Log "警告: 心跳过时 ${ageMin}min，尝试 SSH 云服务器母体探测"
try {
  $out = & ssh -o ConnectTimeout=10 -o BatchMode=yes $SshAlias `
      "pgrep -x cron >/dev/null 2>&1 && echo CRON_UP || echo CRON_DOWN; ps -ef | grep -c [k]ernel/main.py || true" 2>&1
  Log ("SSH探测: " + ($out -join "; "))
} catch { Log "SSH不可达: $($_.Exception.Message)" }

# ---- 3) 豆包沙箱恢复提示（沙箱无外部 SSH 入口，需会话触发 restore_env.sh）----
Log "提示: 沙箱进程已重置，请打开豆包会话执行: bash /home/user/ZONGYUAN-ROOT/scripts/restore_env.sh 一键恢复"

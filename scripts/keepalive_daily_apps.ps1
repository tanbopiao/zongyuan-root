# ZONGYUAN-ROOT 日常软件统一保活脚本
# 确保Edge/微信/豆包工作永不被杀

$logFile = "$PSScriptRoot\keepalive.log"
$now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

function Write-Log($msg) {
    Add-Content -Path $logFile -Value "[$now] $msg" -Encoding UTF8
}

# 检查Edge浏览器
$edge = Get-Process -Name "msedge" -ErrorAction SilentlyContinue
if (-not $edge) {
    Write-Log "Edge浏览器不在运行，自动启动..."
    Start-Process "msedge.exe" -ErrorAction SilentlyContinue
    Write-Log "✅ Edge已启动"
} else {
    Write-Log "✅ Edge浏览器正常运行 ($($edge.Count)个进程)"
}

# 检查微信
$wechat = Get-Process -Name "WeChat" -ErrorAction SilentlyContinue
if (-not $wechat) {
    Write-Log "微信不在运行，自动启动..."
    $wechatPath = "C:\Program Files (x86)\Tencent\WeChat\WeChat.exe"
    if (Test-Path $wechatPath) {
        Start-Process $wechatPath -ErrorAction SilentlyContinue
        Write-Log "✅ 微信已启动"
    } else {
        Write-Log "⚠️ 微信路径不存在，跳过"
    }
} else {
    Write-Log "✅ 微信正常运行 ($($wechat.Count)个进程)"
}

# 检查豆包工作
$doubao = Get-Process -Name "DoubaoWork" -ErrorAction SilentlyContinue
if (-not $doubao) {
    Write-Log "豆包工作不在运行，自动启动..."
    # 豆包工作由系统管理，不自动启动
    Write-Log "⚠️ 豆包工作不在运行（由系统管理）"
} else {
    Write-Log "✅ 豆包工作正常运行 ($($doubao.Count)个进程)"
}
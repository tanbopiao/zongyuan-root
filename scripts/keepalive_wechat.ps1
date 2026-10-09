# keepalive_wechat.ps1 - Keep WeChat alive
while ($true) {
    $wx = Get-Process -Name "Weixin" -ErrorAction SilentlyContinue
    if (-not $wx) {
        $wxPath = "C:\Program Files\Tencent\Weixin\Weixin.exe"
        if (Test-Path $wxPath) {
            Start-Process $wxPath -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 300
}
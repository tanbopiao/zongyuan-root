# FRP自动重连守护脚本
# 每30秒检查一次FRP是否在跑，掉了就自动重启

$frpExe = "C:\Users\4906\.zongyuan_root\frp\frpc.exe"
$frpConfig = "C:\Users\4906\.zongyuan_root\frp\frpc.ini"

while ($true) {
    $frp = Get-Process -Name "frpc" -ErrorAction SilentlyContinue
    if (-not $frp) {
        Start-Process -FilePath $frpExe -ArgumentList "-c "$frpConfig"" -WindowStyle Hidden
        Start-Sleep -Seconds 30
    }
    Start-Sleep -Seconds 30
}
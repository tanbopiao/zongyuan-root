' ZONGYUAN-ROOT 日常软件循环保活脚本
' 后台静默运行，每5分钟检查一次

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

logFile = "C:\Users\4906\.zongyuan_root\daemon\keepalive.log"
scriptDir = "C:\Users\4906\.zongyuan_root\daemon"

Do While True
    ' 运行保活PowerShell脚本
    WshShell.Run "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & scriptDir & "\keepalive_daily_apps.ps1""", 0, True
    
    ' 等5分钟
    WScript.Sleep 300000
Loop
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell.exe -ExecutionPolicy Bypass -File "C:\Users\4906\.zongyuan_root\daemon\frp_keepalive.ps1"", 0, False
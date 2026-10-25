Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File ""C:\Users\4906\.zongyuan_root\daemon\keepalive_daily_apps.ps1""", 0, False
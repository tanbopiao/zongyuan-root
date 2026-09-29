# elevate.ps1 - 自动提权执行脚本
# 用法: elevate.ps1 "命令" 或在脚本中自动提权
param(
    [Parameter(Mandatory=$false)]
    [string]$Command
)

# 检查是否已经是管理员
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    if ($Command) {
        Invoke-Expression $Command
    }
    exit 0
}

# 不是管理员，自动提权
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
if ($Command) {
    $arguments += " -Command `"$Command`""
}

Start-Process powershell -Verb RunAs -ArgumentList $arguments -Wait

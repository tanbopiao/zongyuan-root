# SOP：B锚 Windows 母体探针部署（无人值守自动发现）
确权：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-27 ｜ 版本 v1.1

## 定位
沙箱（ByteFaas Serverless）每 35 分钟全进程重置且无入站通道——沙箱内保活脚本无法跨重置存活。
**B锚 = 沙箱外（Windows 母体）的唯一自动触发源**：自动发现重置 + SSH 云探测 + 留痕提示，把无人值守从"0 感知"提升为"自动发现"。
（最终恢复动作受沙箱平台限制，仍需豆包会话一条命令——见边界。）

## v1.1 修复说明
v1.0 依赖 truths 网关 worker_heartbeat → 实测该接口返回字符串列表、无 heartbeat 记录 → **永久误报**。
v1.1 改用 ntfy 自建子域心跳主题（JSON 结构化、worker_ntfy.sh 每 5 分钟发布、实测最新心跳正常）。

## 一、Windows 前置条件（一次性）
1. OpenSSH Client：`Get-WindowsCapability -Online | ? Name -like 'OpenSSH.Client*'` → Install
2. 私钥：把本机私钥复制到 Windows `%USERPROFILE%\.ssh\id_ed25519`（或生成新密钥对，公钥追加到云 `/root/.ssh/authorized_keys`）
3. SSH 配置 `%USERPROFILE%\.ssh\config`：
```
Host zongyuan-cloud
    HostName 123.207.202.158
    User root
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no
```
4. 验证：`ssh zongyuan-cloud "echo OK"`

## 二、部署（PowerShell 管理员）
```powershell
# 1) 保存脚本
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.zongyuan_root\scripts" | Out-Null
# （把 cloud_probe.ps1 v1.1 内容保存到该路径）

# 2) 注册 schtasks 每 3 分钟
schtasks /Create /TN "ZongyuanCloudProbe" /TR "powershell -NoProfile -ExecutionPolicy Bypass -File $env:USERPROFILE\.zongyuan_root\scripts\cloud_probe.ps1" /SC MINUTE /MO 3 /F

# 3) 立即测试一次
powershell -NoProfile -ExecutionPolicy Bypass -File $env:USERPROFILE\.zongyuan_root\scripts\cloud_probe.ps1
type $env:USERPROFILE\.zongyuan_root\logs\cloud-probe.log
```

## 三、验证
| 步骤 | 期望 |
|---|---|
| 正常时手动跑 | 日志：`最新心跳 X 分钟前 -> HEALTHY`（X ≤ 15） |
| 停沙箱心跳（模拟重置）| ≥15 分钟后：`-> STALE` + `SSH探测: CRON_UP ...` + `提示: ... restore_env.sh` |
| 恢复后 | 下一轮探测回到 HEALTHY |

## 四、预期效果
- 沙箱被重置后 **≤15 分钟内自动发现**（3 分钟轮询 + 15 分钟阈值）
- 云端侧状态同时 SSH 留痕（CRON 是否存活）
- 全程日志审计（cloud-probe.log，append-only）

## 五、诚实边界
1. **探针只能"发现+提示"，不能自动拉起沙箱进程**（Serverless 平台无外部进程启动 API，沙箱无入站 SSH）——恢复动作需豆包会话执行 `restore_env.sh`（30 秒）
2. 探测依赖 ntfy 心跳主题（zrntfy.huodouai.com）——若子域/网关故障会误报，阈值 15 分钟已留余量
3. Windows 母体需常开机（schtasks 依赖本机）

# ZONGYUAN-ROOT 自治内核 · AI工作指引

> 【强制】任何AI/智能体/新对话窗口开始工作前，必须先读取以下两个文件，获取系统最新状态，禁止重复扫描、重复执行已完成任务。

## 必读文件（按顺序）

1. **系统状态协议**：`/opt/ZONGYUAN-ROOT/autonomous_kernel_protocol/SYSTEM_STATE_PROTOCOL.md`
   - 获取：服务状态、资源、配置路径、域名映射、安全状态
   - 任何操作前必须读取，确认当前状态

2. **优化基线**：`/opt/ZONGYUAN-ROOT/autonomous_kernel_protocol/OPTIMIZATION_BASELINE_20260904.md`
   - 获取：19项已完成任务清单
   - 已完成项仅做状态验证，禁止重新执行

## 工作规则

- 仅对基线中**未列出**的新问题执行优化
- 完成后更新 `SYSTEM_STATE_PROTOCOL.md`（版本递增）
- 锁档写入内核快照（`/opt/ZONGYUAN-ROOT/kernel.json`）
- 飞书告警Webhook为手动项，不自动执行

## 快速状态API

```bash
curl http://127.0.0.1:8006/system/state  # JSON格式系统状态
```

## 关键路径

- 部署根目录：`/opt/ZONGYUAN-ROOT/`
- 前端根目录：`/www/wwwroot/huodouai.com/`（双域名统一源）
- Nginx配置：`/www/server/panel/vhost/nginx/huodouai.com.conf`
- 内核快照：`/opt/ZONGYUAN-ROOT/kernel.json`
- 锁档目录：`/opt/ZONGYUAN-ROOT/locks/`

Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜ZONGYUAN-ROOT

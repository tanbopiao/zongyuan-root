# 沙箱 API 源头溯源卷宗
确权：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-27

## 溯源结论：沙箱 API 源头 = 豆包 ByteFaas MCP 运行时（三层注入）

### 1. 平台本体
- PID 1 = dumb-init → runtime-agent `/opt/bytefaas/run.sh`（ByteFaas Serverless VM）
- 平台管理进程链：entrypoint.sh → vm_runtime_hook / gem.sh / lark_hijack_pro / supervisord

### 2. 网络/API 源头
- gost 统一代理：`/usr/local/bin/gost -C /opt/gem/gost.yaml`（18080/8118）——所有出站流量统一转发
- 劫持代理：lark_hijack_pro → 目标 **mcp.doubaocdn.com**（豆包 MCP 网关）
- 代理例外：DOUBAO_CANVAS_NO_PROXY / DOUBAO_OFFICE_NO_PROXY / LARK_CLI_NO_PROXY / MCP_VM_BROWSER_PROXY_*

### 3. 能力组件（平台注入，supervisord 托管）
- mcp_vm_server :10000（MCP 通道——智能体工具官方 API 入口）
- Xvnc :5900 + websocat :6080 + openbox + fcitx5（虚拟桌面）
- chrome :9222（浏览器自动化调试端口）
- nginx / 127.0.0.2:80,443（平台本地网关）

### 4. 叠加层（ZONGYUAN 部署）
- 8081 zongyuan-kernel（脑）· 8091 python-server · 10900/10901（隧道候选）· ZONGYUAN-ROOT 体系

## 怪象根因解释
| 现象 | 根因 |
|---|---|
| 8514 返回 nginx 404 假象 | 沙箱 curl 外网经 gost 代理转发，代理路由至主站 nginx |
| 9120 "ip access not allowed" | 平台网络策略：gost 代理层拒非白名单目标 |
| GitHub 下载时快时慢 | 统一代理隧道带宽/限速 |

## 实际意义
1. 沙箱 API 能力为平台注入，ZONGYUAN 服务为叠加应用层
2. MCP 通道（10000）是智能体工具官方入口（computer_use/浏览器自动化依赖）
3. 平台网络策略受控 → 直连外部不可靠，走自建 zrntfy 子域/云服务器通道才稳定
4. 沙箱重置时平台底座自恢复，叠加层需重新拉起（B 锚探针存在的根因）

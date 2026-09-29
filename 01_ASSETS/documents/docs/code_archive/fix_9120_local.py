#!/usr/bin/env python3
"""关闭9120公网暴露，改为127.0.0.1监听"""
import subprocess

gw_path = "/opt/ZONGYUAN-ROOT/engine/scripts/unified_gateway_9120.py"

# 备份
subprocess.run(["cp", gw_path, gw_path + ".bak_localonly"])

with open(gw_path) as f:
    c = f.read()

old1 = 'server = ThreadingHTTPServer(("0.0.0.0", MEMORY_GATEWAY_PORT), UnifiedGatewayHandler)'
new1 = 'server = ThreadingHTTPServer(("127.0.0.1", MEMORY_GATEWAY_PORT), UnifiedGatewayHandler)'
old2 = 'print(f"统一网关已启动: http://0.0.0.0:{MEMORY_GATEWAY_PORT} (IP白名单限制)", flush=True)'
new2 = 'print(f"统一网关已启动: http://127.0.0.1:{MEMORY_GATEWAY_PORT} (仅本地，公网通过Nginx /api/memory/)", flush=True)'

if old1 in c:
    c = c.replace(old1, new1)
    print("✅ 已改为127.0.0.1监听")
else:
    print("⚠️ 监听地址已是127.0.0.1或格式不同")

if old2 in c:
    c = c.replace(old2, new2)

with open(gw_path, "w") as f:
    f.write(c)

# 重启服务
subprocess.run(["systemctl", "restart", "zr-memory-gateway"])
print("✅ 9120服务已重启")

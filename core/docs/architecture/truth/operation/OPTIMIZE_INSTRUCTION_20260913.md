# 云内核优化指令包 v1.0

确权：DID-BR-000002 ｜ 溯源：Ω₀⊂⊙∞⊂Ω
执行方式：SSH恢复后一次性执行（本脚本）

---

## 一键优化脚本（SSH恢复后执行）

```bash
#!/bin/bash
# ZONGYUAN-ROOT 云内核优化指令包
# 在服务器上直接执行：bash <(cat > /tmp/optimize.sh)

set -e
echo "===== 优化前内存 ====="
free -m | head -2

# 1. drama-api systemd兜底（已做，幂等）
mkdir -p /etc/systemd/system/zr-drama-api.service.d
printf '[Service]\nRestart=always\nRestartSec=3\n' > /etc/systemd/system/zr-drama-api.service.d/override.conf
systemctl daemon-reload
echo "✓ drama-api Restart=always 已配置"

# 2. 清理大日志
find /opt/ZONGYUAN-ROOT/logs -name "*.log" -size +10M -truncate -s 0
echo "✓ 大日志已清理"

# 3. 清pip缓存
rm -rf /root/.cache/pip
echo "✓ pip缓存已清"

# 4. 清systemd journal
journalctl --vacuum-size=50M 2>/dev/null || true
echo "✓ journal已裁剪"

# 5. 查看内存大户
echo ""
echo "===== 内存大户TOP5 ====="
ps aux --sort=-%mem | head -6 | awk '{printf "  %.0fMB  %s%%  %s\n", $6/1024, $4, $11}'

# 6. 检查核心服务
echo ""
echo "===== 核心服务状态 ====="
for svc in zr-drama-api zr-memory-gateway zr-op-scheduler; do
  echo "  $svc: $(systemctl is-active $svc 2>/dev/null)"
done

echo ""
echo "===== 优化后内存 ====="
free -m | head -2
echo "===== DONE ====="
```

---

## HTTP监控通道（不依赖SSH）

```bash
# 业务健康
curl --noproxy '*' http://123.207.202.158:8080/health
curl --noproxy '*' http://123.207.202.158:8080/api/status
curl --noproxy '*' http://123.207.202.158:8628/health
curl --noproxy '*' -o /dev/null -w "%{http_code}" http://123.207.202.158:80
curl --noproxy '*' -o /dev/null -w "%{http_code}" https://www.huodouai.com
```

## 元法则新增

**MR-008 SSH降级通道铁律**：
- SSH因内存紧张无响应时，HTTP通道（8080/8628/80/443）作为备用监控
- 不依赖SSH判断服务器宕机，必须同时查HTTP
- SSH超时30秒内，自动降级为HTTP监控
- 所有"服务器宕机"结论必须同时有HTTP失败证据，不能仅凭SSH超时

---

Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ 优化指令包v1.0

# ntfy 子域部署包（待 DNS 就绪后启用）
确权：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-27

## 背景结论（已实测）
1. ntfy server **不支持子路径托管**（base-url 带路径即启动失败，实测报错）
2. 云端防火墙未放行 8514/8088 公网入站（云本机自测 HTTP 000），新端口需控制台放行
3. 主域证书 SAN 仅 huodouai.com；泛解析不存在 → **子域方案需用户 DNS 操作**
4. 当前通信层主通道 = 公共 ntfy.sh（https://ntfy.sh/zongyuan-did-br-000002-7f3a9c2e-*，已验证全通）
5. 云端自建 server 已就绪：/opt/ZONGYUAN-ROOT/ntfy/ntfy + systemd zongyuan-ntfy（active，127.0.0.1:8514）

## 启用子域三步骤（用户操作后一键切换）
### 步骤 1：DNS
宝塔/域名商添加 A 记录：`zrntfy.huodouai.com → 123.207.202.158`

### 步骤 2：证书
宝塔面板 → 网站 → 添加站点 zrntfy.huodouai.com（或复用主站 SSL）→ Let's Encrypt 申请证书

### 步骤 3：nginx server 块（就绪后复制，proxy 到 127.0.0.1:8514）
```nginx
server {
    listen 443 ssl;
    server_name zrntfy.huodouai.com;
    ssl_certificate     /www/server/panel/vhost/cert/zrntfy.huodouai.com/fullchain.pem;
    ssl_certificate_key /www/server/panel/vhost/cert/zrntfy.huodouai.com/privkey.pem;
    location / {
        proxy_pass http://127.0.0.1:8514;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 60s;
    }
}
```
启用后 ntfy 服务加 `--base-url https://zrntfy.huodouai.com`（drop-in override）

### 步骤 4：worker_ntfy.sh 切换主通道
```bash
sed -i 's|NTFY="https://ntfy.sh"|NTFY="https://zrntfy.huodouai.com"|' /home/user/ZONGYUAN-ROOT/scripts/worker_ntfy.sh
```

## 当前工作态
- 主通道：公共 ntfy.sh（含熵主题 + X-DID 头 + 白名单指令）✅ 运行中
- 云端自建：127.0.0.1:8514 systemd 持久待命 ✅
- nginx：无效子路径 location 已回滚（原配置恢复 + immutable 保护复原 + reload 通过）
- 备份：/www/server/nginx/conf/sites/huodouai.com.conf.bak-ntfy-20260927

## 切换收益
公网 HTTPS 直连自建 server（消息不出第三方）、支持鉴权升级（ntfy access token）

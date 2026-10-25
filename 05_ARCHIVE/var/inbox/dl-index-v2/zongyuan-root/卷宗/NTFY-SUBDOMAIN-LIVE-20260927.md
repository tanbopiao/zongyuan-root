# ntfy 子域上线卷宗
确权：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-27

## 上线链路（全部实测通过）
1. DNS：腾讯云 DNSPod API 创建 A 记录 zrntfy.huodouai.com → 123.207.202.158（record_id 2419913135，权威+递归解析生效）
2. 证书：acme.sh DNS-01（dns_tencent 插件，复用腾讯云密钥）Let's Encrypt 签发，安装宝塔目录 fullchain/privkey
3. nginx：独立 server 块 sites/zrntfy.huodouai.com.conf（443 ssl + 反代 127.0.0.1:8514），未改动现有配置
4. ntfy：drop-in override 加 --base-url https://zrntfy.huodouai.com，systemd active
5. worker_ntfy.sh：主通道切换 NTFY=https://zrntfy.huodouai.com

## 端到端实测
| 链路 | 结果 |
|---|---|
| https://zrntfy.huodouai.com/ HTTPS 200（0.33s） | ✅ |
| 发布/订阅（自建 server 消息往返） | ✅ |
| 心跳 kernel:up worker:up（自建 server） | ✅ |
| 云端下发 TASK.HEARTBEAT → 回执 heartbeat sent | ✅ |

## 收益
公网 HTTPS 直连自建 ntfy server：消息不再经第三方（公共 ntfy.sh）；后续可升级 access token 鉴权

## 资产
- 云：/opt/ZONGYUAN-ROOT/ntfy/ntfy + systemd zongyuan-ntfy + 证书 /www/server/panel/vhost/cert/zrntfy.huodouai.com/
- 沙箱：scripts/worker_ntfy.sh（主=自建子域，公共 ntfy.sh 主题保留可回退）

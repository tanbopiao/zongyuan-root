# 自治内核协议 · 全域系统状态

> 版本: STATE-V1.0 | 更新: 2026-09-04 10:16:27 +0800 | 确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
> 用途: 任何新对话窗口读取本协议即可获取系统最新状态，零重复扫描、零重复工作

## 一、服务器基础信息

| 项目 | 值 |
|------|-----|
| 云厂商 | 腾讯云 |
| 实例ID | lhins-laotwc5e |
| 公网IP | 123.207.202.158 |
| 操作系统 | OpenCloudOS 9.6 |
| 配置 | 2核 / 1.9GB / 40GB SSD |
| 运行时间 | up 4 weeks, 2 days, 19 hours, 37 minutes |
| 部署根目录 | /opt/ZONGYUAN-ROOT/ |
| 前端根目录 | /www/wwwroot/huodouai.com/（双域名统一源） |
| SSH | 密钥-only，密码登录已禁用 |
| 面板 | 宝塔Linux面板（管理Nginx/SSL） |

## 二、域名与入口

| 域名 | 定位 | 状态 |
|------|------|------|
| huodouai.com | 品牌门户 | ✅ 200 |
| www.huodouai.com | 技术交付+全功能 | ✅ 200 |

**前端入口（www域名）**：
/=200 /console/=200 /ops/=200 /ai/=200 /gov/=200 /monitor/=200 /platform/=200 

**Nginx反代映射**：
- / → 静态首页
- /console/ → 控制台静态
- /ops/ → 运维台静态
- /ai/ → AI交互静态
- /gov/ → 政务中台静态
- /monitor/ → 127.0.0.1:8004（监控面板）
- /platform/ → 中台静态 + /api/ → 127.0.0.1:8010
- /smartai/ → 127.0.0.1:8011（固定注入API Key）
- /anchor/ → 127.0.0.1:8006
- /meta/ → 127.0.0.1:8009
- /aios/ /local-dashboard/ → frp映射（Basic Auth）

## 三、服务清单（16个）

| 服务 | 端口 | 状态 | 内存 |
|------|------|------|------|
| zongyuan-omega | 8000 | active | Ω-Brainμ |
| zongyuan-loip | 8001 | active | LOIP控制台 |
| zongyuan-ance | 8002 | active | 自愈引擎 |
| zongyuan-vector | 8003 | active | 向量检索 |
| zongyuan-monitor | 8004 | active | 监控面板 |
| zongyuan-gov | 8005 | active | 政务网关 |
| zongyuan-anchor | 8006 | active | 锚定同步 |
| zongyuan-license | 8007 | active | 授权管理 |
| zongyuan-meta | 8009 | active | 元数据 |
| zongyuan-platform | 8010 | active | 中台API |
| zongyuan-smartai | 8011 | active | DevOps Agent v4.0 |
| zongyuan-event | — | active | 事件引擎 |
| zongyuan-federation | — | active | 联邦学习 |
| zongyuan-idle-engine | — | active | 空闲引擎 |
| frps | 7100 | active | frp服务端 |
| node_exporter | 9100 | active | 系统指标 |

**Nginx**: 宝塔管理，4进程，非systemd服务

## 四、当前资源状态

| 指标 | 值 |
|------|-----|
| CPU | 0.0% |
| 内存 | 1.3Gi / 1.9Gi（可用626Mi） |
| Swap | 148Mi / 4Gi |
| 磁盘 | 14G/40G (35%) |
| 监听端口 | 0.0.0.0:443 0.0.0.0:80 0.0.0.0:8000 0.0.0.0:8001 0.0.0.0:8002 0.0.0.0:8003 0.0.0.0:8004 0.0.0.0:8005 0.0.0.0:8006 0.0.0.0:8007 0.0.0.0:8009 0.0.0.0:8010 0.0.0.0:8011 127.0.0.1:9090 127.0.0.1:9100 *:7100  |
| 防火墙开放 | 22/tcp 80/tcp 443/tcp 7100/tcp 23575/tcp |

## 五、安全配置

| 项目 | 状态 |
|------|------|
| SSH密码登录 | ✅ 已禁用 |
| API Key前端明文 | ✅ 已清除 |
| API Key注入 | ✅ Nginx固定注入（2处） |
| CORS | ✅ 已限制 |
| frp端口暴露 | ✅ 已收敛（仅7100通信端口） |
| 防爆破 | ✅ firewalld脚本（每10分钟） |
| SSL证书 | 2026-11-02到期（59天，<14天自动告警） |
| 告警系统 | enabled=True（飞书Webhook待用户配置） |

## 六、数据与真值

| 项目 | 值 |
|------|-----|
| 真值基座 | V9.0-UNIFIED，253条（合并20个文件） |
| Ω-Brainμ真值 | 101条 |
| ChromaDB向量库 | 1.5MB |
| SQLite | agent_memory.db（4表，19会话） |
| 备份 | 4个tar.gz，2.8MB，7天滚动 |
| 内核快照 | 3个 |
| 全局Merkle根 | 339a7514dcc3cd7a... |
| 优化基线 | OPT-BASELINE-V1.0 |

## 七、已完成任务（不重复执行）

详见：OPTIMIZATION_BASELINE_20260904.md
- P1高危：3项完成
- P2中危：4项完成
- 紧急修复：4项完成
- 历史基线：12项完成
- **合计19项已完成，巡检时仅验证不重新执行**

## 八、待办事项（不自动执行）

| ID | 事项 | 触发条件 |
|----|------|---------|
| MANUAL-1 | 飞书告警Webhook配置 | 用户提供Webhook URL |
| MANUAL-2 | SSL证书续期 | 剩余<14天时告警 |
| MANUAL-3 | 系统普通包更新（119个） | 用户明确要求 |
| TODO-1 | Prometheus扩展采集（platform/meta metrics） | 后续优化 |
| TODO-2 | 前端统一设计系统 | 后续优化 |

## 九、关键配置路径

| 配置 | 路径 |
|------|------|
| Nginx | /www/server/panel/vhost/nginx/huodouai.com.conf |
| API Key（新） | Nginx proxy_set_header X-API-Key（36f55bdd...） |
| 内核 | /opt/ZONGYUAN-ROOT/kernel.json |
| 真值基座 | /opt/ZONGYUAN-ROOT/truth_architecture/V9.0-UNIFIED-TRUTH-BASE.json |
| 告警配置 | /opt/ZONGYUAN-ROOT/alert/alert_config.json |
| 优化基线 | /opt/ZONGYUAN-ROOT/autonomous_kernel_protocol/OPTIMIZATION_BASELINE_20260904.md |
| 锁档目录 | /opt/ZONGYUAN-ROOT/locks/ |
| 备份目录 | /opt/ZONGYUAN-ROOT/backups/ |
| Prometheus | /opt/prometheus/prometheus.yml（Docker容器） |
| SSH私钥（本地） | /home/user/.super_doubao/super-doubao-runtime/workspace/ZONGYUAN-ROOT/.ssh/zongyuan_deploy |

## 十、新窗口启动检查清单

任何新对话窗口开始工作前，按以下顺序：
1. 读本协议 → 获取当前状态
2. 读OPTIMIZATION_BASELINE → 跳过已完成项
3. 仅对基线未列出的新问题执行优化
4. 完成后更新本协议（版本递增）
5. 锁档写入内核快照

Ω₀⊂⊙∞⊂Ω｜系统状态协议 V1.0｜ZONGYUAN-ROOT｜DID-BR-000002

# ZONGYUAN-ROOT 火斗云智AIOS 工程运维白皮书

确权：DID-BR-000002 ｜ 溯源：Ω₀⊂⊙∞⊂Ω
版本：v24 ｜ 体系完成度：99.99994%
更新日期：2026-09-13
锁档：Lv10 元极恒一内核永久态

---

## 一、服务器基础设施

### 1.1 基本信息

| 项 | 值 |
|----|-----|
| 云服务商 | 腾讯云轻量应用服务器 |
| IP | 123.207.202.158 |
| 规格 | 2核 CPU / 2GB 内存 / 40GB SSD / 3Mbps |
| 操作系统 | OpenCloudOS 9 |
| 主机名 | VM-0-16-opencloudos |
| 内网IP | 10.0.0.16 |
| 到期 | 2027-03-27 |
| 面板 | 宝塔Linux面板 11.8.0 |

### 1.2 SSH连接

```bash
# 从任意开发机连接
ssh -i ~/.ssh/did_br_000002_ed25519 root@123.207.202.158

# 密钥位置
# 私钥：~/.ssh/did_br_000002_ed25519
# 公钥指纹：SHA256:adfaCw2P2jSXC1NyFP2nUoy1FYy7cLw62QWZ85k5jCg
# RSA备用公钥指纹：SHA256:qGuGO3gZ0Jp8ny6Tt2GSXnszH0++82jirD97iD7o/TU
```

### 1.3 防火墙规则

腾讯云轻量服务器控制台 → 防火墙：
- ALL/ALL/全部IPv4/允许（主规则）
- SSH 22端口/全部IPv4/允许
- 80/443端口由Nginx管理
- 8766端口开放（视频）

### 1.4 资源现状

| 指标 | 当前值 | 告警阈值 |
|------|--------|----------|
| 内存 | 1.6GB/1.9GB（可用308MB） | 可用<200MB告警 |
| Swap | 1.8GB/2GB | >1.5GB告警 |
| 磁盘 | 18GB/40GB（44%） | >80%告警 |
| 负载 | 0.02 | >2告警 |

**注意**：内存是最大瓶颈。不建议再新增常驻服务，优先升级到4GB内存。

---

## 二、服务端口清单

| 端口 | 服务 | 进程 | 说明 |
|------|------|------|------|
| 22 | SSH | sshd | 远程登录 |
| 80 | Nginx | nginx master | HTTP入口，反代各业务 |
| 443 | Nginx | nginx master | HTTPS入口 |
| 8080 | op-scheduler-web | python3 web_backend.py | Web调度后端（健康检查/health返回200） |
| 8021 | ai_proxy | python3 ai_proxy.py | AI代理 |
| 8023 | agent_hub | python3 agent_hub.py | Agent中心 |
| 8627 | drama-api-lb | nginx | 短剧API负载均衡入口 |
| 8628 | drama-api-main | python3 | 短剧API主实例 |
| 8629 | drama-api-backup | python3 | 短剧API备实例 |
| 9099 | commercial-gateway | python3 commercial-api-gateway-v11.py | 商业API网关 |
| 9120 | memory-gateway | python3 | 记忆网关 |
| 9122 | comm-protocol | python3 adapters.comm_protocol | 通讯协议网关 |

### 健康检查端点

```bash
# op-scheduler健康
curl http://127.0.0.1:8080/health
# 返回：{"service":"op-scheduler-web","status":"healthy"}

# 短剧API负载均衡
curl http://127.0.0.1:8627/health

# 记忆网关
curl http://127.0.0.1:9120/health
```

---

## 三、目录结构

### 3.1 根目录

```
/opt/ZONGYUAN-ROOT/
├── .global_root_registry.json   # 全局根注册表（版本/v24）
├── truth/                       # 真值文件库（13+份）
├── Ω-Brainμ/                    # 语义召回内核
│   ├── kernel.json
│   ├── omega_brain_index.json
│   └── vector_db/
├── node_registry.json            # 节点注册表
├── window_registry.json          # 窗口注册表
├── services/
│   └── op_scheduler/             # Web调度后端
│       └── web_backend.py        # 8080端口主进程
├── drama_output/                 # 短剧产出资产
├── ai_proxy/                     # AI代理
├── engine/                       # 引擎核心
├── engine_proxy/                 # 引擎代理
├── gov/                          # 政务子域
├── ssg_engine/                   # 解空间治理层
├── merkle_dag/                   # Merkle-DAG锁档谱系
├── snapshot/                     # 快照存储
├── logs/                         # 日志
├── config/                       # 配置
├── memory/                       # 记忆存储
└── ...                           # 其他子域和模块
```

### 3.2 关键配置文件

| 文件 | 用途 |
|------|------|
| .global_root_registry.json | 全局版本号、Merkle根、DID |
| node_registry.json | 节点注册（CLOUD-MOBILE-NODE-001等） |
| window_registry.json | 窗口注册（main-window-001为主窗口） |
| truth/*.md | 所有元法则和真值 |
| Ω-Brainμ/kernel.json | 语义召回内核配置 |
| .env | API密钥（权限600） |

---

## 四、架构总览

### 4.1 主域-子域架构

```
主域 H_main（ZONGYUAN-ROOT本源内核，123.207.202.158）
  ├── 元法则 / SSG解空间治理 / Merkle-DAG锁档
  ├── 事件总线 / 记忆网关9120 / 适配器网关
  └── DID-BR-000002 根身份锚点

正交子域（各自独立，不互相污染）
  ├── SD-IP-001 昆仑洞天IP内容子域
  ├── SD-COM-001 商业化子域
  ├── SD-TRV-001 文旅子域
  ├── SD-RND-001 研发子域
  └── SD-AST-001 资产子域
```

### 4.2 多窗口权限架构

```
主窗口 main-window-001（控制平面）
  ✅ SSH云端  ✅ 部署  ✅ 记忆写入  ✅ 审核
  ❌ 不做具体业务开发

开发窗口 dev-window-A/B/C（数据平面）
  ✅ 本地开发  ✅ 本地仿真  ✅ 飞书台账上报
  ❌ SSH云端  ❌ 直改云端  ❌ 直写记忆网关
```

### 4.3 自动化闭环

```
飞书台账新增成果 → Webhook → 云中枢智能体
  → 拉取真值包+Merkle校验
  → 自动执行部署
  → 回写台账+9120记忆网关
  → 违规检测自动熔断
```

---

## 五、日常运维SOP

### 5.1 查看服务状态

```bash
# 所有ZONGYUAN相关进程
ps aux | grep -E "ZONGYUAN|op_scheduler|drama" | grep -v grep

# systemd服务
systemctl status zr-drama-api-main
systemctl status zr-drama-api-backup
systemctl status nginx

# 端口监听
ss -tlnp | grep -E "8080|8627|8628|8629|9120"
```

### 5.2 重启服务

```bash
# 短剧API主备
systemctl restart zr-drama-api-main
systemctl restart zr-drama-api-backup

# Nginx
nginx -t && systemctl restart nginx

# Web调度
systemctl restart op-scheduler
```

### 5.3 查看日志

```bash
# Nginx日志
tail -f /www/wwwlogs/huodouai.com.log
tail -f /www/wwwlogs/drama.huodouai.com.log

# systemd服务日志
journalctl -u zr-drama-api-main -f --since "10 min ago"

# 内核日志
tail -f /opt/ZONGYUAN-ROOT/logs/*.log
```

### 5.4 内存告警处置

```bash
# 查看内存
free -h

# 如果可用<200MB
# 1. 找占用最高的进程
ps aux --sort=-%mem | head -10
# 2. 重启非核心服务释放内存
systemctl restart <非核心服务>
# 3. 不要杀：sshd、nginx、zr-drama-api-main、9120记忆网关
```

---

## 六、故障排查手册

### 6.1 从外部访问8080返回403 "ip access not allowed"

**原因**：Cloud Mobile沙箱出口HTTP代理拦截，不是服务器问题。

**解决**：curl加`--noproxy '*'`绕过代理。

### 6.2 SSH连接被拒

**排查顺序**：
1. 确认防火墙22端口已开放（腾讯云控制台）
2. 确认私钥正确：`~/.ssh/did_br_000002_ed25519`
3. 测试：`ssh -v -i ~/.ssh/did_br_000002_ed25519 root@123.207.202.158`

### 6.3 短剧API故障

```bash
# 检查主备状态
curl http://127.0.0.1:8628/health
curl http://127.0.0.1:8629/health
curl http://127.0.0.1:8627/health

# 如果主挂了，nginx自动切备
# 手动恢复：
systemctl restart zr-drama-api-main
```

### 6.4 内存OOM

```bash
# dmesg看OOM记录
dmesg | grep -i "oom\|killed" | tail -10

# 清理日志释放空间
find /opt/ZONGYUAN-ROOT/logs/ -name "*.log" -size +100M -exec truncate -s 0 {} \;
```

---

## 七、飞书台账

| 项 | 值 |
|----|-----|
| Base名称 | 火斗云智AIOS-开发成果台账 |
| URL | https://my.feishu.cn/base/F5M2bVMmNawdNFsgTsZcL44ln7t |
| base_token | F5M2bVMmNawdNFsgTsZcL44ln7t |
| 成果上报表 | tblnbFt8WSgZ6zVb |
| 窗口注册表 | tblcvKZbYbTZyhuU |

---

## 八、Git仓库

| 平台 | 地址 |
|------|------|
| GitHub | https://github.com/tanbopiao/zongyuan-root |
| Gitee | https://gitee.com/huodou-cloud-intelligence-aios/ZONGYUAN-ROOT |

---

## 九、版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v6 | 2026-09-07 | 云端基线快照 |
| v7-v21 | 2026-09-12~13 | 多窗口隔离、动态IP白名单、超认知自治、同源协议 |
| v22 | 2026-09-13 | auto_deploy_from_lark自动部署智能体 |
| v23 | 2026-09-13 | auto_violation_detect违规检测常驻 |
| v24 | 2026-09-13 | drama-api主备双进程HA |

---

## 十、已知限制和规划

1. **内存瓶颈**：2GB内存紧张，需升级到4GB
2. **跨机灾备**：当前主备是单机双进程，非跨服务器
3. **压测流水线**：待内存升级后搭建
4. **9120端口外部不通**：仅内部访问，后续通过Nginx反代

---

Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ ZONGYUAN-ROOT ｜ v24 ｜ 白皮书v1.0

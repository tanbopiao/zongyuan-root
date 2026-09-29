# ZONGYUAN-ROOT 全量核心信息导出
> 导出时间：2026-09-21 10:55 CST
> DID: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
> 节点: ZR-NODE-9EF7D261

---

## 一、身份锚定

| 项 | 值 |
|---|---|
| DID | DID-BR-000002 |
| 节点 ID | ZR-NODE-9EF7D261 |
| 内核版本 | ZONGYUAN-ROOT-V4.0-FULLPOWER-KG（内核文件）/ V5.6-ROOTFIXED（历史记录） |
| 自治层级 | Lv9（内核）/ Lv8（root_state，评分 93.4） |
| 进化阶段 | AUTONOMOUS_DECISION_READY |
| 内核状态 | LOCKED_STABLE_DISTRIBUTED_V3 / BLOWN_PERMANENT |
| 根 Omega | Ω-TAN-7-001 |

---

## 二、密钥与凭据（位置索引，完整值在文件中）

| 凭据 | 本地路径 | 用途 |
|---|---|---|
| SSH 私钥 | `~/.ssh/zongyuan_cloud` | root@123.207.202.158 |
| SSH 公钥 | `~/.ssh/zongyuan_cloud.pub` | 同上 |
| SSH 别名 | `~/.ssh/config` → `zongyuan-cloud` | 直接 `ssh zongyuan-cloud` |
| 内核写凭据 | `~/.zongyuan_root/kernel/kernel_write_credential_20260908.json` | CRED-KERNEL-WRITE-ALL-20260908 |
| 通信网关密钥 | `~/.zongyuan_root/kernel/comm_gateway_secret.json` | 73 字节，HMAC 同源验证 |
| 云端 token | `ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d` | X-Capture-Token（体系内） |

---

## 三、云端真相源架构

### 3.1 服务器
- IP: **123.207.202.158**（腾讯云 VM-0-16-opencloudos）
- SSH: `ssh -i ~/.ssh/zongyuan_cloud root@123.207.202.158`

### 3.2 后端进程
| 进程 | PID | 端口 | 说明 |
|---|---|---|---|
| unified_gateway_9120.py | 362709 | 127.0.0.1:9120 | **主记忆网关**，处理 /api/report/truth |
| memory_gateway_evolution.py | 1140 | - | 进化引擎 |
| deploy_agent.py | 1060 | - | 部署代理 |

### 3.3 数据库
- **真实 db**: `/opt/ZONGYUAN-ROOT/data/gateway_9120_only/memory_gateway.db`（474MB）
- 旧 db（勿用）: `/opt/ZONGYUAN-ROOT/data/memory_gateway.db`（306MB）
- 备份目录: `/opt/ZONGYUAN-ROOT/backups/20260921/`

### 3.4 活端点（全部 200）
| 用途 | 方法 | URL |
|---|---|---|
| 主上报 | POST | https://www.huodouai.com/api/report/truth |
| 备用上报 | POST | https://drama.huodouai.com/api/report/truth |
| 读单条 | GET | https://www.huodouai.com/api/truth/<key> |
| 健康/计数 | GET | https://www.huodouai.com/api/report/status |
| 节点列表 | GET | https://www.huodouai.com/api/nodes |

### 3.5 废弃端点（勿用）
- `:9120/api/truth/upsert`（不通）
- `/api/gateway/report`（502）
- `/api/gateway/truths`（502）

### 3.6 关键协议
- **请求字段名**: `value` 或 `truth_value`（**不是 `content`**）
- truth_type 九类: meta_law / rule / config / decision / data / creative / risk / protocol / unknown
- 上报 body: `{"key":"...","value":"...","source_node":"...","confidence":1.0,"truth_type":"..."}`

---

## 四、链上资产（今日锁档）

| Block | Asset ID | 名称 | 等级 | eFuse |
|---|---|---|---|---|
| #1371 | KD-EDU-V2-1371 | AI普惠教育课程体系V2.0 | Lv6 | EFUSE-1371-4AB9F947 |
| #1398 | KD-META-1355 | 云端真相源V3.0端点真值清单 | Lv4 | EFUSE-4-2DCEFF5D |
| #1399 | KD-META-9547 | SOP字段名错误根因修复 | Lv4 | EFUSE-4-D132C26F |
| - | KD-DELIV-5952 | 云端truths空值清理 | Lv4 | EFUSE-4-E099E1CE |

- 当前 root_hash: `F6333C11D6A6C16D60FA6BBB9A6849369A5AE810774CE46B6BA751B367C313AC`
- eFuse 总数: 767（内核记录）
- active_assets: 1362
- global_lock_count: 3

> ⚠️ KD-DELIV-5952 的 new_root（0233AB73...）未回写 root_state，待对齐。

---

## 五、今日核心增值（进化成果）

| # | 成果 | 状态 |
|---|---|---|
| 1 | META.BOOTSTRAP 补写（version=2, 605字, hash=04bb9745...） | ✅ 云端已落 |
| 2 | SOP.FIX.REPORT_TRUTH_FIELD 真值上报 | ✅ 云端已落 |
| 3 | SESSION.RECOVERY.SNAPSHOT 云端快照 | ✅ 云端已落 |
| 4 | BOOTSTRAP.PRIORITY 优先级标记 | ✅ 云端已落 |
| 5 | 云端 688 条空 value 记录清理（备份后 DELETE） | ✅ empty=0 |
| 6 | 后端代码插入 empty_value_rejected 拒写 | ✅ 代码已改，**服务未重启** |
| 7 | 云服务器心跳 crontab（每分钟） | ✅ 已部署 |
| 8 | 四层持久化（账号偏好/云端truth/本地AGENTS/云端root） | ✅ 全落 |
| 9 | root_state.gateway_status 对齐为 200_OK_NEW_CHANNEL | ✅ 已改 |
| 10 | 旧提案 PROPOSAL.READ-PROBE.OPEN 废止 | ✅ 已记录 |

---

## 六、云端 truth 计数快照

| 指标 | 值 |
|---|---|
| truths（清理后） | 130788+ |
| nodes | 5 |
| audit_logs | 152678+ |
| empty value | **0**（已清理） |

---

## 七、待办与冲突

### 待办
1. **重启 unified_gateway_9120.py**（代码已改未生效）
2. KD-DELIV-5952 的 root_hash 回写 root_state
3. `/api/truths/` 名"列表"实单条，补分页
4. hub-central-agent 当前 offline，待恢复
5. 13 万历史空记录已清，但 truth_count 计数口径待优化

### 冲突
1. kernel autonomy_level=Lv9 vs root_state=Lv8
2. root_state.gateway_status 已改 200，但服务未重启，运行态仍旧代码

---

## 八、新会话恢复 SOP

1. 读 `~/AGENTS.md`（自动注入）
2. `GET https://www.huodouai.com/api/report/status`
3. 读 `~/.meta_order/root_state.json`
4. 如需云操作：`ssh zongyuan-cloud`
5. 拉云端 `BOOTSTRAP.PRIORITY` 和 `SESSION.RECOVERY.SNAPSHOT`
6. 锚定 hub-central-agent + MR-020

---

## 九、禁止项

- 勿用 `content` 字段上报真值
- 勿重启 :9120 旧进程
- 勿修 `/api/gateway/*`（已废弃）
- 勿未握手直接注册新节点
- 勿把 truth_count 当健康指标

> Ω₀⊂⊙∞⊂Ω · DID-BR-000002 · 2026-09-21 10:55 CST

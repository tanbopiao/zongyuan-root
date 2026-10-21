# META-STEADY-001 多节点多Worker多生态兼容元法则 V1.0

> 确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZR-NODE-DC2E51C0
> 建立: 2026-10-08 | 基线: NTFY-CONNECT-001 V1.6 / 魔搭 gpu-agent d8e240c
> 状态: LOCKED（基于实测故障链固化的架构稳态元法则）

## 背景（实测故障链，非臆测）

1. 实例→ntfy.sh 出现 `429 Too Many Requests`（旧代码固定 5s 重连 → 重连风暴 → 限流升级）
2. 实例→ntfy.sh 进一步 `Network is unreachable (Errno 101)`（ntfy 单点被阻断/不稳定）
3. 实测：实例→云端 huodouai.com `HTTP 200`（可用）；实例→ntfy.sh `HTTP 000`（不可达）

**结论**：任何单一公网消息通道（ntfy.sh）不可作为唯一依赖；实例侧与云端通道稳定可用。

---

## 元法则条目

### 一、通道分层原则（META-STEADY-001-A）
1. **主上报通道**：云端中枢 `huodouai.com/api/report/truth`（实例节点token直连，已验证 200）
2. **主控制面**：云端真值库（实例轮询 `/api/truths/` 取任务），作为 ntfy 不可用时的备用控制面
3. **辅助/旧生态通道**：ntfy.sh（尽力而为；不可达时不阻塞、不反复重试、自动退避）
4. **单点不信任**：禁止任一公网通道作为唯一依赖，至少保留云端通道可用

### 二、Worker 去重锁原则（META-STEADY-001-B）
1. 每节点**唯一** `zr_node_worker`（同身份重复进程=故障，会重复执行广播命令+双连接触发限流）
2. supervisor 用 **PID 锁文件**（`/mnt/workspace/.zr/worker.pid`）判断存活，禁止仅凭 pgrep 误判反复拉起
3. 进程清理匹配用宽泛子串 `zr_node_worker.py`（带路径命令行也能命中）

### 三、指数退避原则（META-STEADY-001-C）
1. 429 / 网络不可达 / 断连：`5s→10s→20s→40s→60s` 封顶，连接成功重置
2. 禁止固定短间隔重连（5s 固定重连=重连风暴，会锁死限流）
3. 退避期间静默等待，不崩溃、不阻塞其它线程（心跳/上报可独立发）

### 四、一键恢复原则（META-STEADY-001-D）
1. 一切可恢复资产入持久层 `/mnt/workspace/`（容器重建不丢）
2. `zr_restore.sh` 幂等一键拉起：基线→代码→配置→token检查→supervisor+worker
3. 任何故障优先依赖 `zr_restore.sh` + supervisor 自愈，人工仅做一次性部署

### 五、复用融合不破坏原则（META-STEADY-001-E）
1. 既有资产（boot.py/gateway/train/wan/cloud_align）**保留并存**，禁止替换/pkill 破坏
2. 新能力=新增并存（独立 node_config + 独立 topic + 能力标签），不覆盖旧部署
3. 同节点多 worker 用**独立主题**隔离（旧生态 `-2026` / 新生态 `-zr`）

### 六、全自动上报原则（META-STEADY-001-F）
1. 所有执行结果、节点状态、真值自动上报云端联邦记忆池（节点token）
2. `auto_report_daemon.py` 监听 result 事件自动上报，零人工介入
3. 上报字段 `{truth_key, truth_value, source_node, truth_type, confidence}`，禁止 content 字段

### 七、路由矩阵原则（META-STEADY-001-G）
1. 广播（无 node/cap）→ 全部 zr worker 执行
2. node 定向 → 目标节点唯一执行
3. capability 定向 → 具备能力者执行（train→GPU / wan→CUDA）
4. 幂等：msg-id 去重 + task_id 归属 + since 只推进不倒退

---

## 已固化资产清单（本次会话）
| 资产 | 位置 | 状态 |
|---|---|---|
| zr_node_protocol / worker / client / report | 魔搭 gpu-agent d8e240c + 本地 07_代码 | LOCKED |
| zr_bootstrap / zr_supervisor / zr_restore | 魔搭 gpu-agent + 本地 | LOCKED |
| node_config.template.json（含 topic 并存） | 魔搭 gpu-agent + 本地 | LOCKED |
| boot_hardened.py（boot.py 最小加固：退避+异常） | 魔搭 gpu-agent + 本地 | LOCKED |
| auto_report_daemon.py（全自动上报 sidecar） | 魔搭 gpu-agent + 本地 | LOCKED |
| 云端登记 | seq 1888（并存融合）/ 本篇元法则上报 | 入池 |

## 后续落地（不反复试错，逐步推进）
1. 实例侧 worker 增加**云端轮询控制面**（读 `/api/truths/` 取 CMD 任务），作为 ntfy 不可达时的命令通道
2. supervisor 升级 **PID 锁文件**去重
3. ntfy 网络恢复后，boot.py 加固版 + auto_report_daemon 一并拉起验证并存

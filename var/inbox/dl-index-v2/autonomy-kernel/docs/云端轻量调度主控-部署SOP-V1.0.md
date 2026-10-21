# 云端轻量调度主控 · 部署与启动记忆

确权：Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 协议 NTFY-CONNECT-001
生成时间：2026-10-08
状态：**已部署并验证运行**（腾讯云 123.207.202.158）

---

## 一、这是什么

**云端轻量调度主控**（`zr_cloud_ctl.py`），跑在腾讯云中枢服务器上，**零 ms-agent 依赖**，
复用现有 worker 联通协议（NTFY-CONNECT-001），做三件事：

1. **订阅结果主题** → 收所有同源 worker 的 online / heartbeat / done 回传，维护节点表
2. **下发命令** → 广播或定向给在线 worker（复用 ntfy 命令主题 `zongyuan-kunlun-2026`）
3. **云端真值上报** → 复用网关 `/api/report/truth`（X-DID + token）

不替代 ms-agent 框架；它只是"轻量主控"，符合最小额度/不折腾偏好。

## 二、部署位置（云端）

| 项 | 值 |
|---|---|
| 服务器 | 腾讯云轻量 `lhins-laotwc5e` 123.207.202.158（OpenCloudOS 9）|
| 主控脚本 | `/www/wwwroot/huodouai.com/zhongshu/zhongshu-server/zr_cloud_ctl.py` |
| 协议包 | 同目录 `zr_node_protocol.py`（复用，未覆盖）|
| 日志 | `/www/wwwroot/huodouai.com/zhongshu/data/msagent-ctl.log` |
| 台账 | `/www/wwwroot/huodouai.com/zhongshu/data/msagent-ctl-ledger.jsonl` |
| 节点表 | `/www/wwwroot/huodouai.com/zhongshu/data/msagent-nodes.json` |
| 控制面 | `127.0.0.1:9010`（仅本机，token 保护）|

**无损保障**：不改 gateway(9001) / scheduler / 真值库 / 官网docroot / 现有worker；新端口 9010 仅本机监听。

## 三、本地启动命令（一条拉起）

```bash
TOKEN=$(grep '^ZR_TOKEN=' /home/user/ZONGYUAN-ROOT/04_系统配置/凭证/active_token.env | cut -d'"' -f2)
ssh -o BatchMode=yes huodouai-cloud "ZR_TOKEN='$TOKEN' ZR_CTL_TOKEN='ZR-CTL-2026-OMEGA' nohup python3 /www/wwwroot/huodouai.com/zhongshu/zhongshu-server/zr_cloud_ctl.py > /www/wwwroot/huodouai.com/zhongshu/data/msagent-ctl.log 2>&1 &"
```

SSH 别名：`huodouai-cloud` → `~/.ssh/zr_cloud_ed25519` → root@123.207.202.158:22

## 四、控制面 API

```bash
# 健康 + 节点快照
curl -s -H 'X-CTL-Token: ZR-CTL-2026-OMEGA' http://127.0.0.1:9010/health
# 下发命令（广播）
curl -s -X POST -H 'X-CTL-Token: ZR-CTL-2026-OMEGA' -H 'Content-Type: application/json' \
  -d '{"cmd":"echo hi","node":""}' http://127.0.0.1:9010/cmd
# 下发命令（定向节点）
curl -s -X POST -H 'X-CTL-Token: ZR-CTL-2026-OMEGA' -H 'Content-Type: application/json' \
  -d '{"cmd":"echo hi","node":"ZR-NODE-MODEL-dsw-223619"}' http://127.0.0.1:9010/cmd
# 上报真值
curl -s -X POST -H 'X-CTL-Token: ZR-CTL-2026-OMEGA' -H 'Content-Type: application/json' \
  -d '{"key":"TEST.K","value":{"k":"v"}}' http://127.0.0.1:9010/report
```

## 五、已解决的关键坑

1. **ntfy 订阅流读取**：云端 Python 3.11 的 `HTTPResponse` 无 `iter_lines`（那是 requests 的），
   已改用 `readline()` 循环。**若再报 `'HTTPResponse' object has no attribute 'iter_lines'` → 用 readline 版。**
2. **SSH 多行命令 255**：pkill + 多行带引号会触发 SSH 会话终止，**拆单行执行**。
3. **腾讯云密钥配额 10/10**：无法 CreateKeyPair 新建；本地已有 `~/.ssh/zr_cloud_ed25519`
   （=腾讯云 `zryinbaideploy`，指纹 SHA256:RL08）可直接登录，**无需新建密钥**。

## 六、验证状态（2026-10-08）

- ✅ 主控进程运行（PID 100860）
- ✅ 网关健康上报成功：truth_count 2996，seq 2996
- ✅ 控制面 9010 监听，/health /cmd /report 均正常
- ✅ 命令广播下发 publish_status=200
- ✅ 台账 msagent-ctl-ledger.jsonl 自动记录

### 真实握手测试（通过）— 完整双向闭环

2026-10-08 18:20 通过本地测试 worker（ZR-NODE-TEST-LOCAL-001）完成真实握手：

```
云端主控 --cmd--> ntfy(zongyuan-kunlun-2026) --> worker执行
     --> 回传 done + 真实输出 --> ntfy(result) --> 云端主控节点表
```

验证证据：
- 命令下发：`echo HANDSHAKE-OK && hostname && date`，定向 node，publish_status=200
- worker 执行日志：`[执行] src=ZR-CLOUD-CTL-001 task=t-handshake-001`
- 主控节点表：`type=done, last_out=HANDSHAKE-OK\nvefaas-...-sandbox\nThu Oct 8 06:20 PM +08 2026`
- 台账：命令记录 publish_status=200

**结论：云端主控 → 任意同源 worker 双向握手闭环打通。**
任何在线 worker 上报 online 后自动入节点表，主控可定向/广播下发命令并收回执行结果。

### 自愈守护（2026-10-08 补齐）— systemd 三服务托管

排查确认：网关/调度器本就有 systemd 托管，主控本次补上，**三服务全部自愈**：

| 服务 | systemd unit | 状态 | 自愈 |
|---|---|---|---|
| 真值网关 | zhongshu-gateway.service | active+enabled | ✅ Restart=always |
| 调度器 | zhongshu-scheduler.service | active+enabled | ✅ Restart=always |
| **云端主控** | **zr-cloud-ctl.service（新增）** | **active+enabled** | ✅ Restart=always, RestartSec=5 |

主控自愈实测：故意 kill 主控进程(104010) → systemd 自动拉起新进程(104038)，服务保持 active，控制面恢复。

**至此"自动运行 + 自愈"闭环达成。**

### 自动决策能力（2026-10-08 新增）— "自己找事做"

给主控新增**自动决策循环**：周期性扫描任务池 + 在线节点表，按节点能力自动匹配派发待办任务，无需人工下发命令。

核心机制：
- **任务池**：`data/msagent-taskpool.jsonl`，投递待办任务（status=pending）
- **决策循环**：每20s扫描，找能力匹配的在线节点自动派发
- **能力匹配**：`node_capability()` 按节点名启发式（gpu/dsw/model→含 train/infer；默认 echo/ls/python3）
- **控制面接口**：`POST /enqueue` 投递任务进池

实测证据（2026-10-08，worker ZR-NODE-TEST-DECIDE-002）：
```
[决策] 派发 t-auto-001 → ZR-NODE-TEST-DECIDE-002 | echo AUTO-DECISION-OK
[决策] 派发 t-auto-002 → ZR-NODE-TEST-DECIDE-002 | echo AUTO-DECISION-OK-2
```
- 仅投任务进池，未手动下发 → 主控自动识别节点、自动匹配、自动派发
- worker 自动执行并回传 done，任务池自动标记 dispatched

**"自动决策"能力达成。**

### RSI 自我进化（2026-10-08 新增）— 从"准自治"到"真自治"

给主控新增 **RSI 自我进化模块**：基于历史决策结果自我评估、自我调整派发策略。

核心机制：
- **节点信誉表**：`data/msagent-evolution.json`，每个节点有信誉分 score（初始100）
- **进化学习**：`on_result` 收到 done/error → 更新信誉（成功+2，失败-8，错误-5）
- **策略自适应**：`dispatch_one` 按信誉降序选节点，低信誉(<40)剔除
- **进化评估**：`evolution_thread` 每2分钟评估，高信誉(≥120)/低信誉(<50淘汰候选)上报真值中枢

实测证据（2026-10-08，worker ZR-NODE-TEST-EVOLVE-001）：
```
[决策] 派发 t-evolve- → ZR-NODE-TEST-EVOLVE-001(信誉100) | echo EVOLVE-TASK-
[完成] ZR-NODE-TEST-EVOLVE-001 | t-evolve- code=0
```
信誉表变化：score 100 → 102 → 104（2次成功，win=2, lose=0）
- worker 上线 → 决策按信誉派发 → 完成回传 → 信誉自动+2
- **主控会自我学习节点可靠性，自动优先高信誉节点**

**至此"自动决策 + 自我进化"闭环达成，云端中枢进入真自治状态。**

### ntfy 限流经验（重要坑）

云端出口 IP 高频轮询 ntfy 会触发 **429 限流**（长窗口），导致主控收不到消息。
规避：
- 订阅用**低频率长轮询**（poll=1），连接间加 5s 最小间隔
- 429 时 **30s 长退避**，指数退避封顶 60s
- 不要高频 curl 同一主题测连通（会加剧限流）
- 限流是暂时的，恢复后自动继续（本机+云端恢复后均 200）

## 七、回滚

主控已由 systemd 托管，回滚用：
```bash
ssh -o BatchMode=yes huodouai-cloud "systemctl stop zr-cloud-ctl.service && systemctl disable zr-cloud-ctl.service"
```
停主控不影响网关/调度器/官网，中枢零影响。

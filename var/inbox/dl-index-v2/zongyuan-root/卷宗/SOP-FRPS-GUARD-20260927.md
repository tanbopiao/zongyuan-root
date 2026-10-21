# frps(7000) 内核守护链路 SOP

- **事件 ID**：SOP-FRPS-GUARD-20260927
- **锚定**：Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ NODE-DEV-DOUBAO-WORK-001
- **适用**：腾讯云轻量服务器 `lhins-laotwc5e`（123.207.202.158）frps 主隧道守护
- **版本**：v1.1（2026-09-27 自愈机制排查完成，原子锁修复生效，加固+锁档）
- **原则来源**：META-RULE-012（MR12-4 全局互斥锁）、META-RULE-WORKER-HARDENING-001（脚本 555 只读 + SHA-256 登记）、META-FIVE-LOCK-001、HASH-LEDGER append-only

---

## 〇、体系定位

**云端 = 智能大脑；本地 worker = 大脑的手脚；frp 隧道 = 大脑与手脚的神经。**

- frps(7000) 为本地 frpc 的主隧道服务端（kunlun-8443 / kunlun-8089 / kunlun-gw-19120 三条隧道）。
- **运行形态约束（用户定案）**：7000 保持 nohup 手工启动形态，**不引入 systemd 托管**；由守护脚本实现崩溃自愈。
- frps-legacy(7100) 由 systemd（frps-legacy.service）管理，守护脚本**只观测告警、不接管**。

---

## 一、守护架构（双层自愈）

| 层 | 机制 | 间隔 | 职责 |
|---|---|---|---|
| 快速守护 | `frps_guard.sh`（cron） | 每 2 分钟 | 端口探测 → 发现 7000 未监听 → 拉起 → 复检 → 二次重试 → 上报 |
| 兜底 | `auto_heal.sh`（原体系） | 每 10 分钟 | 全域健康兜底（非 frps 专项） |

**原子互斥锁（MR12-4）**：`mkdir /tmp/frps_guard.lock`——同一时刻仅一个守护实例执行，杜绝 cron 与手动并发双拉起（这是 v1.0→v1.1 修复的核心缺陷）。

---

## 二、自愈失败机制排查结论（v1.1 实测）

| 现象 | 根因 | 结论 |
|---|---|---|
| TAT 会话内模拟 kill 后拉起失败 | **7500 dashboard 端口竞争**（frps.log 6 条 `bind: address already in use`）+ **TAT 会话结束清理其启动的后台进程** | 非脚本缺陷；cron 环境拉起不受会话清理影响，多次成功自愈 |
| cron 触发与手动触发瞬时并存 | 旧版 `echo $$` 锁非原子，双实例并发 | v1.1 改为 mkdir 原子锁后消除（并发时后到者静默退出） |
| 7000 恢复后 frpc 重连 | frpc 保活 cron 拉起，三条隧道 `start proxy success` | 隧道自愈闭环成立 |

**运维要点**：
- **禁止在 TAT 会话内验证守护拉起**（会话清理机制导致假失败）；验证走 cron 触发日志（`/opt/ZONGYUAN-ROOT/logs/frps_guard.log`）。
- 拉起失败一律先查 `frps.log` 的 `bind: address already in use`——7500 被占说明存在僵留实例，先 `pkill -f 'frps -c /opt/frp/frps.toml'` 清理再拉起（脚本二次重试已内置该逻辑）。

---

## 三、脚本部署与加固

**本地**：`/home/user/ZONGYUAN-ROOT/scripts/frps_guard.sh`（chmod 555，SHA-256 登记于 `meta-rules/worker-hardening.json`）
**云端**：`/opt/ZONGYUAN-ROOT/scripts/frps_guard.sh`（chmod 555，与本地哈希一致）
**cron**：`*/2 * * * * /bin/bash /opt/ZONGYUAN-ROOT/scripts/frps_guard.sh`（已挂载，幂等去重）
**日志**：`/opt/ZONGYUAN-ROOT/logs/frps_guard.log`

### 加固登记

| 资产 | 权限 | SHA-256 |
|---|---|---|
| scripts/frps_guard.sh | 555 | `7f1e213751b110f173b328c1fb7491f107352587ae900548aac85f8cf3d63005` |

升级流程（META-RULE-WORKER-HARDENING-001）：改脚本 → 重算哈希 → 更新 `worker-hardening.json` → 恢复 444 → 全域锁档 → 上报。

---

## 四、守护事件流（真值网关上报）

| 事件 | 触发 | 载荷要点 |
|---|---|---|
| `frps_guard_revive` | 7000 被拉起并恢复监听 | node=did=detail=时间戳 |
| `frps_guard_fail` | 二次重试仍失败 | 升级告警，人工介入 |
| `frps_guard_legacy_down` | 7100 未监听（仅观测） | systemd 管辖提示 |

上报端点：`https://www.huodouai.com/api/report/truth`（无尾部斜杠）｜ 头：`X-DID: DID-BR-000002`｜ 失败不阻塞主流程。

---

## 五、故障速查表

| 症状 | 排查 | 处置 |
|---|---|---|
| 7000 未监听 | `ss -tln \| grep ':7000 '`；`pgrep -af frps` | 等 2 分钟 cron 守护；或手动 `bash /opt/ZONGYUAN-ROOT/scripts/frps_guard.sh`（勿在 TAT 会话验证） |
| 守护日志 ERROR | `tail -20 frps.log` 查 bind 错误 | 清僵留实例后重试（脚本已内置） |
| 守护锁残留 | `/tmp/frps_guard.lock` 存在但无守护进程 | `rmdir /tmp/frps_guard.lock`（原子锁目录空则自动消失） |
| 隧道断 | 本地 `pgrep -ax frpc`；云端 7000 状态 | 等保活 cron（*/10）；手动 `env -u ... frpc -c var/frp/frpc.toml` |
| 19120 无响应 | 本地 `ss -tln \| grep ':9120 '`（网关未起） | `bash scripts/gateway_keepalive.sh` |

---

## 六、验证记录（2026-09-27）

1. T0 基线：7000 pid=3120785 / 7100 pid=2877654（双轨共存）。
2. T1 幂等：正常期手动执行守护脚本 → 进程不变（PASS）。
3. T2 模拟消亡：kill -9 7000 → 7000 无监听。
4. T3 自愈：cron 轮次拉起（09:46）→ 7000 恢复监听（pid 3129020）；frpc 重连三条隧道 `start proxy success`。
5. 全链路：云端 19120 → 隧道 → 本地 9120 → `/healthz 200`（upstreams ok）。
6. 失败机制：frps.log 6 条 7500 bind 冲突 + TAT 会话清理 → 定位为环境机制，脚本经原子锁修复后 cron 环境自愈成立。

---
*本 SOP 随守护链路资产一并全域锁档；变更须走五层链式锁与加固升级流程。*

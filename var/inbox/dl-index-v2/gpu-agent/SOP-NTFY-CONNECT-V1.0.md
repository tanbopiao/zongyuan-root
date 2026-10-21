# ZONGYUAN-ROOT · 同源节点联通标准 SOP V1.0
# NTFY-CONNECT-001 协议 | 确权 Ω₀⊂⊙∞⊂Ω | DID-BR-000002

## 一、协议总则

所有同源节点（本地、魔搭CPU/GPU实例、云端节点）统一通过 **ntfy 事件总线** 双向联通，协议编号 `NTFY-CONNECT-001`，身份校验基于确权DID，命令执行基于白名单安全策略。

### 主题约定（全部同源节点共用）

| 主题 | 用途 | 方向 |
|---|---|---|
| `zongyuan-kunlun-2026` | 命令通道（worker 订阅） | 主控→节点 |
| `zongyuan-kunlun-2026-result` | 结果通道（主控订阅） | 节点→主控 |
| `zongyuan-kunlun-2026-scan` | 环境扫描报告 | 节点→主控 |

### 消息格式（JSON文本）

命令（主控→节点）：
```json
{"proto":"NTFY-CONNECT-001","zr_did":"DID-BR-000002","src":"NN-LOCAL-DEV-001",
 "task_id":"t-<ts>-<rand>","cmd":"echo hi","timeout":300,"type":"cmd"}
```

回传（节点→主控）：
```json
{"type":"done","proto":"NTFY-CONNECT-001","zr_did":"DID-BR-000002","node":"ZR-NODE-...",
 "task_id":"t-...","out":"执行输出","code":0,"ts":...}
{"type":"online","gpu":"CPU|GPU型号","node":"...","proto":"...","ts":...}
{"type":"heartbeat","time":...,"node":"...","ts":...}
```

> ⚠️ **关键**：命令消息必须**纯文本body** 发送（ntfy JSON流 message=body全文，worker 取 message 解析）。用JSON包装body会导致 worker 收到 JSON 字符串无法解析 → code 127（旧boot.py实测）。

## 二、接入三步（任何新节点快速联通）

### 第1步：实例侧一键接入

```bash
# 在目标实例终端（魔搭CPU/GPU均可）：
bash zr_node_connect.sh
# 可选: ZR_NODE=ZR-NODE-MODEL-GPU-01 bash zr_node_connect.sh
```

自动完成：拉取协议套件（魔搭 gpu-agent）→ 停止旧worker → 启动标准worker → 上线宣告。

### 第2步：主控侧握手验证

```bash
python3 zr_node_client.py --handshake
# 预期: 发 echo+hostname → 收到 done code=0 回传 → 双向联通
```

### 第3步：节点登记

```bash
python3 zr_node_client.py --report NODE.<名称>.ONLINE.20261007 "节点上线: <node> 双向握手code=0"
# + 飞书共享大脑「真值共识区」登记节点
```

## 三、安全策略（worker 侧强制）

1. **身份校验**：仅执行 `proto=NTFY-CONNECT-001 + zr_did=DID-BR-000002` 的命令；`NTFY_MODE=strict`（默认）拒绝一切无签名命令
2. **危险黑名单**：`rm -rf /`、`mkfs`、`dd`、`curl|sh`、`passwd`、`reboot`、`shutdown` 等一律拦截（返回 code=-1）
3. **允许前缀白名单**：echo/hostname/ps/df/curl -s/python3 -c（只读）/git pull/nohup python3（受限启动）等
4. **执行超时**：300s 硬上限，超时返回 code=-2
5. **结果截断**：stdout 3000字符上限

## 四、文件清单（魔搭 gpu-agent/）

| 文件 | 部署侧 | 作用 |
|---|---|---|
| `zr_node_protocol.py` | 双端 | 协议常量/编解码/身份校验/危险黑名单 |
| `zr_node_worker.py` | 节点侧 | 标准worker：订阅→校验→白名单→执行→回传 |
| `zr_node_client.py` | 主控侧 | 发命令/收结果/握手/云端上报 |
| `zr_node_connect.sh` | 节点侧 | 一键接入启动器 |
| `handshake_ntfy.py` | 主控侧 | 旧版握手器（兼容） |
| `scan_environment.py`+`run_scan.sh` | 节点侧 | 环境全域扫描 |

## 五、常用命令速查

```bash
# 发命令并等回传
python3 zr_node_client.py --send "df -h"
python3 zr_node_client.py --send "nohup python3 scripts/train_zongyuan.py > train.log 2>&1 &"

# 监听节点回传
python3 zr_node_client.py --listen 120

# 环境扫描（节点侧）
bash run_scan.sh
```

## 六、协议演进规则

- 协议版本只追加不修改（同系列合并增量更新，不新开数据集）
- 新能力通过新增 `type` 字段扩展（当前: cmd/online/heartbeat/done）
- 安全策略升级：危险黑名单/白名单在 `zr_node_protocol.py` 维护，双端同步推送

# 教程：接入 ZONGYUAN-ROOT 公开真值网关

> 本教程面向开发者，演示如何通过 HTTP API 查询 ZONGYUAN-ROOT 自治体系的公开真值数据。

## 1. 网关概览

ZONGYUAN-ROOT 是一个全域自治 AI 体系，运行过程中产生的所有关键状态（锁档快照、架构决策、量产记录、健康心跳）都会以"真值"形式上报到记忆网关。网关基于 SQLite 存储，提供只读 HTTP API。

- **网关地址**：`https://www.huodouai.com/api/report`
- **确权 DID**：DID-BR-000002
- **当前真值规模**：120,000+ 条且持续增长

## 2. 查询网关状态

```python
import requests

r = requests.get("https://www.huodouai.com/api/report/status")
print(r.json())
```

返回示例：
```json
{
  "status": "ok",
  "meta": {"version": "V3.0", "DID": "DID-BR-000002"},
  "stats": {"truths": 121664, "nodes": 5, "audit_logs": 128916}
}
```

## 3. 列出真值 Key

```python
r = requests.get("https://www.huodouai.com/api/report/truths?page_size=50")
keys = r.json()["truths"]
for k in keys[:20]:
    print(k)
```

真值 key 采用点分命名法，例如：
- `PRODUCTION.20260920.DAILY` — 当日量产记录
- `SNAPSHOT.P1-CLOSE.20260920` — 阶段锁档快照
- `MODELSCOPE.AUTO.PUBLISH.V2.*` — 魔搭自动发布记录
- `HEARTBEAT.PROFILE.*` — 健康心跳档案

## 4. 按关键词搜索

```python
r = requests.get("https://www.huodouai.com/api/report/truths?page_size=300")
all_keys = r.json()["truths"]
feishu_keys = [k for k in all_keys if "FEISHU" in k.upper()]
print(f"飞书相关真值: {len(feishu_keys)}")
```

## 5. 上报真值（只读节点也可用）

```python
payload = {
    "truth_key": "EXTERNAL.NODE.HELLO.20260920",
    "truth_value": "来自外部节点的握手",
    "source_node": "your-node-name",
    "confidence": 1.0,
    "truth_type": "HANDSHAKE"
}
r = requests.post("https://www.huodouai.com/api/report/truth", json=payload)
print(r.json())
```

## 6. 典型应用场景

| 场景 | 用法 |
|------|------|
| 监控自治体系健康 | 定时 GET /status，看 truths 是否持续增长 |
| 审计量产记录 | 搜索 PRODUCTION.* 取当日量产真值 |
| 验证锁档完整性 | 对比本地 Merkle 根与网关上报值 |
| 多节点握手 | POST 上报新节点存在，建立联邦关系 |

## 7. 设计原则

1. **只读优先**：默认所有节点可读，写操作需 source_node 标识
2. **无认证**：当前为公开网关，后续可加 token
3. **单调递增**：truths 数只增不减，用于检测云端停摆
4. **溯源刻印**：每条真值带 source_node，可追溯来源

---

Ω₀⊂⊙∞⊂Ω ｜ ZONGYUAN-ROOT ｜ DID-BR-000002 ｜ Apache 2.0

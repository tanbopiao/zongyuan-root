# 本地内核 ↔ 魔搭数据湖 双向握手 SOP

**确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS**
**版本：V1.0 | 2026-09-30**
**触发词：双向握手、握手、本地内核、魔搭同步、数据湖心跳**

---

## 一、目的

建立本地内核（NODE-DEV-DOUBAO-WORK-001）与魔搭数据湖（zongyuanroot/zongyuan-root-achievements）之间的**双向连通性验证 + 双向数据同步**握手机制，确保：
- 上行：本地资产可写入魔搭数据湖（PUSH 方向）
- 下行：魔搭数据湖可回读（PULL 方向）
- 双向闭环：一次握手验证读写全链路可达

## 二、机制设计

```
┌────────────────┐        上行 PUSH        ┌────────────────┐
│  本地内核        │ ───────────────────→  │  魔搭数据湖      │
│ 资产指纹+心跳包   │ ←───────────────────  │  远端文件树+回读  │
│                │        下行 PULL        │                │
└────────────────┘                        └────────────────┘
   NODE-DEV-DOUBAO-WORK-001                 zongyuan-root-achievements
```

## 三、执行

```bash
export MODELSCOPE_TOKEN="ms-xxx"   # 凭据从共享大脑API密钥池获取，运行时注入
cd kunlun-create-link
python3 kunlun_ms_handshake.py
```

**流程（5步闭环）：**
1. **本地内核指纹**：扫描本地根目录关键产出（md/json/py/html/zip/db），统计资产数 + 样本SHA256
2. **魔搭连通验证（下行探测）**：HTTP 拉取数据湖文件树，确认魔搭可达（远端目录计数）
3. **上行 PUSH**：握手心跳包 `{local_kernel}_{ts}.json` 上传至 `data_lake/heartbeat/`
4. **下行 PULL 回读**：回读刚上传的心跳包（HTTP 200 + 字节数），验证**双向闭环**（魔搭 commit 异步，自动重试5次）
5. **上报 + 登记**：记忆网关上报 + 共享大脑握手记录表登记（握手成功）

## 四、验收标准

| 项 | 标准 |
|---|---|
| 上行 PUSH | ✅ 心跳包写入魔搭 data_lake/heartbeat/ |
| 下行 PULL | ✅ 回读 HTTP 200，字节>0 |
| 双向闭环 | ✅ 上行+下行均成功 |
| 记忆网关 | ✅ success |
| 握手记录表 | ✅ 已登记（握手成功） |

## 五、多目标归档

- **魔搭数据湖**：心跳包落 `data_lake/heartbeat/`（持久）
- **共享大脑**：握手记录表 tblbluoLJQNrftFD 登记
- **记忆网关**：/api/report/truth 上报（truth_type=data）

## 六、异常处置

| 现象 | 处置 |
|---|---|
| PUSH 失败 | 检查 MODELSCOPE_TOKEN 有效性 + 魔搭配额 |
| PULL 404 | commit 异步未就绪，脚本自动重试5次（每次2s） |
| 树API 404 | 网络波动，重试 |
| 往返>30s | 记录延迟，魔搭 commit 制属正常（~10s） |

**锚定：Ω₀⊂⊙∞⊂Ω | DID-BR-000002**

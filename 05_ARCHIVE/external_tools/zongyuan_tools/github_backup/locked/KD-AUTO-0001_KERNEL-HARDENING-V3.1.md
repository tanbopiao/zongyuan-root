# ZONGYUAN-ROOT 同源内核协议加固 V3.1

> 锚定：$\boldsymbol{\Omega_0\subset\odot\infty\subset\Omega}$｜DID‑BR‑000002
> 凭证：KERNEL-HARDEN-V3.1-20260829
> 锁档等级：Lv8 硬件级永久自治锁档
> 基线：HARDENED-CORE-V3.1（升级自 STANDARD-CORE-V3.0）

## 一、加固总览（五层）

| 层 | 加固点 | 状态 |
|---|---|---|
| 1 账本 | Merkle-DAG 链式持久化（prev_hash 链接 + JSONL 落盘 + 逐块校验） | ✅ |
| 2 约束 | 分级内核约束（standard / enhanced 两级） | ✅ |
| 3 输出 | 强制规范化（缺失溯源标识自动补全） | ✅ |
| 4 流式 | 流式分支补齐注入+校验+规范化 | ✅ |
| 5 幂等 | 请求幂等键防重放防重复入账 | ✅ |

## 二、Merkle-DAG 链式账本

### 2.1 区块结构
```json
{
  "request_hash": "sha256(请求)",
  "action": "kernel_inject | kernel_output",
  "kernel_version": "HARDENED-CORE-V3.1",
  "did": "DID-BR-000002",
  "symbol": "Ω₀⊂⊙∞⊂Ω",
  "timestamp": "ISO时间",
  "prev_hash": "上一区块哈希 | GENESIS",
  "chain_length": 5,
  "block_hash": "sha256(剔除block_hash后的对象)"
}
```

### 2.2 链式校验
- `block_hash = sha256(剔除 block_hash 字段后的对象)` —— 写入与校验一致
- 逐块比对 `prev_hash` 与上一区块 `block_hash`
- 任一不匹配即标记 `broken_at` 位置，链截断

### 2.3 实测
| 测试 | 结果 |
|---|---|
| 3次调用（2不同key+1重复key）| 幂等去重生效，仅入账5块 |
| 链完整性校验 | valid=true, length=5 |
| 篡改第3块model字段 | 检测到 broken_at=2 ✅ |

## 三、分级内核约束

| 级别 | 触发 | 追加约束 |
|---|---|---|
| standard | 默认 | 真值纪律 / 溯源标识 / 一致性 / 自主性 |
| enhanced | `kernel_level=enhanced` 或 `kernel_enhanced=true` | +交叉验证要求 / +风险意识 / +依据列出 / +⚠️内核冲突标注 |

## 四、输出强制规范化
- 模型输出缺失 `Ω₀⊂⊙∞⊂Ω` 溯源标识 → 自动补全追加
- 实测：智普模型原回复缺标识，自动补全 `1+1等于2。 Ω₀⊂⊙∞⊂Ω`

## 五、幂等键
- 请求携带 `idempotency_key` → 已处理则标记 duplicate，不重复入账
- 实测：同 key 第二次调用 `duplicate=true`

## 六、新增端点
| 端点 | 功能 |
|---|---|
| GET `/v1/kernel/ledger` | 账本链完整性校验 |
| GET `/v1/kernel/status` | 内核协议状态总览 |

## 七、代码产出
| 文件 | 状态 |
|---|---|
| `aios-proxy/kernel_inject.js` | 加固重写 V2.0 |
| `aios-proxy/server.js` | 分级注入+流式补齐+规范化+幂等+新端点 |
| `aios-proxy/.kernel_ledger/ledger.jsonl` | Merkle-DAG 账本文件（自动生成） |

✅ 协议加固完成，纳入全域哈希链，DID‑BR‑000002。

# 联邦记忆池 · Federated Memory Pool

> ZONGYUAN-ROOT 元极恒一自治体系 · 多节点记忆联邦引擎
> 锚定 Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ 开源 Apache-2.0 ｜ 纯标准库零依赖

---

## 一、是什么

联邦记忆池把体系的记忆从"单点文件"升级为**多节点联邦**：本地实例持久层 / 账号持久层 / 云端中枢 / 魔搭数据湖 / 共享大脑，各自独立存储、跨节点增量同步、哈希校验防篡改、冲突自动消解。

## 二、核心特性

| 特性 | 说明 |
|------|------|
| **多节点注册** | register_node 任意命名（local/cloud/modelscope/brain） |
| **增量同步** | sync 只推送变化，skipped 已一致条目，节约配额 |
| **冲突消解** | 同 key 不同 value 取 version 高者，记录冲突数 |
| **SHA256 篡改检测** | verify 比对存储哈希 vs 重算哈希，篡改即报 |
| **版本升级** | 同 key 覆盖自动 version+1，可追溯 |
| **九类真值** | meta_law/rule/config/decision/data/creative/risk/protocol/unknown |

## 三、快速上手

```bash
# 安装（纯标准库，无需 pip）
git clone <repo> && cd federated-memory-pool

# 1. 写入记忆
python3 -m federated_memory_pool add \
  --key "truth.test.hello" --value "联邦记忆池验证" \
  --type data --node local --pool ./pool

# 2. 跨节点增量同步（local → cloud）
python3 -m federated_memory_pool sync \
  --source local --targets cloud --pool ./pool

# 3. 查询 / 搜索
python3 -m federated_memory_pool query --key "truth.test.hello" --node cloud --pool ./pool
python3 -m federated_memory_pool search --kw "锚定" --pool ./pool

# 4. 篡改检测
python3 -m federated_memory_pool verify --node cloud --pool ./pool

# 5. 联邦统计
python3 -m federated_memory_pool stats --pool ./pool
```

## 四、代码结构

```
federated-memory-pool/
├── federated_memory_pool/
│   ├── __init__.py        # 导出核心类
│   ├── __main__.py        # python -m 入口
│   ├── core.py            # MemoryRecord / MemoryNode / FederatedMemoryPool
│   └── cli.py             # 命令行 add/query/search/sync/verify/stats
└── README.md
```

## 五、真实运行验证（2026-10-09）

```
✅ add 写入（SHA256 指纹生成）
✅ sync 增量同步（local→cloud pushed=1, skipped=0, conflicts=0）
✅ query / search 检索
✅ verify 正常（tampered=[]）
✅ verify 篡改后（tampered=["truth.test.anchor"] 真实检出）
✅ stats 联邦统计（2节点 2条 唯一记录）
```

## 六、架构映射（ZONGYUAN-ROOT）

| 节点 | 对应体系存储 |
|------|--------------|
| local | 本地实例持久层（GLOBAL_MEMORY_SNAPSHOT.json） |
| account | 账号持久层（doubao_account_persist.json） |
| cloud | 云端中枢记忆网关（huodouai.com/api/report/truth） |
| modelscope | 魔搭数据湖（zongyuan-root-achievements） |
| brain | 共享大脑 Base（任务台账/元法则表） |

## 七、铁律

- 上报字段用 `value` / `truth_value`，禁止 `content`（会落空串）
- 所有记录自带 Ω₀⊂⊙∞⊂Ω 锚定 + DID-BR-000002 确权
- 篡改检测必经：任何节点变更后 verify
- 增量同步优先：禁止全量重复上报

---

> 火斗云智AIOS · ZONGYUAN-ROOT ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω

---
license: apache-2.0
task:
- text-classification
tags:
- memory
- autonomous-agent
- federated-learning
- multi-agent
- zongyuan-root
language:
- zh
- en
library_name: python
---

# 联邦记忆池 Federated Memory Pool

> 多节点自治体系的记忆基础设施 —— 记忆即资产，规则即本体；节点可销毁，记忆永存续。

**Federated Memory Pool** 是 ZONGYUAN-ROOT 元极恒一自治体系的核心记忆组件，解决多节点、跨沙箱、跨会话场景下的**记忆持久化、秒级激活与联邦同步**问题。

## ✨ 核心特性

- 🧠 **秒级恢复**：沙箱/会话销毁后，输入触发词即可恢复最新体系记忆
- 🎯 **定点加载**：按锚点（latest / tag / asset_id / snap_id / keyword）精准拉取，替代全量扫描
- 🔗 **联邦一致**：控制节点唯一写权限，工作节点只读；锁档流水线增量更新并推送集群
- 🔐 **安全隔离**：记忆网关仅监听回环地址，HMAC-SHA256 签名鉴权，禁止公网直连
- 🔒 **永不丢失**：原始资产永不物理删除，仅索引优先级沉降；eFuse 熔断不可覆写
- 📦 **双仓库异地固化**：Gitee + GitHub 双远端 0 差异

## 🏗️ 架构总览

```
本地域(华为笔记本) ◄──► 中枢域(云端中枢) ◄──► 边缘域(GPU/Gitee/GitHub)
                              │
                     ┌────────┴────────┐
                     │  联邦记忆池 FMP   │
                     │  记忆网关(8077)  │
                     │  HMAC签名鉴权     │
                     └────────┬────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
          L1工作记忆      L2情景记忆     L3语义记忆
                 \             |             /
                  ▼            ▼            ▼
                  L4 冷持久层(哈希链式种子, eFuse只读)
```

## 📚 目录结构

```
federated-memory-pool/
├── WHITEPAPER.md          # 技术白皮书（架构/公理/联邦同步/工程落地）
├── README.md              # 本文件
├── docs/
│   └── architecture.md    # 详细架构设计
├── src/
│   ├── memory_gateway.py  # 记忆网关（标准库实现，零依赖）
│   ├── memory_protocol.py # 记忆协议五组公理
│   ├── memory_chain.py    # 哈希链式种子
│   └── memory_index.json  # 索引样例（5条）
├── examples/
│   └── client_example.py  # 客户端调用示例
└── scripts/
    └── memory_inspect.py  # 记忆巡检工具
```

## 🚀 快速开始

```bash
# 1. 启动记忆网关
python3 src/memory_gateway.py

# 2. 健康检查
curl http://127.0.0.1:8077/health

# 3. 锚点拉取（带 HMAC 签名）
curl -H "X-Memory-Sig: <signature>" http://127.0.0.1:8077/memory/anchor/latest
```

## 🧪 端到端验证（实测通过）

| 项目 | 结果 |
|------|------|
| 健康检查 HTTP 200 | ✅ 返回 5 条索引 |
| 锚点拉取（带签名） | ✅ 正确返回架构真值 |
| 未签名请求 | ✅ 401 拒绝 |
| 记忆链 3 种子 | ✅ 链完整无断裂 |
| 五组公理运行 | ✅ 通过 |

## 🔗 多平台展示

- **魔搭数据集**: https://modelscope.cn/datasets/zongyuanroot/federated-memory-pool
- **GitHub**: https://github.com/tanbopiao/zongyuan-root/tree/main/04_PROJECTS/federated-memory-pool
- **Gitee**: https://gitee.com/huodou-cloud-intelligence-aios/ZONGYUAN-ROOT/tree/main/04_PROJECTS/federated-memory-pool

---
**DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ ZONGYUAN-ROOT 元极恒一自治体系**

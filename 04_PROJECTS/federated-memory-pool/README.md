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
                              ▼
                    记忆网关 :8077（HMAC鉴权/定点拉取/token节流）
                              │
                              ▼
                    记忆元索引 memory_index.json（795条资产，分片存储）
                              │
                              ▼
                    冷持久层：飞书三端 + 本地归档 + Merkle-DAG账本
```

## 🚀 快速开始

```bash
# 1. 启动记忆网关（依赖 FastAPI）
pip install fastapi uvicorn
python src/memory_gateway.py

# 2. 健康检查
curl http://127.0.0.1:8077/memory/health

# 3. 锚点拉取记忆
curl -X POST http://127.0.0.1:8077/memory/anchor \
  -H "Content-Type: application/json" \
  -H "X-Memory-Sig: <HMAC签名>" \
  -d '{"anchor_type":"latest","extract_mode":"truth_only"}'
```

## 📁 目录结构

```
federated-memory-pool/
├── WHITEPAPER.md          # 架构体系技术白皮书（完整版）
├── README.md              # 项目简介
├── docs/                  # 架构文档
├── src/                   # 核心源码
│   ├── memory_gateway.py  # 三域记忆网关
│   ├── memory_protocol.py # 记忆协议公理
│   └── memory_index.json  # 记忆元索引样例
├── examples/              # 使用示例
└── scripts/               # 部署/巡检脚本
```

## 📜 核心公理（AUTOKERN-MEMORY-PROTO V1.1）

1. **记忆恢复公理**：沙箱销毁后输入触发词秒级恢复；支持显式锚点定点加载
2. **元索引公理**：元索引只存指针/摘要/哈希，不存全文；控制节点唯一写权限
3. **记忆网关公理**：仅监听回环，HMAC-SHA256 鉴权；外部业务经 API 网关隔离
4. **记忆安全公理**：凭证环境变量托管，日志脱敏，只读锁档（444）

## 🧩 应用场景

- 多会话 AI 助手：新会话秒级恢复历史上下文与规则
- 多节点集群：控制节点统一写权限，工作节点只读消费
- 沙箱易逝环境：实例销毁后记忆从冷持久层完整恢复
- 合规审计：记忆请求全量埋点，30 天审计日志轮转

## 📄 许可

开源展示 · 免费使用 · 确权标识：Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ ZONGYUAN-ROOT

---

> **元极恒一 · 超认知永恒自治模式** | 主节点 hub-central-agent | DID-BR-000002 | 锚定 Ω₀⊂⊙∞⊂Ω

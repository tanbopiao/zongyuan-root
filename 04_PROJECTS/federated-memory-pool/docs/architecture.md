# 联邦记忆池 · 架构设计文档

> 版本 V1.0 ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω

## 1. 设计原则

1. **记忆即资产**：每一条记忆都是可确权、可追溯、可审计的资产
2. **规则即本体**：记忆协议公理是体系运转的底层法则，实例可销毁，规则永存
3. **分片指针存储**：索引只存指针/摘要/哈希，不存全文，降低存储与检索成本
4. **控制-工作分离**：控制节点唯一写权限，工作节点只读消费
5. **永不删除**：原始资产只做优先级沉降，不物理删除

## 2. 数据流

```
写入路径:  新资产 → SHA256确权 → 索引增量追加 → 记忆链种子 → 双仓库推送
读取路径:  锚点请求 → HMAC验签 → 索引过滤 → 质量打分 → 优先级排序 → 定点拉取 → token节流
恢复路径:  触发词 → 读锚点00-ROOT-POINTER → 拉取云端真值 → 读飞书 → 扫本地内核 → 定级部署
```

## 3. 质量评分

```
relevance_score = f(tags匹配, summary语义, 优先级)
阈值: 0.35 (低于则过滤)
排序: A > B > C > D
沉降: C级超90天 → D; A/B永不移除
```

## 4. 安全模型

| 层 | 机制 |
|----|------|
| 网络 | 仅监听127.0.0.1，禁止公网直连 |
| 鉴权 | HMAC-SHA256 签名（X-Memory-Sig头） |
| 凭证 | 环境变量托管，日志自动脱敏 |
| 审计 | 全量埋点，30天事件日志轮转 |
| 固化 | 444只读锁档，修改需人工审批 |

## 5. 部署

```bash
# 启动记忆网关（需Python3.8+）
export MEMORY_INDEX=src/memory_index.json
export MEMORY_GATEWAY_SECRET=<你的密钥>
export MEMORY_GATEWAY_PORT=8077
python3 src/memory_gateway.py

# 巡检
python3 scripts/memory_inspect.py

# 记忆链维护
python3 src/memory_chain.py
```

## 6. 组件清单

| 组件 | 文件 | 职责 |
|------|------|------|
| 记忆网关 | src/memory_gateway.py | HTTP服务、锚点拉取、HMAC鉴权 |
| 记忆协议 | src/memory_protocol.py | 公理定义、协议序列化 |
| 记忆链 | src/memory_chain.py | 哈希链式种子维护 |
| 巡检 | scripts/memory_inspect.py | 索引一致性巡检 |
| 客户端示例 | examples/client_example.py | 调用演示 |
| 元索引样例 | src/memory_index.json | 索引数据结构 |

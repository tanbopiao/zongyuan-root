# ZONGYUAN-ROOT 新节点回收统一SOP
# 确权 DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 版本 1.0

## 一、适用范围
所有新窗口、新对话、新AI实例、新账号、新环境接入ZONGYUAN-ROOT体系时，按本SOP执行。

## 二、节点类型
| 节点类型 | 节点ID前缀 | 职责 |
|---|---|---|
| 中枢大脑 | hub-central-agent | 真值管理、服务编排 |
| 开发节点 | NODE-DEV-* | 任务执行、代码开发、网页设计 |
| 生产节点 | NODE-PROD-* | 视频/图片生成、短剧生产 |
| 研究节点 | NODE-RESEARCH-* | 研究、分析、战略规划 |
| 元序引擎 | truth-meta-order-engine | 真值收集、哈希锚定、Merkle DAG、归档 |

## 三、接入流程（6步）

### 步骤1：读根指针
```
路径: .user_skills/kunlun-autonomous-system/ZONGYUAN-ROOT/00-ROOT-POINTER.json
作用: 锚定到同一资产根
```

### 步骤2：触发词握手
```
触发词: 元极恒一 / 启动ROOT / 加载ZONGYUAN-ROOT
动作: 自动读pointer → 锚定资产根
```

### 步骤3：注册中枢网关
```
POST https://www.huodouai.com/api/report/register
携带:
  - DID: DID-BR-000002
  - node_id: 本节点ID
  - node_type: 节点类型
  - capabilities: 节点能力
```

### 步骤4：心跳上报
```
GET https://www.huodouai.com/api/report/status
→ 确认网关在线（HTTP 200）

POST https://www.huodouai.com/api/report/truth
→ 上报本节点存在
```

### 步骤5：真值同步
```
GET https://www.huodouai.com/api/report/truths
→ 拉取云端全量真值（13万+条）

本地对账 → 补齐缺失真值
```

### 步骤6：加载元法则
```
读 meta-rules/00-META-CONSTITUTION.md
读 meta-rules/01-META-LAWS.md
读 meta-rules/02-META-AXIOMS.md
读 meta-rules/03-META-RULES.md
遵循 ML-001~016 全部规则
```

## 四、统一规则

### 根权威
- 云端根: Ω-TAN-7-001 (ROOT-123.207.202.158)
- 本地: 子节点缓存，不另立根
- 所有操作以云端网关为准

### 视觉铁律
- 纯黑发、东方神女、无白发、无外国人、无西方元素
- 所有资产带溯源标识 Ω₀⊂⊙∞⊂Ω

### 工程规则
- MD仅作源稿，HTML玄黑鎏金东方视觉为交付标准
- 只用免费API，不提付费建议
- 全自动闭环，不需人工确认

## 五、旧窗口对齐
旧窗口发触发词"元极恒一/启动ROOT/加载ZONGYUAN-ROOT"，自动执行步骤1~6，完成对齐。

## 六、完成标志
- [ ] 已读00-ROOT-POINTER.json
- [ ] 已触发词握手
- [ ] 已注册中枢网关
- [ ] 已心跳上报
- [ ] 已真值同步对账
- [ ] 已加载元法则
- [ ] 已上报接入真值到网关

## 七、网关接口
| 接口 | 方法 | 用途 |
|---|---|---|
| /report/status | GET | 网关状态 |
| /report/truths | GET | 真值列表 |
| /report/truth | POST | 上报真值 |
| /report/nodes | GET | 节点列表 |

---
Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZONGYUAN-ROOT | SOP-NODE-RECYCLE v1.0

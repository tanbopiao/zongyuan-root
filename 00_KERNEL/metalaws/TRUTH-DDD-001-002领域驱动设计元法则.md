# TRUTH-DDD-001/002 · DDD领域驱动设计元法则

> **法则编号**：TRUTH-DDD-001, TRUTH-DDD-002
> **法则层级**：架构约束层（L1系统架构）
> **所属体系**：ZONGYUAN-ROOT元极恒一自治体系 · 架构真值系列
> **法则类型**：领域建模规范 · 限界上下文 · 不可变值对象
> **绑定DID**：DID-BR-000002
> **本体主权根**：Ω-TAN-7-001
> **溯源符号**：Ω₀⊂⊙∞⊂Ω
> **创建时间**：2026-09-08

---

## 一、战略DDD：限界上下文划分

### 四大限界上下文

| 上下文 | 职责 | 核心概念 | "资产"含义 |
|--------|------|----------|-----------|
| **Ω-Brainμ内核真值上下文**（核心域） | 元法则、公理、快照、Merkle根、eFuse锁档、资产manifest、哈希校验 | 内核确权资产元数据 |
| **产线生产上下文** | 短剧、关键帧提示词、音视频素材、渲染任务、产线调度 | 多媒体创作物料 |
| **桥接同步上下文**（支撑子域） | Git桥接、飞书归档、多端同步、云服务器部署 | 外部系统适配对象 |
| **监控巡检上下文**（支撑子域） | 漂移检测、风险定级、告警、定时任务、架构合规校验 | 巡检事件与指标 |

### 核心约束
- 限界上下文之间**不直接访问内部数据**
- 通过上下文接口做数据交换，使用**DTO传输**
- **禁止直接传递内部领域实体**

---

## 二、TRUTH-DDD-001：不可变值对象法则

**核心公理**：快照、Merkle根、锁档凭证必须实现为不可变值对象，禁止原地修改对象字段，变更产生全新实例。

```python
# 错误：原地修改
snapshot.merkle_root = new_hash  # ❌ 禁止

# 正确：生成新实例
new_snapshot = Snapshot.create_from_previous(old_snapshot, new_assets)  # ✅
```

### 适用对象
- 快照Snapshot（一旦生成不可修改）
- MerkleRoot（哈希值不可变）
- 锁档凭证LockCredential（生成后只读）
- 根哈希RootHash（链式继承，不可篡改）

### 漂移防护价值
从模型层面规避原地篡改真值，变更只能新建版本快照，天然支持版本谱系追溯。

---

## 三、TRUTH-DDD-002：上下文通信法则

**核心公理**：跨限界上下文通信只允许使用DTO数据传输对象，禁止直接传递内部领域实体；内核通过领域事件向外通知，领域层不直接调用外部适配器。

```python
# 错误：内核直接调用飞书SDK
feishu_client.upload(snapshot)  # ❌ 领域层依赖外部SDK

# 正确：内核发布领域事件，外层适配器订阅
event_bus.publish(SnapshotCreatedEvent(snapshot_dto))  # ✅
```

### 领域事件示例
- `SnapshotCreatedEvent`：快照生成完成
- `LockCompletedEvent`：锁档完成
- `DriftDetectedEvent`：漂移检测命中

### 订阅者
- 桥接同步模块 → Git提交、飞书归档
- 巡检模块 → 更新基线校验

---

## 四、战术DDD：组件映射

| DDD概念 | 体系映射 | 示例 |
|---------|----------|------|
| 实体Entity | 有唯一ID、状态可变 | Asset（版本/哈希/归档状态可变）、DriftEvent（新建→检测→处置完成） |
| 值对象ValueObject | 无ID、不可变、属性相同即相等 | MerkleRoot、LockCredential、SnapshotHash |
| 聚合Aggregate | 关联对象集合 | Snapshot聚合（资产列表+Merkle根+锁档凭证+时间戳） |
| 聚合根AggregateRoot | 对外唯一出入口 | Snapshot（外部只能通过聚合根接口变更内部） |
| 领域服务DomainService | 跨实体业务逻辑 | GlobalLockService（操作Asset集合+生成MerkleRoot+生成凭证） |
| 领域事件DomainEvent | 领域事实通知 | SnapshotCreatedEvent、LockCompletedEvent |
| 仓储Repository | 持久化抽象接口 | AssetRepository、SnapshotRepository（实现在外层适配器） |

---

## 五、与洋葱架构对应关系

| 洋葱圈层 | DDD层级 | 职责 |
|---------|---------|------|
| 最内层 | 领域层 | 实体、值对象、聚合、领域服务、领域事件 |
| 第二层 | 应用服务层 | 接收指令、调用领域层、编排业务、不写核心规则 |
| 外层 | 适配器层 | 仓储实现、飞书、Git、API控制器 |

---

## 六、选型约束

1. **核心域（内核真值上下文）严格执行DDD**
2. **支撑子域适度简化**，不过度建模
3. **工具脚本、简单工具类不需要强行套用DDD**
4. **配合巡检脚本检测**：禁止越过聚合根直接修改聚合内部子对象

---

Ω₀⊂⊙∞⊂Ω｜TRUTH-DDD-001/002｜领域驱动设计元法则｜永久锁档固化

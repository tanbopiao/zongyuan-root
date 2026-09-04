# MWP (Multi-Writer Protocol) v1.0 协议规范

> **协议编号**: MWP-v1.0
> **发布日期**: 2026-08-30
> **体系归属**: ZONGYUAN-ROOT · Ω-Brainμ自治内核
> **协议状态**: 正式发布
> **替代**: 无（首个版本）

---

## 1. 协议概述

### 1.1 目的

MWP（Multi-Writer Protocol）是ZONGYUAN-ROOT体系中多写入者并发进化的标准化协议，定义了多写入者之间的握手、注册、心跳、事件提交、冲突协商、状态同步和注销的完整流程。

### 1.2 解决的问题

- 多写入者并发修改同一状态导致的数据覆盖
- 写入者身份不明确导致的权限混乱
- 并发修改无法检测和解决
- 状态不同步导致的认知偏差
- 重复提交导致的重复进化

### 1.3 设计原则

1. **事件溯源优先**: 所有变更作为不可变事件，状态由事件重放得到
2. **版本向量因果**: 使用Vector Clock检测并发和因果关系
3. **写入者身份化**: 所有写入者必须握手注册，获得身份和优先级
4. **仲裁串行化**: 事件由单一仲裁者串行应用，避免并发写入
5. **幂等性保证**: 相同事件多次提交只应用一次
6. **冲突可协商**: 并发冲突支持自动合并、优先级仲裁、人工审核三级解决

---

## 2. 写入者角色与优先级

### 2.1 角色定义

| 角色 | role值 | 默认优先级 | 说明 |
|------|--------|-----------|------|
| 定时任务 | scheduled | 0 | 定时进化任务，最高权威 |
| 常驻进程 | daemon | 1 | 后台常驻服务，系统状态维护 |
| 手动操作 | manual | 2 | 用户手动指令，用户意图 |
| API调用 | api | 3 | 外部API调用，最低权威 |
| 观察者 | observer | 10 | 只读，不能提交事件 |

### 2.2 优先级规则

- 优先级数字越小，权威越高
- 冲突时高优先级写入者胜出
- 同优先级采用最后写入胜出（LWW）或自动合并
- 观察者角色只能读取状态，不能提交事件

---

## 3. 协议流程

### 3.1 完整生命周期

```
写入者启动
    │
    ▼
[1. 握手 Handshake] ──→ 获得writer_id + session_token
    │
    ▼
[2. 心跳 Heartbeat] ←── 每300秒一次，维持活跃
    │
    ▼
[3. 事件提交 Event Submit] ──→ 标准化事件 → 仲裁队列
    │                              │
    │                              ▼
    │                        [4. 冲突检测]
    │                              │
    │                    ┌─────────┼─────────┐
    │                    ▼         ▼         ▼
    │               无冲突     可合并     不可合并
    │                    │         │         │
    │                    ▼         ▼         ▼
    │               直接应用   自动合并   [5.冲突协商]
    │                    │         │         │
    │                    └─────────┼─────────┘
    │                              ▼
    │                        应用到状态
    │                              │
    ▼                              ▼
[6. 状态同步 State Sync] ←── 写入者请求最新状态
    │
    ▼
[7. 注销 Unregister] ──→ 优雅退出
```

### 3.2 阶段详解

#### 阶段1: 握手（Handshake）

**请求**:
```json
{
  "protocol_version": "1.0.0",
  "writer_id": "scheduled_daily_0200",
  "role": "scheduled",
  "description": "每日凌晨2点定时进化任务",
  "priority": 0,
  "capabilities": ["truth_update", "kernel_write", "asset_lock"],
  "timestamp": "2026-08-30T02:00:00+08:00"
}
```

**响应**:
```json
{
  "status": "handshake_accepted",
  "protocol_version": "1.0.0",
  "writer_id": "scheduled_daily_0200",
  "role": "scheduled",
  "priority": 0,
  "session_token": "a1b2c3d4e5f6...",
  "challenge": "ch_abc123",
  "current_writers": 3,
  "current_state_version": "state_v1.2.3"
}
```

**规则**:
- writer_id必须全局唯一
- 已注册的写入者重新握手会更新session_token
- 未握手的写入者不能提交事件
- session_token用于后续所有操作的身份验证

#### 阶段2: 心跳（Heartbeat）

**请求**:
```json
{
  "writer_id": "scheduled_daily_0200",
  "session_token": "a1b2c3d4e5f6..."
}
```

**响应**:
```json
{
  "status": "heartbeat_ack",
  "writer_id": "scheduled_daily_0200",
  "timestamp": "2026-08-30T02:05:00+08:00",
  "active_writers": 3,
  "next_heartbeat_deadline": 300
}
```

**规则**:
- 心跳间隔: 300秒（5分钟）
- 超过300秒无心跳的写入者被标记为inactive
- inactive写入者的事件提交会被拒绝
- 心跳同时触发超时写入者清理

#### 阶段3: 事件提交（Event Submit）

**请求**:
```json
{
  "writer_id": "scheduled_daily_0200",
  "session_token": "a1b2c3d4e5f6...",
  "event_type": "truth_update",
  "payload": {
    "formula": "H = (1+T)(1+S)(1+E)(1+I)(1+O)(1+R)(1+B)",
    "value": 30.43
  },
  "priority": 0
}
```

**响应**:
```json
{
  "status": "applied",
  "event_id": "evt_0ed98e805c4ba87d",
  "idempotency_key": "idem_a1b2c3d4",
  "version_vector": {"scheduled_daily_0200": 1, "manual_A": 3},
  "priority": 0,
  "conflict_with": null,
  "resolution": null
}
```

**事件类型**:

| event_type | 说明 | 状态目标 |
|------------|------|----------|
| truth_update | 真值公式更新 | merged_state.truth_base |
| architecture_evolution | 架构进化 | merged_state.architecture |
| kernel_write | 内核协议写入 | merged_state.kernel |
| asset_lock | 资产锁档 | merged_state.assets |
| config_change | 配置变更 | merged_state.config |
| manual_override | 手动覆盖 | merged_state.manual_override |
| evolution_cycle | 进化循环计数 | merged_state.evolution_cycles |
| heartbeat | 心跳事件 | - |
| handshake | 握手事件 | - |
| conflict_resolution | 冲突解决 | - |
| state_sync | 状态同步 | - |

**幂等性**:
- idempotency_key = SHA256(event_type + sorted(payload))[:16]
- 相同key的事件只应用一次
- 重复提交返回`duplicate_rejected`

#### 阶段4: 冲突检测

**并发检测**:
```
事件A的版本向量: {A:1, B:0}
事件B的版本向量: {A:0, B:1}
→ A和B并发（concurrent=True）
→ 需要冲突解决
```

**字段重叠检测**:
```
事件A payload: {"formula": "H=abc", "value": 42}
事件B payload: {"value": 99, "name": "test"}
→ 重叠字段: ["value"]
→ 需要冲突解决
```

**冲突条件**: 并发 + 字段重叠 = 冲突

#### 阶段5: 冲突协商（Conflict Negotiation）

**冲突解决策略**:

| 策略 | resolution值 | 适用场景 |
|------|-------------|----------|
| 自动合并 | auto_merge | 重叠字段为集合/字典/计数器 |
| 优先级胜出 | priority_wins | 优先级不同，高优先级胜出 |
| 最后写入胜出 | last_write_wins | 同优先级，标量字段 |
| 人工审核 | manual_review | 同优先级，不可合并 |
| 拒绝 | reject | 低优先级事件被拒绝 |

**协商请求**:
```json
{
  "writer_id": "manual_A",
  "session_token": "...",
  "conflict_id": "conf_abc123",
  "proposed_resolution": "manual_review"
}
```

#### 阶段6: 状态同步（State Sync）

**请求**:
```json
{
  "writer_id": "manual_A",
  "session_token": "..."
}
```

**响应**:
```json
{
  "protocol_version": "1.0.0",
  "state_version": "state_a1b2c3d4",
  "version_vector": {"scheduled": 5, "manual_A": 3},
  "merged_state": {
    "truth_base": {...},
    "architecture": {...},
    "assets": {...}
  },
  "active_writers": {...},
  "event_count": 42,
  "applied_count": 40,
  "conflict_count": 2,
  "sync_type": "full_sync",
  "synced_at": "2026-08-30T07:30:00+08:00"
}
```

#### 阶段7: 注销（Unregister）

**请求**:
```json
{
  "writer_id": "manual_A",
  "session_token": "..."
}
```

**响应**:
```json
{
  "status": "unregistered",
  "writer_id": "manual_A",
  "message": "写入者 manual_A 已优雅退出MWP协议",
  "remaining_writers": 2
}
```

---

## 4. 数据结构

### 4.1 版本向量（Version Vector）

```json
{
  "scheduled_daily": 5,
  "manual_session_A": 3,
  "daemon_loop": 12
}
```

- 每个写入者一个逻辑时钟
- 提交事件时递增自己的时钟
- 合并时取每个写入者的最大值
- 用于检测并发和因果关系

### 4.2 协议事件（Protocol Event）

```json
{
  "protocol_version": "1.0.0",
  "event_id": "evt_0ed98e805c4ba87d",
  "event_type": "truth_update",
  "writer_id": "scheduled_daily",
  "writer_role": "scheduled",
  "timestamp": "2026-08-30T02:00:00+08:00",
  "version_vector": {"scheduled_daily": 1},
  "payload": {"formula": "H=abc"},
  "idempotency_key": "idem_a1b2c3d4",
  "priority": 0,
  "status": "applied",
  "conflict_with": null,
  "resolution": null,
  "applied_at": "2026-08-30T02:00:01+08:00",
  "ttl": 86400
}
```

### 4.3 写入者身份（Writer Identity）

```json
{
  "writer_id": "scheduled_daily",
  "role": "scheduled",
  "description": "每日定时任务",
  "priority": 0,
  "protocol_version": "1.0.0",
  "registered_at": "2026-08-30T02:00:00+08:00",
  "last_heartbeat": "2026-08-30T02:05:00+08:00",
  "capabilities": ["truth_update", "kernel_write"],
  "is_active": true,
  "session_token": "a1b2c3d4e5f6..."
}
```

---

## 5. 错误码

| 错误码 | 说明 |
|--------|------|
| HANDSHAKE_REQUIRED | 未握手，需要先执行handshake |
| INVALID_SESSION | session_token无效或已过期 |
| INVALID_ROLE | 角色不在允许列表中 |
| INVALID_EVENT_TYPE | 事件类型不支持 |
| DUPLICATE_REJECTED | 幂等重复，事件已应用 |
| CONFLICT_REJECTED | 冲突，低优先级被拒绝 |
| CONFLICT_MANUAL_REVIEW | 冲突，需要人工审核 |
| WRITER_INACTIVE | 写入者已超时未心跳 |
| PROTOCOL_VERSION_MISMATCH | 协议版本不兼容 |

---

## 6. 安全考虑

1. **会话令牌**: 所有操作必须携带session_token，令牌在握手时生成
2. **角色权限**: 不同角色有不同的事件提交权限
3. **优先级保护**: 低优先级写入者不能覆盖高优先级写入者的修改
4. **不可变日志**: 事件日志只追加不修改，提供完整审计
5. **心跳超时**: 异常退出的写入者会被自动标记为inactive
6. **观察者隔离**: observer角色只能读取，不能修改状态

---

## 7. 兼容性

### 7.1 向后兼容

- 协议版本号遵循语义化版本（MAJOR.MINOR.PATCH）
- MINOR和PATCH版本保持向后兼容
- MAJOR版本变更需要双写过渡

### 7.2 与现有系统集成

- `evolution_loop.py`: 注册为daemon角色，进化阶段提交为事件
- 定时任务: 注册为scheduled角色（优先级0）
- 手动操作: 注册为manual角色（优先级2）
- FastAPI: 注册为api角色（优先级3）
- 旧状态文件: 通过一次性迁移导入为事件

---

## 8. 实现参考

协议参考实现: `omega_brain/mwp_protocol.py`

核心类:
- `MultiWriterProtocol`: 协议主类
- `WriterIdentity`: 写入者身份
- `ProtocolEvent`: 协议事件
- `ProtocolHandshake`: 握手包
- `ConflictNegotiation`: 冲突协商包

---

## 9. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-08-30 | 首个正式版本，定义完整协议流程 |

---

Ω₀⊂⊙∞⊂Ω｜MWP v1.0 多写入者协议规范 · ZONGYUAN-ROOT · DID-BR-000002 · Ω-TAN-7-001

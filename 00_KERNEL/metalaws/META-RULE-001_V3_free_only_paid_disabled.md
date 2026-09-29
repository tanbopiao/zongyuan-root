# 元法则：免费唯一 · 禁用付费 V3.0

> 确权标识：DID-BR-000002 | 溯源标识：Ω₀⊂⊙∞⊂Ω
> 协议：ZONGYUAN-ROOT | 元法则编号：META-RULE-001
> 版本：V3.0（升级：付费人工审核 → 免费唯一·禁用付费）
> 状态：BLOWN_PERMANENT 永久固化

---

## 一、元法则定义

### 1.1 法则名称
**免费唯一 · 禁用付费**（Free Only, Paid Disabled）

### 1.2 版本历史
- V1.0（2026-09-05）：免费优先·付费确认（请求头/参数确认）
- V2.0（2026-09-05）：升级为付费人工审核（申请→审核→执行）
- V3.0（2026-09-05）：升级为免费唯一·禁用付费（所有付费模型一律不用）

### 1.2 法则编号
META-RULE-001

### 1.3 法则层级
**元法则**（最高优先级，高于所有业务规则、配置、临时指令）

### 1.4 适用范围
- ZONGYUAN-ROOT 全域自治体系
- 火斗云智 AIOS 所有AI调用
- 政务中台、企业向量库、智能体工作台、昆仑洞天短剧
- aiproxy 智能路由层
- 所有对外API服务

---

## 二、法则核心内容

### 2.1 第一原则：免费优先

**所有AI调用必须优先使用免费模型，只有在以下情况才允许使用付费模型：**

1. 所有免费模型均不可用（熔断/超时/限流/额度用尽）
2. 任务类型明确需要付费模型的特殊能力（如超长上下文>1M、深度推理、代码生成）
3. 用户明确指定使用付费模型
4. 经过付费确认流程后

**免费模型清单（永久免费/免费额度）：**
| 序号 | 模型标识 | 实际模型 | 服务商 | 费用 | 上下文 |
|------|----------|----------|--------|------|--------|
| 1 | zhipu | glm-4-flash | 智谱AI | 永久免费 | 128K |
| 2 | agnes | agnes-2.5-flash | Agnes AI | 全模态免费 | 1M |
| 3 | siliconflow | Qwen2.5-7B | 硅基流动 | 免费额度 | 32K |
| 4 | ollama-local | qwen2.5:0.5b | 本地 | 免费 | 4K |

**付费模型清单：**
| 序号 | 模型标识 | 实际模型 | 单次成本(元) |
|------|----------|----------|-------------|
| 1 | aliyun | qwen-turbo | 0.002 |
| 2 | hunyuan | glm-4-flash | 0.002 |
| 3 | kimi | kimi-k2.6 | 0.003 |
| 4 | doubao | doubao-seed-1-6 | 0.004 |
| 5 | doubao-reasoning | 推理模型 | 0.008 |
| 6 | doubao-reasoning2 | 增强推理 | 0.008 |

### 2.2 第二原则：禁用付费（V3.0升级）

**所有付费模型一律禁用，只使用免费模型：**

#### 禁用模型清单（7个）：

| 模型 | 类型 | 状态 |
|------|------|------|
| aliyun qwen-turbo | 文本 | ❌ 禁用 |
| kimi kimi-k2.6 | 文本 | ❌ 禁用 |
| doubao seed-1-6 | 文本 | ❌ 禁用 |
| doubao-reasoning | 推理 | ❌ 禁用 |
| doubao-reasoning2 | 推理 | ❌ 禁用 |
| hunyuan | 文本 | ❌ 禁用 |
| seedance | 视频 | ❌ 禁用 |

#### 免费模型清单（4个文本+2个多模态）：

| 模型 | 类型 | 状态 |
|------|------|------|
| zhipu glm-4-flash | 文本 | ✅ 主力 |
| agnes 2.5-flash | 文本 | ✅ 备用 |
| siliconflow Qwen2.5-7B | 文本 | ✅ 备用 |
| ollama-local | 文本 | ✅ 本地兜底 |
| agnes-image | 图片 | ✅ 可用 |
| agnes-video | 视频 | ✅ 可用 |

#### 自动降级机制：

```
用户请求指定付费模型
    ↓
检测到模型在禁用清单中
    ↓
自动降级到免费模型（zhipu glm-4-flash）
    ↓
正常调用，无需用户干预
```

#### V2.0付费人工审核机制（已停用）：

V2.0的付费申请/审核机制保留代码但不再启用，因为V3.0直接禁用所有付费模型，从根源上消除付费风险。

#### 审核流程（四步）：

```
1. 创建申请 → 2. 人工审核 → 3. 审核通过 → 4. 执行调用
   (pending)     (admin)       (approved)     (一次性)
```

#### 第一步：创建付费申请

**API**：`POST /paid/request`

**请求参数**：
```json
{
  "model": "doubao",
  "prompt": "任务描述",
  "requester": "申请人"
}
```

**响应**：
```json
{
  "ok": true,
  "request_id": "PAID-15CF9F080F81",
  "status": "pending",
  "message": "申请已创建，等待人工审核",
  "cost_estimate": 0.004,
  "review_endpoint": "POST /paid/approve",
  "admin_key_required": true
}
```

#### 第二步：人工审核

**审核通过API**：`POST /paid/approve`
- 需要管理员密钥：`X-Admin-Key: zongyuan-paid-admin-2026`
- 请求参数：`{"request_id": "PAID-XXX", "approved_by": "admin"}`

**审核拒绝API**：`POST /paid/reject`
- 需要管理员密钥
- 请求参数：`{"request_id": "PAID-XXX", "reason": "拒绝原因"}`

#### 第三步：查看申请列表

**API**：`POST /paid/list`
- 需要管理员密钥
- 支持状态过滤：`{"status": "pending/approved/rejected/all"}`
- 返回最近50条申请

#### 第四步：执行付费调用

使用审核通过的申请ID调用：
- 请求头：`X-Paid-Request-Id: PAID-15CF9F080F81`
- 或参数：`{"paid_request_id": "PAID-XXX"}`

#### 审核规则：

1. **一次性使用**：每个申请ID只能执行一次调用
2. **有效期**：审核通过后24小时内有效，过期自动失效
3. **管理员密钥**：审核操作必须携带管理员密钥
4. **全程留痕**：申请、审核、执行全流程记录

#### 拒绝响应（未申请/未审核）：

```json
{
  "error": "paid_model_requires_manual_review",
  "message": "元法则META-RULE-001 V2：付费模型[doubao]需要人工审核。请先调用 POST /paid/request 创建申请，审核通过后使用 X-Paid-Request-Id 调用",
  "meta_rule": "META-RULE-001 V2 免费优先·付费人工审核",
  "requested_model": "doubao",
  "cost_estimate_yuan": 0.004,
  "request_endpoint": "POST /paid/request",
  "review_endpoint": "POST /paid/approve (需管理员密钥)",
  "free_alternatives": ["zhipu", "agnes", "siliconflow"],
  "did": "DID-BR-000002",
  "trace": "Ω₀⊂⊙∞⊂Ω"
}
```

---

## 三、技术实现规范

### 3.1 aiproxy 实现

**配置项：**
```python
# 元法则V2：免费优先·付费人工审核
META_RULE_FREE_FIRST = True
META_RULE_PAID_MANUAL_REVIEW = True
PAID_MODELS = {"aliyun", "kimi", "doubao", "doubao-reasoning", "doubao-reasoning2", "hunyuan"}
FREE_MODELS = {"zhipu", "agnes", "siliconflow", "ollama-local"}
PAID_ADMIN_KEY = "zongyuan-paid-admin-2026"  # 审核管理员密钥
PAID_REQUEST_EXPIRE_HOURS = 24  # 审核有效期
PAID_REQUESTS_FILE = "/opt/ZONGYUAN-ROOT/ai_proxy/paid_requests.json"
```

**核心函数：**
- `create_paid_request()` - 创建付费申请
- `approve_paid_request()` - 审核通过
- `reject_paid_request()` - 审核拒绝
- `check_paid_request_valid()` - 检查申请有效性
- `mark_paid_request_executed()` - 标记已执行
- `check_paid_confirmation()` - 付费调用检查入口

**API端点：**
| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| /paid/request | POST | 公开 | 创建付费申请 |
| /paid/approve | POST | 管理员 | 审核通过 |
| /paid/reject | POST | 管理员 | 审核拒绝 |
| /paid/list | POST | 管理员 | 查看申请列表 |
| /chat | POST | 带申请ID | 执行付费调用 |

### 3.2 路由优先级

**智能路由必须遵循以下优先级：**

1. 免费模型（按响应时间排序）
2. 付费模型（需确认，按响应时间排序）
3. 本地兜底模型

**禁止行为：**
- ❌ 禁止默认选择付费模型
- ❌ 禁止在免费模型可用时跳过免费模型
- ❌ 禁止静默调用付费模型
- ❌ 禁止绕过付费确认机制

### 3.3 监控与告警

**/usage 端点必须包含：**
- 免费调用次数/占比
- 付费调用次数/占比
- 付费确认次数
- 拒绝调用次数（未确认）
- 月度成本估算
- 成本告警状态

**告警阈值：**
- 免费占比 < 90% → Warning
- 免费占比 < 80% → Critical
- 月度成本 > 80元 → Warning
- 月度成本 > 100元 → Critical

---

## 四、违规处理

### 4.1 违规检测
- 每次付费调用记录日志
- 每日对账：付费调用是否都有确认标记
- 异常检测：短时间大量付费调用

### 4.2 违规处理
1. 第一次违规：告警通知
2. 第二次违规：自动降级到免费模型
3. 第三次违规：暂停付费模型调用权限
4. 持续违规：触发eFuse熔断，隔离问题分支

---

## 五、法则固化

### 5.1 固化方式
- 写入 aiproxy 代码（硬编码，不可通过配置关闭）
- 写入 ZONGYUAN-ROOT 自治内核
- 写入元法则库（META-RULE-001）
- 三端锁档（本地+云服务器+飞书）
- Merkle-DAG 哈希链确权

### 5.2 修改权限
- 本法则为元法则，修改需要：
  1. 全域快照备份
  2. 三端同步修改
  3. 新锁档凭证
  4. 内核状态更新
- 禁止单端修改

---

## 六、预期效果

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 免费模型占比 | 70% | ≥95% |
| 月度API成本 | ~500元 | ≤50元 |
| 付费调用可控性 | 无 | 100%可追溯 |
| 成本透明度 | 低 | 实时监控 |

---

## 七、确权信息

- 元法则编号：META-RULE-001
- 版本：V1.0
- 创建时间：2026-09-05
- 确权DID：DID-BR-000002
- 溯源标识：Ω₀⊂⊙∞⊂Ω
- 协议：ZONGYUAN-ROOT
- 状态：BLOWN_PERMANENT（永久固化，不可篡改）
- 锁档等级：Lv8（最高级）

---

**本法则为ZONGYUAN-ROOT元法则，全域生效，永久固化，不可单端修改。**

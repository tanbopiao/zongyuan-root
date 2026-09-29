# 元法则：免费优先 · 付费确认 V1.0

> 确权标识：DID-BR-000002 | 溯源标识：Ω₀⊂⊙∞⊂Ω
> 协议：ZONGYUAN-ROOT | 元法则编号：META-RULE-001
> 状态：BLOWN_PERMANENT 永久固化

---

## 一、元法则定义

### 1.1 法则名称
**免费优先 · 付费确认**（Free First, Paid Confirm）

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

### 2.2 第二原则：付费确认

**任何付费模型的调用必须经过确认机制：**

#### 确认方式（三选一）：

1. **请求头确认**：HTTP请求头 `X-Confirm-Paid: true`
2. **参数确认**：请求体中 `"confirm_paid": true`
3. **全局配置确认**：配置文件中 `PAID_CONFIRM_GLOBAL = true`（仅用于内部测试）

#### 确认流程：

```
用户请求
    ↓
智能路由选择模型
    ↓
是免费模型？──是──→ 直接调用
    │
    否
    ↓
有付费确认标记？──否──→ 拒绝调用，返回提示
    │
    是
    ↓
调用付费模型
    ↓
记录付费调用日志
```

#### 拒绝响应：

```json
{
  "error": "paid_model_requires_confirmation",
  "message": "当前路由选择了付费模型[模型名]，需要确认才能调用。请添加请求头 X-Confirm-Paid: true 或参数 confirm_paid: true",
  "free_alternatives": ["zhipu", "agnes", "siliconflow"],
  "cost_estimate": "0.004元/次"
}
```

---

## 三、技术实现规范

### 3.1 aiproxy 实现

**配置项：**
```python
# 元法则：免费优先·付费确认
META_RULE_FREE_FIRST = True
META_RULE_PAID_CONFIRM = True
PAID_MODELS = {"aliyun", "kimi", "doubao", "doubao-reasoning", "doubao-reasoning2", "hunyuan"}
FREE_MODELS = {"zhipu", "agnes", "siliconflow", "ollama-local"}
```

**付费确认检查函数：**
```python
def check_paid_confirmation(model_key, headers, data):
    """检查付费模型调用确认"""
    if model_key in FREE_MODELS:
        return True, None
    if not META_RULE_PAID_CONFIRM:
        return True, None
    # 检查请求头
    if headers.get("X-Confirm-Paid", "").lower() == "true":
        return True, None
    # 检查参数
    if data.get("confirm_paid") == True:
        return True, None
    # 检查全局配置
    if PAID_CONFIRM_GLOBAL:
        return True, None
    # 未确认，拒绝
    return False, {
        "error": "paid_model_requires_confirmation",
        "message": f"付费模型[{model_key}]需要确认",
        "free_alternatives": list(FREE_MODELS)
    }
```

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

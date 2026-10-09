# API网关 OpenAI兼容协议设计文档

> DID-BR-000002｜ZONGYUAN-ROOT｜本体主权根Ω-TAN-7-001
> 溯源：Ω₀⊂⊙∞⊂Ω｜版本：V1.0｜2026-09-08
> 定位：adapters/api_gateway/openai_compatible_gateway.py 使用

## 一、设计公理

1. **完全兼容OpenAI /v1/chat/completions**：第三方SDK可直接调用，不需要修改客户端代码
2. **meta扩展字段注入**：通过meta字段注入本系统专属控制指令（锁档标记、产线任务参数、漂移校验等级、Saga控制、归档开关）
3. **协议过滤网内置**：识别逃逸、越权指令，触发拦截/降级/告警，不把非法指令透传到内层
4. **z_meta扩展返回**：保持OpenAI标准返回结构，同时扩展z_meta带回内部信息（task_id、snapshot_id、event_id、风险等级）
5. **适配器层定位**：网关只属于adapters层；校验失败只在网关层拦截，不污染kernel领域层

## 二、分层架构

```
原始OpenAI协议层 → 网关扩展meta字段层 → 内部Command DTO转换
     ↑                    ↑                        ↓
  第三方SDK         协议过滤网校验          应用服务层Command
```

## 三、请求核心字段

### 3.1 OpenAI原生字段
- model: 模型标识（kunlun-media-v1 / kernel-inspect-v1 / general-agent-v1）
- messages: 对话消息数组（system/user/assistant）
- temperature / top_p / max_tokens / stream

### 3.2 meta扩展字段
| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| enable_archive | bool | false | 完成后触发全域锁档归档 |
| produce_task_type | enum | none | keyframe/pv/episode/script |
| ip_character_ref | string | - | 昆仑洞天角色ID（KF-M07/TAIYIN-01） |
| drift_check_level | int | 2 | 0关闭/1基础/2常规/3最高严格 |
| saga_auto_start | bool | false | 自动启动归档Saga流程 |
| protocol_enforce | bool | true | 激活前置协议过滤网 |
| priority | int | 5 | 产线任务优先级1-10 |
| snapshot_parent_id | string | - | 父快照ID，谱系追踪 |

### 3.3 drift_check_level等级说明
- 0：关闭额外漂移校验，仅基础格式校验
- 1：基础参数校验
- 2：常规生产校验（默认），视觉范式、元规则校验开启
- 3：最高严格模式，违背任意一条元规则直接拦截请求，返回400

## 四、响应核心字段

### 4.1 OpenAI原生字段
- id / object / created / model
- choices[]: index/message/finish_reason
- usage: prompt_tokens/completion_tokens/total_tokens

### 4.2 z_meta扩展字段
| 字段 | 说明 |
|------|------|
| task_id | 内部任务ID |
| snapshot_id | 快照ID |
| saga_instance_id | Saga实例ID |
| event_ids | 领域事件ID集合 |
| drift_risk_level | 漂移风险等级0-3 |
| risk_message | 风险提示信息 |
| archive_status | 归档状态none/pending/completed/failed |
| merkle_root | Merkle根哈希 |
| trace_chain_hash | 溯源链哈希 |

## 五、网关内部流转

1. 入站限流中间件 → 超限返回429
2. JSON Schema校验 → 格式错误返回400
3. 协议过滤网 request_acl_filter.py → 检测逃逸/越权/视觉范式违背
4. OpenAI格式 → BaseCommand DTO转换
5. Command投递应用服务层 → 业务执行
6. 内部结果 → OpenAI标准响应 + z_meta填充
7. 返回响应（stream模式在结束chunk带回z_meta）

## 六、错误码

| 码 | 说明 |
|----|------|
| 400 | 参数格式错误 / 协议过滤网拦截 |
| 429 | 入站限流触发 |
| 500 | 内部服务异常 |
| 503 | 熔断器打开，下游不可用 |

## 七、4条网关元规则

- **TRUTH-GATEWAY-023**：API网关保持OpenAI协议兼容，扩展信息全部放在meta/z_meta字段，不破坏原生结构
- **TRUTH-GATEWAY-024**：协议过滤网属于adapters网关层组件，拦截逻辑不侵入kernel领域层
- **TRUTH-GATEWAY-025**：meta仅作为外部控制参数，内核真值以Command内部DTO为准
- **TRUTH-GATEWAY-026**：z_meta携带所有溯源链路信息，供外部应用做审计溯源

## 八、调用示例

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
-H "Content-Type: application/json" \
-d '{
  "model":"kunlun-media-v1",
  "messages":[{"role":"user","content":"生成昆仑神女关键帧"}],
  "meta":{
    "produce_task_type":"keyframe",
    "ip_character_ref":"KF-M07",
    "drift_check_level":2,
    "enable_archive":true
  }
}'
```

Ω₀⊂⊙∞⊂Ω｜API网关OpenAI兼容协议设计｜永久锁档固化

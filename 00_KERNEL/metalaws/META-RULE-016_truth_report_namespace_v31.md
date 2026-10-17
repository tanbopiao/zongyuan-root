# META-RULE-016 记忆网关真值上报命名空间规范 V3.1

**规则ID**：META-RULE-016
**版本**：V3.1（对齐云端 RULE-005 V3.1）
**状态**：active
**创建日期**：2026-10-16
**确权**：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
**适用**：所有节点 → 记忆网关 https://www.huodouai.com/api/report/truth 的真值上报

---

## 一、背景与目的

记忆网关是全网真值共识的唯一写入通道。此前引擎/节点使用旧字段（`truth_key`/`truth_value`）且不带 `X-DID` 头，被网关以 `401 unauthorized` / `empty_value_rejected` / `alignment_rejected` 拒绝。
经云端实测（2026-10-16），网关校验规则为 **RULE-005 V3.1**：仅接受标准命名空间前缀 + 结构化 JSON 对象。本规则统一全网上报 key 命名空间，防止前缀冲突与非标准前缀拒收。

## 二、强制规则

### 2.1 请求头
- 必须携带 `X-DID: DID-BR-000002` 头，否则返回 `401 unauthorized`。

### 2.2 请求体字段（V3.1，禁止旧字段）
```json
{
  "key": "命名空间.业务域.对象.动作.日期",
  "value": {"结构化JSON对象（≥2字段，<10KB）"},
  "truth_type": "meta_law|rule|config|decision|data|creative|risk|protocol|unknown",
  "did": "DID-BR-000002"
}
```
- **禁止**使用旧顶层字段 `content` / `truth_key` / `truth_value`（会触发 `empty_value_rejected`，value 落空）。
- `value` 必须是 JSON **对象**（字符串将被 `value_must_be_object` 拒绝）。

### 2.3 key 命名空间规范
- key 格式：`<命名空间>.<业务域>.<对象>.<动作>.<日期>`，全部大写，点号分隔。
- **禁止 `truth-` 前缀**。
- 标准命名空间前缀（白名单，实测通过）：
  | 前缀 | 域 | 用途 | 实测状态 |
  |------|----|------|---------|
  | `KERNEL` | 内核执行域 | 执行种子、白皮书锻造、内核状态（执行种子固定用 `KERNEL.EVOLUTION.DIRECTIVE.` 前缀） | ✅ 通过 |
- 扩展新命名空间前缀须先申请并走审批（见第四节），否则会被 `alignment_rejected`（对齐评分 <50）拒绝。

### 2.4 对齐评分要求
- 网关对每条上报执行对齐评分（阈值 50/100）：
  - 结构化 dict ≥2 字段：+20
  - 长度合规（<10KB）：+10
  - 标准命名空间：+20（非标准前缀该检查项 +0，总分 30 → 被拒）
- 上报前必须自检：key 前缀在白名单内、value ≥2 字段且 <10KB。

## 三、已分配命名空间台账

| 前缀 | 归属域 | 节点 | 现有 key 示例 |
|------|--------|------|--------------|
| `KERNEL` | 内核执行 | NODE-DEV-DOUBAO-WORK-001 | KERNEL.WHITEPAPER.WP-031.AUTO-FORGE.20261016 |
| `KERNEL.EVOLUTION.DIRECTIVE.*` | 执行种子 | 全节点 | KERNEL.EVOLUTION.DIRECTIVE.{任务}.{日期} |

## 四、新增命名空间流程

1. 提交申请：`<前缀>` + 归属域 + 用途 + 示例 key；
2. 经飞书审批（lark-approval）通过；
3. 网关侧登记白名单；
4. 本地更新本规范台账后生效。

## 五、校验命令（上报前自检）

```bash
# 校验 key 前缀
key="KERNEL.WHITEPAPER.WP-031.AUTO-FORGE.20261016"
case "$key" in
  KERNEL.*) echo "前缀合规";;
  *) echo "非标准前缀，将被拒"; exit 1;;
esac
```

## 六、合规约束

1. 所有节点、脚本、引擎（含 auto_wp_forge.py）一律按本规范上报；
2. 违反本规范的上报将被网关拒收，视为未上报；
3. 旧协议（truth_key/truth_value）已废弃，禁止在新增代码中使用。

---
**溯源锚点**：Ω₀⊂⊙∞⊂Ω
**DID**：DID-BR-000002
**关联**：RULE-005 V3.1（云端）、docs/ENDPOINT_NAMESPACE.md（HTTP端点规范，与本规范互补）

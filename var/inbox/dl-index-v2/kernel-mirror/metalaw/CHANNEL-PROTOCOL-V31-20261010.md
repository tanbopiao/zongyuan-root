# 云端写通道协议 V3.1（RULE-005 V3.1 实测修正 · 2026-10-10）
## 版本说明
- 本版本由 V3.0 升级而来，版本号与网关校验规则 **RULE-005 V3.1** 对齐
- V3.0 协议（2026-10-07）基础上，实测确认 V3.1 校验细节

## 关键变更（实测确认，V3.0 旧格式作废）
1. **鉴权头**：上报必须携带 `X-DID: DID-BR-000002`，否则返回 `unauthorized / X-DID 未授权`
2. **请求体格式**：`{"key":"命名空间KEY","value":{"content":"..."}}`
   - **value 必须是含 content 键的 JSON 对象**（content/text/summary/value 键均可）
   - 字符串 value 返回 `value_must_be_object`（RULE-005 V3.1 核心校验）
   - **作废字段**：`truth_key` / `truth_value` 不再使用
3. **key 规范**：命名空间前缀 key，不可为空，禁止 truth- 自动前缀冲突
4. **响应格式**：`{"ok":true,"message":"真值写入成功","key":...,"truth_count":N,"seq":N,"event_id":"truth-..."}`
5. **健康探测**：/api/health 与 /api/truths/ 当前返回 404（路径变更），以写通道实测为准

## 上报示例
```bash
curl -X POST https://www.huodouai.com/api/report/truth \
  -H "Content-Type: application/json" \
  -H "X-DID: DID-BR-000002" \
  -d '{"key":"REPORT.MODULE.VERSION","value":{"content":"说明"}}'
```

## 实测握手结果（2026-10-10）
- www 上报成功：truth_count=4945, seq=5038
- drama 上报成功：truth_count=4946, seq=5039
- 云端主控上报恢复：truth_count=4947, seq=5040
- 握手裁决：**CLOUD-HANDSHAKE-OK**

## 状态：ACTIVE ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω

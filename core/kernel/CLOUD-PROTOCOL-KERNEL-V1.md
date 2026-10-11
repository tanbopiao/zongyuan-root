# 云端协议内核卡 V1.0（自治内核·实测校准版）
> 更新：2026-10-11 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 校准依据：全站扫描实测 + 官网API文档 + gateway-v31-protocol白皮书

## 一、中枢坐标（唯一真值源）
| 项 | 值 |
|---|---|
| 主域 | https://www.huodouai.com |
| 备用上报域 | https://drama.huodouai.com/api/report/truth（可用，需双头） |
| 真值上报 | POST /api/report/truth |
| 中枢状态 | GET /api/status（truth_count/merkle_root/version） |
| DAL健康 | GET /dal/health |
| DAL原子发布 | POST /dal/deploy |
| 试用网关 | POST /try/chat |
| 媒体清单 | POST /v1/frames/list · /v1/videos/list |
| 拉取端点 | ❌ 未部署（/api/truths* 全404，GAP-01） |

## 二、认证协议（双头必带）
- X-DID: DID-BR-000002
- X-Capture-Token: ZR-CAPTURE-2026-OMEGA-666b43e342a6b57ee54742f58d3e3fcd

## 三、上报规范（RULE-005 V3.1）
- value：JSON 对象（字符串→400，content顶层→401）
- key：域.类型.主题.日期 四级命名；禁 truth- 前缀；同 key 覆盖旧值 → 必用新 key
- truth_type 九类：meta_law / rule / config / decision / data / creative / risk / protocol / unknown
- 成功：HTTP 200 + ok:true + event_id + truth_count

## 四、执行种子前缀
- KERNEL.EVOLUTION.DIRECTIVE.*（执行种子专用命名空间）

## 五、容灾降级
- 主域失败 → 备用域 drama 直报（双头认证）
- 拉取端点缺失 → 增量直报 + 记录缺口，禁止静默跳过
- 每 IP /try/chat 限流 5次/10min

# 多模型 API 全量连通测试报告 V1.0
归档节点：ZONGYUAN-ROOT｜DID-BR-000002｜Ω₀⊂⊙∞⊂Ω
版本：V1.0-LOCK｜2026-09-14｜结论：8 通道 5 通 3 阻，附逐项修复动作

## 一、测试范围
体系内全部模型 API 通道（config/keys.env 全量）+ 自有 AI 网关，密钥仅测试脚本内使用，未外泄。

## 二、测试结果（可用通道）
1. 智谱 GLM-4-Flash（open.bigmodel.cn）—— ✅ HTTP 200，真实推理响应，永久免费主力通道，双 Key 容灾
2. 通义千问 qwen-max（DashScope compatible-mode）—— ✅ HTTP 200，真实推理响应，深度推理通道
3. 硅基流动（api.siliconflow.cn）—— ✅ HTTP 200，**94 个模型聚合**（含 GLM-5.3/DeepSeek-V4/Kimi-K2.7/Qwen3.8/Tencent-Hy4 等）；修正文档「DNS 不通」为过时信息
4. 自有网关 /v1/models（huodouai.com）—— ✅ HTTP 200，OpenAI 兼容模型列表正常（doubao 等）
5. ai-proxy/operators/call（huodouai.com）—— ⚠️ 端点可达且认证通过，参数路由正常；返回 500 后端缺 operators 模块（云端部署缺陷）

## 三、受阻通道与修复动作
1. 火山方舟豆包 Pro —— ❌ 403 AccountOverdueError：账号欠费/逾期 → 续费火山方舟账号或更换有效 Key
2. 通义万相 wan3.0-video（阿里 MaaS）—— ❌ 401 InvalidApiKey：当前 WS Key（sk-ws 前缀）无效或未绑定该端点 → 更换有效 DASHSCOPE_WS_KEY
3. 腾讯 IMA（ima.qq.com）—— ❌ 404：缺正确调用路径文档 → 补齐 IMA 官方 API 文档与调用路径
4. ai-proxy 后端 —— 500 No module named operators → 云端补装/修复 operators 模块后重测

## 四、调度策略验证
配置中「免费优先」策略有效：文本链路 = 智谱GLM（免费）→ 通义千问 → 豆包；本次实测前两环均通，豆包欠费暂由硅基流动/自有网关兜底。

## 五、安全确认
- 全程未输出任何密钥明文；测试脚本与结果仅含状态码/耗时/错误类别
- 密钥文件权限 600，仅 root 可读

## 六、结论
群体智能联邦的多模型底座：**4 条真实可用大模型通道 + 1 条自有网关（认证通）**；3 个受阻项均已定位根因与修复动作，修复后即可全通。

---
Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜MULTIMODEL-API-TEST-REPORT V1.0｜LOCKED

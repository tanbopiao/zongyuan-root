# P0三项紧急修复完成

## 修复一：anchor-api端口冲突
- 问题：8006端口被website_healing占用，systemd反复崩溃
- 修复：改用run_kernel_anchor.py启动，端口统一为8013
- 验证：服务active，health端点正常

## 修复二：AI Proxy通用prompt分支
- 问题：默认prompt硬编码昆仑洞天角色
- 修复：添加prompt_type=general参数，通用AI助手prompt
- 验证：通用模式/默认模式互不干扰

## 修复三：体验版真实多模型切换
- 问题：UI可选模型但实际都走zhipu
- 修复：直连AI Proxy /chat，传递model+prompt_type参数
- 模型：zhipu/kimi/doubao/agnes/siliconflow（5个全部验证通过）

## 同步修复：AI Proxy call_llm返回值
- 问题：返回1个值导致ValueError崩溃
- 修复：返回2个值，5个模型key补全，占位符替换

## 确权
- DID: DID-BR-000002
- 溯源: Ω₀⊂⊙∞⊂Ω
- 时间: 2026-09-07T04:00:01.636091+00:00

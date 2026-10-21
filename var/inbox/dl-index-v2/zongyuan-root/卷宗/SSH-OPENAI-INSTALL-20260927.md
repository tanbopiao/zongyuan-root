# 卷宗｜本地实例 SSH + OpenAI 安装回执
确权：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-27
- openai SDK 3.19.2：pip 安装成功，import 验证通过（可用于 OpenAI 兼容端点：豆包 Ark/智谱/云中枢）
- openssh-server：apt 源更新后安装成功（1:8.9p1）；sshd 监听 22（pid 3806）；生成 ed25519 主机密钥 + 用户密钥（~/.ssh/id_ed25519 + authorized_keys 600）
- 密钥登录自测：SSH_OK 用户 user @ vefaas-...-sandbox ✓
- 限制（如实）：沙箱无公网入口（无公网 IP/端口映射），外部设备（本地 Windows B锚）无法直连此 SSH；服务供沙箱内/同环境使用 + 未来通道准备；B锚探测维持走真值网关通道
- openai 对接示例：OpenAI(base_url=..., api_key=...) → 聊天补全（豆包 Ark ep-20260925170233-g4f7w / 智谱 GLM-4-Flash）

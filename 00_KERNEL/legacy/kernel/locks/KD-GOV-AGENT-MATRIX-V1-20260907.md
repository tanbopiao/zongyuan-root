政务智能体矩阵 V1.0 锁档凭证

第一期完成：3个专业智能体（政策解读员/办事导航员/公文写作员）
第二期规划：4个智能体（审批助理员/数据分析员/决策参谋员/合规审查员）

核心能力：
- 智能路由：自动匹配最佳智能体
- 专属知识库：政策库/办事指南/公文模板
- 专属system prompt：每个智能体有专业身份和回答规范
- 通用AI助手兜底：无匹配时使用通用模式

API端点：
- GET /api/agents/list - 智能体列表
- GET /api/agents/{id} - 智能体详情
- POST /api/agents/chat - 智能体对话
- POST /api/agents/route - 智能路由测试

前端界面：https://huodouai.com/gov-agents/

确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

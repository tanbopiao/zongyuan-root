双内核架构V3.0智能体操作系统锁档凭证
========================================

版本：V3.0（从任务执行引擎进化为智能体操作系统）
架构：调度内核(Ω-Brainμ) + 双执行内核集群 + 智能体注册中心 + HITL人在回路 + 多模态支持

【V3.0新增能力】

1. 政务智能体注册中心（8个智能体）
   - gov-policy-analyst 政策解读员 (policy, P1)
   - gov-service-navigator 办事导航员 (service, P1)
   - gov-document-writer 公文写作员 (document, P2)
   - gov-data-analyst 数据分析员 (data, P2)
   - gov-risk-assessor 风险评估员 (risk, P0)
   - gov-legal-advisor 法务顾问 (legal, P1)
   - gov-public-opinion 舆情监测员 (opinion, P2)
   - gov-meeting-assistant 会议助手 (meeting, P3)
   - API: GET /kernel/agents/list, GET /kernel/agents/get, POST /kernel/agents/register

2. 任务优先级调度（P0/P1/P2/P3四级队列）
   - P0: 最高优先级，立即执行（紧急任务、用户实时请求）
   - P1: 高优先级（重要业务任务）
   - P2: 普通优先级（默认，常规任务）
   - P3: 低优先级（后台批量任务）
   - 同优先级按创建时间排序
   - stats端点返回priority_queue实时状态

3. HITL人在回路（高风险人工审批）
   - 高风险关键词检测：删除/清空/转账/支付/发布/审批/合同/法律/敏感/机密
   - 命中关键词自动设为pending_approval状态
   - 飞书Webhook推送交互式审批卡片（批准/拒绝按钮）
   - API: POST /kernel/hitl/check, POST /kernel/mission/resume
   - 配置：HITL_ENABLED=true + FEISHU_WEBHOOK_URL

4. 多模态任务支持
   - 任务类型：text(文本推理) / image(图片生成) / video(视频生成) / audio(音频生成) / multimodal(多模态)
   - 能力路由：执行内核声明capabilities，调度内核只分配匹配任务
   - 指定智能体：agent_id参数绑定特定智能体执行
   - GET /kernel/mission/get?capabilities=text,image

【V2.0已有能力（继承加固）】
- 调度内核Ω-Brainμ: 8032端口，HMAC-SHA256认证，防重放±300秒
- 双执行内核集群: 8030(Executor1) + 8033(Executor2)，可N水平扩展
- 5节点状态机: 任务理解→核心推理→漂移校验→结果优化→快照提交
- 5维漂移校验: length(0.15)+reject(0.25)+keyword_coverage(0.3)+relevance(0.2)+structure(0.1)
- Redis Checkpoint: 每节点写入Redis，断点续跑，24小时过期
- 同步执行端点: /kernel/mission/execute_sync，外部系统一行代码调用
- 监控告警: health_monitor 8目标，自动恢复
- 飞书Base日志: 任务全生命周期同步，配置即启用
- 任务自动恢复: 启动从missions/目录恢复，running超10分钟回退pending
- 原子写入: root_state.json 文件锁+临时文件+fsync+rename
- 熔断保护: iteration > max_iter+1 自动熔断

【API端点清单（14个）】
1. POST /kernel/mission/dispatch - 创建任务（优先级/类型/智能体）
2. GET /kernel/mission/get - 拉取任务（能力路由）
3. GET /kernel/mission/status - 任务状态
4. POST /kernel/mission/execute_sync - 同步执行
5. POST /kernel/mission/interrupt - 中断任务
6. POST /kernel/mission/resume - 恢复任务（HITL）
7. POST /kernel/snapshot/commit - 快照确权
8. POST /kernel/heartbeat - 心跳
9. GET /kernel/stats - 统计（含优先级队列）
10. GET /kernel/health - 健康检查
11. GET /kernel/agents/list - 智能体列表
12. GET /kernel/agents/get - 智能体详情
13. POST /kernel/agents/register - 注册智能体
14. POST /kernel/hitl/check - 高风险检测

【资源占用】
- 调度内核: 18MB内存
- 执行内核×2: 25MB×2 = 50MB
- 总计: 约70MB，CPU空闲0%
- 服务器: 2核2GB，剩余可用内存约300MB

【外网访问】
- 调度内核: https://huodouai.com/kernel-api/
- 执行内核1: https://huodouai.com/agent-api/
- Nginx反向代理，443主站server块

确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | ZONGYUAN-ROOT V3.0

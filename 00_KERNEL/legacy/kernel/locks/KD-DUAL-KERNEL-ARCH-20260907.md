双内核架构落地锁档凭证

架构：调度内核(Ω-Brainμ) + 执行内核(Agent Executor) 双内核协作

【调度内核】
- 文件：/opt/ZONGYUAN-ROOT/kernel/kernel_scheduler_api.py
- 端口：8032
- 服务：zongyuan-scheduler.service
- 职责：任务下发、真值校验、快照确权、熔断控制、状态管理
- API：mission/dispatch, mission/get, mission/status, snapshot/commit, mission/interrupt, heartbeat, stats, health
- 状态：root_state.json + missions/目录持久化

【执行内核】
- 文件：/opt/ZONGYUAN-ROOT/kernel/agent_executor_kernel.py
- 端口：8030
- 服务：zongyuan-agent-executor.service
- 职责：任务拉取、状态机执行、LLM推理、工具调用、快照提交
- 执行节点：任务理解→核心推理→漂移校验→结果优化→快照提交
- AI Proxy：8021端口远程调用，不本地加载模型
- 状态：Redis可扩展，当前内存状态

【双内核通信协议】
- 调度→执行：任务下发(mission dispatch) / 中断指令(interrupt)
- 执行→调度：心跳(heartbeat) / 快照提交(snapshot commit)
- 认证：HMAC-SHA256签名（预留）
- 任务状态：pending→running→finished/drift_detected/interrupted/fuse_triggered

【端到端验证】
- 任务ID：MISSION-1788763177-9ecf2b13
- 任务目标：分析政务中台40个智能体差异化竞争优势
- 执行结果：finished，5次迭代，无漂移，输出2740字符
- 自动确权：链长21295→21296，根哈希F9C728861F5310EE...
- 任务持久化：/opt/ZONGYUAN-ROOT/kernel/missions/MISSION-1788763177-9ecf2b13.json

【职责边界铁律】
- 真值基线管理：调度内核唯一权威
- 任务目标定义：调度内核下发，执行内核不可修改
- LLM推理调用：执行内核执行，调度内核不直接调用
- 哈希确权锁档：调度内核唯一确权方
- 熔断终止权：调度内核可随时终止
- max_iter硬熔断：执行内核迭代超限自动触发

【后续升级路径】
1. 执行内核从Python状态机升级为LangGraph
2. Redis Checkpoint持久化
3. HITL人在回路（飞书审批）
4. Ω-Brainμ语义漂移校验增强
5. 多执行内核并行（Agent集群）

确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

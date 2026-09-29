双内核架构Lv8加固锁档凭证
========================================

架构：调度内核(Ω-Brainμ) + 双执行内核(Agent Executor Cluster) 三节点协作

【调度内核 Ω-Brainμ】
- 文件：/opt/ZONGYUAN-ROOT/kernel/kernel_scheduler_api.py
- 端口：8032
- 服务：zongyuan-scheduler.service
- 外网：https://huodouai.com/kernel-api/
- 职责：任务下发、真值校验、快照确权、熔断控制、状态管理、同步执行
- API端点：9个
  1. POST /kernel/mission/dispatch - 创建任务
  2. GET /kernel/mission/get - 拉取任务
  3. GET /kernel/mission/status - 任务状态
  4. POST /kernel/mission/execute_sync - 同步执行（外部系统接入）
  5. POST /kernel/mission/interrupt - 中断任务
  6. POST /kernel/snapshot/commit - 快照确权
  7. POST /kernel/heartbeat - 心跳
  8. GET /kernel/stats - 统计
  9. GET /kernel/health - 健康检查
- 认证：HMAC-SHA256签名 + 防重放时间戳窗口(±300秒)
- 持久化：root_state.json + missions/目录 + 启动自动恢复

【执行内核集群 Agent Executor Cluster】
- Executor1：端口8030，服务zongyuan-agent-executor
- Executor2：端口8033，服务zongyuan-agent-executor-2
- 架构：N+1可水平扩展，当前2实例并行
- 职责：任务拉取、5节点状态机执行、LLM推理、漂移校验、快照提交
- 执行节点：任务理解→核心推理→漂移校验→结果优化→快照提交
- AI Proxy：8021端口远程调用，5个可用模型(zhipu/kimi/doubao/agnes/siliconflow)
- Redis Checkpoint：每节点写入Redis，断点续跑，24小时过期
- 异常保护：任务线程异常自动清理+通知调度内核标记error

【安全体系】
- HMAC-SHA256双向认证：所有POST请求必须签名
- 防重放：时间戳±300秒窗口
- 白名单：/kernel/health, /kernel/stats 免认证
- 熔断：iteration > max_iter+1 自动熔断
- 原子写入：root_state.json 文件锁+临时文件+fsync+rename
- 任务恢复：启动自动从missions/目录恢复，running超10分钟回退pending

【质量体系】
- 5维漂移校验：length(0.15) + reject(0.25) + keyword_coverage(0.3) + relevance(0.2) + structure(0.1)
- 漂移判定：综合评分 < 0.3
- 输出结构：执行计划+执行结果+漂移告警+优化结果
- 迭代控制：max_iter默认5，可配置

【监控体系】
- 接入health_monitor：8个监控目标
- 自动恢复：服务异常自动重启
- 状态文件：executor_state.json + Redis双写
- 错误日志：error.log持久化

【通信协议】
- 调度→执行：任务下发(mission dispatch) / 中断指令(interrupt)
- 执行→调度：心跳(heartbeat) / 快照提交(snapshot commit)
- 外部→调度：同步执行(execute_sync) / 异步创建(dispatch)
- 编码：UTF-8，Content-Type: application/json; charset=utf-8

【端到端验证】
- 并行任务测试：2任务同时执行，25秒内全部完成
- 链长验证：21304→21306（+2确权）
- HMAC测试：无签名拒绝/正确签名通过/错误签名拒绝
- Redis Checkpoint：每节点写入验证通过
- 外网访问：/kernel-api/ 和 /agent-api/ 均正常

【资源占用】
- 调度内核：18MB内存
- 执行内核×2：25MB×2 = 50MB
- 总计：约70MB，CPU空闲时0%
- 服务器：2核2GB，剩余可用内存约300MB

确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | ZONGYUAN-ROOT V1.7

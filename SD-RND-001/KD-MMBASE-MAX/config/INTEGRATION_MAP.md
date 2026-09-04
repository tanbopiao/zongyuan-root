# KD-MMBASE-MAX 模块集成映射（17核心模块 + 2内核桥接）

| 模块ID | 名称 | 层级 | 自治内核集成 | 文件 |
|--------|------|------|-------------|------|
| MM-GATEWAY | 统一能力网关 | L5 | api_server.py HTTP桥接 | mmbase_server.py |
| MM-ROUTER | 能力路由器 | L5 | 十二阶段流水线分发插桩 | core/router.py |
| MM-QUEUE | 任务队列引擎 | L4 | auto_lock.py调度继承 | core/task_queue.py |
| MM-CONCURRENCY | 并发控制器 | L4 | meta_daemon.py令牌桶共享 | core/task_queue.py |
| MM-RETRY | 重试熔断引擎 | L4 | self_healing.py Lv3自愈联动 | core/retry_engine.py |
| MM-IMAGE | 图像生成适配器 | L3 | Seedream5.0 Harness直连 | adapters/image_adapter.py |
| MM-VIDEO | 视频生成适配器 | L3 | Seedance2.5 Harness直连 | adapters/video_adapter.py |
| MM-UNDERSTAND | 图像理解适配器 | L3 | 方舟Harness直连 | adapters/understand_adapter.py |
| MM-SEARCH | 联网搜索适配器 | L3 | 方舟Harness直连 | adapters/search_adapter.py |
| MM-AUDIO | 音频合成适配器 | L3 | 方舟TTS+外部TTS双后端 | adapters/audio_adapter.py |
| MM-DRIFT | 漂移校验引擎 | L2 | L0天元法则l0_axioms直接引用 | core/drift_checker.py |
| MM-QUALITY | 质量评分引擎 | L2 | m2_verifier.py M2单调收敛联动 | core/quality_scorer.py |
| MM-ARCHIVE | 锁档归档引擎 | L1 | full_pipeline.py十二阶段直接调用 | core/archive_engine.py |
| MM-MONITOR | 监控巡检引擎 | L6 | meta_daemon.py + breakpoint_check.py | core/monitor.py |
| MM-TRUTH | 真值资产库 | L1 | architecture_truth.md + merkle_chain.json | assets_baseline/ |
| MM-KERNEL-BRIDGE | 自治内核桥接器 | L0 | kernel_writer.py双向同步 | mmbase_server.py |
| MM-BRAIN-RECALL | Ω-Brainμ前置召回 | L0 | omega_brain_mu.py指令前置召回 | mmbase_server.py |

## 真值链路

```
任务提交 → Ω-Brainμ前置召回 → 路由分发 → 排队+并发控制 → 重试熔断
→ 多模态执行 → L0四层校验 → 质量评分+M2收敛 → Merkle-DAG+DID+eFuse
→ 自治内核写入 → 飞书四端同步 → 元极恒一巡检
```

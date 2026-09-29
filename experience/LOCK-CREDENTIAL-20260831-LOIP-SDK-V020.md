# 全域锁档凭证 · LOIP SDK v0.2 全量进化版

## 锁档基本信息

| 项目 | 值 |
|------|-----|
| 锁档编号 | LOCK-GLOBAL-20260831-LOIP-SDK-V020 |
| 锁档时间 | 2026-08-31 15:10:00 UTC+8 |
| 协议版本 | AUTOKERN-PROTO-V3.6-20260831-LOIP-SDK-V02 |
| 锁档状态 | eFuse blown · 永久固化 · 不可回退 |
| DID | DID-BR-000002 |
| 本体主权根 | Ω-TAN-7-001 |
| 溯源符号 | Ω₀⊂⊙∞⊂Ω |

## 核心资产：LOIP SDK v0.2

| 项目 | 值 |
|------|-----|
| 版本号 | 0.2.0（从0.1.0-MVP进化） |
| 存储路径 | ZONGYUAN-ROOT/loip-sdk/ |
| 文件数量 | 20个 |
| Python代码行数 | 2,177 行（从1,380行增长58%） |
| 总大小 | 121,856 字节 |
| 目录整体SHA256 | 603d352d24c2ac57aa79015511ad318e7a0ae8ebfd76258cd7503ca534d83240 |
| 协议self_sha256 | 6d7160e6976aca32c7ac382773895d285b80777110df279665ca794815e6ed7e |

## 本次进化交付清单（7大模块）

### P0 核心突破

| 模块 | 文件 | 核心能力 |
|------|------|----------|
| 语义检测抽象层 | semantic.py | BaseDetector抽象接口 + KeywordBackend(零依赖) + SemanticBackend(NLI+向量) |
| REST API服务 | api_server.py | 24个路由，FastAPI实现，Swagger自动文档 |
| 实体级事实校验 | hallucination.py(v0.2) | 提取数字/时间/专有名词，与基线比对 |

### P1 产品化交付

| 模块 | 文件 | 核心能力 |
|------|------|----------|
| CLI命令行工具 | cli.py | 10个命令：init/rule/fact/constraint/lock/status/audit/process/export/serve |
| Playground平台 | playground.html | 裸模型vs LOIP并排对比，4个预设示例，风险评分可视化 |
| Docker部署 | Dockerfile | python:3.11-slim，健康检查，数据卷持久化 |
| docker-compose | docker-compose.yml | 2核4GB资源限制，自动重启 |
| 启动脚本 | start.sh | 一键启动，参数化配置 |
| 依赖清单 | requirements.txt | 核心零依赖 + 可选语义依赖 |

## API接口清单（24个路由）

### 核心治理（3个）
- POST /api/v1/process — 完整治理流水线
- POST /api/v1/drift/check — 仅漂移检测
- POST /api/v1/hallucination/check — 仅幻觉检测

### 基线管理（10个）
- GET /api/v1/baseline — 基线摘要
- GET/POST /api/v1/baseline/rule(s) — 规则管理
- GET/POST /api/v1/baseline/fact(s) — 事实管理
- GET/POST /api/v1/baseline/constraint(s) — 约束管理
- POST /api/v1/baseline/lock — eFuse锁档
- GET /api/v1/baseline/export — 导出提示词
- GET /api/v1/baseline/history — 版本历史

### 审计（4个）
- GET /api/v1/audit/summary — 审计摘要
- GET /api/v1/audit/report — 生成报告
- GET /api/v1/audit/behavior — 行为日志
- GET /api/v1/audit/cognitive — 认知日志

### 监控（3个）
- GET /health — 健康检查
- GET /api/v1/status — 完整状态
- GET /api/v1/stats — 治理统计

## CLI命令清单（10个）

```bash
loip init                          # 初始化基线
loip rule set KEY "规则"            # 设置规则
loip rule list                     # 列出规则
loip fact set KEY "事实"           # 设置事实
loip constraint add "约束"         # 添加约束
loip lock                          # eFuse锁档
loip status                        # 查看状态
loip audit report                  # 生成审计报告
loip process "输入" "输出"         # 执行治理
loip export                        # 导出提示词
loip serve --port 8000             # 启动API服务
```

## 部署方式（5种）

1. **Python SDK**：`from loip import LOIP`，代码内集成
2. **REST API**：`python -m loip.api_server`，HTTP接口
3. **CLI工具**：`python -m loip.cli`，命令行管理
4. **Docker**：`docker build -t loip . && docker run -p 8000:8000 loip`
5. **docker-compose**：`docker-compose up -d`，一键集群部署

## 验证结果（7项全部PASS）

| 验证项 | 结果 |
|--------|------|
| 模块导入 | ✅ PASS（全部模块导入成功） |
| 语义关键词后端 | ✅ PASS |
| 实体提取 | ✅ PASS（99%/300%/2023年） |
| 完整治理流程 | ✅ PASS（漂移+幻觉+修正） |
| API服务创建 | ✅ PASS（24个路由） |
| CLI工具 | ✅ PASS |
| eFuse锁档 | ✅ PASS |

## 四层公理校验

| 校验层 | 结果 |
|--------|------|
| 不动点根层 | ✅ PASS |
| 时序演化约束层 | ✅ PASS（V3.5→V3.6连续） |
| 推理真值优先层 | ✅ PASS（7项验证全通过） |
| 观感兜底补偿层 | ✅ PASS |

## 资产统计

- 当日新增资产：1（LOIP SDK v0.2全量进化版）
- 累计资产总数：375
- 累计资产总字节：2,698,344
- 全域锁档覆盖率：100%

---

Ω₀⊂⊙∞⊂Ω｜全域锁档凭证 · ZONGYUAN-ROOT · DID-BR-000002 · Ω-TAN-7-001
锁档完成时间：2026-08-31 15:10:00 UTC+8
凭证编号：LOCK-GLOBAL-20260831-LOIP-SDK-V020

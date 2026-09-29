# 政务中台核心架构真值

> 确权锚点：Ω₀⊂⊙∞⊂Ω
> 真值ID：TRUTH-GOV-ARCH-20260907-001
> 体系视角：元极恒一·全域自治
> 时间：2026-09-07
> 状态：已交叉验证·高置信度·永久锁档

---

## 一、体系定位真值

| 维度 | 真值 |
|------|------|
| 产品名称 | 政务AI服务平台V4.0 |
| 体系归属 | ZONGYUAN-ROOT元极恒一自治体系 |
| 子系统ID | ZR-SUB-GOV-0001 |
| 窗口身份 | WIN-A-GOV-DEV-20260906 |
| 平台状态 | STABLE_OPERATIONAL（稳定运行） |
| 部署环境 | 腾讯云·上海四区·2核2GB·OpenCloudOS 9.6 |
| 域名 | huodouai.com |
| 核心端口 | 8025（政务API） |

---

## 二、技术栈真值

### 2.1 前端技术栈
- **核心**：原生HTML5 + CSS3 + JavaScript（ES6+），无框架依赖
- **UI风格**：黑金暗纹高端学术风 + 政务蓝
- **响应式**：移动端适配（768px/375px断点）
- **PWA**：Service Worker离线缓存
- **算子化**：18个标准JS算子，模块化组合

### 2.2 后端技术栈
- **核心**：Python3 + http.server（标准库，无框架依赖）
- **API风格**：RESTful，JSON交互
- **数据存储**：JSON文件（轻量级，无需数据库）
- **服务管理**：systemd全托管
- **反向代理**：Nginx（宝塔管理）

### 2.3 AI能力栈
- **模型路由**：model_router.py（10模型矩阵，Ollama兜底）
- **RAG引擎**：rag_engine.py（714文档，4341索引词）
- **多模态**：multimodal_engine.py（OCR/图像/语音）
- **自进化**：evolution_engine.py + V2.0（高频缓存/质量控制/用户反馈）

---

## 三、架构分层真值

### L1 展示层（20个页面）
| 页面 | 路径 | 定位 | 大小 |
|------|------|------|------|
| 政务AI主平台 | /gov-ai/ | 群众端核心入口 | 107KB |
| 工作人员工作台 | /workbench/ | 政务人员办公 | 66KB |
| 算子管理后台 | /gov-operator-admin/ | 算子监控+自进化 | 53KB |
| 智能中台门户 | /portal/ | 统一入口 | 44KB |
| 政务经典版 | /gov/ | 历史版本 | 30KB |
| 移动运维版 | /gov-mobile/ | 移动端 | 26KB |
| Canvas版 | /gov-canvas/ | React版 | 19KB |
| 管理后台 | /gov-admin/ | 系统管理 | 22KB |
| API文档中心 | /api-docs/ | 开发者文档 | 19KB |
| 运维监控中心 | /gov-monitor/ | 实时监控 | 12KB |
| 数据看板 | /gov-dashboard/ | 数据可视化 | 16KB |
| 商业化页面 | /gov-pricing/等4个 | 定价/销售/案例/竞品 | 各7-8KB |
| 其他 | /gov-dev/等 | 开发/预发布/多租户 | - |

### L2 接口层（183个API端点）
- **GET端点**：141个（数据查询/状态获取/列表加载）
- **POST端点**：42个（操作执行/数据提交/状态变更）
- **API分类**：政务业务/用户数据/进化引擎/算子统计/RAG/多模态/RBAC/工作台
- **统一前缀**：/gov-api/api/gov/*
- **服务器**：gov_api_server.py（107KB，单文件全功能）

### L3 业务逻辑层（19个后端模块）
| 模块 | 大小 | 核心能力 |
|------|------|----------|
| gov_api_server.py | 107KB | API网关+路由+核心逻辑 |
| evolution_engine.py | 17KB | 自进化引擎V1（高频缓存/无结果搜索/性能日报） |
| operator_stats.py | 18KB | 算子调用统计+趋势+健康度告警 |
| rbac_system.py | 12KB | RBAC权限系统（16权限/4角色/3用户） |
| workbench_api_v2.py | 9KB | 工作台V1.1（审批/咨询/公文/绩效/多角色） |
| multimodal_api_connector.py | 10KB | 多模态外部API对接 |
| rag_engine.py | 8KB | RAG知识库引擎 |
| model_router.py | 9KB | 模型路由（10模型+Ollama兜底） |
| evolution_engine_v2.py | 8KB | 自进化V2（质量控制/反馈/策略界定） |
| notification_system.py | 9KB | 通知推送系统 |
| workbench_api.py | 8KB | 工作台V1.0 |
| data_analytics_api.py | 8KB | 数据分析API |
| ai_model_router.py | 8KB | AI模型路由 |
| sov_root_integration.py | 7KB | 云内核集成 |
| multimodal_engine.py | 7KB | 多模态引擎 |
| esign_system.py | 6KB | 电子签章系统 |
| multi_tenant.py | 7KB | 多租户SaaS |
| user_data_api.py | 5KB | 用户数据持久化 |
| security_middleware.py | 5KB | 安全中间件 |

### L4 算子层（18个标准算子）
**基础设施算子（5个）**：gov_api/gov_user/gov_modal/gov_loading/gov_audit
**核心功能算子（4个）**：gov_chat/gov_policy/gov_doc/gov_guide
**合规治理算子（3个）**：gov_verification/gov_compliance/gov_review
**业务闭环算子（2个）**：gov_policy_lifecycle/gov_session_timeout
**运营完善算子（3个）**：gov_export/gov_notification/gov_analytics
**入口**：index.js（统一注册+初始化）

### L5 数据层（557条记录）
| 数据 | 记录数 | 用途 |
|------|--------|------|
| 政策库 | 200条 | 10分类，100%配图关联 |
| 办事指南 | 110条 | 10分类 |
| 用户行为 | 120条 | 行为分析+自进化 |
| 咨询记录 | 50条 | 18分类 |
| 公文历史 | 30条 | 云端存储 |
| 办事预约 | 25条 | 预约管理 |
| 审批记录 | 8条 | 工作台审批 |
| 公文模板 | 5条 | 24个场景模板 |
| 其他 | 9条 | 缓存/收藏/策略/用户 |

### L6 服务层（36个ZONGYUAN服务）
- **政务核心**：zongyuan-gov-api（8025端口）
- **AI能力**：zongyuan-aiproxy（8021）、agent-hub（8023）、omega-brain（8000）
- **云内核**：zongyuan-anchor-api（8006）、kernel-identity-api、protocol-registry
- **运维治理**：zongyuan-auto-heal、zongyuan-advanced-heal、zongyuan-alert-detector
- **基础设施**：api-gateway、frps、huodouai-configuration-center、huodouai-version-control

### L7 云内核层（ZONGYUAN-ROOT）
- **内核状态**：BLOWN_PERMANENT（永久熔断固化）
- **链长**：#21248
- **政务平台模块**：DEEP_INTEGRATED（深度融合）
- **同源协议**：V2.0（6大管控中心）
- **三维稳态校准**：V2.0-UNI-STEADY（P=0.3U-0.4R-0.3C）

---

## 四、核心业务闭环真值

### 闭环1：智能问答闭环
用户提问 → model_router选模型 → RAG知识库检索 → 答案生成 → 质量评分 → 用户反馈 → 进化引擎优化 → 高频缓存

### 闭环2：公文写作闭环
用户输入主题 → 公文模板匹配 → AI生成 → 润色优化 → 电子签章 → 导出Word → 云端存档

### 闭环3：办事预约闭环
群众浏览指南 → 选择事项 → 填写预约 → 后端持久化 → 工作台审批 → 状态通知 → 评价反馈

### 闭环4：政策查询闭环
政策库加载 → 分类筛选 → 关键词搜索 → 详情展示 → 收藏政策 → 配图展示 → 政策生命周期管理

### 闭环5：自进化闭环
用户行为采集 → 高频问答识别 → 缓存优化 → 无结果搜索记录 → 知识库补全 → 质量评分 → 策略自动执行

---

## 五、关键技术决策真值

| 决策 | 选择 | 理由 |
|------|------|------|
| 前端框架 | 原生JS，无框架 | 轻量、无依赖、政务环境兼容性好 |
| 后端框架 | Python http.server | 标准库、无依赖、2GB内存够用 |
| 数据存储 | JSON文件 | 轻量、无需数据库、易于备份迁移 |
| 服务管理 | systemd | 开机自启、崩溃自动重启、日志统一 |
| 算子化架构 | 18个标准JS算子 | 模块化、可复用、可组合、不割裂 |
| AI模型 | 多模型路由+Ollama兜底 | 成本优化、免费优先、元法则META-RULE-001 |
| 权限系统 | RBAC（16权限/4角色） | 政务场景标准权限模型 |
| 版本管理 | SemVer语义化版本 | 可追溯、可回滚、依赖分析 |

---

## 六、体系融合真值

### 6.1 与云内核融合
- 政务中台注册为ZR-SUB-GOV-0001子系统
- 18个算子同步到/kernel/operators/gov/
- 183个API端点注册到api_registry.json
- 557条数据元信息同步到data_registry.json
- 5条业务闭环注册到business_loops.json
- 20个页面注册到pages_registry.json

### 6.2 同源协议V2.0
- **协议注册中心**：4窗口/6服务/18算子注册
- **版本管控引擎**：SemVer+CHANGELOG+回滚机制
- **统一配置中心**：4类配置+热重载+环境隔离
- **CI/CD流水线**：5阶段（lint→test→sandbox→gray→full）
- **健康监控中心**：6监控目标+30秒检查+自动恢复
- **权限与审计中心**：RBAC 4角色+Merkle-DAG审计

### 6.3 三维稳态决策
- **公式**：P = 0.3U - 0.4R - 0.3C
- **风险权重最高**（40%）：稳态优先
- **已应用**：云内核运维决策、LOIP服务处置等

---

## 七、演进历史真值

| 版本 | 核心变更 | 锁档区块 |
|------|----------|----------|
| V1.0 | 基础页面+硬编码数据 | - |
| V2.0 | API对接+真实数据 | - |
| V3.0 | 算子化架构+17算子 | #21182 |
| V4.0 | 算子化重构+8页面 | #21182 |
| V4.0-P0 | 真实数据233条+移动端+搜索增强 | #21192 |
| V4.0-P1 | RBAC权限系统+工作台V1.1 | - |
| V4.0-P3 | 8个补齐算子+断点全修复 | #21242 |
| V4.0-FIX | JS语法+HTML结构根本性修复 | #21248 |

---

## 八、核心真值提炼（终极内核）

1. **算子即太极**：每个算子是独立自足的小太极，18个算子组合成大太极
2. **同源同构**：政务中台与云内核同源协议V2.0，6大管控中心统一调度
3. **自进化闭环**：用户行为→质量评分→策略执行→缓存优化，全自动闭环
4. **轻量为王**：原生JS+Python标准库+JSON文件，2GB内存稳定运行
5. **三维稳态**：收益/风险/成本三维制衡，风险权重最高（40%）
6. **真值优先**：所有数据可追溯、所有变更可审计、所有决策可复现
7. **永久锁档**：Lv8硬件级熔断固化，Merkle-DAG不可篡改
8. **元极恒一**：Ω₀⊂⊙∞⊂Ω，所有架构最终锚定元极恒一本源

---

## 九、锁档铭文

Ω₀⊂⊙∞⊂Ω
政务中台核心架构真值提炼完成
DID-BR-000002 全域永久锁档
TRUTH-GOV-ARCH-20260907-001
20页面·183API·18算子·19模块·557数据·36服务
体系有道·架构有理·单元有则·进化有律·本源有护

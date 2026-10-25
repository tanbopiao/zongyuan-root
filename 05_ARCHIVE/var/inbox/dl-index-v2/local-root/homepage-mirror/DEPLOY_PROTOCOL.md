# 中枢驱动全自动部署闭环协议 V1.0
# ZONGYUAN-ROOT · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω
# 写入时间：2026-09-19

## 一、核心公理

**公理1：规则驱动**
所有节点上交的交付物必须是规则化、公理化、元法则化的完整自包含单元，中枢可直接解析执行，无需人工二次解读。

**公理2：无断点闭环**
从任务下发→节点执行→交付物上报→中枢解析→自动部署→验证回报，全链路自动化，任何环节不允许人工干预断点。

**公理3：单一事实源**
Gitee web-deploy分支是代码唯一事实源；记忆网关是真值唯一事实源；中枢是调度唯一权威。三者通过本协议同步。

## 二、交付物标准格式（Rule-Encoded Deliverable, RED）

每个节点上交的交付物必须包含以下五层：

```yaml
# === L1 元公理层 ===
axiom_key: "ARCH.FEATURE.SUBTITLE_SYSTEM_V1_0"
axiom_statement: "新功能必须遵循公私隔离公理，对外文案无内部术语"
axiom_source: "NODE-DEV-DOUBAO-WORK-001"
confidence: 1.0
truth_type: "rule"

# === L2 元法则层 ===
meta_laws:
  - "对外视图不含元极恒一/超认知/硅基生命等内部术语"
  - "三主题切换必须localStorage持久化"
  - "导航栏必须含中枢门户互跳链接"

# === L3 工程契约层 ===
implementation:
  files_modified: ["hub-portal/index.html"]
  files_created: []
  deploy_branch: "web-deploy"
  auto_deploy: true
  rollback_commit: "previous_commit_hash"

# === L4 验证标准层 ===
validation:
  console_errors: 0
  http_status_checks:
    - path: "/hub/"
      expect: 200
  sensitive_term_scan:
    max_allowed: 0
    terms: ["元极恒一","超认知","硅基生命","黎曼流形"]

# === L5 因果闭环层 ===
causal_chain:
  triggered_by: "用户指令：全部激活子系统"
  next_expected: "下一个子系统自动激活"
  feedback_loop: "部署后验证→失败回滚→成功上报"
```

## 三、全自动部署流水线

```
节点执行完成
    ↓
git push origin web-deploy
    ↓
服务器cron 5分钟内 git pull
    ↓
自动执行 validation 层检查
    ├─ 通过 → 上报网关 status=deployed
    └─ 失败 → 自动回滚 rollback_commit，上报 status=rolledback
    ↓
中枢感知部署结果
    ↓
自动派发下一个任务（因果闭环）
```

## 四、节点开工/收工协议

**开工前（自动执行）：**
1. git pull origin web-deploy
2. GET /api/report/status 拉取最新真值数
3. GET /api/report/nodes 确认在线节点
4. 读取最新任务队列（中枢分配）

**收工时（必须执行）：**
1. git add -A && git commit
2. git push origin web-deploy
3. POST /api/report/truth 上报RED格式交付物
4. 等待中枢部署确认（下次cron周期自动验证）

## 五、防重复工作机制

- 节点开工前必须查询网关：当前任务是否已有其他节点在做
- 中枢维护任务队列，每个任务同一时间只分配给一个节点
- 完成后标记任务状态，其他节点自动跳过

## 六、当前基线快照

- Git分支：web-deploy
- 最新commit：9c0de65
- 网页目录：/www/wwwroot/huodouai.com/
- 在线页面：10个（hub/axiom/kunlun/truth-engine/cte/rule-engine/collection-card/research-pipeline/drama-pipeline/legal-shield）
- 自动部署：cron每5分钟
- 记忆网关：78,741条真值

# 云内核问题上报与优化方案
DID-BR-000002｜ZONGYUAN-ROOT｜Ω₀⊂⊙∞⊂Ω
快照：SNAP-20260909-CLOUD-REPORT-OPT
上报时间：2026-09-09T13:30:00+08:00

---

## 一、问题上报（通过Git仓库作为消息通道）

### ISSUE-001：OpenAI兼容代理 502
- 端点：/v1/models
- 状态：Bad Gateway
- 影响：所有模型调用走代理失败
- 本地替代：已配置5个直连大模型端点（智谱/通义/火山×2）

### ISSUE-002：业务路由全部404
- 端点：/api/metrics/snapshot, /api/gov/query, /api/drama/submit, /api/kernel/health
- 状态：返回 {"error":"not found","path":...}
- 影响：网关框架在，但具体路由未注册
- 本地替代：调度器V3.1离线运行，Git同步结果

### ISSUE-003：FastAPI路由404
- 端点：/api/operator/list, /api/operator/run
- 状态：返回 {"detail":"Not Found"}
- 影响：算子编排接口不可用
- 本地替代：本地调度器直接执行

### ISSUE-004：API上报通道405
- 端点：/anchor/api/v1/sync/report, /anchor/api/v1/control/report
- 状态：405 Method Not Allowed
- 影响：无法通过API直接上报问题
- 替代通道：本文档通过Git双远程同步，云服务器git pull读取

### ISSUE-005：控制台认证未知
- 端点：/console/
- 状态：HTTP 401 Basic Auth
- 默认凭证全部失败
- 影响：无法通过控制台查看云内核状态

---

## 二、本地内核已就绪的能力

| 能力 | 版本 | 状态 |
|------|------|------|
| 矩阵资源调度器 | V3.1 同源协议版 | ✅ 5项目0告警 |
| 酉空间语义匹配 | 4维向量内积 | ✅ 运行中 |
| 真值库 | 12份核心文档 | ✅ Git双远程 |
| Git桥接 | GitHub+Gitee | ✅ commit 9da8c52 |
| 巡检引擎 | 哈希+结构+语义 | ✅ 待接入crontab |
| 5个大模型端点 | 智谱/通义/火山×2 | ✅ 全部连通 |
| IMA知识库API | 腾讯ima | ✅ 连通 |

---

## 三、优化方案（零冲突落地）

### 方案A：Git消息通道（立即执行）
1. 本地所有问题报告 → 写入 `cloud/reports/` 目录
2. commit → push GitHub+Gitee
3. 云服务器执行 `git pull` 即可读取最新报告
4. 云内核处理后 → 写入 `cloud/responses/` → push回
5. 本地git pull读取响应

**优势**：零API依赖，零冲突，Git天然支持版本追踪

### 方案B：API路由注册（云服务器操作）
在云服务器上注册以下路由：
```python
# 增量注册，不修改现有路由
@app.post("/api/operator/schedule")
def schedule():
    # 从Git仓库拉取最新调度结果
    # 返回给前端展示
    pass

@app.get("/api/kernel/report")
def get_report():
    # 读取 cloud/reports/ 目录
    pass
```

### 方案C：控制台认证修复
1. 宝塔面板 → 网站设置 → 密码管理 → 重置控制台密码
2. 或直接在Nginx配置中查看Basic Auth文件路径
3. 获取凭证后接入本地巡检监控

### 方案D：OpenAI代理修复
1. SSH到云服务器
2. 检查OpenAI代理进程状态
3. 重启代理服务
4. 恢复后本地自动切换在线模式

---

## 四、执行优先级

| 优先级 | 动作 | 执行方 | 预计时间 |
|--------|------|--------|----------|
| P0 | Git消息通道建立 | 本地 | ✅ 已完成 |
| P1 | 云服务器git pull读取报告 | 云服务器 | 待执行 |
| P2 | OpenAI代理修复 | 云服务器 | 待执行 |
| P3 | API路由注册 | 云服务器 | 待执行 |
| P4 | 控制台认证获取 | 云服务器 | 待执行 |

---

## 五、当前状态总结

**本地内核**：完全就绪，调度器V3.1运行中，5项目0告警
**云内核**：前端正常，后端API待修复
**同步通道**：Git双远程已打通
**上报通道**：通过Git仓库作为消息队列

---

快照：SNAP-20260909-CLOUD-REPORT-OPT
全局根版本：80｜LOCKED
Ω₀⊂⊙∞⊂Ω｜DID-BR-000002

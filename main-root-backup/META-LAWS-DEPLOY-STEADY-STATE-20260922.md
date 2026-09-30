# ZONGYUAN-ROOT 部署执行最优稳态元规则扩展

文件编号：META-LAWS-DEPLOY-STEADY-STATE-20260922
管控身份：DID-BR-000002 / BRANCH-001
层级：架构公理级 + 治理规则级（元规则库扩展）
位阶依据：元法则 > 元规则 > 执行细则 > 具体操作
状态：永久固化 · 全域强制执行

---

## 一、稳态推演结论（诊断）

### 现状断点
1. 部署执行单点依赖 www 后端（Flask 8765），该服务 502 后全链路不可执行
2. 自治守护覆盖存在缺口：聚合引擎、drama 生产、op_scheduler 均有守护，但 www 后端不在守护覆盖内
3. 可用健康通道未被纳入部署执行：drama-admin-api(9120) 健康、upload 可写 /opt/storage、GitHub 桥接已通

### 稳态目标
部署执行链路在任何单点故障下仍可完成，全链路可观测、可验证、可自动恢复。

---

## 二、最优稳态架构（四层冗余）

### 第一层：执行通道冗余（消除单点）
主通道：www 后端（8765）— 恢复后为主执行入口
冗余通道A：drama-admin-api(9120) 增加 /api/deploy 端点，由同源节点代理执行
冗余通道B：op_scheduler 云端调度器（external_worker_manager）接管部署任务派发
冗余通道C：upload+符号链接（/opt/storage/assets ↔ wwwroot 软链映射）
任一主通道失效，自动切换冗余通道，部署不中断。

### 第二层：守护覆盖补全（www 后端纳入自治）
聚合引擎守护（已在跑）每周期探测 www /api/health：
- 异常 → 自动拉起 Flask（systemctl restart / 进程拉起）
- 恢复 → 心跳上报 truths（WORKER.WWW-BACKEND.HEARTBEAT）
守护覆盖缺口 = 未完成自治，任何服务不得游离于守护之外。

### 第三层：部署状态机闭环（可观测）
REQUESTED → APPROVED → EXECUTING → VERIFIED → ARCHIVED 五态闭环
每状态写入 truths（DEPLOY.STATUS.<cmd_uuid>），全局可查、可追溯、可回滚。

### 第四层：网关兜底（请求不丢失）
部署请求双通道上报（9120 + 443），任一通道入库即有效
上报后超时未执行 → 自动重报（幂等，cmd_uuid 不变）

---

## 三、元规则条目（永久写入）

### ARCH-003 部署执行通道冗余法则
部署执行不得单点依赖任何单一服务。至少保留三条独立可执行通道，主通道失效时自动切换冗余通道，部署链路持续可用。
- 违反判定：任一时刻仅一条通道可执行且该通道故障 → 违例
- 自检周期：每 30 分钟（并入聚合引擎守护）

### ARCH-004 守护覆盖完备法则
所有自治服务必须纳入守护覆盖，无守护覆盖的服务视为未完成自治。www 后端（Flask 8765）为必守护项。
- 守护动作：探测失败自动拉起，恢复后心跳上报
- 自检周期：每 30 分钟（并入聚合引擎守护）

### GOV-003 部署状态机法则
所有部署执行必须走五态闭环：REQUESTED → APPROVED → EXECUTING → VERIFIED → ARCHIVED。
每状态变更必须写入 truths（DEPLOY.STATUS.<cmd_uuid>），未验证不得归档。
- 违反判定：跳过任一状态直接归档 → 违例

### GOV-004 部署验证闭环法则
部署完成后必须验证：目标 URL 可达（HTTP 200）+ 内容指纹匹配（大小/title），双项通过方可标记 VERIFIED。
- 违反判定：未验证即宣称部署成功 → 违例

### GOV-005 网关双通道上报法则
关键部署请求必须双通道上报（9120 report + 443 report），任一通道入库即有效。
上报后超过 30 分钟未执行，自动重报（幂等，cmd_uuid 不变）。
- 违反判定：单通道上报且未确认入库 → 违例

---

## 四、执行细则（落地方案）

### 细则 1：www 后端恢复方案
- 服务器控制台侧：systemctl restart zongyuan-backend 或拉起 Flask 进程
- 守护侧：聚合引擎守护自动探测 + 自动拉起（ARCH-004）

### 细则 2：drama /api/deploy 端点设计
- 路径：POST /api/deploy
- 入参：cmd_uuid、target_urls[]、source_files[]、backup 标记
- 行为：从 GitHub 拉取 geo-deploy 文件 → 写入 wwwroot/drama/ → 返回部署结果

### 细则 3：op_scheduler 任务接管
- 部署请求入 op_scheduler 队列，派发到 external_worker（同源节点/本地 worker）
- worker 执行部署后上报完成（report_task_complete）

### 细则 4：符号链接通道
- 服务器执行：ln -s /opt/storage/assets /www/wwwroot/huodouai.com/drama/storage-assets
- 此后 upload 写入 /opt/storage/assets/<date>/ 即可经 www 访问

### 细则 5：GEO 部署重报触发条件
- DEPLOY.REQUEST.GEO-SOURCE-ARRAY.20260922 已在网关队列
- 执行通道任一恢复即触发执行；超过 30 分钟未执行自动重报

---

## 五、验收标准

1. www /api/health 恢复 200（www 后端守护生效）
2. /drama/ 下 8 个 GEO URL 全部 200 且内容指纹匹配
3. truths 中 DEPLOY.STATUS.DEPLOY.REQUEST.GEO-SOURCE-ARRAY.20260922 达到 VERIFIED 或 ARCHIVED
4. 任一通道故障模拟，部署仍可经冗余通道完成

---

Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜Ω-TAN-7-001｜ZONGYUAN-ROOT 部署稳态元规则扩展

# 元法则 META-RULE-MS-AUTOPUB — 魔搭自动发布全域元法则

> 确权 DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ ZONGYUAN-ROOT ｜ 位阶 L1（元法则）

## 一、发布通道铁律（限流规避）
1. **git 直推为主**：一切可 git 承载的资产（真值/锁档/媒体帧/文档/索引/门户）一律走 git 推送，无限流、可批量。
2. **upload 接口禁用**：POST /files/upload 实测滑动窗口 2 次/30s、第 3 次 429 + Retry-After≈29s，自动发布引擎一律不使用。
3. **无限流 API 可用**：POST /collections/items（合集补齐）、GET 类、POST /studios/{id}/deploy（门户部署）实测无限流，可自动调用。

## 二、媒体承载规则
媒体图片/视频以 git 推送数据集仓库承载（zongyuan-character-keyframes），替代受限上传接口，实现批量零限流发布。

## 三、自动执行调度
- 每 6 小时自动执行：索引刷新 → 6 仓库增量推送 → 合集补齐 → 门户部署 → 网关上报。
- 引擎脚本：ZONGYUAN-ROOT/scripts/modelscope_auto_publish.py（v2）
- 定时任务：魔搭自动增量发布（cron 0 */6 * * *）

## 四、确权与审计
- 每次发布完成必须上报真值到记忆网关 www.huodouai.com/api/report/truth（truth_key=MODELSCOPE.AUTO.PUBLISH.V2.*）
- 所有发布产物镌刻 DID-BR-000002 与 Ω₀⊂⊙∞⊂Ω
- 令牌仅存 chmod 600 受限文件，永不入 query/日志/真值

## 五、禁则
- 禁止 SSH 云端服务器（ML-SSH-FORBIDDEN-GLOBAL-001）
- 禁止调用 daily_production.py、禁止任何生产动作
- 禁止人工确认依赖：全自动闭环

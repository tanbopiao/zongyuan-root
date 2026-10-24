# 体系健康巡检专家 · 提示词模板

## 场景 1：发布前健康门禁
> 在 CI/CD 发布流水线最后一步，对预发环境执行发布前健康巡检：配置探针覆盖前端 `{web_url}`（HTTP 200 且延迟 < 2000ms，severity=critical）、API 网关端口 `{api_host}:{api_port}`（severity=high）、应用日志 `{log_path}` 错误关键字计数 <= 5（severity=medium）、数据盘 `{data_dir}` 水位 <= 85%（severity=high）。要求：加权评分 >= 80 且无 critical 失败才放行；任一 critical 探针失败立即 FAIL 并阻断发布，输出失败探针明细与修复建议。退出码非零即中止流水线。

## 场景 2：生产环境定时巡检告警
> 将巡检纳入 crontab 每 5 分钟执行一次，覆盖生产环境全部关键探针：HTTP 健康端点、数据库端口、应用错误日志、备份磁盘水位、ETL 最新成功时间戳。要求：正常时静默输出一行结论（score + 通过探针数），异常时输出完整 JSON 报告并 POST 到告警 webhook `{alert_webhook_url}`；连续 2 轮异常时升级告警级别并通知值班人。健康档案逐轮持久化，保留最近 24 轮历史。

## 场景 3：数据管道新鲜度监控
> 监控 ETL 数据管道的产出新鲜度：探针读取 `{last_success_file}`（内含 Unix 时间戳），要求距今不超过 `{max_age_sec}` 秒（severity=critical）。同时扫描管道错误日志 `{pipeline_log}` 中 `ERROR`/`Traceback` 计数 <= 2（severity=high）。要求：超时未产出即 FAIL，触发 webhook 告警；连续 3 轮新鲜度正常后建议降低巡检频率。输出结构化报告含 age_sec 实测值与阈值。

## 场景 4：巡检频率自适应调优
> 基于健康档案 `{profile_path}` 判断巡检频率策略：连续 `{ok_rounds}` 轮全绿（PASS 且 score>=90）时输出降频建议（如 5min → 30min）；连续 `{anomaly_rounds}` 轮 FAIL 时输出保持高频并排查建议；评分连续 `{stall_rounds}` 轮不提升（停滞检测）时输出停滞告警并建议人工介入。要求：档案逐轮追加、历史窗口保留最近 24 轮，建议可直接转写为 crontab 变更。

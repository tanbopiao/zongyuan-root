# OP-CRON-ALERT-007｜飞书告警定时通知算子

> 算子编号：OP-CRON-ALERT-007
> 归属体系：ZONGYUAN-ROOT 自治内核
> 状态：契约定稿 v1.0

---

## 一、真值契约

### 目标
监听其余算子执行后的日志回执，分级收集异常，推送飞书机器人 Webhook；正常无异常时静默。

### 执行流程
```
Step1  读取全局算子日志目录，读取本次任务执行回执
Step2  扫描回执内 warnings、alerts 数组
Step3  判断告警等级：INFO / WARN / ERROR
Step4  ERROR → 立刻推送飞书告警卡片；WARN → 汇总每日推送；INFO → 忽略
Step5  消息卡片包含：算子ID、时间戳、异常描述、文件路径、哈希信息
Step6  记录告警发送日志，5分钟内相同告警不重复推送
Step7  输出告警回执
```

### 禁止项
- ❌ 禁止推送 private 资产原图、完整本地路径、密钥、DID
- ❌ 无异常时发送空消息
- ❌ 短时间内重复推送同一条告警（限流防轰炸）

### 异常分支
| 异常 | 处理 |
|---|---|
| 飞书 webhook 调用失败 | 重试2次；失败写入本地告警日志，下轮重发 |
| 日志文件损坏 | 标记 log_parse_error，生成简易告警 |

---

## 二、输入输出 Schema

### 输入
```json
{
  "op_name": "OP-CRON-ALERT-007",
  "log_dir": "/archive/op_logs/",
  "feishu_webhook_key": "***",
  "rate_limit_seconds": 300
}
```

### 输出回执
```json
{
  "op_name": "OP-CRON-ALERT-007",
  "run_timestamp": "2026-10-10T23:45:00+08:00",
  "alert_count": 1,
  "sent_alerts": ["OP-VERIFY-002: hash_conflict detected"],
  "failed_send": 0
}
```

---

## 三、测试用例

| 编号 | 场景 | 预期 |
|---|---|---|
| TC-01 | 巡检发现文件篡改（ERROR） | 立刻推送飞书告警卡片 |
| TC-02 | 仅存在 INFO 级别日志 | 不推送消息 |
| TC-03 | 重复相同告警5分钟内 | 触发限流，不重复推送 |
| TC-04 | webhook 失效 | 重试两次，日志留存待下次发送 |
| TC-05 | 同步算子配额不足 WARN | 汇总到每日告警推送 |

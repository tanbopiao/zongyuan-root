# OP-VERIFY-002｜资产完整性定时巡检算子

> 算子编号：OP-VERIFY-002
> 归属体系：ZONGYUAN-ROOT 自治内核自检机制
> 状态：契约定稿 v1.0

---

## 一、真值契约

### 目标
定时遍历已归档资产，重算哈希并与账本记录比对，检测损坏/篡改/缺失，输出巡检报告，不修改任何资产。

### 执行流程（严格顺序）
```
Step1  读取 manifest.md 全部历史记录
Step2  逐条定位文件，检查是否存在
Step3  对存在文件重算 SHA256
Step4  与账本记录哈希比对：
        - 一致 → ok
        - 不一致 → corrupted/tampered 告警
        - 文件不存在 → missing 告警
Step5  统计各级 privacy_level 资产数量
Step6  输出巡检报告 JSON（只读，不写账本）
Step7  如发现异常，触发告警队列（待接入飞书通知）
```

### 禁止项
- ❌ 禁止修改、删除、移动任何已归档文件
- ❌ 禁止重写 manifest.md（只读巡检）
- ❌ 禁止在巡检过程中执行归档写入

### 异常分支
| 异常 | 处理 |
|---|---|
| manifest.md 缺失 | 报告状态 ledger_missing，不初始化 |
| 文件权限拒绝 | 记录 permission_denied，跳过 |
| 哈希不匹配 | 标记 integrity_fail，告警 |

---

## 二、输入输出 Schema

### 输入
```json
{
  "op_name": "OP-VERIFY-002",
  "manifest_path": "/archive/manifest.md",
  "asset_root": "/assets/",
  "schedule_cron": "0 3 * * *",
  "alert_on_fail": true
}
```

### 输出（巡检报告）
```json
{
  "op_name": "OP-VERIFY-002",
  "run_timestamp": "2026-10-11T03:00:00+08:00",
  "summary": {
    "total_records": 40,
    "integrity_ok": 40,
    "corrupted": 0,
    "missing": 0,
    "permission_denied": 0
  },
  "privacy_stats": {
    "private": 28,
    "public": 12
  },
  "alerts": [],
  "status": "clean"
}
```

---

## 三、测试用例

| 编号 | 场景 | 预期 |
|---|---|---|
| TC-01 | 全部资产完整 | status=clean，integrity_ok=总数 |
| TC-02 | 1张图片被篡改 | corrupted=1，alerts含文件路径 |
| TC-03 | 1张图片被删除 | missing=1，不崩溃 |
| TC-04 | manifest缺失 | ledger_missing，不初始化账本 |
| TC-05 | 巡检后资产无变更 | 报告只读输出，manifest未被修改 |

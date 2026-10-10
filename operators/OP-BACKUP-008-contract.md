# OP-BACKUP-008｜跨存储冷备份算子

> 算子编号：OP-BACKUP-008
> 归属体系：ZONGYUAN-ROOT 冷存储层
> 状态：契约定稿 v1.0
> 前置依赖：OP-ARCHIVE-001（账本稳定后才有备份源）

---

## 一、真值契约

### 目标
将本地热沙箱的资产账本与素材，加密增量同步至冷存储端（Gitee / GitHub 私有仓库 / 飞书云盘），实现跨存储冗余备份，冷端只读不回写。

### 备份目标（按优先级）
1. **文本内核**：manifest.md、算子契约、账本、元法则文档 → 推送至 Gitee/GitHub 私有仓库
2. **大体积素材**：图片、视频 → 仅本地保留，不推送 Git（按用户偏好规则）
3. **飞书云盘**：关键账本副本 → 通过 Lark 连接器上传

### 执行流程
```
Step1  读取 OP-ARCHIVE-001 的 manifest.md 最新版本
Step2  计算本次备份前的 Merkle 根，与上次备份记录比对
Step3  增量收集变更的文本文件（manifest、contract、README）
Step4  生成备份快照目录：/backup/YYYYMMDD-HHMM/
Step5  写入备份清单 backup-manifest.json（含文件列表、哈希、Merkle根）
Step6  推送文本文件至 Gitee/GitHub 私有仓库（git commit + push）
Step7  通过 Lark 连接器上传 manifest.md 副本至飞书云盘
Step8  记录备份点到本地 backup-history.log
Step9  输出备份回执 JSON
```

### 禁止项
- ❌ 禁止推送大体积图片/视频到 Git 仓库（仅文本内核）
- ❌ 禁止冷端反向覆盖本地热沙箱（冷端只读）
- ❌ 禁止备份未加密的凭证、Token、Webhook Key
- ❌ 禁止在备份过程中删除本地原文件
- ❌ 禁止未经用户审批修改备份目标仓库地址

### 异常分支
| 异常 | 处理 |
|---|---|
| Git push 失败（网络/权限） | 记录断点，下次续传，不中断整体任务 |
| Lark 连接器未授权 | 跳过飞书备份，仅完成 Git 备份，标记 `lark_skipped` |
| Merkle 根未变化 | 跳过本次备份，回执 `no_changes` |
| 仓库远端被他人修改 | 先 pull 合并，冲突时按账本时间戳+HASH裁决，不静默覆盖 |

### 备份频率
- 文本内核：每日 03:30 定时备份（增量）
- 全量快照：每周日 04:00 触发一次全量

---

## 二、输入输出 Schema

### 输入
```json
{
  "op_name": "OP-BACKUP-008",
  "local_manifest_path": "/archive/manifest.md",
  "git_repo": "git@github.com:user/zongyuan-root.git",
  "git_branch": "converge",
  "lark_upload_enabled": true,
  "lark_folder_token": "",
  "exclude_large_files": true,
  "large_file_extensions": [".jpg", ".jpeg", ".png", ".mp4", ".webp"],
  "schedule_cron": "30 3 * * *"
}
```

### 输出回执
```json
{
  "op_name": "OP-BACKUP-008",
  "run_timestamp": "2026-10-11T03:30:00+08:00",
  "summary": {
    "backup_type": "incremental",
    "files_changed": 3,
    "git_push_status": "success",
    "lark_upload_status": "success",
    "merkle_root_before": "a3f5...",
    "merkle_root_after": "b7c9..."
  },
  "snapshot_path": "/backup/20261011-0330/",
  "backup_history_entry": "20261011-0330 | incremental | success",
  "warnings": []
}
```

---

## 三、测试用例

| 编号 | 场景 | 预期 |
|---|---|---|
| TC-01 | manifest 有3处变更 | 生成快照目录，git push 成功，飞书副本上传 |
| TC-02 | Merkle 根未变化 | no_changes，跳过备份 |
| TC-03 | 大体积图片存在 | 被 exclude_large_files 过滤，不推送 Git |
| TC-04 | Lark 连接器未授权 | lark_skipped，Git 备份仍完成 |
| TC-05 | Git push 网络失败 | 记录断点，下次续传，不删除本地快照 |
| TC-06 | 冷端反向覆盖测试 | 冷端只读，不触发本地回写 |
| TC-07 | 备份后回读校验 | 从 Gitee pull 回 manifest，哈希与本地一致 |

---

## 四、技术约束
- Git 操作使用 `git` CLI（沙箱预装）
- Lark 上传通过 `lark-drive` 技能调用
- 备份分支固定 `converge`（单源真值分支，按用户元公理）
- 提交信息格式：`backup: YYYYMMDD-HHMM | incremental | N files`
- 备份历史永不删除，保留全部历史快照

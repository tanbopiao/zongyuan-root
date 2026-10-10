# OP-ARCHIVE-001｜资产增量归档算子

> 算子编号：OP-ARCHIVE-001
> 归属体系：ZONGYUAN-ROOT 持久层真值账本
> 状态：契约定稿 v1.0

---

## 一、真值契约

### 目标
扫描指定目录下的图片资产，计算真实哈希，增量写入归档账本，产出归档回执，并对已锁档资产执行只读保护。

### 前置条件
- 云容器内存在待归档资产目录（如 `/assets/portrait/`）
- 每个资产旁存在同名 `.meta.json` 提示词元数据文件（可选，缺失则标记 `meta_missing`）
- 归档根目录下已有 `manifest.md` 账本（首次运行自动初始化）
- 隐私分级标记存在于 `.meta.json` 的 `privacy_level` 字段（`private` / `public`）

### 执行流程（严格顺序）
```
Step1  扫描资产目录，收集所有图片文件（.jpg/.jpeg/.png/.webp）
Step2  对每个文件计算 SHA256 哈希
Step3  读取同名 .meta.json，解析提示词、主题、privacy_level、时间戳
Step4  与 manifest.md 已有记录比对：
        - 哈希一致且未变更 → 跳过，标记 unchanged
        - 哈希不一致（文件被修改）→ 触发告警，不自动覆盖旧记录
        - 新文件 → 追加新记录
Step5  追加写入 manifest.md（纯增量，禁止覆盖历史行）
Step6  计算 Merkle 根快照，写入 manifest 尾部
Step7  对新归档文件执行 chmod 444 只读锁档
Step8  输出归档回执 JSON
```

### 禁止项
- ❌ 禁止删除任何已归档文件
- ❌ 禁止修改 manifest.md 历史记录行（只追加）
- ❌ 禁止将 privacy_level=private 的资产标记为可对外
- ❌ 禁止在未计算真实哈希的情况下写入账本
- ❌ 禁止并发写入同一 manifest.md

### 异常分支
| 异常 | 处理 |
|---|---|
| 文件读取失败 | 记录 read_error，跳过该文件，不中断整体任务 |
| .meta.json 缺失 | 记录 meta_missing，资产仍归档，提示词字段留空 |
| 哈希与账本冲突 | 记录 hash_conflict，告警，保留旧记录，不覆盖 |
| manifest.md 不存在 | 自动初始化表头与目录结构 |

---

## 二、输入输出 Schema

### 输入
```json
{
  "op_name": "OP-ARCHIVE-001",
  "scan_dir": "/assets/portrait/",
  "manifest_path": "/archive/manifest.md",
  "lock_after_archive": true,
  "hash_algorithm": "sha256",
  "allowed_extensions": [".jpg", ".jpeg", ".png", ".webp"]
}
```

### 输出回执
```json
{
  "op_name": "OP-ARCHIVE-001",
  "run_timestamp": "2026-10-10T22:30:00+08:00",
  "summary": {
    "total_scanned": 40,
    "new_archived": 0,
    "skipped_unchanged": 40,
    "hash_conflict": 0,
    "meta_missing": 0,
    "read_error": 0
  },
  "merkle_root": "a3f5...e9b2",
  "new_files": [],
  "warnings": [],
  "lock_status": "all_archived_readonly"
}
```

---

## 三、测试用例

| 编号 | 场景 | 输入 | 预期结果 |
|---|---|---|---|
| TC-01 | 正常新文件归档 | 目录有3张新图，无历史账本 | 3条新记录追加，哈希正确，文件chmod 444 |
| TC-02 | 重复扫描无变更 | 已归档40张，再次扫描 | 全部 skipped_unchanged，账本不变 |
| TC-03 | 文件被篡改 | 已归档1张，内容被修改 | hash_conflict告警，旧记录保留不覆盖 |
| TC-04 | meta.json 缺失 | 图片存在但无meta文件 | meta_missing警告，图片仍归档 |
| TC-05 | 隐私分级不泄露 | privacy_level=private | 回执中标记private，不输出public列表 |
| TC-06 | 只读锁档验证 | 归档后尝试写入文件 | chmod 444生效，写入被拒绝 |
| TC-07 | 损坏文件 | 目录中有0字节文件 | read_error告警，跳过，不中断 |
| TC-08 | 并发写入保护 | 两个进程同时跑 | 第二个进程检测到锁，等待或退出 |

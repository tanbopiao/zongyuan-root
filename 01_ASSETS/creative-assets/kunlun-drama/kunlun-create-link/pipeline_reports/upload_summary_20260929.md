# 魔搭全量质检归档上传摘要 — 2026-09-29

- **DID**: DID-BR-000002
- **Trace**: Ω₀⊂⊙∞⊂Ω
- **目标仓库**: `zongyuanroot/zongyuan-character-keyframes`（dataset）
- **db 回传仓库**: `zongyuanroot/zongyuan-root-achievements` → `shared_brain.db`
- **记忆网关**: https://www.huodouai.com/api/report/truth

## 总计

| 指标 | 数值 |
|---|---|
| 待传总数 | 15 |
| 上传成功 | 15 |
| 跳过(skip) | 0 |
| 失败 | 0 |
| db 新增登记 | 15 |
| db 最终行数 | 355（上传前 340 + 15） |
| 公网 URL 验证通过 | 15/15 |
| 网关上报 | 3 次均 success=True |

## 分批结果

| 批次 | 内容 | 子目录 | 成功/失败 | db 新增 | 网关 |
|---|---|---|---|---|---|
| 1 | 8 张幽墟裂隙关键帧 jpg（KF-003~010） | `archive_kunlun-20260913/keyframe_kf003_010_20260913/` | 8/0 | +8（id→348） | True |
| 2 | 5 张九天玄女战斗帧 webp | `xn_webp/` | 5/0 | +5（id→353） | True |
| 3 | 2 条视频 mp4（HEVC 720×1280） | `archive-videos-20260913/` | 2/0 | +2（id→355） | True |

## 去重预检

- 上传前基于本地 `shared_brain.db` 快照（340 条）按 name/sha256 比对：15 个文件均无重复 → 0 skip。
- 脚本运行时每批从魔搭拉取最新 db，再按 sha256 去重插入；本批 15 个 sha256 均为新值，全部落库。

## 公网 URL 验证

- 方法：`urllib` HEAD（失败回退 GET Range: bytes=0-0）跟随 302 重定向。
- 结果：15/15 最终 HTTP 200，Content-Type 全部匹配预期：
  - 8 张 jpg → `image/jpeg`
  - 5 张 webp → `image/webp`
  - 2 条 mp4 → `video/mp4`
- 无失败条目，无需重试。

## db 登记与回传

- 表 `assets(id,name,category,path,sha256,locked_at)`，path 格式 `modelscope://zongyuanroot/zongyuan-character-keyframes/<sub>/<rel>`。
- 脚本每批：下载云端最新 db → 按 sha256 去重 INSERT → 回传覆盖 `zongyuan-root-achievements/shared_brain.db`（日志可见 106k 上传完成）。
- 最终本地副本与云端一致：355 行，15 条新资产全部可按 path 反查命中。

## 记忆网关

- 脚本自动上报 3 次（每批一次），payload 含 event=ms_persist_push、repo、subdir、pushed/failed/db_added、files 列表、did、trace。
- 三次响应均为 `success=True`。

## 日志

- `pipeline_reports/_batch1.log` / `_batch2.log` / `_batch3.log`
- 结构化清单：`pipeline_reports/upload_manifest_20260929.json`

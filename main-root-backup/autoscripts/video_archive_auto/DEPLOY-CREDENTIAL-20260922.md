# 昆仑洞天视频自动化归档流水线 部署凭证

**部署日期：** 2026-09-22
**部署节点：** NODE-DEV-DOUBAO-WORK-001
**身份标识：** DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
**生效元规则：** META.RULE.VIDEO_CDN_AUTO_ARCHIVE.V1

---

## 部署路径

```
ZONGYUAN-ROOT/
├── autoscripts/video_archive_auto/
│   ├── video_archive_auto.sh      # 主下载归档脚本
│   ├── video_timer_scan.sh        # 定时巡检脚本
│   ├── video_archive_schema.json # 元数据字段规范
│   └── scan_log.log              # 巡检日志
└── assets/media/jiutian_xuannu_video_meta/
    └── raw/
        ├── EP01.json              # EP01元数据（待重生成）
        ├── EP02.json              # EP02元数据（待重生成）
        ├── EP03.json              # EP03元数据（待重生成）
        └── EP04.json              # EP04元数据（待生成）
```

## 脚本功能

### video_archive_auto.sh
- **功能：** 断点续传下载MP4 → SHA256校验 → 更新元数据 → 写入全局哈希链
- **用法：** `./video_archive_auto.sh <EP_ID> <DOWNLOAD_URL> [EXPIRE_AT]`
- **权限：** 可执行

### video_timer_scan.sh
- **功能：** 扫描全部视频meta，监控CDN有效期，临近4小时自动下载
- **触发：** crontab 每6小时执行一次
- **巡检结果：** 写入 scan_log.log

## 定时任务

| 任务 | 周期 | 命令 |
|------|------|------|
| 视频资产CDN巡检 | 每6小时 | `bash .../video_timer_scan.sh` |

## 当前资产状态

| 剧集 | 状态 | 本地归档 | CDN状态 |
|------|------|----------|---------|
| EP01 云阶登场 | 待重生成 | ❌ | 已过期 |
| EP02 出殿召辇 | 待重生成 | ❌ | 已过期 |
| EP03 混沌裂隙 | 待重生成 | ❌ | 已过期 |
| EP04 混沌溯源 | 待生成 | ❌ | 无链接 |

## 依赖检查

- ✅ jq 1.6 可用
- ✅ wget 1.21.2 可用
- ✅ crontab 已注册
- ✅ 巡检脚本测试通过

## 闭环流程

```
视频生成 → 拿到task_id + CDN链接
  → 写入raw/EPxx_meta.json
  → 调用video_archive_auto.sh下载MP4
  → SHA256校验 + 写入HASH-LEDGER
  → local_archive=true
  → 巡检脚本持续监控，过期前自动下载
```

---

Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ Lv10稳态自治

# 短剧工业化资产（kunlun-drama）

## 批次名称
短剧工业化资产

## 来源路径
`/home/user/Doubao/chats/1128121028098/`

复制时间：2026-10-11（UTC+8）

## 包含内容概要

本批次从源工作目录整目录复制 5 个子目录，覆盖昆仑洞天短剧工业化生产流水线的脚本、分镜、台词、生产代码与关键帧资产：

| 子目录 | 内容概要 |
|---|---|
| `drama-pipeline/` | 流水线入口展示页（index.html） |
| `creation-plan/` | 全域系统化创作规划、工作台前端（workbench-v2、gallery、_zr 系列控制台）、注册归档脚本、分镜与 QA 目录、persist 持久层 |
| `drama-workbench/` | 昆仑洞天短剧生产工作台：一键量产向导、生产服务端（one_key_production.py / drama_production_server.py）、DRM-PIPE-V1.3 管线、live 实时产物、artifacts / artifacts_live / artifacts_zhipu 三类产出目录、分镜目录 |
| `kunlun-dongtian/` | 昆仑洞天 IP 主展示页（index.html）、assets 资产目录、分镜目录 |
| `kunlun-create-link/` | 统一入库与归档链路：kunlun_unified_pipeline / kunlun_ms_archive / auto_ingest_videos、多路径部署（multi-path-deploy）、huodouai 画廊部署包、meta-lock 锁档目录、shared-brain、pipeline_reports、分镜目录 |

资产类型涵盖：
- **脚本 / 创作规划**：全域系统化创作规划.html、创作规划相关 HTML
- **分镜**：各子目录下 `_shots/` 目录
- **台词 / 生产文档**：USAGE.md、DRAMA-LIVE-VERIFY 验证报告
- **代码**：Python 生产脚本、部署 shell、前端 JS/HTML
- **关键帧 / 图片资产**：各 assets 目录、artifacts 产出目录

## 排除清单及原因

以下内容在复制后已从目标树中删除，未入仓：

| 排除项 | 原因 |
|---|---|
| 所有 `__pycache__/` 目录、所有 `*.pyc` 文件 | Python 编译缓存，不应入 git |
| `creation-plan/_server_produce.py`、`creation-plan/_server_produce.bak.py` | **含真实 API Key 常量（变量名为 AGNES 前缀），严禁外泄，已从仓库树中排除** |
| `kunlun-create-link/_ms_push/` | 约 55 MB 魔搭推送暂存目录，冗余临时数据，未入仓 |
| `kunlun-create-link/_redundant_backup/` | 约 22 MB 冗余备份（含 mp4），未入仓 |
| `kunlun-create-link/_backup_v1/`、`_archived_redundant/`、`_archived_sop_v1/` | 历史冗余备份目录，未入仓 |
| `drama-workbench/_backup/` | 冗余备份目录，未入仓 |
| 所有 `*.log` 文件 | 运行日志，仓库策略不入 git |

## 安全说明
本批次在入库前已执行敏感信息终扫（API Key 正则、身份证号、案号等），目标树终扫 0 命中。

# ZONGYUAN-ROOT 多路径智能调度部署 SOP V1.0

**归属**：ZONGYUAN-ROOT / 火斗云智AIOS / 官网自动部署
**DID**：DID-BR-000002 | **锚定**：Ω₀⊂⊙∞⊂Ω
**生效**：2026-09-29 | **性质**：protocol（协议类）
**配套元法则**：MR-DEPLOY-AUTO-001（审批通过后中枢自动部署）

---

## 1. 核心原则

> **最优稳态优先，故障自动切换备用**。四条部署路径全部实现，每次部署前对所有路径执行稳态探针，从最高优先级可用路径开始部署；路径中断自动降级到下一备用路径；全部失败自动回滚 + 告警 + 故障台账。

## 2. 部署路径矩阵

| 优先级 | 路径ID | 名称 | 角色 | 当前状态 | 依赖 |
|---|---|---|---|---|---|
| P0 | git_pull | Git仓库拉取 | 主路径 | ⏸ 未就绪 | GIT_REMOTE_URL + 云端sync仓库 |
| P1 | modelscope_pull | 魔搭数据集拉取 | 备用1 | ✅ 可用 | 魔搭SDK/HTTP(已实测200) |
| P2 | oss_pull | 对象存储中转 | 备用2 | ⏸ 未就绪 | OSS/TOS密钥 |
| P3 | ssh_rsync | SSH rsync直推 | 备用3 | ❌ 故障 | SSH公钥授信修复 |

## 3. 目录结构与命令

```
kunlun-create-link/multi-path-deploy/
├── deploy_paths_config.json    # 4路径配置+探针+优先级+降级规则
├── deploy_scheduler.py         # 智能调度器(探针+优先级+切换+回滚)
└── executors/
    ├── git_pull_deploy.sh      # P0 Git拉取部署
    ├── modelscope_pull_deploy.sh  # P1 魔搭拉取部署
    ├── oss_pull_deploy.sh      # P2 对象存储部署
    ├── ssh_rsync_deploy.sh     # P3 SSH rsync部署
    └── rollback_common.sh      # 通用回滚(保留最近5版)
```

命令：
```bash
# 稳态探针(不部署,刷新状态)
python3 deploy_scheduler.py --dry-run
# 智能部署(自动择优+降级+回滚)
python3 deploy_scheduler.py --deploy --batch <BATCH_ID>
```

## 4. 标准执行流程（Webhook 触发）

```
飞书【官网画廊发布审批】通过
  → 推送事件到 Webhook https://huodouai.com/api/deploy/webhook
  → Webhook 校验 X-DID + SHA256 签名
  → 云端 Worker 异步入队(避免超时重复回调)
  → 调用 deploy_scheduler.py --deploy --batch <BATCH_ID>
  → 全路径探针 → 按优先级从可用路径部署
  → 部署成功: 写入共享大脑发布台账 + 记忆网关上报 + ntfy通知
  → 部署失败: 切换备用路径 / 全失败回滚 + 告警
```

## 5. 智能调度逻辑

```
1. 全路径稳态探针 → 刷新状态(ready/broken/config_pending)
2. 从最高优先级路径开始:
   - config_pending: 跳过(缺配置,不算故障)
   - broken: 跳过并记录
   - ready: 执行部署
3. 部署失败 → 记录 + 切下一备用路径
4. 全部失败 → 触发: 回滚最近备份 + 告警 + 故障台账 + 网关上报
5. 成功 → 登记 shared_brain.db + 记忆网关上报
```

## 6. 回滚与备份策略

- 每次部署前强制备份当前线上 gallery → `/www/wwwroot/backups/gallery/<批次>_<时间戳>`
- 保留最近 5 个版本，超出自动清理
- 部署失败/自检失败 → 自动回滚到最近备份 + nginx reload

## 7. 各路径就绪清单

### P0 Git（需配置）
- 云端服务器 `/www/wwwroot/gallery-repo` 为 git 仓库
- `export GIT_REMOTE_URL="https://gitee.com/huodou-cloud-intelligence-aios/zongyuan-root-sync.git"`
- 服务器出站访问 Git（无需入站SSH）

### P1 魔搭（✅ 当前可用）
- 魔搭数据集 `zongyuanroot/zongyuan-root-achievements` 含 `data_lake/outreach-p3/` 部署包
- 单文件 GET 已实测 302→200 匿名可用

### P2 对象存储（需密钥）
- `export OSS_ENDPOINT/OSS_BUCKET/OSS_KEY/OSS_SECRET`
- 部署包上传至 `gallery-deploy/<批次>/`

### P3 SSH（需修复）
- 修复 `123.207.202.158` authorized_keys（当前公钥不被接受）
- SSH 别名 `zongyuan-cloud` 恢复连通后启用

## 8. 安全约束（强制）

1. Webhook 仅飞书审批出口IP可访问（nginx IP白名单）
2. 所有入站校验 X-DID 同源协议头 + SHA256 工单签名
3. Webhook 不可绕过飞书审批直接部署（高危动作必须人工审批）
4. 每次部署强制备份，保留5版本可回滚
5. 部署流水线超时 1200s，超时自动终止回滚
6. 所有操作日志写入飞书多维表格 + Merkle-DAG 账本

## 9. 待完成

- [ ] P0 Git 仓库与 GIT_REMOTE_URL 配置
- [ ] P2 对象存储密钥配置
- [ ] P3 SSH authorized_keys 修复
- [ ] 云端 Worker 启动（当前 /api/deploy 502）
- [ ] 飞书部署专用审批定义创建

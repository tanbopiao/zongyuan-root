# 魔搭共享数据湖 · 官网灾备与运行入口说明

> DID-BR-000002 | 锚定 Ω₀⊂⊙∞⊂Ω | 2026-09-30

## 一、数据湖定位
魔搭 `ZONGYUAN-SHARED-DATALAKE` 数据集是 ZONGYUAN-ROOT 体系的**公开分发+灾备双通道**（零成本，Apache-2.0）。

## 二、官网灾备结构（local-root/ 分区）
| 目录 | 内容 | 灾备用途 |
|---|---|---|
| homepage-mirror/ | 官网镜像（含 .well-known/assets/api-docs） | 官网停机时可用魔搭数据湖文件恢复站点 |
| homepage-en/ | 英文官网镜像 | 海外访问镜像 |
| homepage-evolution/ | 官网迭代版本快照 | 回滚与版本对比 |
| homepage-drawer/ | 官网抽屉组件资源 | 前端资源备份 |
| 本地base台账 | 飞书台账离线副本 | 台账双备 |

## 三、运行入口（对外可公开的文件）
- 白皮书：`zongyuan-root/whitepapers/ZONGYUAN-AIOS-TECH-WHITEPAPER-V2.0.{md,html}`
- 确权：`ATTESTATION-WHITEPAPER-V2.0-20260929.json`
- 内核：`zongyuan-kernel/`（config/var/audit）

## 四、灾备恢复流程（SOP）
1. 官网不可达 → 登录魔搭数据湖 → 下载 `local-root/homepage-mirror/` 全量
2. 部署到云服务器网站根目录（走 deploy@SSH 低权限密钥，仅写 /works 与数据湖PUBLIC）
3. 验证 HTTP 200 → 更新资产台账状态
4. 官网恢复后：对比 homepage-mirror 与当前线上，只同步差异

## 五、同步机制
- 云服务器每10分钟拉取魔搭侧最新成果 → 写入中心数据湖 PUBLIC
- 本地节点每10分钟从数据湖拉取 → active_assets
- 手工同步：`sync-datalake.sh`（push/pull/status）

## 六、边界
- 数据湖仅存资产文件，不替代实时服务巡检（实时状态走记忆网关/节点真实查询）
- 密钥与敏感配置不进入公开数据湖（全量归档走私有仓库 zongyuan-root-full-archive）

# 官网全域推送回执 · 2026-11-06

确权：DID-BR-000002 ｜ 锚定：Ω₀⊂⊙∞⊂Ω
通道：Gitee `web-deploy` 分支（唯一合法发布路径，SSH 全域禁止）

## 一、推送结果（已完成：源码侧）

| 项 | 值 |
|---|---|
| 仓库 | gitee.com/huodou-cloud-intelligence-aios/ZONGYUAN-ROOT |
| 分支 | web-deploy |
| 起始提交 | ee02ef92 |
| 当前提交 | fcf79d39 |
| 推送次数 | 3 次提交（f455ecce → 586054fe → fcf79d39） |
| 账本登记 | 母体 HASH-LEDGER.csv 已追加 3 条 |

## 二、发布清单（4 页，双路径）

| 页面 | 首选路径 | 根级备用路径 | sha256（前16位） |
|---|---|---|---|
| 全域自治巡检状态页 | /status/autonomy-20261106.html | /autonomy-20261106.html | bcd62472… / b03de66e… |
| 全域对外展示总览 | /showcase/all-domain.html | /showcase-all-domain.html | b4b92ba9… / 867e0cf8… |
| 全域信息架构树 | /info-architecture.html | — | b1d43f6a… |
| 入口接入 | /domains/index.html、/showcase/index.html、sitemap.xml | — | — |

## 三、线上核验（2026-11-06 09:26 UTC+8）

| URL | 状态 |
|---|---|
| https://www.huodouai.com/info-architecture.html | 200（此前已由云端侧上线） |
| https://www.huodouai.com/autonomy-20261106.html | 404 |
| https://www.huodouai.com/showcase-all-domain.html | 404 |
| https://www.huodouai.com/status/ ｜ /showcase/ | 200（旧内容）｜ 404 |

结论：**分支侧推送完成，线上未同步**。根级与子目录文件均未被云端 pull 到 web root；站点现有内容与本仓库 web-deploy 分支内容哈希不一致（线上 index.html 与历史任一提交均不匹配），说明云端 web root 是本地直接改维护，定时 pull 未配置或已停用。

## 四、阻塞与解除方式（需用户决策，二选一）

1. **首选（零成本、符合铁律）**：云端执行层一次性配置 web root 的 git remote + 每 5 分钟 pull（HTTP 通道）。执行后本轮 4 个页面自动上线，无需再推送。
2. **备选（需人工审批解锁）**：临时解除 ML-SSH-FORBIDDEN-GLOBAL-001，授权一次 SSH 部署，部署后立即恢复只读锁。

## 五、本轮顺手修复的断点

- 巡检发现 `/api/report/status`、`/api/report/truths`、`/api/upload` 全部 404（记忆网关写通道缺失），`/api/status` 正常（truth_count 117862，heartbeat 2026-11-06 09:05）。
- 巡检发现账本自 2026-10-01 起 36 天无增量，eFuse 链 2 节点 0 熔断，根 Merkle 注册表偏移。

DID-BR-000002

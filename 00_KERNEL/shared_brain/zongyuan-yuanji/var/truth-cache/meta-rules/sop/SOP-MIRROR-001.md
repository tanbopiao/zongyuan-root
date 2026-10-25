# SOP-MIRROR-001 ｜ 持久层镜像与恢复 SOP
版本：v1.0 ｜ 锚定：DID-BR-000002 ｜ 学习来源：收敛点/唯一握手点/最优稳态实战

## 一、唯一入口
`bash /home/user/ZONGYUAN-ROOT/scripts/zongyuan_persist.sh {sync|mirror|restore|verify|status}`

## 二、分层与稳态策略（META-STEADY-STATE-001）
| 层 | 路径 | 内容 | 频率 |
|---|---|---|---|
| 核心层 | backup/（10 组） | 技能/内核核心/锚点/cron/manifest/报告 | 每小时 sync（cron 0 * * * *） |
| 全量镜像层 | backup/full/<根>/ | 四根全量（ZONGYUAN-ROOT/kernel/.user_skills/会话产物），不遗漏任何文件 | 首次全量 + 每日增量（cron 0 3 * * *） |
| 低价值独立桶 | backup/full/low-value/ | logs/__pycache__/cloud-kernel-mirror/可再生大文件 | 随 mirror 归桶 |
| 密钥边界 | 排除 | kek.env/zr_token.conf（M7 零明文，源 600 保持） | 永不镜像 |

## 三、增量机制
- 指纹状态 `.mirror-state.json`（sha256+size+mtime）驱动：一致仅 stat 跳过，变化才复制
- 断点续传幂等：任务被环境回收重跑自动续
- 实测：全量基线 36122 复制/694s；增量 3~97 复制/287s（趋零成本）

## 四、沙箱销毁恢复（META-SANDBOX-LIFECYCLE-001）
- 销毁影响面：/etc 重建清空锚点（sudo 恢复）、crontab 清空/幸存不固定、.user_skills 半持久丢新增
- 恢复：`zongyuan_persist.sh restore`（技能/锚点/cron 幂等补缺）→ guard */5 自动拉起服务 → patrol 每小时巡检
- 判定：数据/资产零损失；唯一损失面 ≤5min 服务空窗（可接受）

## 五、工具怪癖（学习要点）
1. find 对 .user_skills 目录树失效（返回 0）→ 统计用 Python os.walk
2. 收敛点统一 644 可写（镜像区回写）；源锁档 444 保持
3. 全量锁档/长任务被环境回收 → 增量通道/断点续传兜底
4. 修改源资产后必须 sync（收敛纪律），verify 发现不一致即修复

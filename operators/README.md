# ZONGYUAN-ROOT 算子体系｜总 README

> 版本：v1.4（全集10算子）
> 打包时间：2026-10-10
> 打包人：DID-BR-000002
> 目录位置：`/operators/`

---

## 一、算子全集（10个）

| 编号 | 名称 | 职责 | 契约文件 | 测试用例 |
|---|---|---|---|---|
| OP-ARCHIVE-001 | 资产增量归档 | 扫描资产→算哈希→增量写账本→只读锁档 | OP-ARCHIVE-001-contract.md | 8 |
| OP-VERIFY-002 | 定时巡检校验 | 重算哈希→比对账本→检测损坏/篡改/缺失→告警 | OP-VERIFY-002-contract.md | 5 |
| OP-GALLERY-003 | 画廊网页渲染 | 读账本→过滤private→分组→生成静态HTML | OP-GALLERY-003-contract.md | 6 |
| OP-SCRIPT-GEN-009 | 剧本生成 | 世界观+大纲→生成分镜剧本+storyboard.json | OP-SCRIPT-GEN-009-contract.md | 5 |
| OP-BATCH-GEN-004 | 关键帧批量生成 | 读storyboard→批量调用图像API→落盘→自动归档 | OP-BATCH-GEN-004-contract.md | 6 |
| OP-VIDEO-PIPE-005 | 视频合音流水线 | 关键帧→图生视频→BGM/旁白混合→成片归档 | OP-VIDEO-PIPE-005-contract.md | 7 |
| OP-SYNC-MODEL-006 | 魔搭数据湖同步 | 筛选public资产→脱敏→增量同步至魔搭数据集 | OP-SYNC-MODEL-006-contract.md | 6 |
| OP-ASSET-REPORT-010 | 月度资产报表 | 每月汇总资产统计→生成月报→飞书云盘归档 | OP-ASSET-REPORT-010-contract.md | 5 |
| OP-CRON-ALERT-007 | 飞书告警通知 | 监听算子日志→分级告警→推送飞书Webhook | OP-CRON-ALERT-007-contract.md | 5 |
| OP-BACKUP-008 | 跨存储冷备份 | 文本内核增量备份→Gitee/GitHub+飞书云盘 | OP-BACKUP-008-contract.md | 7 |

---

## 二、依赖关系图

```
                    ┌─────────────────────┐
                    │ OP-SCRIPT-GEN-009  │  剧本→storyboard.json
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │  OP-BATCH-GEN-004   │  批量生成关键帧
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │  OP-VIDEO-PIPE-005 │  合成视频+音频
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │  OP-ARCHIVE-001     │  ★ 唯一写账本入口
                    └──┬──────┬──────┬────┘
                       ↓      ↓      ↓
            ┌──────────┐ ┌──────────┐ ┌──────────────┐
            │VERIFY-002│ │GALLERY-003│ │ SYNC-MODEL-006│
            │ 定时巡检 │ │  对外画廊 │ │ 魔搭公开同步  │
            └─────┬────┘ └──────────┘ └──────────────┘
                  ↓
            ┌──────────┐
            │BACKUP-008│  文本冷备份
            └─────┬────┘
                  ↓
            ┌──────────┐
            │REPORT-010│  月度资产报表
            └─────┬────┘
                  ↓
            ┌──────────┐
            │ALERT-007 │  全局异常监听→飞书
            └──────────┘
```

---

## 三、核心边界规则

1. **唯一写账本入口**：仅 OP-ARCHIVE-001 可写 manifest.md（纯增量，禁止覆盖历史）
2. **只读算子**：OP-VERIFY-002 / OP-GALLERY-003 / OP-SYNC-MODEL-006 / OP-BACKUP-008 对账本只读
3. **隐私分级**：private 资产默认不进画廊、不进魔搭、不对外
4. **冷端只读**：Git/Gitee 冷存储不反向覆盖本地热沙箱
5. **单源真值分支**：Git 固定 `converge` 分支，冲突按账本时间戳+HASH裁决
6. **异常不中断**：单文件失败跳过，记录告警，整体任务继续
7. **JSON回执**：所有算子输出结构化 JSON，可被上级调度器收集

---

## 四、迁移到工作任务沙箱｜一次性执行指令

> 在豆包APP新建「工作任务」会话，上传本目录全部8份契约文件后，下发以下指令：

```
请阅读 operators/ 目录下10份契约文档：
1. OP-ARCHIVE-001-contract.md
2. OP-VERIFY-002-contract.md
3. OP-GALLERY-003-contract.md
4. OP-SCRIPT-GEN-009-contract.md
5. OP-BATCH-GEN-004-contract.md
6. OP-VIDEO-PIPE-005-contract.md
7. OP-SYNC-MODEL-006-contract.md
8. OP-ASSET-REPORT-010-contract.md
9. OP-CRON-ALERT-007-contract.md
10. OP-BACKUP-008-contract.md

按契约要求，用 Python 3.10+ 实现全部10个算子：
- OP-ARCHIVE-001 / OP-VERIFY-002 / OP-GALLERY-003：纯标准库
- OP-SCRIPT-GEN-009 / OP-BATCH-GEN-004 / OP-VIDEO-PIPE-005：需调用LLM/图像/视频API
- OP-SYNC-MODEL-006：需调用魔搭API
- OP-ASSET-REPORT-010：纯标准库+飞书云盘上传
- OP-CRON-ALERT-007：需调用飞书Webhook
- OP-BACKUP-008：需 git CLI + lark-drive 技能

严格遵守契约中的流程顺序、禁止项、异常分支。
为每个算子编写单元测试，跑通全部测试用例（共60个用例）。

实施顺序（按依赖链）：
Phase 1: OP-ARCHIVE-001（基础）
Phase 2: OP-VERIFY-002 + OP-GALLERY-003
Phase 3: OP-SCRIPT-GEN-009 + OP-BATCH-GEN-004 + OP-VIDEO-PIPE-005
Phase 4: OP-SYNC-MODEL-006 + OP-ASSET-REPORT-010
Phase 5: OP-CRON-ALERT-007 + OP-BACKUP-008

每个 Phase 完成后跑通测试再进入下一个。
```

---

## 五、验收清单

- [ ] 10个 .py 算子文件全部生成
- [ ] 60个单元测试用例全部通过
- [ ] 用真实图片跑通 OP-ARCHIVE-001，manifest.md 正确写入
- [ ] 用真实账本跑通 OP-GALLERY-003，画廊 HTML 可离线打开
- [ ] 跑通 OP-VERIFY-002，能正确检测篡改文件
- [ ] 跑通 OP-SCRIPT-GEN-009，输出 storyboard.json 格式合法
- [ ] 跑通 OP-BATCH-GEN-004，关键帧自动归档
- [ ] 跑通 OP-VIDEO-PIPE-005，成片带 BGM 混音
- [ ] 跑通 OP-ASSET-REPORT-010，月报统计数与账本一致
- [ ] 跑通 OP-BACKUP-008，git push 成功且飞书副本上传
- [ ] OP-CRON-ALERT-007 能正确触发飞书告警卡片

---

## 六、目录结构

```
operators/
├── README.md                          ← 本文件（总入口，v1.4）
├── OP-ARCHIVE-001-contract.md
├── OP-VERIFY-002-contract.md
├── OP-GALLERY-003-contract.md
├── OP-SCRIPT-GEN-009-contract.md
├── OP-BATCH-GEN-004-contract.md
├── OP-VIDEO-PIPE-005-contract.md
├── OP-SYNC-MODEL-006-contract.md
├── OP-ASSET-REPORT-010-contract.md
├── OP-CRON-ALERT-007-contract.md
├── OP-BACKUP-008-contract.md
├── MIGRATION-PACK-v1.0.md             ← 历史版本（3算子）
├── MIGRATION-PACK-v1.1.md             ← 历史版本（4算子）
└── MIGRATION-PACK-v1.2.md             ← 历史版本（5算子）
```

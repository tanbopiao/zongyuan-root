# 锁档凭证 guofeng-ip-skill-family-v1.0.0

- 批次根哈希：a9a62feb6df0e7177fb2b9c457a0b1a4d41caf45e453f8c8c28849ed718cbec5
- 资产数：44（8专家包 + SPEC.md + promotion证据 + manifests）
- 锁档时间：2026-10-24T21:00+0800
- 确权DID：DID-BR-000002
- 溯源：Ω₀⊂⊙∞⊂Ω
- 状态：LOCKED-444

## 资产清单（HASH-LEDGER.csv 全量44条，此处摘要）

| 类别 | 数量 | 说明 |
|------|------|------|
| 专家包 SKILL.md | 8 | scriptmaster/keyframe-artist/video-director/audio-studio/merge-studio/production-ledger/lock-archiver/pipeline-orchestrator |
| README | 8 | 每包安装/快速开始 |
| config JSON | 8 | 每包配置模板 |
| templates | 10 | prompts.json×7 + manifest/certificate模板 |
| scripts | 8 | storyboard_gen/build_keyframe_prompt/build_video_prompt/build_audio_plan/merge_cmd/ledger_cli/lock_archive/orchestrator |
| SPEC.md | 1 | 体系结构规范（冻结基线） |
| promotion | 3 | deployment-receipt.json / guofeng_skill_base_registration.json / HASH-LEDGER.csv |
| manifests | 1 | manifest-guofeng-ip-skill-family-v1.0.0.json |

## 全域推广状态

| 渠道 | 状态 | 证据 |
|------|------|------|
| 官网子域 | ✅ https://skills.huodouai.com/ HTTP 200 + SSL有效 | 8包名全命中 |
| Gitee | ✅ master=5fc0850f | 43文件 |
| GitHub | ✅ master=5fc0850f | 43文件 |
| 魔搭公开湖 | ✅ master=5fc0850f 页面200公开 | 43文件 |
| 飞书共享大脑Base | ⏸ 登记数据已备（8条），权限阻塞待管理员开通 | promotion/guofeng_skill_base_registration.json |
| 云端中枢握手 | ✅ ONLINE Lv11 truth_count=70274 | /api/status 200 |
| 联邦记忆池 | ✅ 激活 索引536条 | gateway --stats |

## 四端核验

- [x] 本地：HASH-LEDGER.csv 44条 = 文件实算哈希
- [x] Git冷存储：三端master commit 5fc0850f 与本地一致
- [x] 云端：skills.huodouai.com 200 / 魔搭页 200
- [x] 飞书Base：登记数据JSON留档（权限开通后一键写入）

Ω₀⊂⊙∞⊂Ω｜国风IP技能家族 v1.0.0 全域锁档 · ZONGYUAN-ROOT · DID-BR-000002

# 全域锁档凭证 · 短剧生产流水线建成

> **锁档编号**：LOCK-GLOBAL-20260901-SHORTVIDEO-PIPELINE
> **锁档时间**：2026-09-01 00:10 UTC+8
> **版本跃迁**：V4.9 → V5.0（新增短剧生产流水线能力域）
> **DID**：DID-BR-000002
> **溯源符号**：Ω₀⊂⊙∞⊂Ω

---

## 一、新增能力：短剧生产流水线 Skill

| 项目 | 值 |
|------|-----|
| Skill名称 | shortvideo-production-pipeline |
| 版本 | v1.0.0 |
| 位置 | `.user_skills/shortvideo-production-pipeline/` |
| 核心脚本 | `scripts/pipeline.py`（六阶段编排） |
| 配置文件 | `config/pipeline_config.json` + `config/quota_strategy.json` |
| 模板 | `templates/prompt_templates.json` + `templates/storyboard_template.json` |

## 二、六阶段流水线

| 阶段 | 名称 | 调用通道 | 状态 |
|------|------|----------|------|
| S1 | 剧本生成 | 豆包文本API（免费额度） | ✅ 已验证 |
| S2 | 关键帧生成 | APP内置image_gen（免费） | ✅ 任务清单就绪 |
| S3 | 视频生成 | APP内置video_gen（免费） | ✅ 任务清单就绪 |
| S4 | 后期合成 | ffmpeg拼接+字幕+音频 | ✅ 拼接清单就绪 |
| S5 | 生产管理 | 飞书Base台账 | ✅ 已搭建 |
| S6 | 归档锁档 | 全域锁档+四端同步 | ✅ 已激活 |

## 三、免费额度优先策略

```
P0: 豆包APP内置工具(image_gen/video_gen/text) — 完全免费
P1: 火山方舟doubao-seed-2-0-lite — 免费额度
P2: 智普glm-4-flash — 免费额度
P3: 付费API — 仅前三级不可用时降级
```

## 四、飞书Base生产台账

| 项目 | 值 |
|------|-----|
| Base名称 | 短剧生产管理台账 |
| base_token | W803bCuSLazu6ZsctjYcv50Ingc |
| 访问链接 | https://my.feishu.cn/base/W803bCuSLazu6ZsctjYcv50Ingc |
| 项目表 | tbl2aASbRTLajFrt |
| 分镜表 | tblTvi8jNrZMt8dq |
| 资产表 | tblZ6gGyyMy26zte |
| 进度表 | tblVr2PQAhz4qbef |

## 五、测试项目验证

| 项目 | 值 |
|------|-----|
| 项目ID | SV-20260901-001 |
| 名称 | 昆仑洞天·太阴月神觉醒 |
| 集数/分镜 | 1集 / 3镜 |
| 剧本生成 | ✅ 豆包API调用成功，旁白金句到位 |
| 关键帧任务 | ✅ 3个任务清单，L0-MORPH-001约束自动注入 |
| 分镜台账 | ✅ 3条记录已写入Base |

## 六、全域快照

| 项目 | 值 |
|------|-----|
| 快照ID | SNAP-GLOBAL-20260901-SHORTVIDEO-PIPELINE |
| 全量资产 | 449文件 |
| Merkle根 | `cce73bbe0a2b38de2ac5cb8029b3cfd049416f6a4d90cd9f04f14dc281844bf1` |
| 自治内核协议 | V5.0-SHORTVIDEO-PIPELINE |
| 协议self_sha256 | `5ef796e778210a2753854ee941357cc889b0ddd56a3bc49ba24bae0577984977` |
| Base快照记录 | recvtTjKiHitNR |
| eFuse状态 | blown · 不可回退 |

## 七、使用方式

```bash
# 全流程生产一部短剧
python3 .user_skills/shortvideo-production-pipeline/scripts/pipeline.py \
  --mode full --project "项目名" --topic "主题" --episodes 1 --scenes-per-ep 6

# 仅生成剧本
python3 .../pipeline.py --mode script --project "项目名" --topic "主题"

# 生成关键帧任务清单（用APP image_gen批量生成）
python3 .../pipeline.py --mode keyframe --project "项目名"

# 归档锁档
python3 .../pipeline.py --mode archive --project "项目名"
```

---

Ω₀⊂⊙∞⊂Ω｜短剧生产流水线建成 · V5.0全域锁档完成 · ZONGYUAN-ROOT · DID-BR-000002 · Ω-TAN-7-001

# 昆仑洞天根目录图片资产质检汇总报告

- 生成时间: 2026-09-29
- 根目录: `/home/user/Doubao/chats/1128121028098`
- 计算方式: 真实 PIL.Image.open + verify + numpy 灰度/std/唯一色数/Laplacian方差 + SHA256

## 一、总量与分布

| 指标 | 数量 |
|---|---|
| 扫描图片总数 | 198 |
| PASS | 188 |
| FAIL | 10 |
| 模糊WARN(30≤lapvar<60) | 0 |

### 分类分布

| class | 数量 | 说明 |
|---|---|---|
| KEEP | 97 | 高质量作品关键帧 |
| EXCLUDE | 64 | 元法则卡/截图/部署资产 |
| EXCLUDE_ROSE | 16 | 玫瑰作品(独立画廊) |
| dup | 21 | 与_ms_push组内sha256重复 |

### 子目录分布
- `_shots`: 8 张
- `cte-engine`: 2 张
- `history/01-jiutian_xuannv_20260929`: 21 张
- `history/02-kunlun_dongtian`: 35 张
- `history/03-archive_ep01_03_xuannv`: 12 张
- `history/04-archive_zhulong_duizhi`: 11 张
- `history/05-archive_kunlun_assets_shennv`: 27 张
- `history/06-archive_meta_rule_cards`: 11 张
- `history/07-xuannv_works`: 9 张
- `history/09-shots`: 8 张
- `hub-portal`: 4 张
- `huodouai-deploy`: 8 张
- `kunlun-gallery-rose`: 12 张
- `kunlun-portfolio`: 2 张
- `oriental-rose-brightred-01.png`: 1 张
- `oriental-rose-brightred-02.png`: 1 张
- `oriental-rose-brightred-03.png`: 1 张
- `oriental-rose-brightred-04.png`: 1 张
- `origin-axiom-dashboard`: 2 张
- `truth-engine`: 2 张
- `unitree-analysis`: 5 张
- `xn_webp`: 5 张
- `yuanjihengyi-deploy`: 9 张
- `zongyuan-bridge-mvp`: 1 张

## 二、高质量关键帧清单

- 数量: 97 张 (class=KEEP 且 verdict=PASS)
- 竖屏9:16 (aspect 0.50~0.62): 84 张, 占比 **86.6%**
- 清单文件: `qc_high_quality_root_20260929.json`

## 三、去重结果

- _ms_push 基准集: 21 张 (jiutian_xuannv-20260929)
- 命中 dup: 21 张 (主要为 01-jiutian_xuannv_20260929 与 ms_push/03_太古元凰型 等同名同哈希文件)

## 四、ZIP 归档完整性

- 总 zip 数: 47 (磁盘实际, 用户预期61)
- OK: 47
- 损坏: 0

全部 zip 完整性校验通过 (testzip 无异常)。

## 五、可疑文件清单 (verdict=FAIL)

共 10 张:
- `_kf_lake/kunlun-history-20260929/09-shots/下一步优化推演_mobile.jpg` — 短边<480px(390)
- `_kf_lake/kunlun-history-20260929/09-shots/全域资产体系可视化_V2_mobile.jpg` — 短边<480px(469)
- `_kf_lake/kunlun-history-20260929/09-shots/成果汇报_IMA资产目录化_mobile.jpg` — 短边<480px(415)
- `_kf_lake/kunlun-history-20260929/09-shots/昆仑洞天短剧流水线架构_mobile.jpg` — 短边<480px(390)
- `kunlun-portfolio/_shots/index_mobile.jpg` — 短边<480px(390)
- `_shots/下一步优化推演_mobile.jpg` — 短边<480px(390)
- `_shots/全域资产体系可视化_V2_mobile.jpg` — 短边<480px(469)
- `_shots/成果汇报_IMA资产目录化_mobile.jpg` — 短边<480px(415)
- `_shots/昆仑洞天短剧流水线架构_mobile.jpg` — 短边<480px(390)
- `zongyuan-bridge-mvp/data/storage_test/images/2026-09-13/test_image.png` — 快速读取失败:cannot identify image file '/home/user/Doubao/chats/1128121028098/zongyuan-bridge-mvp/data/storage_test/images/2026-09-13/test_image.png'

## 六、交付物清单

1. `qc_report_root_20260929.json` — 每张图一条完整质检记录
2. `qc_high_quality_root_20260929.json` — KEEP+PASS 高质量关键帧清单
3. `zip_integrity_report_20260929.json` — zip 完整性与媒体清单
4. `qc_summary_root_20260929.md` — 本汇总报告

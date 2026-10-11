# _archive 全量质检报告 (2026-09-29)

根目录: `/home/user/Doubao/chats/1128121028098`

## 图片统计

- 图片总数: **129**
- KEEP 类: 71（其中 PASS=71, 非PASS=0）
- EXCLUDE 类: 58
- 判定分布: PASS=113, WARN=0, FAIL=16

## 视频统计

- 视频总数: **9**，PASS=8，FAIL=1
- canonical 视频数: 4

### Canonical 视频清单

| rel | codec | 分辨率 | 时长(s) | fps | 大小 | target_sub |
|---|---|---|---|---|---|---|
| _archive/videos_20260913/video1_赤色战甲神女.mp4 | hevc | 720x1280 | 15.073 | 24.0 | 5918995 | archive-videos-20260913/videos |
| _archive/videos_20260913/video2_九天玄女烛龙.mp4 | hevc | 720x1280 | 15.073 | 24.0 | 5179689 | archive-videos-20260913/videos |
| jiutian_xuannv_videos_20260929/videos/九天玄女神像苏醒式史诗视频_20260912.mp4 | hevc | 720x1280 | 15.073 | 24.0 | 3904821 | jiutian_xuannv-20260929/videos |
| zongyuan-bridge-mvp/data/storage_test/videos/2026-09-13/test_video.mp4 |  | 0x0 | 0.0 | 0.0 | 1912 |  |

### 失败/可疑文件

**图片 FAIL:**
- `_archive/media_archive_20260913/_flat_assets/IMG_02_index_mobile.jpg` [EXCLUDE] — 超低分辨率(短边405px<480)
- `_archive/media_archive_20260913/_flat_assets/IMG_03_index_mobile_p1of3.jpg` [EXCLUDE] — 超低分辨率(短边405px<480)
- `_archive/media_archive_20260913/_flat_assets/IMG_04_index_mobile_p2of3.jpg` [EXCLUDE] — 超低分辨率(短边405px<480)
- `_archive/media_archive_20260913/_flat_assets/IMG_05_index_mobile_p3of3.jpg` [EXCLUDE] — 超低分辨率(短边405px<480)
- `_archive/media_archive_20260913/_flat_assets/IMG_07_下一步优化推演_mobile.jpg` [EXCLUDE] — 超低分辨率(短边390px<480)
- `_archive/media_archive_20260913/_flat_assets/IMG_09_全域资产体系可视化_V2_mobile.jpg` [EXCLUDE] — 超低分辨率(短边469px<480)
- `_archive/media_archive_20260913/_flat_assets/IMG_11_成果汇报_IMA资产目录化_mobile.jpg` [EXCLUDE] — 超低分辨率(短边415px<480)
- `_archive/media_archive_20260913/_flat_assets/IMG_13_昆仑洞天短剧流水线架构_mobile.jpg` [EXCLUDE] — 超低分辨率(短边390px<480)
- `_archive/media_archive_20260913/images/index_mobile.jpg` [EXCLUDE] — 超低分辨率(短边405px<480)
- `_archive/media_archive_20260913/images/index_mobile_p1of3.jpg` [EXCLUDE] — 超低分辨率(短边405px<480)
- `_archive/media_archive_20260913/images/index_mobile_p2of3.jpg` [EXCLUDE] — 超低分辨率(短边405px<480)
- `_archive/media_archive_20260913/images/index_mobile_p3of3.jpg` [EXCLUDE] — 超低分辨率(短边405px<480)
- `_archive/media_archive_20260913/images/下一步优化推演_mobile.jpg` [EXCLUDE] — 超低分辨率(短边390px<480)
- `_archive/media_archive_20260913/images/全域资产体系可视化_V2_mobile.jpg` [EXCLUDE] — 超低分辨率(短边469px<480)
- `_archive/media_archive_20260913/images/成果汇报_IMA资产目录化_mobile.jpg` [EXCLUDE] — 超低分辨率(短边415px<480)
- `_archive/media_archive_20260913/images/昆仑洞天短剧流水线架构_mobile.jpg` [EXCLUDE] — 超低分辨率(短边390px<480)

**图片 WARN (轻度模糊，可保留):**
- （无）

**视频 FAIL:**
- `zongyuan-bridge-mvp/data/storage_test/videos/2026-09-13/test_video.mp4` — ffprobe失败:[mov,mp4,m4a,3gp,3g2,mj2 @ 0x561e0e9b4200] moov atom not found
/home/user/Doubao/chats/1128121028098/zongyuan-bridge-mvp/data/storage_test/videos/2026-09-13/test_video.mp4: Invalid data found when pro

### 视频去重组

- sha256 `84f9a3195c4c8bba…` ×4 → canonical: `jiutian_xuannv_videos_20260929/videos/九天玄女神像苏醒式史诗视频_20260912.mp4`
  - dup_of: `_archive/media_archive_20260913/_flat_assets/VID_01_九天玄女神像苏醒式史诗视频_20260912.mp4`
  - dup_of: `_archive/media_archive_20260913/videos/九天玄女神像苏醒式史诗视频_20260912.mp4`
  - dup_of: `九天玄女神像苏醒式史诗视频_20260912.mp4`
- sha256 `4a1051f0241e73e5…` ×2 → canonical: `_archive/videos_20260913/video1_赤色战甲神女.mp4`
  - dup_of: `_archive/videos_lock_20260913/video1_赤色战甲神女.mp4`
- sha256 `83f935d5c9f797cc…` ×2 → canonical: `_archive/videos_20260913/video2_九天玄女烛龙.mp4`
  - dup_of: `_archive/videos_lock_20260913/video2_九天玄女烛龙.mp4`

## 交付文件

- `/home/user/Doubao/chats/1128121028098/kunlun-create-link/pipeline_reports/qc_report_archive_20260929.json`
- `/home/user/Doubao/chats/1128121028098/kunlun-create-link/pipeline_reports/qc_high_quality_archive_20260929.json`
- `/home/user/Doubao/chats/1128121028098/kunlun-create-link/pipeline_reports/video_qc_20260929.json`
- `/home/user/Doubao/chats/1128121028098/kunlun-create-link/pipeline_reports/qc_summary_archive_20260929.md`
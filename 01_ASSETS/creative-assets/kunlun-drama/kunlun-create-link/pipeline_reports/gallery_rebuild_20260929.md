# 昆仑洞天·作品关键帧画廊 重建更新说明

- 重建日期：2026-09-29
- 触发：基于质检后的最终帧清单 `final_frames_manifest_20260929.json` 用模板重建单页 HTML
- 画廊产物：`/home/user/Doubao/chats/1128121028098/kunlun-create-link/昆仑洞天作品关键帧画廊.html`（已覆盖旧版）

## 一、总量对比

| 指标 | 旧版画廊 | 新版画廊 |
|---|---|---|
| 关键帧数量 | 116 | **113** |
| 主题/分类数 | — | 8 |
| 画幅 | 混排 | 全部 9:16 竖屏（aspect≈0.5618） |

## 二、URL 可达性验证（硬要求）

对清单内 **113 个魔搭公网 URL** 逐个请求（urllib，跟随重定向，超时 15s，UA 伪装浏览器），判定标准：最终 HTTP 200 且 `Content-Type` 以 `image/` 开头。

| 项 | 数量 |
|---|---|
| 验证总数 | 113 |
| 通过（HTTP 200 + image/*） | **113** |
| 失败（剔除） | **0** |

- 通过明细：`image/jpeg` 108 张、`image/webp` 5 张（即 `xn_webp` 目录 5 帧）。
- 失败帧文件名列表：**无**（本轮 113/113 全部可达，无坏链）。
- 完整逐条记录见 `gallery_url_verify_20260929.json`（每帧含 url / final_status / content_type / final_url）。

## 三、116 → 113 差异说明

本轮最终帧清单为质检（PIL verify + 灰度/std/ Laplacian 清晰度 + SHA256 去重）后的产物，相对旧版 116 帧：

- **剔除 3 帧**：质检阶段剔除，原因为非 9:16 竖屏（横版/超宽幅）、坏名/低分辨率 EXCLUDE、以及与 `_ms_push` 组内 SHA256 重复的重复帧。
- **URL 失败剔除**：0 帧（本轮全量可达）。
- **新增来源**：
  - `archive_kunlun-20260913` 下 `keyframe_kf003_010_20260913` / `keyframe_lock_20260913` → 主题「玄女×烛龙·幽墟裂隙」**8 帧**；
  - `xn_webp/` → 主题「九天玄女·战斗帧」**5 帧**（webp）。

## 四、主题分布（新版 113 帧）

| 主题 | 帧数 |
|---|---|
| 昆仑洞天·太阴/角色（02-kunlun_dongtian） | 35 |
| 神女·创世（05-archive_kunlun_assets_shennv） | 23 |
| 九天玄女·三型（jiutian_xuannv-20260929） | 21 |
| 九天玄女（07-xuannv_works） | 9 |
| 九天玄女·横版（03-archive_ep01_03_xuannv） | 8 |
| 玄女×烛龙·幽墟裂隙（archive_kunlun-20260913） | 8 |
| 九天玄女·战斗帧（xn_webp） | 5 |
| 玄女×烛龙（04-archive_zhulong_duizhi） | 4 |
| **合计** | **113** |

## 五、模板机制与保留功能

- 由脚本 `_build_gallery.py` 注入 `var FRAMES = [...]`（每帧 `{name, path: rel, url, theme}`），替换模板占位符 `__FRAMES_JSON__`。
- 清单自带 `theme` 字段，注入后直接使用；`themeOf(path)` 仅作兜底，并已扩展 THEME 映射表覆盖全部 8 类前缀（含 `xn_webp`、`archive_kunlun-20260913` / `keyframe_kf003_010_20260913` / `keyframe_lock_20260913`）。
- 保留：统计卡片（总数/主题数）、分类下拉、lightbox 大图、懒加载 `loading='lazy'`、加载失败 `onerror` 隐藏。
- 响应式：手机两列（<600px）/ 平板三列（≥600px）/ 桌面四列（≥900px），卡片 `aspect-ratio:9/16`。
- 页头/页脚确权标识保留：`确权 DID-BR-000002 · 锚定 Ω₀⊂⊙∞⊂Ω`，标题「昆仑洞天 · 作品关键帧画廊」。

## 六、自检结果

- (a) 生成 HTML 中 FRAMES 数量 = 113 = 验证通过帧数 ✅
- (b) 无 `__FRAMES_JSON__` 残留 ✅
- (c) FRAMES 内每个 url 均在通过列表中（无越界/坏链）✅
- (d) 页面含 `DID-BR-000002` 与 `Ω₀⊂⊙∞⊂Ω` 确权标识 ✅

## 七、视觉渲染结论

无头 Chromium 渲染（`--virtual-time-budget=15000` 等待远端图片加载）：

- 移动端 430px 宽：两列 9:16 卡片正常，缩略图全部加载，无空白卡片，统计卡片显示 113 / 8。
- 桌面端 1280px 宽：四列 9:16 卡片正常，图片正常加载，无空白卡片。
- 截图产物：
  - `gallery_screenshot_20260929.png`（移动端两列，主截图）
  - `gallery_screenshot_desktop_20260929.png`（桌面四列）
  - `gallery_screenshot_mobile_20260929.png`（同主截图副本）

## 八、产物清单

| 文件 | 说明 |
|---|---|
| `昆仑洞天作品关键帧画廊.html` | 更新后画廊（覆盖旧版，113 帧） |
| `pipeline_reports/gallery_url_verify_20260929.json` | 全量 URL 验证结果（113 通过 / 0 失败） |
| `pipeline_reports/gallery_rebuild_20260929.md` | 本更新说明 |
| `pipeline_reports/gallery_screenshot_20260929.png` | 移动端渲染截图 |
| `pipeline_reports/gallery_screenshot_desktop_20260929.png` | 桌面端渲染截图 |

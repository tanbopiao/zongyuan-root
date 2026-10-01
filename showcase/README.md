---
license: apache-2.0
task_categories:
- text-to-video
- text-to-image
tags:
- zongyuan-root
- 昆仑洞天
- 东方神话
- AI生成
- 关键帧
- 短视频
language:
- zh
---

# ZONGYUAN-ROOT · 昆仑洞天媒体湖

> 确权：DID-BR-000002 ｜ 溯源：Ω₀⊂⊙∞⊂Ω
> 纯东方神话视觉资产库 · AI 生成内容，含合成标识

本数据集收录昆仑洞天 IP 体系的**东方神话视觉资产**：系列关键帧、五态短视频、剧集片段与角色体系图。

## 内容分类

| 系列 | 内容 | 目录 |
|---|---|---|
| 昆仑女帝 | 心誓截天/终章/太素神女/万灵同悲 关键帧 | `showcase/kf-complete/kunlun-empress-three-act` |
| 昆仑月神 | kf/master/meta/v1/zeroref 全系 | `showcase/session-pictures2` |
| 玄鸟EP | 玄鸟图腾系列 | `showcase/keyframes/xuanniao-ep` |
| 五态短视频 | 静息/觉醒/过渡/调停/归寂（各10s） | `showcase/videos/five-states` |
| 太阴短片 | 太阴月神短剧 | `showcase/videos/media-videos` |
| 赤女chiwa | 赤女系列片段 | `showcase/videos/media-videos` |
| 九天玄女/黄湾/绯灵汐 | 角色体系 | `showcase/core-pictures/core-media-images` |
| 核心媒体库 | 9大系列图+系列视频 | `assets/media` |

## 视频精选

五态短视频（10s）：
- 静息态 · 觉醒态 · 过渡态 · 调停高潮态 · 归寂态

太阴月神短剧与赤女系列片段见 `showcase/videos/media-videos/`。

## 关键帧精选

- 昆仑女帝三幕：`kf-complete/kunlun-empress-three-act`（13帧）
- 昆仑月神全系：`session-pictures2`（45帧）
- 静息/觉醒/过渡/调停/归寂五态：`session-pictures`（5帧）
- 九天玄女/黄湾/绯灵汐/seedream：`session-pictures`（9帧）

## 下载方式

```bash
# Git
git lfs install
git clone https://modelscope.cn/datasets/zongyuanroot/ZONGYUAN-ROOT-MEDIA.git

# SDK
from modelscope.hub.api import HubApi
api = HubApi()
api.dataset_download('zongyuanroot/ZONGYUAN-ROOT-MEDIA')
```

## 统一展示窗

本数据集是 ZONGYUAN-ROOT 体系的**唯一对外统一展示窗**。全部对外展示资产（媒体/脱敏文档/成果）集中于此扩展，不分散于其他渠道。

| 渠道 | 角色 |
|---|---|
| 本数据集（魔搭） | ✅ 唯一对外展示窗 |
| 飞书云盘/知识库/表格 | 存储归档层（仅内部） |
| GitHub/Gitee | 冷存储版本母体 |
| 云端记忆网关 | 真值确权层 |
| 本地归档母体 | 唯一权威源 |

后续新资产按 媒体 / 文档 / 成果 三类归集扩展，并更新本分类索引。

---
Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ 昆仑洞天 · 东方神话视觉资产库

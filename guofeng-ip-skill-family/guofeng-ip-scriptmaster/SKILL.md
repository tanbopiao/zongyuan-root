---
name: guofeng-ip-scriptmaster
version: 1.0.0
description: "国风IP短剧剧本/分镜生成专家：输入主题→东方审美叙事编剧→结构化分镜JSON(含画面/旁白/时长/镜头/BGM情绪)→可直传飞书文档。当用户说'写剧本'、'分镜脚本'、'短剧编剧'、'国风剧情'、'旁白台词'时使用。零成本优先，豆包APP/免费API通道优先，严格遵循东方审美元法则。"
metadata:
  requires:
    bins: ["python3", "jq"]
  pypi: ["requests"]
  optional_bins: ["lark-cli"]
did: "DID-BR-000002"
trace_symbol: "Ω₀⊂⊙∞⊂Ω"
---

# 国风IP剧本大师 v1.0

> 华夏正统叙事 · 东方审美铁律 · 零成本生成 · 结构化分镜

## 核心设计原则

1. **东方纯粹叙事**：以华夏上古原生神话为根基（绝地天通/女娲/太阴月神/九天玄女等），严守"去外源化"——禁用西方奇幻叙事框架、西方神祇称谓、异质文化符号。
2. **结构化输出**：所有产物为合法JSON分镜脚本，字段完备（scene_id/shot/visual/narration/duration/camera/rhythm_beat/bgm_emotion/sound_effect），可直接进入关键帧/视频/音频阶段。
3. **零成本优先**：文本通道优先级 = 豆包APP会话内置 > 火山方舟免费额度 > 智普glm-4-flash免费 > 付费API（仅兜底，置末尾备注）。
4. **视觉可执行**：画面描述(visual)按"角色动作/场景/光影/服饰"四要素成句，保证下游关键帧提示词可直接引用，杜绝抽象修辞。
5. **旁白金句化**：narration为可配音的史诗感旁白（沉稳女声/气口停顿标记），支持音画节奏对齐。

## 快速路由

| 目标 | 命令 |
|------|------|
| 生成整剧分镜脚本 | `python3 scripts/storyboard_gen.py --topic <主题> --episodes N --scenes-per-ep M` |
| 仅生成分镜JSON文件 | `python3 scripts/storyboard_gen.py --topic <主题> --output ./storyboard.json` |
| 输出到飞书文档 | `python3 scripts/storyboard_gen.py --topic <主题> --feishu-doc "<文档标题>"` |
| 校验既有分镜JSON | `python3 scripts/storyboard_gen.py --validate ./storyboard.json` |
| 生成旁白台词表 | `python3 scripts/storyboard_gen.py --narration ./storyboard.json` |

## 配置模板

`config/scriptmaster_config.json`：

```json
{
  "provider": {
    "text_channel_priority": [
      {"channel": "app_builtin", "priority": 0, "cost": "free", "note": "豆包APP会话内置文本能力"},
      {"channel": "doubao_lite_api", "priority": 1, "cost": "free_tier", "model": "doubao-seed-2-0-lite-260215", "api_key_env": "DOUBAO_API_KEY"},
      {"channel": "zhipu_flash_api", "priority": 2, "cost": "free_tier", "model": "glm-4-flash", "api_key_env": "ZHIPU_API_KEY"},
      {"channel": "paid_api", "priority": 9, "cost": "paid", "note": "仅前三级不可用时兜底，需人工审批"}
    ]
  },
  "generation": {
    "default_episodes": 1,
    "default_scenes_per_episode": 6,
    "default_scene_duration_sec": 10,
    "ratio": "9:16",
    "language": "zh-CN",
    "quality_target": 4.5
  },
  "aesthetics": {
    "narrative_roots": ["绝地天通", "女娲补天", "太阴月神", "九天玄女", "昆仑洞天", "石猴余脉"],
    "banned": ["西方神祇称谓", "西方奇幻框架", "异质文化符号", "雄性化角色叙事"],
    "trace_symbol": "Ω₀⊂⊙∞⊂Ω"
  },
  "feishu": {
    "enabled": false,
    "doc_title_prefix": "【国风分镜】",
    "base_token_env": "FEISHU_BASE_TOKEN"
  }
}
```

## 提示词模板

`templates/prompts.json`：

```json
{
  "script": "你是专业国风短剧编剧，深耕华夏上古神话。请围绕主题'{topic}'创作{episodes}集短剧，每集{scenes}个分镜。每个分镜包含：scene_id(格式S01E01)、shot(镜号)、visual(画面描述，四要素：角色动作/场景/光影/服饰，可直接转绘画提示词)、narration(史诗感旁白金句，沉稳女声可配音，可含（0.3s停顿）类气口标记)、duration(时长秒)、camera(镜头运动)、rhythm_beat(节奏节拍)、bgm_emotion(配乐情绪)、sound_effect(音效)。叙事根基：华夏上古原生神话（绝地天通/昆仑洞天/石猴余脉），严守东方纯粹，禁用西方神祇与异质符号。严格输出JSON，不要输出任何其他内容。JSON结构：{\"episodes\":[{\"episode\":1,\"title\":\"集标题\",\"scenes\":[{\"scene_id\":\"S01E01\",\"shot\":\"1\",\"visual\":\"...\",\"narration\":\"...\",\"duration\":10,\"camera\":\"slow_push_in\",\"rhythm_beat\":\"strong_entry\",\"bgm_emotion\":\"epic\",\"sound_effect\":\"\"}]}]}",
  "narration_voice": "沉稳女声，语速适中，情感饱满，带有史诗感和神秘感。旁白内容：{narration}",
  "title_card": "短剧标题卡：{title}。黑金配色，天书符文装饰，玄鸟图腾，9:16竖屏，高端商业质感。"
}
```

## 分镜JSON Schema（输出契约）

```json
{
  "project": "<项目名>",
  "topic": "<主题>",
  "episodes": [
    {
      "episode": 1,
      "title": "<集标题>",
      "scenes": [
        {
          "scene_id": "S01E01",
          "shot": "1",
          "visual": "<画面描述：角色动作/场景/光影/服饰>",
          "narration": "<旁白金句，可含停顿标记>",
          "duration": 10,
          "camera": "slow_push_in",
          "rhythm_beat": "strong_entry",
          "bgm_emotion": "epic",
          "sound_effect": "",
          "keyframe": "",
          "video": "",
          "audio": "",
          "merged_video": "",
          "status": "pending"
        }
      ]
    }
  ],
  "metadata": {
    "created_at": "<ISO-8601>",
    "l0_laws": ["L0-MORPH-001", "L0-DOMAIN-001"],
    "quality_target": 4.5,
    "ratio": "9:16",
    "did": "DID-BR-000002",
    "trace": "Ω₀⊂⊙∞⊂Ω"
  }
}
```

## 东方审美叙事铁律（不可违反）

1. 角色范式：纯东方神女/女帝/少年武侠/山海经萌宠，绝对去雄性化（神女类），纯乌黑长发，九头/8.5头身超模体态。
2. 场景范式：水墨画/OC渲染/胶片质感，华夏正统汉服/素青武侠长衫，冷蓝青黑/勃艮第红/黑金配色。
3. 禁止项：西方铠甲、畸形肢体、多手多颅、冗余光影特效、白发、性别混杂、外源化内容。
4. 溯源：每集分镜 metadata 带 DID-BR-000002 + Ω₀⊂⊙∞⊂Ω。

## 输入/输出规范

- **输入**：`--topic` 主题（必填）；`--episodes` 集数（默认1）；`--scenes-per-ep` 每集分镜数（默认6）。
- **输出**：合法JSON分镜文件（UTF-8）；`--narration` 模式输出旁白台词表（分镜ID→台词→停顿标记）。
- **错误处理**：JSON解析失败→重试并检查模型输出；通道限额→按 priority 自动降级；所有失败在输出中显式标注，禁止虚构补全。

## 依赖清单（独立安装）

- 必选：Python 3.8+，`pip install requests`；命令行 `jq`。
- 可选：`lark-cli`（飞书文档直传）。
- 无任何内部路径硬编码；全部配置通过 `config/scriptmaster_config.json` 与环境变量注入（`DOUBAO_API_KEY`/`ZHIPU_API_KEY`/`FEISHU_BASE_TOKEN`）。

## 确权与溯源

- 产物默认携带 `did: DID-BR-000002` 与 `trace: Ω₀⊂⊙∞⊂Ω` 元数据。
- 生产完成建议执行 SHA256 哈希登记入账本（配合 guofeng-ip-lock-archiver 包使用）。

Ω₀⊂⊙∞⊂Ω｜国风IP剧本大师 v1.0 · ZONGYUAN-ROOT · DID-BR-000002

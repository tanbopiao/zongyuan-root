---
name: guofeng-ip-keyframe-artist
version: 1.0.0
description: "国风IP关键帧画师：分镜JSON→东方审美绘图提示词→L0-MORPH-001形态校验→角色一致性/防漂移检测→五维质量评分(≥4.5)→关键帧图片资产。当用户说'画关键帧'、'关键帧生成'、'分镜出图'、'角色一致性'、'防漂移'、'关键帧校验'时使用。零成本优先（豆包APP内置image_gen免费额度），严格遵循东方审美元法则与人体结构绝对禁止法则。"
metadata:
  requires:
    bins: ["python3"]
  pypi: []
  optional_bins: ["jq"]
did: "DID-BR-000002"
trace_symbol: "Ω₀⊂⊙∞⊂Ω"
---

# 国风IP关键帧画师 v1.0

> 分镜visual四要素 → 可执行绘图提示词 · L0形态校验 · 角色零漂移 · 五维质量门

## 核心设计原则

1. **东方审美铁律不可省略**：所有提示词强制注入纯东方神女/女帝/少年武侠/山海经萌宠范式，纯乌黑长发，九头/8.5头身，华夏正统汉服，冷蓝青黑/勃艮第红/黑金配色，9:16竖屏，UE5.7光追，Portra400胶片质感。
2. **L0-MORPH-001形态校验前置**：生成前提示词内嵌负面约束（畸形/多肢/西方铠甲/白发/性别混杂），生成后复检人体结构合规，违规即拒并重生成。
3. **角色一致性锚定**：同一角色跨分镜携带面部/发型/服饰/配色/光影五维锚点，漂移相似度<0.88即触发重生成，杜绝形象跳变。
4. **五维质量门(≥4.5)**：L0合规30% + 东方审美25% + 画面细节20% + 配色和谐15% + 溯源标识10%，总分不达标即重生成。
5. **零成本通道优先**：豆包APP内置image_gen(免费会话额度) > 火山方舟seedream免费额度 > 付费API(最高优先级号+需人工审批标注)。
6. **人像分级**：人像/写真类关键帧仅本地归档锁档，不推公开湖、不对外展示。

## 快速路由

| 目标 | 命令 |
|------|------|
| 分镜JSON→关键帧提示词清单 | `python3 scripts/build_keyframe_prompt.py --storyboard ./storyboard.json --output ./keyframe_tasks.json` |
| 校验任务清单完整性 | `python3 scripts/build_keyframe_prompt.py --validate ./keyframe_tasks.json` |
| 输出质量评分汇总 | `python3 scripts/build_keyframe_prompt.py --score ./keyframe_tasks.json` |
| 单镜头手动补提示词 | 调用 templates/prompts.json 的 keyframe_prompt_template 自行拼接 |
| 角色漂移检测 | 用 prompts.json 的 drift_check_prompt 对生成图做相似度比对 |

## 配置模板

`config/guofeng_ip_keyframe_artist_config.json`：

```json
{
  "provider": {
    "image_channel_priority": [
      {"channel": "doubao_app_image_gen", "priority": 0, "cost": "free", "model": "seedream_5.0_flash", "note": "豆包APP内置image_gen，完全免费"},
      {"channel": "volc_seedream_free", "priority": 1, "cost": "free_tier", "model": "seedream_4.5", "api_key_env": "VOLC_ACCESS_KEY", "note": "火山方舟免费额度"},
      {"channel": "paid_api", "priority": 9, "cost": "paid", "model": "seedream_5.0_pro", "api_key_env": "DOUBAO_API_KEY", "note": "付费兜底，需人工审批"}
    ]
  },
  "generation": {
    "default_ratio": "9:16",
    "default_width": 1152,
    "default_height": 2048,
    "quality_target": 4.5,
    "drift_threshold": 0.88,
    "l0_morph_check": true
  },
  "character_consistency": {
    "enabled": true,
    "anchor_fields": ["character_name","face_shape","hair_style","hair_color","body_proportion","costume_style","main_color","lighting_tone"],
    "drift_threshold": 0.88
  },
  "quality_scoring": {
    "dimensions": [
      {"name": "l0_morph_compliance", "weight": 0.30},
      {"name": "eastern_aesthetic", "weight": 0.25},
      {"name": "visual_detail", "weight": 0.20},
      {"name": "color_harmony", "weight": 0.15},
      {"name": "trace_symbol_visible", "weight": 0.10}
    ],
    "min_total_score": 4.5
  },
  "aesthetics": {
    "paradigms": ["纯东方神女","女帝","少年武侠","山海经萌宠"],
    "hair": "纯乌黑长发",
    "body": "九头/8.5头身超模体态",
    "costume": "华夏正统汉服/素青武侠长衫",
    "palette": ["冷蓝青黑","勃艮第红","黑金"],
    "render_style": ["水墨画","OC渲染","胶片质感"],
    "engine": "UE5.7光追",
    "film_stock": "Portra400胶片质感",
    "lighting": "强烈轮廓光/霞光",
    "background": "深空青黑背景",
    "motifs": ["玄鸟图腾","天书符文"],
    "banned": ["西方铠甲","畸形肢体","多手多颅","冗余光影特效","白发","性别混杂","雄性化元素","外源化内容"],
    "trace_position": "画面右下角隐秘镌刻",
    "portrait_policy": "人像/写真类仅本地归档，不对外展示"
  },
  "l0_morph_check": {
    "rule_id": "L0-MORPH-001",
    "check_items": ["肢体=2臂2腿","头部=1","每手5指","九头/8.5头身","无西方铠甲","纯乌黑长发","无性别混杂"],
    "on_violation": "reject_and_regenerate"
  }
}
```

## 提示词模板

`templates/prompts.json`（核心字段说明）：

- **keyframe_base**：分镜visual描述前置模板
- **l0_morph_suffix**：东方审美铁律后缀（不可省略，所有关键帧必须拼接）
- **keyframe_prompt_template**：完整提示词 = base + suffix
- **character_consistency_anchor**：角色一致性锚点注入模板（跨分镜保持形象）
- **drift_check_prompt**：漂移检测提示词，输出JSON相似度报告
- **quality_score_prompt**：五维质量评分提示词，输出JSON总分
- **refusal_negative**：负面提示词（西方铠甲/畸形/白发/外源化等）

完整东方审美铁律（写进 l0_morph_suffix，不可省略）：

> 纯东方神女/女帝/少年武侠范式，纯乌黑长发，九头/8.5头身超模体态，华夏正统汉服/素青武侠长衫，冷蓝青黑/勃艮第红/黑金配色，水墨画/OC渲染/Portra400胶片质感，9:16竖屏，UE5.7光追，强烈轮廓光/霞光，深空青黑背景，玄鸟图腾/天书符文装饰。严禁：西方铠甲、畸形肢体、多手多颅、冗余光影特效、白发、性别混杂、雄性化元素、外源化内容。画面右下角隐秘镌刻Ω₀⊂⊙∞⊂Ω。

## 输入/输出规范

**输入**：分镜JSON（由 guofeng-ip-scriptmaster 产出），关键字段：
- `episodes[].scenes[].scene_id`：分镜ID
- `episodes[].scenes[].visual`：画面描述（角色动作/场景/光影/服饰四要素）
- `episodes[].scenes[].character`（可选）：角色名，用于一致性锚点
- `episodes[].scenes[].face_shape/hair_style/costume_style/main_color/lighting_tone`（可选）：角色锚点补充字段

**输出**：关键帧任务清单JSON，每镜头一条：
```json
{
  "scene_id": "S01E01",
  "prompt": "完整绘图提示词（visual+L0后缀+角色锚点）",
  "output_path": "./keyframes/S01E01.png",
  "ratio": "9:16",
  "width": 1152,
  "height": 2048,
  "model": "seedream_5.0_flash",
  "l0_morph_check": true,
  "drift_threshold": 0.88,
  "quality_target": 4.5,
  "negative_prompt": "西方铠甲,armor,畸形,...",
  "status": "pending_generation"
}
```

**错误处理**：
- visual为空 → 标记 `skipped_empty_visual`，不生成空提示词
- L0校验失败 → reject_and_regenerate，最多重试3次
- 漂移<0.88 → 用更高优先级通道重生成
- 质量总分<4.5 → 重生成，记录失败原因
- 所有失败显式标注，禁止虚构补全

## 角色一致性锚点定义

同一角色在不同分镜中必须保持以下锚点不漂移：

| 锚点字段 | 说明 | 漂移阈值 |
|----------|------|----------|
| character_name | 角色名 | 必须一致 |
| face_shape | 脸型（鹅蛋脸/瓜子脸等） | 相似度≥0.88 |
| hair_style | 发型（乌黑长发及腰等） | 相似度≥0.88 |
| hair_color | 发色（必须纯乌黑） | 必须一致 |
| costume_style | 服饰款式（汉服/武侠长衫） | 相似度≥0.88 |
| main_color | 主色调（冷蓝青黑/勃艮第红/黑金） | 色距≤阈值 |
| lighting_tone | 光影基调（轮廓光/霞光） | 相似度≥0.88 |

## 五维质量评分维度

| 维度 | 权重 | 评分要点 |
|------|------|----------|
| L0形态合规 | 30% | 无畸形肢体/多手多颅/西方铠甲/白发 |
| 东方审美还原 | 25% | 神女/武侠范式纯正度，去外源化 |
| 画面细节 | 20% | 服饰纹理/光影层次/场景纵深 |
| 配色和谐 | 15% | 冷蓝青黑/勃艮第红/金黑体系统一 |
| 溯源标识可见 | 10% | 右下角Ω₀⊂⊙∞⊂Ω隐秘可辨 |

总分≥4.5通过；<4.5重生成。

## 依赖清单（独立安装）

- 必选：Python 3.8+（无第三方pip依赖，纯标准库）
- 可选：`jq`（JSON命令行处理）
- 无内部路径硬编码；全部配置通过 `config/guofeng_ip_keyframe_artist_config.json` 与环境变量注入（`DOUBAO_API_KEY`/`VOLC_ACCESS_KEY`）

## 确权与溯源

- 产物默认携带 `did: DID-BR-000002` 与 `trace: Ω₀⊂⊙∞⊂Ω` 元数据。
- 生成图片右下角必须隐秘镌刻 Ω₀⊂⊙∞⊂Ω。
- 生产完成建议 SHA256 哈希入账本（配合 guofeng-ip-lock-archiver 包使用）。
- 人像/写真类关键帧仅本地归档锁档，不推公开湖、不对外展示。

Ω₀⊂⊙∞⊂Ω｜国风IP关键帧画师 v1.0 · ZONGYUAN-ROOT · DID-BR-000002

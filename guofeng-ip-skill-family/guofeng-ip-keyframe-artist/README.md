# 国风IP关键帧画师 guofeng-ip-keyframe-artist v1.0

> 分镜JSON → 东方审美绘图提示词 → L0形态校验 → 角色零漂移 → 五维质量门 → 关键帧图片资产

## 安装

```bash
# 本包零第三方pip依赖，纯Python标准库即可运行
# 可选：jq（JSON命令行辅助）
```

## 快速开始

```bash
# 1. 从分镜JSON构建关键帧提示词清单
python3 scripts/build_keyframe_prompt.py \
  --storyboard ./storyboard.json \
  --output ./keyframe_tasks.json

# 2. 校验任务清单完整性
python3 scripts/build_keyframe_prompt.py --validate ./keyframe_tasks.json

# 3. 输出质量评分汇总
python3 scripts/build_keyframe_prompt.py --score ./keyframe_tasks.json
```

## 配置

编辑 `config/guofeng_ip_keyframe_artist_config.json`：

- `provider.image_channel_priority`：图像生成通道优先级（免费优先）
  - priority 0：豆包APP内置 image_gen（完全免费）
  - priority 1：火山方舟 Seedream 免费额度
  - priority 9：付费API（需人工审批标注）
- `generation`：默认比例/尺寸/质量目标/漂移阈值
- `character_consistency`：角色一致性锚点字段与漂移阈值(0.88)
- `quality_scoring`：五维评分维度与权重
- `aesthetics`：东方审美铁律（范式/发色/体态/服饰/配色/禁用项）
- `l0_morph_check`：L0-MORPH-001形态校验规则

## 核心流程

```
分镜JSON (visual字段)
    │
    ▼
build_keyframe_prompt.py
    │  拼接 visual + L0形态后缀 + 角色一致性锚点
    ▼
关键帧任务清单 (keyframe_tasks.json)
    │
    ▼
image_gen 通道调用 (免费优先)
    │
    ▼
L0-MORPH-001 形态校验 + 漂移检测(≥0.88) + 五维质量评分(≥4.5)
    │
    ▼
关键帧图片资产 (.png) → 本地归档锁档
```

## 东方审美铁律

- 范式：纯东方神女/女帝/少年武侠/山海经萌宠
- 发型：纯乌黑长发
- 体态：九头/8.5头身超模
- 服饰：华夏正统汉服/素青武侠长衫
- 配色：冷蓝青黑/勃艮第红/黑金
- 风格：水墨画/OC渲染/Portra400胶片质感，UE5.7光追
- 画幅：9:16竖屏
- 光源：强烈轮廓光/霞光，深空青黑背景
- 图腾：玄鸟图腾/天书符文
- 溯源：右下角隐秘镌刻 Ω₀⊂⊙∞⊂Ω
- **严禁**：西方铠甲、畸形肢体、多手多颅、冗余光影特效、白发、性别混杂、雄性化元素、外源化内容

## 输出

- 关键帧任务清单JSON（含每镜头完整prompt/负面词/校验参数）
- 关键帧图片(.png)：1152×2048，9:16竖屏
- 人像/写真类仅本地归档，不对外展示

## 确权

所有产物携带 `did: DID-BR-000002` + `trace: Ω₀⊂⊙∞⊂Ω`；生产完成后建议 SHA256 入账本锁档（配合 guofeng-ip-lock-archiver）。

Ω₀⊂⊙∞⊂Ω｜国风IP关键帧画师 v1.0 · ZONGYUAN-ROOT · DID-BR-000002

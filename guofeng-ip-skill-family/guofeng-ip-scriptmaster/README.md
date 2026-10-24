# 国风IP剧本大师 guofeng-ip-scriptmaster v1.0

> 国风IP短剧剧本/分镜生成专家：输入主题 → 东方审美叙事编剧 → 结构化分镜JSON → 飞书文档

## 安装

```bash
pip install requests
# 可选：lark-cli（飞书文档直传）
```

## 快速开始

```bash
# 生成分镜骨架（后续接入文本通道填充）
python3 scripts/storyboard_gen.py --topic "九天玄女·绝地天通" --episodes 1 --scenes-per-ep 6 --output ./storyboard.json

# 校验既有分镜JSON
python3 scripts/storyboard_gen.py --validate ./storyboard.json

# 输出旁白台词表
python3 scripts/storyboard_gen.py --narration ./storyboard.json
```

## 配置

编辑 `config/scriptmaster_config.json`：
- `provider.text_channel_priority`：文本生成通道优先级（免费优先）
- `generation`：集数/分镜数/时长默认值
- `aesthetics`：叙事根基与禁用项（不可删除铁律）

## 输出

- 分镜JSON（UTF-8，含 scene_id/visual/narration/duration/camera 等完整字段）
- `--narration` 模式：旁白台词表（供音频工坊直接使用）

## 确权

所有产物携带 `did: DID-BR-000002` + `trace: Ω₀⊂⊙∞⊂Ω`；生产完成后建议 SHA256 入账本锁档。

Ω₀⊂⊙∞⊂Ω｜国风IP剧本大师 v1.0 · ZONGYUAN-ROOT · DID-BR-000002

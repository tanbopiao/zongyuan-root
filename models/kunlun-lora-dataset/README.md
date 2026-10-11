# 昆仑洞天 LoRA 训练数据集

## 分桶说明
| 目录 | 张数 | 角色 | 建议 |
|---|---|---|---|
| 001_red_goddess | 24 | 红裙九尾狐/红裙神女 | ✅ 数据量够，可单独训LoRA |
| 002_xiwangmu | 4 | 西王母 | ❌ 太少，需补到15+ |
| 003_yaoji | 4 | 瑶姬 | ❌ 太少 |
| 004_jiutian_xuannv | 61 | 九天玄女/玄鸟 | ✅ 数据量最大，优先训 |
| 005_goddess_other | 4 | 碧霞元君/骊山老母/嫦娥 | ❌ 太少 |
| 006_change | 8 | 变化帧/alt | 训练辅助用 |

## 推荐训练顺序
1. 先训 `004_jiutian_xuannv`（61张，数据最足）
2. 再训 `001_red_goddess`（24张，红裙风格统一）
3. 其他角色补图到15张后再训

## 基础模型
- SD 1.5（4GB）或 SDXL（7GB）
- 推荐 SD 1.5 因为9:16竖屏训练更快

## 训练参数建议
- resolution: 512
- batch_size: 2
- learning_rate: 1e-4
- max_train_steps: 1500
- network_dim: 32

# guofeng-ip-production-ledger · 国风IP生产台账管家 v1.0

国风IP短剧生产全生命周期台账：四表（项目/分镜/资产/进度），CSV 本地落账零成本，飞书 Base 为可选增强。

- 确权：DID-BR-000002
- 溯源：Ω₀⊂⊙∞⊂Ω

## 安装

零依赖（仅 Python 3.8+ 标准库）：

```bash
# 直接把整个目录放进你的技能目录即可，无需 pip install
python3 scripts/ledger_cli.py --help
```

可选（飞书 Base 免费额度增强）：安装 `lark-cli`，并配置环境变量：

```bash
export FEISHU_BASE_TOKEN="{FEISHU_BASE_TOKEN}"
export FEISHU_TABLE_PROJECTS="{FEISHU_TABLE_PROJECTS}"
export FEISHU_TABLE_STORYBOARDS="{FEISHU_TABLE_STORYBOARDS}"
export FEISHU_TABLE_ASSETS="{FEISHU_TABLE_ASSETS}"
export FEISHU_TABLE_PROGRESS="{FEISHU_TABLE_PROGRESS}"
```

## 快速开始

```bash
# 1. 初始化台账（生成四表 CSV 表头）
python3 scripts/ledger_cli.py init --dir ./ledger

# 2. 新建项目
python3 scripts/ledger_cli.py record project \
  --id P001 --name "少年剑客" --topic "元明洞阳" --episodes 1 --owner tanbopiao

# 3. 登记分镜
python3 scripts/ledger_cli.py record storyboard \
  --id S01E01 --pid P001 --episode 1 --shot 1 \
  --visual "白衣剑客立于丹霞崖顶，冷青色调" --narration "（0.3s停顿）剑出洞阳"

# 4. 登记资产（自动实算 SHA256）
python3 scripts/ledger_cli.py record asset \
  --id A001 --type image --sid S01E01 \
  --file ./kf/S01E01.png --token S01E01.png --quality 4.6

# 5. 查看状态 / 更新进度
python3 scripts/ledger_cli.py status --project-id P001
python3 scripts/ledger_cli.py progress --project-id P001 --update --stage keyframed --completed 4 --total 6

# 6. 对账（台账 vs 磁盘实算哈希）
python3 scripts/ledger_cli.py reconcile --project-id P001 --asset-dir ./kf
```

## 四表字段

| 表 | 文件 | 关键字段 |
|----|------|----------|
| 项目表 | projects.csv | project_id, name, topic, episodes, status, owner, created_at, updated_at, did, trace |
| 分镜表 | storyboards.csv | storyboard_id, project_id, episode, shot_no, visual, narration, duration_sec, keyframe_url, video_url, status, updated_at, did, trace |
| 资产表 | assets.csv | asset_id, type(image/video/audio), storyboard_id, file_token, sha256, quality_score, lock_status, updated_at, did, trace |
| 进度表 | progress.csv | project_id, stage, completed, total, percentage, updated_at, did, trace |

## 状态流转

```
pending → scripted → keyframed → videoed → audioed → merged → locked
```

单向，禁止跳级。`status` 命令会输出当前状态与 allowed next。

## 对账铁律

- 资产 SHA256 优先 `--file` 实算；无文件必须显式 `--sha256`，否则拒绝入账。
- `reconcile` 发现差异**只标记不补全**，JSON 报告 `auto_fix=false`，差异项 exit code=10。
- 禁止虚构补全任何哈希或记录。

## 文件清单

```
guofeng-ip-production-ledger/
├── SKILL.md
├── README.md
├── config/guofeng-ip-production-ledger_config.json
├── templates/prompts.json
└── scripts/ledger_cli.py
```

Ω₀⊂⊙∞⊂Ω · DID-BR-000002

# 📦 归档标识 · 2026-10-08 数据湖价值挖掘

> 事件: DATALAKE-MAX-VALUE-UTILIZATION-20261008
> 节点: ZR-NODE-DC2E51C0 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
> 云端seq: 2947 / 2949 / 2950 / 2967

## 本批产出清单

### 训练语料（train/）
| 文件 | 条数 | 大小 | 说明 |
|---|---|---|---|
| 4d-corpus-v5.jsonl | 2932 | 1.7MB | **最新版**，合并SFT+真值库+公理实操+白皮书QA+SOP锚点QA |
| 4d-corpus-v2.jsonl | 28 | 13KB | 历史版（公理/SOP/工程实操QA） |
| README-4D-CORPUS.md | — | — | 语料说明文档 |

### 索引与指南
| 文件 | 说明 |
|---|---|
| INDEX.md | 数据湖全资产目录导航（P0/P1/P2分级） |
| LAUNCH.md | 新实例三步接入指南（clone→bootstrap→验证） |
| SOP-MANUAL-INDEX.md | 36个SOP + 核心锚点操作手册索引 |
| ASSET-INDEX.csv | 72039条完整资产目录（路径+哈希+大小+类型） |

### 算子（gpu-agent/intel-operators/）
| 文件 | 说明 |
|---|---|
| op_vista_frame_search.py | 视觉帧快照检索算子（META-RULE-017落地） |
| resource_bill.py | 算子级资源账单埋点（META-RULE-018落地） |
| frame_snapshot_autosave.py | 帧快照自动保存钩子（昆仑洞天流水线V1.7集成） |

### 元法则（meta-rules/）
| 文件 | 说明 |
|---|---|
| META-RULE-017-视觉帧快照记忆.md | 帧级快照记忆元规则 |
| META-RULE-018-算子级资源账单.md | 算子级Token账单元规则 |

### 情报与看板（intel-weekly/）
| 文件 | 说明 |
|---|---|
| ZONGYUAN-前沿情报周报-V1.0.{txt,html} | VISTA+WorkBuddy情报解读 |
| ZONGYUAN-体系增量完善提案-情报转化V1.0.{txt,html} | 对标分析+行动提案 |
| RESOURCE-BILLBOARD-001-资源消耗看板.html | ECharts三图+JSONL实时渲染 |

## 核心数据
- 训练语料增长: 20条 → 2932条（**146倍**）
- 资产索引: 72039条完整文件记录
- 新实例接入: 从小时级 → 分钟级（LAUNCH.md三步）
- 算子总数: 3个新算子 + 4个稳态元法则

## 后续待办
- [ ] resource-bill.jsonl 积累真实数据后导入看板（P1）
- [ ] 1094个.py脚本按功能分类（P3）
- [ ] 卷宗167MB历史快照git LFS瘦身

# ZONGYUAN-ROOT 魔搭仓库整合规范 V1.0

> 生效: 2026-10-08 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

## 一、仓库定位与边界

| 仓库 | 用途 | 可见性 | 存放内容 | 禁止存放 |
|---|---|---|---|---|
| **zongyuan-root-open-knowledge** | 对外公开知识库 | 公开 | 白皮书HTML+MD、落地页、情报周报、元法则注册、SOP文档 | 密钥/凭证/内部脚本/GPU运维细节 |
| **ZONGYUAN-SHARED-DATALAKE** | 内部共享数据湖 | 私有 | 训练语料、GPU算子、联通脚本、资产索引、卷宗快照、运行时数据 | 对外宣传页、营销内容 |

## 二、命名规范

- 仓库名: 小写连字符（公开库）/ 大写下划线（内部库），保持现状
- 文件名: 大写下划线（ZONGYUAN-xxx-V1.0.md）或小写连字符（op_vista_frame_search.py）
- 日期后缀: YYYYMMDD（如20261008），禁止用中文日期
- 版本号: V1.0/V1.1/V2.0，禁止用"最新/新版"

## 三、目录结构标准

### 公开库 zongyuan-root-open-knowledge
```
whitepaper/      白皮书（MD+HTML）
landing/         对外落地页
intel-weekly/    情报周报+体系提案
registries/      元法则注册表
docs/            技术文档
drama/           昆仑洞天IP资产（对外展示部分）
```

### 内部库 ZONGYUAN-SHARED-DATALAKE
```
train/           训练语料（jsonl + README）
gpu-agent/       GPU实例算子+联通脚本
  ├─ intel-operators/   新算子（帧检索/资源账单/帧快照）
  └─ operator-worker-trigger/  Worker部署算子
meta-rules/      元法则文档（META-RULE-017/018...）
zongyuan-root/   内核全量镜像
  ├─ meta_law/          核心公理
  ├─ meta-rules/sop/     SOP
  ├─ whitepaper(s)/      白皮书备份
  ├─ scripts/           工程脚本
  └─ 卷宗/              锁档快照（历史归档）
control/         命令槽（git-pipe-worker通信）
ASSET-INDEX.csv  全资产索引
INDEX.md         数据湖导航
LAUNCH.md        新实例接入指南
ARCHIVE-MARKER-*.md  归档标识
```

## 四、推送规范

1. 推送前必须更新对应README
2. 每个目录必须有README说明用途
3. 新增文件必须在INDEX.md中登记
4. 大文件（>10MB）走git LFS
5. 禁止推送密钥/token/凭证明文
6. commit message格式: `类型: 简述`（如`新增: META-RULE-017`）

## 五、边界规则

- 白皮书/宣传内容 → 只放公开库
- 训练语料/算子/运维脚本 → 只放内部库
- 两份都需要的 → 公开库存MD版，内部库存完整版+脚本
- 冲突时: 公开库优先（对外一致性），内部库补充技术细节

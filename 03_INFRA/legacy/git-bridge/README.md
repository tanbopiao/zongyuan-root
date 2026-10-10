# ZONGYUAN-ROOT 内核真值桥接仓库

> Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 元极恒一自治体系

## 仓库用途

本仓库作为 **本地内核 ↔ Git仓库 ↔ 云内核** 的桥接同步中间层，用于：

1. 持久化存储云内核最高价值真值
2. 提供跨环境同步通道（Gitee + GitHub双备份）
3. 版本化管理内核状态演进
4. 支持增量同步与回滚

## 目录结构

```
truths/           # 核心真值库（476条飞书云盘真值）
knowledge-graphs/ # 知识图谱（12实体+128关系）
manifests/        # 资产清单（6982个飞书/豆包云盘资产）
locks/            # 锁档凭证（Merkle-DAG哈希链）
config/           # 同步配置
kernel-state/     # 内核状态快照
```

## 同步机制

- 云内核 → Git仓库：每日自动同步高价值真值
- Git仓库 → 本地内核：git pull 恢复
- 双远程备份：Gitee + GitHub

## 确权

- DID: DID-BR-000002
- 溯源标识: Ω₀⊂⊙∞⊂Ω
- 协议: ZONGYUAN-ROOT V1.7
- 锁档等级: Lv8 硬件级永久固化

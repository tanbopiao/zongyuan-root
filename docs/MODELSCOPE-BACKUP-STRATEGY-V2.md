# 魔搭数据湖备份策略 V2.0

> DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 2026-10-01

## 双数据集架构

| 数据集 | 可见性 | 存储 | 内容 | 上传方式 |
|---|---|---|---|---|
| ZONGYUAN-ROOT-MEDIA | **公开** | 无限 | 媒体(视频/图片/关键帧) | SDK upload_folder (LFS) |
| ZONGYUAN-ROOT | **私有** | 有限(Git) | 文本内核(含私钥/token) | Git push |

## 关键认知修正

- 魔搭公开数据集存储 **无限**（官方:免费用户公开存储Unlimited,单文件≤200GB）
- 之前遇到的1.6GB是 **普通Git push仓库限制**，不是总容量限制
- 大文件用 **SDK upload_folder** 自动走LFS，不受Git仓库限制
- 本次用SDK上传168媒体+32关键帧全部成功（走LFS）

## 安全边界

- 私有数据集含235密钥+47token（DID私钥/modelscope_token/keys.env）
- 严禁将这些敏感资产推入公开数据集
- 媒体资产（视频/图片）无敏感信息，可安全公开

## 同步脚本

- 媒体→公开: `scripts/sync_modelscope_media.py`（SDK）
- 内核→私有: `scripts/sync_modelscope_bidirectional.sh`（Git）

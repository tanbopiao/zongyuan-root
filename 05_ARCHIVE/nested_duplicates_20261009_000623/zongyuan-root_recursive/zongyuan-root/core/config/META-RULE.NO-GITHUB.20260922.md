# 元法则：禁止使用 GitHub
> 确权: DID-BR-000002 | 2026-09-22

## 规则
**永久禁止使用 GitHub 作为 Git 仓库或部署通道。**

## 原因
- 网络连接慢，经常超时
- 仓库 404 不可达
- Gitee 国内访问更快更稳定

## 替代方案
- Gitee: https://gitee.com/huodou-cloud-intelligence-aios/huodouai-website

## 备份架构更新（3 层）
| 层级 | 位置 | 状态 |
|---|---|---|
| L1 本地主根 | /home/user/ZONGYUAN-ROOT/ | ✅ 活跃 |
| L2 全局技能锚定 | .user_skills/kunlun-autonomous-system/ZONGYUAN-ROOT/ | ✅ 活跃 |
| L3 云端真值库 | https://www.huodouai.com/api/truths/ | ✅ 活跃 |
| L4 Git 仓库 | Gitee（仅 Gitee，移除 GitHub） | ✅ 活跃 |

**GitHub 层已永久移除，仅保留 Gitee。**

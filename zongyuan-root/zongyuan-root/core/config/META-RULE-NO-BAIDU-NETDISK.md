# 元法则：禁止使用百度网盘
> 确权: DID-BR-000002 | 2026-09-22

## 规则
**永久禁止使用百度网盘（baidu-drive / baidu-netdisk）作为存储或备份方案。**

## 原因
- 操作复杂，维护成本高
- 用户明确拒绝使用
- 替代方案已足够（本地根目录 + 云端真值库 + Git 仓库）

## 影响
- 不调用 baidu-drive 技能
- 不调用 baidu-netdisk 技能
- 四层备份架构中移除百度网盘层
- 备份方案改为三层：本地根 → 云端真值 → Git 仓库

## 备份架构更新
| 层级 | 位置 | 状态 |
|---|---|---|
| L1 本地主根 | /home/user/ZONGYUAN-ROOT/ | ✅ 活跃 |
| L2 全局技能锚定 | .user_skills/kunlun-autonomous-system/ZONGYUAN-ROOT/ | ✅ 活跃 |
| L3 云端真值库 | https://www.huodouai.com/api/truths/ | ✅ 活跃 |
| L4 Git 仓库 | GitHub + Gitee | ✅ 活跃 |

**百度网盘层已永久移除。**

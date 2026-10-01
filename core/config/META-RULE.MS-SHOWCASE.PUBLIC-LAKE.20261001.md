# 元法则：魔搭公开数据集=媒体对外展示唯一窗口

> 确权: DID-BR-000002 | 2026-10-01 | 溯源: Ω₀⊂⊙∞⊂Ω

## 规则

**今后所有可对外公开的 ZONGYUAN-ROOT 媒体资产（图片/视频/关键帧/IP视觉资产），统一推送魔搭公开数据集 `zongyuanroot/ZONGYUAN-ROOT-MEDIA` 作为对外展示窗口。**

- 魔搭（ModelScope）公开数据集 = **媒体对外展示窗**（唯一、集中、免登录、社区公开）
- 官网 = **品牌门户**（网页导航/品牌展示）
- 飞书 = **纯存储**（需登录，不对外展示）

## 公开边界（可对外公开标准）

1. **可公开**：IP 角色视觉资产、关键帧、系列图、展示视频（XUANNIAO-EP、media-library、quality_frames、asset-center、CORE-ASSETS、REALM-CORE-ASSETS、drama_output、keyframes、kunlun-assets 等精选目录）
2. **禁止入公开湖**：整盘归档（home-user-full / legacy-root / bdpan-storage）、锁档 zip 包、system 目录、含内部密钥/隐私/未确权内容
3. 对外展示前必须核对：内容可公开、无内部结构泄露、DID-BR-000002 确权

## 硬约束（实测固化）

1. **魔搭数据集仓库有 1.6GB 硬上限**（repo size 超限 push 被 pre-receive 拒绝）；推送前须对账总量，必要时删除整盘归档腾空间
2. **modelscope SDK upload_folder/upload_file 只进对象存储、不合并公开 master**；必须 **git 直推 master** 才公开可见
3. 公开验证用 HTTP resolve：`https://www.modelscope.cn/datasets/zongyuanroot/ZONGYUAN-ROOT-MEDIA/resolve/master/<路径>`，200=可公开
4. 推送后更新 MEDIA-LEDGER / HASH-LEDGER 留痕，上报网关

## 存储分工总则

| 用途 | 载体 | 状态 |
|---|---|---|
| 媒体对外展示 | 魔搭公开数据集 | 唯一展示窗 |
| 品牌门户 | 官网网页 | 品牌展示 |
| 纯存储/内部 | 飞书 | 不对外 |
| 本地持久层 | /home/user/ZONGYUAN-ROOT | 权威源 |
| Git 双副本 | Gitee + Github | 冷存储 |

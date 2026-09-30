# 官网(huodouai.com) × 自动展示站 集成方案

> DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 2026-09-30 | 零成本 | 全自动

## 一、现状探测（2026-09-30 实测）
| 项 | 状态 |
|---|---|
| https://www.huodouai.com/ | HTTP 200（火斗云智AIOS官网运行正常）|
| https://www.huodouai.com/showcase/ | HTTP 200（云端已有"真实作品展示"页，昆仑洞天短剧工业版）|
| 魔搭自动展示站 | 6黑金页全通 + 导航页33项（本沙箱自动生成，自动更新）|

## 二、目标架构：双域一体
```
官网(云服务器)                       魔搭自动展示站(零成本)
www.huodouai.com/                    modelscope.cn/datasets/zongyuanroot/...
  ├─ /showcase/  ←每10分钟同步──→  zongyuan-root/web/INDEX.html + showcase/*.html
  │    （官网展示子域=自动展示站镜像）   （自动生成+自动发布，数据实时刷新）
  ├─ 首页加入口链接 → /showcase/         入口: 官网 /showcase/ = 魔搭导航页
  └─ 其余业务页不变                       ← 每日22:00流水线自动更新
```
- **官网 /showcase/ 与魔搭展示站内容 100% 同步**（云端cron每10分钟拉取）
- 官网停机时：魔搭展示站仍是公开访问入口（灾备）
- 魔搭发布新页 → 10分钟内官网同步出现（全自动，零人工）

## 三、实施步骤（SSH/云权限恢复后一键执行）
1. 上传 `deploy_website_integration.sh` 到云服务器 /root/
2. 执行 `bash deploy_website_integration.sh`
3. 脚本自动完成：建 /showcase/ 目录 → 从魔搭拉取展示站 → 首页加"体系展示"入口 → nginx重载校验 → 注册10分钟cron同步

## 四、验收标准
- [ ] curl https://www.huodouai.com/showcase/ 返回 200 且含"共N项资产"
- [ ] 首页存在指向 /showcase/ 的入口链接
- [ ] 魔搭展示站改版后，10分钟内官网 /showcase/ 自动同步
- [ ] 官网停机测试：魔搭展示站可独立访问（灾备成立）

## 五、回退方案
- 删除 cron 同步条目 + 恢复 nginx 原配置备份即回退
- 展示站本身在魔搭数据湖，永久可访问，不受官网影响

## 六、零成本约束
- 无对象存储/COS/OSS；仅 Gitee Git / 魔搭 / 自有SSH服务器
- 同步走 git pull（数据湖→官网），无额外流量费用

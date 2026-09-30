# 快速上手 · 演示版

**昆仑洞天 · ZONGYUAN-ROOT ｜ 演示环境快速体验指南**

归档节点：ZONGYUAN-ROOT ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω

---

## 查看公开演示样例

无需任何配置，直接浏览以下目录即可查看体系产出样例：

- `demo-showcase/ip-sample-assets/sample-storyboard.md` — 完整10秒短剧分镜
- `demo-showcase/ip-sample-assets/sample-keyframes.md` — 关键帧提示词样例
- `demo-showcase/ip-sample-assets/sample-voiceover.txt` — 旁白金句合集
- `demo-showcase/architecture-overview.md` — 系统架构说明
- `demo-showcase/feature-list.md` — 产品能力清单
- `business-docs/` — 商业文档（项目简述、BP摘要、路线图）
- `visual-docs/` — 流程图与架构图解

---

## 理解体系运作

体系每日自动执行以下流程，无需人工干预：

1. 定时任务触发，从角色库和主题库中轮询选定当日组合
2. 生成五段式10秒短剧分镜脚本
3. 为爆点帧和收尾帧生成标准化关键帧提示词
4. 创作一条文言文旁白金句
5. 对所有文件计算SHA256哈希，生成Merkle根
6. 写入内核锁档配置，打包ZIP和BASE85归档
7. Git提交并推送到GitHub + Gitee双仓
8. 云内核persist_task归档元数据
9. 闭环完成，等待次日触发

---

## 三端同步命令

在内核目录执行以下命令可手动触发三端同步：

```bash
bash sync.sh
```

该脚本依次执行：本地Git提交 → GitHub推送 → Gitee推送 → 云内核归档。

---

## 视觉标准说明

所有视觉产出遵循统一标准：

- 画幅：9:16竖屏
- 渲染：UE5.7光追
- 胶片：柯达Portra400质感
- 光影：强烈轮廓光 + 伦勃朗侧光
- 配色：冷白 / 赤金 / 玄黑 / 正红 / 青金
- 发型：纯乌黑长发及腰（永久基准，零白发）
- 体态：九头身比例，单头单脸
- 溯源：右下角隐秘镌刻Ω₀⊂⊙∞⊂Ω

---

## 联系与授权

商业合作、IP授权、文旅联动请通过体系主权根Ω-TAN-7-001对接。
所有资产确权至DID-BR-000002，溯源符号Ω₀⊂⊙∞⊂Ω。

Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ ZONGYUAN-ROOT

# 作品库展示全链路 SOP

**版本**：v1.0
**生效日期**：2026-09-25
**归属**：ZONGYUAN-ROOT / 昆仑洞天作品库
**DID**：DID-BR-000002
**锚定**：Ω₀⊂⊙∞⊂Ω
**成本**：全链路零成本

---

## 1. 全链路流程图

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ GPU/其他节点  │ →  │ 飞书Base附件  │ →  │ 云端定时拉取  │ →  │ nginx对外展示 │
│ 生产图片      │    │ 字段         │    │ 存本地       │    │ huodouai.com  │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                                              │
                                                              ▼
                                                        ┌──────────────┐
                                                        │ 魔搭永久备份  │
                                                        │ dataset      │
                                                        └──────────────┘
```

## 2. 各节点动作

| 节点 | 职责 | 输入 | 输出 |
|---|---|---|---|
| GPU / 其他生产节点 | 生成图片、视频、关键帧 | prompt / 参考图 | 成品文件 |
| 飞书 Base | 中转登记，附件字段存原图 | 节点上传的文件 + 元数据 | Base 记录行 |
| 云端服务器（定时任务） | 从 Base 拉附件，落地到 web 目录 | Base API 轮询 | `/www/wwwroot/huodouai.com/gallery/` 下的静态文件 |
| nginx | 对外静态服务 | web 目录 | `https://www.huodouai.com/gallery/...` |
| 魔搭 ModelScope | 永久备份 + 跨节点可拉 | 云端或节点直传 | dataset repo 不可变快照 |

## 3. 目录规范

云端 nginx 根目录：`/www/wwwroot/huodouai.com/gallery/`

```
gallery/
├── characters/   角色图（西王母/九天玄女/太阴月神/昆仑女帝/东方玫瑰/暗夜玫瑰…）
├── scenes/       场景图（昆仑洞天/瑶池/云海/夜景…）
├── videos/       视频成片（分镜短片/动态封面…）
└── rose-gallery/ 作品库独立站（本次新增）
```

文件命名建议：`<子域名>-<编号>-<姿态>.png`，例：`or-01-侧身回眸.png`。

## 4. 飞书 Base 附件字段规范

每条记录至少包含：

| 字段 | 类型 | 说明 |
|---|---|---|
| `asset_name` | 文本 | 资产中文名 |
| `subdomain` | 单选 | 东方玫瑰 / 暗夜玫瑰 / 西王母 / 太阴月神… |
| `category` | 单选 | characters / scenes / videos |
| `file` | 附件 | 原图（PNG/MP4） |
| `sha256` | 文本 | 文件哈希（节点生成时算好） |
| `status` | 单选 | draft / pending_publish / published / archived |
| `created_at` | 日期 | 生产时间 |
| `modelscope_path` | 文本 | 魔搭备份路径（备份后回填） |

## 5. 云端定时任务

- 频率：每 15 分钟轮询一次飞书 Base
- 过滤条件：`status = pending_publish`
- 动作：
  1. 调 Base API 拉附件下载链接
  2. 落地到 `gallery/<category>/<subdomain>/`
  3. 校验 sha256
  4. Base 记录 status 改为 `published`，回填 nginx URL
  5. 异步推一份到魔搭 dataset 做永久备份
- 失败重试：3 次，仍失败写问题阻塞表，不静默吞

## 6. 魔搭永久备份规则

- 视觉资产主库：`zongyuanroot/zongyuan-character-keyframes/<子域名>/`
- 原始包/部署包：`zongyuanroot/zongyuan-root-achievements/data_lake/<主题>/`
- 每次入库必须登记 shared_brain.db 的 assets 表（sha256 + modelscope:// 路径）
- 禁止重复入库：入库前先按 sha256 在 assets 表查重

## 7. 零成本边界

| 环节 | 成本 |
|---|---|
| GPU 生产 | 魔搭赠送 100h，用完即毁，不常驻 |
| 飞书 Base | 免费额度内 |
| 云端服务器 | 已有，nginx 静态服务无额外费用 |
| 魔搭 dataset | 免费仓库，不跑推理 |
| 记忆网关 | 免费 HTTP 上报 |

**禁止**：付费 CDN、付费对象存储、付费转码服务。

## 8. 验收清单

- [ ] Base 附件字段齐全
- [ ] 云端目录结构符合第 3 节
- [ ] nginx 可访问 `https://www.huodouai.com/gallery/...`
- [ ] 魔搭 dataset 里有对应不可变 commit
- [ ] shared_brain.db assets 表可查到 sha256
- [ ] 记忆网关 truth_count 递增

## 9. 异常处理

| 异常 | 处理 |
|---|---|
| Base API 限流 | 指数退避，最多 3 次 |
| 云端磁盘满 | 清理旧视频，图片保留；告警通知 |
| 魔搭上传失败 | 本地 + Base 双备份，下次定时任务重试 |
| nginx 404 | 检查文件权限 755 与属主 www-data |
| sha256 不一致 | 该文件隔离，不对外暴露 |

---

**维护**：链路任何一环变更，版本号 +0.1，并同步更新 shared_brain.db。

# 执行回执：atomgit 最高价值利用方案
2026-10-11 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω

## 一、已完成并落地（本地 → 远端，均可复核）

| 阶段 | 内容 | 本地来源 | 远端位置（zongyuangen/zongyuan-root-sync @ atomgit） | 证据 |
|---|---|---|---|---|
| P0 | 静态站点五站点 | 官网作品库/作品库画廊/kunda、政务AI总入口+政务AI中台、火斗云智能力总入口、昆仑洞天（rose+酒红睡袍+全域归档）、misc（home/ledger/dashboard） | `website/{gallery,gov-portal,aios-entry,kunlun,misc,docs}/`（28 个文本文件） | commit `aa98690`，push `0953a8f..aa98690` 一次成功，`git ls-remote` 与本地 HEAD 双向一致 |
| P2 | 公开文档合集 | 精选 1 白皮书 + 5 SOP + 1 巡检样例 | `website/docs/`（含 README 索引） | 同上 commit |
| P2 | 模型中心（A 类小文件） | atomgit-model-release / lora_dataset / models/sd15 等 | `models/{zongyuan-3b,kunlun-lora-dataset,sd15-inference,modelscope-demo-card}/` + `models/MODEL-DISTRIBUTION-PLAN.md` | 同上 commit |
| P2 | 部署指引 | 实测 API + 官方文档 | `website/DEPLOY-GUIDE.md`、`website/AI-SPACE-GUIDE.md` | 见文档内来源 URL |
| P2 | Action YAML 草案 | 官方 `.gitcode/workflows/` 规范 | `.gitcode/workflows/website-deploy.yml` | 同上 commit |
| P2 | 多仓镜像计划 | 实测 gitee/github 凭据与仓库状态 | `website/docs/MIRROR-PLAN.md` | 见文档内 ls-remote 证据 |
| P0 | Pages 总入口 hub | 本回执同批生成 | `website/index.html`（站点导航，供 Pages 以 website/ 为根发布） | 同上 commit |
| P0 | 本回执 | —— | `website/EXECUTION-RECEIPT.md` | 同上 commit |

技术实测要点：AtomGit 真实 API 基址 `https://api.atomgit.com/api/v5/`（Gitea 风格，`PRIVATE-TOKEN` 认证）；仓库 public、default_branch=main；Pages/Space 均无开放写接口（GET/PUT/POST `/api/v5/repos/.../pages` 与 `/api/v5/spaces` 均 404）；`atomgit.com/pages/...` 对任意仓库返回 200 系 SPA 兜底壳，不代表已上线；Action 官方 workflow 目录为 `.gitcode/workflows/`（现有 `.github/workflows/ci.yml` 可能不被识别）。

## 二、需用户网页端操作（诚实清单，未虚报上线）

1. **开启 Pages**：登录 → https://atomgit.com/zongyuangen/zongyuan-root-sync/settings/pages → 安装应用 → 分支 `main` + 目录 `website/` → 保存 → 等待构建。公开链接格式以保存后页面显示的官方地址为准（官方文档未公布 URL 格式，勿采用任何未证实域名）。
2. **创建 AI Space**（可选；静态站建议优先 Pages，不耗核时）：https://ai.gitcode.com/space/create → Static 构建。
3. **启用 Action**：联系 AtomGit 客服开通「代码化流水线」；YAML 已就位 `.gitcode/workflows/website-deploy.yml`。
4. **模型 B 类上传**（约 6.3GB，本地未硬传）：2GB `qwen2.5-3b-instruct-q4_k_m.gguf`、4GB `models/sd15`、261MB 图片集 → AtomGit 模型仓库网页端新建并上传（预期 `https://atomgit.com/zongyuangen/<model-name>`，需确认）。注意：本地 `zongyuan-3b/7b/quantized/training-data` 目录实为空（README 声称有权重但文件不存在），暂无可分发自研权重，未对外声称。
5. **Gitee 镜像对齐**：已非破坏性推送源 main → Gitee 新分支 `mirror/atomgit-main-20261011`（=`0953a8f`），Gitee `main`（`e98aad5b`，2026-10-02 容灾快照）未动——历史分叉（1/259），如需对齐请网页 PR 合入或授权强制。Gitee 仓库 4.5GB 超 1GB 配额、仅剩 3 次推送机会，建议网页端 GC/清历史。
6. **GitHub 镜像**：本机无 GitHub 凭据（`~/.git-credentials` 仅含 atomgit 与代理主机），需用户建仓 + 提供 PAT 后按 `MIRROR-PLAN.md` 内同步脚本执行。ModelScope 通道由后台执行体负责，本方案不重复推。

## 三、敏感项与风险（已遵守「不推送密钥/证件/案号」）

- **已排除未推送**：`政务敏感信息智能脱敏演示_live.html`（含身份证/银行卡样式测试串）、`SOP-GALLERY-DEPLOY-v2.0.md`（公网服务器 IP + root@ SSH）、腾讯云密钥事件报告。
- **源仓库既有敏感跟踪文件**：`.auth_credentials`、`.env.brain`、`.secure-backup/`（含 `kernel-core-secret-*.tar.gz[.enc]`）、1675 个 `*_credential.json`、33 个内核 `backups/` 快照等。对外公开镜像前建议 `git filter-repo` 从历史剥离。
- **图片策略**：仓库 `.gitignore` 规定图片走魔搭数据湖/外链、不进 Git（与既有 `kunlun-portfolio` 先例一致），本次 0 二进制入库；gallery/wine-robe 外链图经截图验证渲染正常。rose 画廊 25 个 `OR-KEY-*.webp` 缩略图源端缺失，属既有断链。
- **Gitee 配额告警**：远端 4565MB > 1024MB，仅剩 3 次推送机会。

## 四、下一步（建议顺序）

1. 网页端开启 Pages（最快获得公开链接）→ 2. 开通 Action 实现推送即发布 → 3. 网页端上传 B 类模型 → 4. 决策 Gitee main 对齐方式 → 5. GitHub 建仓 + 提供 PAT → 6. filter-repo 清洗历史后再对外公开镜像。

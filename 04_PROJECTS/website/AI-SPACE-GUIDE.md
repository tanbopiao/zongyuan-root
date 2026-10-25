# AtomGit AI Space 创建指引 — zongyuangen/zongyuan-root-sync

> 生成时间：2026-10-11（UTC+8）
> 目标：为静态站点 `website/kunlun-portfolio` 申请一个 AI Space（Static 构建）作为展示入口，或为后续 Gradio 应用预留。
> 诚实声明：**本执行体未创建任何 Space**。AI Space 创建为网页端操作，经探测无 CLI/API，且需登录管理员账号激活。

---

## 一、结论速览

| 事项 | 状态 |
|---|---|
| Space 创建入口 | ✅ https://ai.gitcode.com/space/create |
| 构建方式 | Gradio 构建 / Static 构建（静态网页用 Static） |
| 硬件配置 | CPU / 内存 / 可选 GPU |
| 首次激活 | ⚠️ 仅**管理员**可激活；游客/成员只能「前去讨论」 |
| 免费核时 | ⚠️ 背景称约 1000 核时/月，**未在官方文档独立核实** |
| CLI / API 创建 | ❌ 未发现；探测 `/api/v5/spaces`、`/api/v5/user/spaces` 均 404 |
| 本执行体是否已建 Space | ❌ **未创建，需用户网页端执行** |

---

## 二、API/CLI 探测证据（真实执行）

认证头 `PRIVATE-TOKEN: <token>`，基址 `https://api.atomgit.com/api/v5/`：

| 端点 | 状态码 | 结论 |
|---|---|---|
| `https://api.atomgit.com/api/v5/spaces` | 404 | 无此路由 |
| `https://api.atomgit.com/api/v5/user/spaces` | 404 | 无此路由 |
| `https://atomgit.com/open-apis/user` | 404 | 无开放 API 网关 |
| AI 社区站 `https://ai.atomgit.com/` | 200 | 网页存在，创建走网页表单 |

> 结论：Space 无开放创建 API，**只能网页端创建**。

---

## 三、网页端创建步骤（需用户登录执行）

1. 登录 AtomGit / AtomGit AI 账号（`zongyuangen`）。
2. 打开创建地址：**https://ai.gitcode.com/space/create**
   （或：右上角头像 →「创建 Space」/「Space」→「Create Space」）。
3. 填写基本信息：
   - **Space ID / 名称**：建议 `zongyuan-root-showcase`（可自定义）。
   - **描述**：元极恒一自治体系静态展示。
   - **可见性**：Public（公开，免费额度可用）。
   - **License**：按需选择。
4. 选择**应用类型**（可多选，用于筛选）。
5. 选择**构建方式**：
   - 纯静态网页 → 选 **Static 构建**（官方：「Static 构建一般用于静态网页」）。
   - 若后续要跑 Gradio 交互 Demo → 选 **Gradio 构建**（需 `app.py`）。
6. 配置**服务器与基础镜像**：按构建方式选默认即可；静态站无需 GPU。
7. 点击 **创建**。
8. 创建后 Space 处于「待激活」状态 → **管理员点击「激活」**：
   - 二次确认服务器配置与容器镜像；
   - 选「休眠设置」（默认 30 分钟无活动自动休眠，省核时）；
   - 核时不足时无法启动。
9. 启动成功后（启动超时 20 分钟，超时自动暂停），进入 Space 页面获得访问 URL。
10. 若用默认模板且未改代码，会先看到 Gradio 默认页——需把 `website/kunlun-portfolio` 的静态文件推到该 Space 仓库后才会展示真实内容。

### 静态站如何接入 Static Space
- Space 本质是一个 git 仓库（类似 Hugging Face Space）。创建后克隆其 git 地址。
- 官方模板：`git clone https://gitcode.com/gitcode-ai/space_init_template.git`
- 把 `index.html` 及资源放入 Space 仓库根目录（Static 构建约定），push 后平台自动重建。
- 关联模型/数据集：仅在 Space **暂停**状态下，于「Space 设置 → 关联设置」中配置。

---

## 四、Space 管理要点（官方文档原文提炼）

- **暂停**：Space 设置 → Space 管理 → 暂停；暂停后容器保留，再次启动不重建。
- **重置**：删除容器从头重建（慢，需重拉依赖；非必要不用）。
- **资源切换**：Space 设置 → Space 资源；切换会重建容器。
- **计时**：每分钟按 CPU 核数计核时（例：0.5 核跑 60 分钟 = 0.5 核时；2 核跑 30 分钟 = 1 核时）。
- **用量查看**：个人设置 → 用量及存储。
- **删除**：仅管理员，Space 设置 → 高级设置 → 删除，需输入 Space 路径确认。
- **启动失败排查**：看 K8S container event logs 与 container running logs（非管理员不可见），常见原因是代码/依赖错误或服务器与镜像不匹配。

---

## 五、本场景建议

- **优先用 Pages（见 DEPLOY-GUIDE.md）托管 `website/`**：静态站用 Pages 更轻量、不耗核时、不休眠。
- **AI Space 仅在以下情形创建**：
  1. 需要一个 Gradio/Streamlit 交互 Demo（如元极恒一内核的在线交互页）；
  2. 需要一个可休眠、按核时计费的容器环境跑模型推理；
  3. 想要 AI 社区主页上的「Space」展示卡片。
- 若只为展示静态首页，**不必创建 Space**，避免无谓消耗免费核时。

---

## 六、来源 URL（原文）

- Space 创建入口：https://ai.gitcode.com/space/create
- AtomGit 官方 Space 文档：https://docs.atomgit.com/docs/help/home/ai-community/ai-space/
- Space 新手指南（英文）：https://ai-docs.gitcode.com/en/docs/spaces/getting-started/
- Space 模板仓库：https://gitcode.com/gitcode-ai/space_init_template.git
- AtomGit AI 社区首页：https://ai.atomgit.com/

# AtomGit Pages 开启指引 — zongyuangen/zongyuan-root-sync

> 生成时间：2026-10-11（UTC+8）
> 仓库：`zongyuangen/zongyuan-root-sync`（公开仓库，默认分支 `main`，仓库 id=11038354）
> 静态站点目录：`website/kunlun-portfolio/index.html`（已核实存在）
> 诚实声明：本指引区分「已用 API/命令行验证」与「必须用户网页端手动操作」两类。**截至本指引生成，Pages 并未被开启**——本执行体无网页登录态，且经探测不存在可用的开启 API。

---

## 一、结论速览

| 事项 | 状态 |
|---|---|
| 仓库存在、public、默认分支 main | ✅ 已 API 验证 |
| `website/kunlun-portfolio/index.html` 已在 main 分支 | ✅ 已 API 验证 |
| Pages 开启 API（GET/PUT/POST） | ❌ 全部 404，**无开放写接口** |
| 网页端 Pages 入口 | ✅ 路径存在，但**需登录后操作**（未登录抓到的是兜底壳页） |
| Pages 是否已开启 / 已上线 | ❌ **未开启，需用户网页端执行** |
| 官方 Pages 文档 | ⚠️ 未在 docs.atomgit.com 找到独立 Pages 章节 |
| 预计公开访问 URL | ⚠️ **未证实**，见下方「五、公开 URL」（不要直接采用未验证格式对外宣传） |

---

## 二、API 探测证据（真实执行，带状态码）

认证方式：请求头 `PRIVATE-TOKEN: <token>`（实测有效；`?private_token=` 与 `Authorization: Bearer` 同样可用）。
真实 API 基址：`https://api.atomgit.com/api/v5/`（Gitea 风格路由）。

| 端点 | 方法 | 状态码 | 结论 |
|---|---|---|---|
| `https://atomgit.com/api/v1/user` | GET | 404 | 不存在（错误体 `NOT_PATH`） |
| `https://atomgit.com/api/v3/user` | GET | 200 | 兼容垫片，返回 login=zongyuangen |
| `https://api.atomgit.com/api/v5/user` | GET | 200 | ✅ 真实用户端点 |
| `https://api.atomgit.com/api/v5/repos/zongyuangen/zongyuan-root-sync` | GET | 200 | ✅ 仓库存在，public，default_branch=main |
| `https://api.atomgit.com/api/v5/repos/.../branches` | GET | 200 | 仅有 `main` 分支 |
| `https://api.atomgit.com/api/v5/repos/.../contents/website` | GET | 200 | 含子目录 `kunlun-portfolio` |
| `https://api.atomgit.com/api/v5/repos/.../contents/website/kunlun-portfolio` | GET | 200 | 含 `index.html` |
| `https://api.atomgit.com/api/v5/repos/.../pages` | GET | 404 | 无此路由 |
| `https://api.atomgit.com/api/v5/repos/.../pages` | PUT | 404 | 无写路由 |
| `https://api.atomgit.com/api/v5/repos/.../pages` | POST | 404 | 无写路由 |
| `https://atomgit.com/zongyuangen/zongyuan-root-sync/settings/pages` | GET(网页) | 兜底页 | 未登录态，无法读到设置表单 |
| `https://atomgit.com/pages/zongyuangen/zongyuan-root-sync/` | GET | 200 | **SPA 兜底壳**（同名不存在仓库也返回 200），不代表 Pages 已上线 |

> 结论：**Pages 只能在网页端开启**，token 无法代开。

---

## 三、网页端开启步骤（需用户登录后执行）

入口（已核实路径存在）：
**https://atomgit.com/zongyuangen/zongyuan-root-sync/settings/pages**

操作流程（参考 Gitee Pages 交互，因 AtomGit 官方文档将其描述为「安装应用后和 Gitee Pages 操作一样」）：

1. 浏览器登录 AtomGit 账号 `zongyuangen`。
2. 进入仓库：https://atomgit.com/zongyuangen/zongyuan-root-sync
3. 顶部/侧边进入 **Settings（设置）** → 左侧菜单 **Pages**。
   直达链接：https://atomgit.com/zongyuangen/zongyuan-root-sync/settings/pages
4. 首次进入可能要求**安装 Pages 应用/授权**（按页面提示点确认/授权）。
5. 选择发布源：
   - **分支（Branch）**：`main`
   - **目录（Folder/Path）**：`website/kunlun-portfolio`
     （因为站点入口 `index.html` 位于该子目录；若平台只接受根目录或 `/docs`，则需改为把 `index.html` 放到所选目录顶层，见下方「六、注意事项」）
6. 点击 **保存 / 发布 / 部署**。
7. 等待首次构建（通常 1–5 分钟），页面会给出站点地址。
8. 访问该地址确认首页正常。

> ⚠️ 第 4 步「安装应用」与第 5 步目录选择器的具体文案，因未登录无法截图核实——以实际网页为准。

---

## 四、AtomGit Action 启用（流水线自动构建并发布）

> 重要更正：经官方《快速开始》文档核实，**AtomGit Action 的 workflow 目录是 `.gitcode/workflows/`，不是 `.github/workflows/`**。
> 仓库当前已有 `.github/workflows/ci.yml`（GitHub 风格写法），**该文件很可能不会被 AtomGit 流水线识别**，需迁移到 `.gitcode/workflows/`。

### 4.1 前置门槛（必须先做）
- **联系 AtomGit 客服申请开通「代码化流水线（Pipeline as Code）」能力**。官方《快速开始》原文：「前提条件：联系 AtomGit 客服申请开通代码化流水线能力」。未开通前，即使放了 YAML 也不会运行。
- Secret/变量在网页端创建：项目设置 → Actions 密钥与变量。

### 4.2 YAML 存放路径
- 官方路径：仓库根目录 **`.gitcode/workflows/<任意名>.yml`**
- 本执行体已在本目录产出草案：`../website-deploy.yml`（随其他交付物一并放入仓库 `website/` 目录，由后续执行体归位到 `.gitcode/workflows/`）。

### 4.3 网页端开启位置
- 开通后，仓库页面顶部出现 **「流水线」/「Actions」** Tab。
- 推送 `.gitcode/workflows/*.yml` 到 `main` 即自动触发；也可在该 Tab 左侧选 workflow → 右侧 **Run workflow** 手动触发（需 YAML 里含 `workflow_dispatch`）。

### 4.4 预期效果
- push 到 `main` → Runner 拉代码 → 把 `website/` 整理为产物 →（发布步骤）。
- **注意**：官方文档未提供名为 `deploy-pages` 的内置插件的确切名称。若 Pages 本身是「选分支+目录」的静态托管，则最简方案是**不写 Action，直接在 Pages 设置里选 main + website 目录**；YAML 草案用于需要构建/拷贝产物的场景，其中「发布到 Pages」一步需在网页端确认插件名后填实（见 YAML 内注释）。

---

## 五、公开 URL（未证实，谨慎使用）

- 未在官方文档找到 AtomGit Pages 的默认域名格式。
- 探测 `https://zongyuangen.atomgit.com/zongyuan-root-sync/` → **404**。
- 探测 `https://atomgit.com/pages/zongyuangen/zongyuan-root-sync/` → 200，但**对不存在的仓库路径也返回 200**，判定为站点 SPA 兜底，**不能作为已上线证据**。
- 参考同类平台：Gitee Pages 为 `https://{owner}.gitee.io/{repo}`；GitHub Pages 为 `https://{owner}.github.io/{repo}`。AtomGit 可能类似 `https://{owner}.atomgit.com/{repo}`，但**此为推断，未经证实**。
- ✅ 正确做法：在网页端完成第 3 节保存后，**以 Pages 设置页显示的官方站点地址为准**，再回填到此处。

---

## 六、注意事项

1. 站点入口文件必须是所选目录顶层的 `index.html`。当前入口在 `website/kunlun-portfolio/index.html`：
   - 若 Pages 目录选择器可填任意子路径 → 选 `website/kunlun-portfolio` 即可。
   - 若只接受根目录或固定目录（如 `/docs`）→ 需把 `index.html` 及其资源放到对应目录顶层（这一步由推送 `website/` 的执行体处理，本执行体不碰 git）。
2. 仓库为 public，Pages 默认公开可访问。
3. 本执行体**未做任何 git push / 未修改仓库文件**。

---

## 七、来源 URL（原文）

- Gitee issue 确认 Pages 路径与「安装应用后同 Gitee Pages」：https://gitee.com/oschina/git-osc/issues/I9NGES?skip_mobile=true
- AtomGit Action 产品总览（能力全景、触发事件、目录 `.gitcode/workflows/`）：https://docs.atomgit.com/docs/help/home/org_project/pipeline/overview/
- AtomGit Action 快速开始（前置开通、workflow 目录、最小 YAML、系统变量）：https://docs.atomgit.com/docs/help/home/org_project/pipeline/quick-start/
- AtomGit Action 语法参考目录：https://docs.atomgit.com/docs/help/home/org_project/pipeline/syntax-reference/
- AI Space 创建：https://ai.gitcode.com/space/create ；文档 https://docs.atomgit.com/docs/help/home/ai-community/ai-space/
- Pages 设置入口（需登录）：https://atomgit.com/zongyuangen/zongyuan-root-sync/settings/pages

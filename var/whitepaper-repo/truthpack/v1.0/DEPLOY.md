# 元极恒一 · 种子真值包 V1.0 — 部署说明文档

> 溯源锚点：Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ 版本 V1.0 ｜ 锁档权限：L4 人工审批锁档
>
> 本文档面向运维/部署人员，说明如何将《元极恒一 · 哲学+工程合并全集种子真值包 V1.0》对外展示网页部署到目标环境。

---

## 一、交付物概览

交付物为**纯静态自包含站点**：无后端、无数据库、无构建步骤、无外部 CDN 依赖，字体与图表库全部本地化，支持完全离线运行。

```
yuanji-truthpack/                      总计约 1.4 MB
├── yuanji-truthpack.html              主页面（约 58 KB，含全部 84 条真值与样式）
├── assets/
│   ├── app.js                         检索与主题簇筛选交互（约 2 KB，纯展示层、只读）
│   └── charts.js                      ECharts 图表配置（约 4 KB）
└── _shared/
    ├── js/
    │   └── echarts.min.js             图表库（约 1 MB，本地化，无 CDN）
    └── fonts/                         本地化字体（共约 373 KB）
        ├── Tektur-Regular.ttf         展示字体（数字 / Ω 符号）
        ├── Tektur-Medium.ttf
        ├── JetBrainsMono-Regular.ttf  等宽字体（真值 ID / 徽章）
        └── JetBrainsMono-Bold.ttf
```

**页面能力边界**（对应 ENG_019 网页作品库工程真值）：

- 本页仅做阅读展示，**不作为权威真值源**；
- 不具备修改、写入内核的权限，无任何上传 / 写入接口；
- 交互仅限客户端检索与筛选（PHI 区 48 条、ENG 区 36 条），不产生网络请求（除加载本站静态资源外）。

---

## 二、部署前校验

上传前核对以下清单，任何一项不满足应停止部署：

| # | 校验项 | 预期 |
|---|--------|------|
| 1 | 目录结构完整 | `yuanji-truthpack.html` 与 `assets/`、`_shared/` 同级，相对路径不得打乱 |
| 2 | 文件数量 | 共 9 个文件（见第一节清单），无缺失 |
| 3 | 真值条目 | 页面内含 PHI_001–048 共 48 条、ENG_001–036 共 36 条，合计 84 条 |
| 4 | 版本标记 | 页面 Hero 区徽章显示 `VERSION 1.0`，页脚含 `DID-BR-000002` |
| 5 | 内容分级 | 确认为**公开脱敏精简版**；完整带哈希、账本、溯源凭证版本**不得**随本包上传（PHI_039 / ENG_014） |

---

## 三、部署方式

> 通用原则：将 **`yuanji-truthpack/` 整目录**原样上传至静态托管根目录，保持内部相对路径不变。可作为子目录部署（如 `/truthpack/`），页面内全部资源为相对路径引用，自动适配。

### 方式 A · 本地直接打开（预览 / 单机展示）

双击 `yuanji-truthpack.html` 即可在 Chrome / Edge 中打开。如需完整字体加载保真，建议用本地静态服务器预览：

```powershell
# PowerShell 5.1 本地预览（无 Python / Node 环境时可用）
$root = "C:\path\to\yuanji-truthpack"
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add('http://127.0.0.1:8791/')
$listener.Start()
while ($listener.IsListening) {
  $ctx = $listener.GetContext()
  $rel = $ctx.Request.Url.AbsolutePath.TrimStart('/')
  if ($rel -eq '') { $rel = 'yuanji-truthpack.html' }
  $file = Join-Path $root ($rel -replace '/', '\')
  if (Test-Path $file) {
    $bytes = [IO.File]::ReadAllBytes($file)
    $ctx.Response.ContentLength64 = $bytes.Length
    $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
  } else { $ctx.Response.StatusCode = 404 }
  $ctx.Response.OutputStream.Close()
}
# 浏览器访问 http://127.0.0.1:8791/，Ctrl+C 停止
```

### 方式 B · Nginx 静态站点（推荐生产环境）

```nginx
server {
    listen 443 ssl;
    server_name truth.example.com;          # 按实际域名修改
    root /var/www/yuanji-truthpack;
    index yuanji-truthpack.html;

    # 字体与图表库：长缓存 + immutable
    location ~* \.(ttf|js)$ {
        add_header Cache-Control "public, max-age=31536000, immutable";
    }
    # HTML：短缓存，保证版本更新即时生效
    location ~* \.html$ {
        add_header Cache-Control "no-cache";
    }

    gzip on;
    gzip_comp_level 5;
    gzip_types text/html text/javascript;
}
```

### 方式 C · Gitee Pages / GitHub Pages

1. 新建仓库（如 `yuanji-truthpack`），将目录内容整体推送至仓库根或 `docs/` 分支目录；
2. 在仓库设置中开启 Pages 服务，选择对应分支 / 目录；
3. 访问 `https://<用户名>.gitee.io/yuanji-truthpack/` 验证。
4. 注意：对应 ENG_030 多端同步工程真值，远端仅作分发渠道，同步前后均需做哈希校验留档。

### 方式 D · 对象存储静态网站托管（OSS / COS / OBS 等）

1. 在控制台创建 Bucket，开启「静态网站托管」功能；
2. 将目录内全部 9 个文件上传（保持 `assets/`、`_shared/` 层级）；
3. 默认索引文档设置为 `yuanji-truthpack.html`；
4. MIME 类型确认：`.html → text/html`、`.js → text/javascript`、`.ttf → font/ttf`；
5. 建议绑定自定义域名并启用 CDN 与 HTTPS。

### 方式 E · 官网 Tab 页 iframe 嵌入

本页按「官网 Tab 页面」场景设计，可直接嵌入现有官网：

```html
<div class="tab-panel" style="height: calc(100vh - 64px);">
  <iframe
    src="/truthpack/yuanji-truthpack.html"
    title="元极恒一 · 种子真值包 V1.0"
    style="width: 100%; height: 100%; border: 0;"
    loading="lazy">
  </iframe>
</div>
```

要点：

- 页面自带顶部导航与锚点跳转，iframe 内可独立使用；
- 若宿主官网希望隐藏页内导航，可另行提出定制（需新版本增量发布）；
- `height` 按宿主布局调整，页面内部各区块自带响应式与滚动。

---

## 四、部署后验证清单

部署完成后逐项验证（与本包出厂验证项一致）：

| # | 验证项 | 操作 | 预期 |
|---|--------|------|------|
| 1 | 页面可达 | 访问部署 URL | HTTP 200，Hero 区标题、徽章、84/48/36 统计正常 |
| 2 | 图表渲染 | 滚动至「真值分布」区 | 环形图中心显示 84；条形图显示 16 个主题簇，非空白 |
| 3 | 检索功能 | PHI 区搜索「熵增」 | 仅剩 PHI_004，计数「显示 1 / 48 条」 |
| 4 | 筛选功能 | ENG 区点击「稳态与总控」 | 仅剩 ENG_032–036，计数「显示 5 / 36 条」 |
| 5 | 字体加载 | 检查真值 ID 与数字 | 等宽 / 展示字体生效（DevTools Network 无 404） |
| 6 | 页脚信息 | 滚动至页脚 | `DID-BR-000002 ｜ 元极恒一 Lv11 ｜ ZONGYUAN-ROOT 自治代理` |
| 7 | 只读声明 | 查看「锁档说明」区 | RO-READONLY-GATE 横幅存在且文案完整 |
| 8 | 控制台 | DevTools Console | 无资源 404、无脚本报错 |

---

## 五、版本更新与锁档规则

本交付物遵循体系锁档真值（PHI_018 / PHI_043 / ENG_002 / ENG_035），更新流程如下：

1. **历史不可覆写**：已发布版本的线上文件视为锁档存量，禁止原地覆写修改；
2. **增量追加**：内容变更（新增真值、修订展示）以新版本号发布，推荐目录化版本管理：

   ```
   /truthpack/v1.0/    ← 锁档保留，只读
   /truthpack/v1.1/    ← 新版本目录，增量发布
   ```

3. **入口切换**：官网 Tab 的 iframe `src` 指向最新版本目录；历史版本 URL 保持可访问，用于快照比对与审计（PHI_032）；
4. **变更留痕**：每次发布在部署侧记录：版本号、变更条目清单、发布时间、操作人，纳入审计账本（ENG_010）；
5. **回滚**：如新版异常，将 iframe `src` 指回上一版本目录即可完成回滚，历史版本始终可用（ENG_011）。

---

## 六、安全边界与内容分级

- **公私双视图隔离**：本包为公开视图（脱敏精简版）；含哈希指纹、审计账本、溯源凭证的完整版本仅存于本地持久层与私有仓库，**严禁**部署至公开渠道（PHI_039 / ENG_014 / 体系边界第四条）；
- **只读属性**：页面无任何写入能力，不采集访客数据，不含外部统计脚本；
- **传输安全**：生产环境强制 HTTPS；若嵌入官网，确保 iframe 与宿主同域或明确 `Content-Security-Policy: frame-ancestors` 白名单；
- **降级预案**：本页无外部依赖，无第三方服务失效风险；托管平台故障时按 ENG_027 切换备用静态渠道（如 Gitee Pages ↔ 对象存储互为备份）。

---

*本文档遵循 L4 锁档规则：历史内容不可修改，仅支持增量追加新版本。*
*文档版本：V1.0 ｜ 生成于 2026-10-18 ｜ 对应页面版本：yuanji-truthpack V1.0*

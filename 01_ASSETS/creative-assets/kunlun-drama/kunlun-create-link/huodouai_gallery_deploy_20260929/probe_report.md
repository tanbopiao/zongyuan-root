# 官网只读探测报告

> **探测时间**：2026-09-29 22:57 (UTC+8)
> **探测方式**：`curl -sI` / `curl -s`，超时 10s，仅 GET/HEAD，未做任何写操作
> **探测目标**：https://www.huodouai.com/

---

## 一、探测结论（一句话）

**站点可达（HTTP/2 200，nginx，前置 Vortex 代理），但 `/gallery/rose/` 当前返回的是与首页完全相同的内容（同 content-length 57817 / 同 etag），并非独立静态目录——疑似 nginx SPA fallback 兜底，需用户确认玫瑰库实际部署路径。**

---

## 二、详细探测结果

### 2.1 首页 `https://www.huodouai.com/`

| 项目 | 值 |
|------|-----|
| 状态码 | `HTTP/2 200` |
| 服务器 | `nginx` |
| 前置代理 | `X-VE-Vortex-IP: 123.57.90.27`（火山引擎 Vortex） |
| Content-Type | `text/html` |
| Content-Length | `57817` 字节 |
| ETag | `"6ab17ed0-e1d9"` |
| Last-Modified | `Mon, 21 Sep 2026 19:00:32 GMT` |
| Cache-Control | `no-cache, must-revalidate` |

**已有安全响应头**（完整列表）：
```
strict-transport-security: max-age=31536000; includeSubDomains
x-frame-options: SAMEORIGIN
x-content-type-options: nosniff
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
permissions-policy: camera=(), microphone=(), geolocation=()
```

**未发现**：
- ❌ `X-DID` / `X-Ontology` / `X-Anchoring` 等确权响应头
- ❌ `X-Powered-By`（已隐藏，良好）

### 2.2 `/gallery/rose/` 探测

| 项目 | 值 |
|------|-----|
| 状态码 | `HTTP/2 200` |
| Content-Length | **`57817`**（与首页完全一致） |
| ETag | **`"6ab17ed0-e1d9"`**（与首页完全一致） |
| Last-Modified | `Mon, 21 Sep 2026 19:00:32 GMT`（与首页一致） |
| GET 内容标题 | `<title>火斗云智AIOS · 智能操作系统</title>`（**首页内容**，非玫瑰库） |

**判断**：
- `/gallery/rose/` 返回的字节数、ETag、最后修改时间与首页**完全相同**
- GET 取回的 HTML 标题是"火斗云智AIOS"，不是玫瑰作品库
- 这说明 nginx 配置中存在类似 `try_files $uri $uri/ /index.html;` 的 SPA fallback，未匹配的路径全部回退到首页
- **玫瑰库当前可能并不在 `/gallery/rose/`，或已被移除/覆盖**——需用户 SSH 登录服务器确认 `/var/www/` 下实际目录结构

### 2.3 图片 URL 抽样验证（魔搭 CDN）

从画廊 HTML 中抽取 5 个唯一 modelscope 图片 URL，全部通过：

| 样本 | 首次 HEAD | 最终 GET | Content-Type | 大小 |
|------|-----------|----------|--------------|------|
| #1 | 302 → cdn-lfs-cn-1.modelscope.cn | 200 | image/jpeg | 1.8 MB |
| #2 | 302 → cdn-lfs-cn-1.modelscope.cn | 200 | image/jpeg | 1.9 MB |
| #3 | 302 → cdn-lfs-cn-1.modelscope.cn | 200 | image/jpeg | 1.7 MB |
| #4 | 302 → cdn-lfs-cn-1.modelscope.cn | 200 | image/jpeg | 1.8 MB |
| #5 | 302 → cdn-lfs-cn-1.modelscope.cn | 200 | image/jpeg | 1.9 MB |

**结论**：魔搭公网图片 URL 302→200 跳转链通畅，画廊上线后图片可正常加载。

### 2.4 画廊 HTML 内嵌确权标识

| 标识 | 是否内嵌 |
|------|----------|
| `DID-BR-000002` | ✅ |
| `Ω₀⊂⊙∞⊂Ω` | ✅ |
| `ZONGYUAN-ROOT` | ✅ |
| 唯一 modelscope 图片 URL 数 | 116 张 |

---

## 三、对部署方案的影响

1. **nginx 配置必须放在现有 443 server 块内**，不能新建独立 server 块（避免与已有 HTTPS 配置冲突）。
2. **location 优先级**：由于存在 SPA fallback，`location /gallery/kunlun-keyframes/` 必须写在 `location /` 之前，否则会被 fallback 拦截返回首页。
3. **DID 响应头需自行添加**：当前站点无 DID 头，本方案的 nginx 配置已包含 `add_header X-DID ...`。
4. **玫瑰库路径需用户确认**：建议用户登录服务器后执行 `ls /var/www/` 和 `cat /etc/nginx/conf.d/*.conf | grep -E "root|location"` 确认实际目录结构，再决定 SITE_DIR。

---

*探测过程全程只读，未对服务器做任何变更。*
*Ω₀⊂⊙∞⊂Ω · DID-BR-000002*

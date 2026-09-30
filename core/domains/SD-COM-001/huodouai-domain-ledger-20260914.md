# 火斗云智 · 全域域名—站点—模块台账（DNS/NGINX/目录三维对照）

> ZONGYUAN-ROOT | DID-BR-000002 | 2026-09-14
> 扫描对象：DNS 解析 + nginx 生效配置（/www/server/nginx/conf/sites/*.conf，主配置仅 include 此目录）+ /www/wwwroot 站点目录 + 公网实测

## 一、核心结论（先看这里）

1. **nginx 只加载 `/www/server/nginx/conf/sites/*.conf`**，宝塔面板目录 `/www/server/panel/vhost/nginx/*.conf` 全部不生效。之前两套配置并存造成的"改了不生效"全部由此解释。
2. **drama.huodouai.com 被改指向，是问题根因**：2026-09-14 02:38 该域名 nginx 配置被修改，root 从 `/www/wwwroot/drama.huodouai.com`（昆仑洞天·AI短剧工业化流水线主页）切到 `/www/wwwroot/huodouai.com/drama`（火斗云智AIOS 官网 drama 子站）。备份 `drama.huodouai.com.conf.bak.20260913_160504` 里仍是昆仑洞天原指向，可追溯。
3. **昆仑洞天内容实际存在三处，职能不清**：
   - 老主页 `/www/wwwroot/drama.huodouai.com/`（昆仑洞天·AI短剧工业化流水线）——目前无任何域名指向（孤儿站）
   - 新站 `/www/wwwroot/huodouai.com/kunlun/`（昆仑洞天·东方神话IP宇宙）——kunlun.huodouai.com 配置指向它，但该域名 DNS 未解析，公网打不开
   - 官网子站 `/www/wwwroot/huodouai.com/drama/`——现在被 drama 域名顶着，却是官网形态首页

## 二、域名—站点台账（公网实测 2026-09-14）

### 已解析可访问（DNS → 123.207.202.158）

**huodouai.com / www.huodouai.com —— 火斗云智AIOS 总官网（主域主页）**
- 首页：火斗云智AIOS · 元极恒一超认知永恒自治体系（HTTP 200）
- 站点目录：/www/wwwroot/huodouai.com（约 29KB 首页，H1「元极恒一超认知永恒自治体系」）
- 含模块子目录：aios / architecture / drama / kunlun / math-axioms / workbench / agent-admin / agent-network / agent-studio / gov-* / api-* / blog / cases / dashboard / console 等数十个
- 关键路径：/kunlun/（昆仑洞天·东方神话IP宇宙，alias）、/math-axioms/（公理体系）、/workbench/（工作台）
- 反代内部服务：8170 / 9200 / 8080 / 8099 / 8095 / 8765 / 8626 / 8015 / 3000 / 8021（edu-ai、ai-proxy）等

**drama.huodouai.com —— ⚠️ 问题域名（昆仑洞天专用域名被官网占用）**
- 现状首页：火斗云智AIOS | 元极恒一自治体系（HTTP 200）
- 生效 root：/www/wwwroot/huodouai.com/drama（9月14日 02:38 改）
- 历史 root（备份可证）：/www/wwwroot/drama.huodouai.com（昆仑洞天·AI短剧工业化流水线）
- 子站含模块：admin / gallery / keyframes / play / studio / videos / audios / characters / kunlun / math-axioms / api.html / pipeline.html / methodology.html / evolution.html / versions.html 等
- 反代：8100（短剧产线 API）、8626（生产流水线）

**api.huodouai.com —— API 网关**
- 首页：火斗云智 API 网关（HTTP 200）
- 站点目录：/www/wwwroot/api.huodouai.com（dist/dashboard.html 面板）
- 统一 API Key 鉴权；反代内部：8000（网关主服务）/ 9000（内核 version/metrics）/ 8023 / 8031 / 8012 / 8072 / 8096–8099

**gov.huodouai.com —— 政务AI中台**
- 首页：火斗云智 政务AI中台（HTTP 200）
- 站点目录：/www/wwwroot/gov.huodouai.com
- 反代：8200 / 8201 / 8203 / 8031

**console.huodouai.com —— AIOS 运维平台**
- 首页：登录 - 火斗云智 AIOS 运维平台（HTTP 200）
- 站点目录：/www/wwwroot/console.huodouai.com（含 ops/、decision/ 子应用）
- 反代：8090 / 8111

**docs.huodouai.com —— 开发者文档站**
- 首页：火斗云智 开发者文档（HTTP 200）
- 站点目录：/www/wwwroot/docs.huodouai.com（纯静态，try_files 路由）

**status.huodouai.com —— 服务状态页**
- 首页：火斗云智 服务状态（HTTP 200）
- 站点目录：/www/wwwroot/status.huodouai.com（纯静态）

### 配置存在但 DNS 未解析（公网 000，补 A 记录即可启用）

**kunlun.huodouai.com —— 昆仑洞天·东方神话IP宇宙**
- 配置 root：/www/wwwroot/huodouai.com/kunlun（标题「昆仑洞天 · 东方神话IP宇宙 | ZONGYUAN-ROOT 本源体系」，含 characters/drama-pipeline/gallery/workbench/videos）
- 状态：80/443 均已配置，缺 DNS A 记录

**ops.huodouai.com —— 运维面板**
- 反代：9210 / 8098 / 8099；缺 DNS A 记录

**mirror.huodouai.com —— 镜像/entangle 服务**
- 反代：9125 / 9160（/entangle/status）；缺 DNS A 记录

**grafana.huodouai.com —— Grafana 监控**
- 80/443 已配置；缺 DNS A 记录

## 三、站点目录对照（磁盘真实内容）

- /www/wwwroot/drama.huodouai.com/ —— 昆仑洞天·AI短剧工业化流水线（老主页 5.9KB，admin/characters/drama/drama-internal/gallery/play/studio/videos/methodology.html）｜当前无域名指向（孤儿）
- /www/wwwroot/huodouai.com/drama/ —— 火斗云智AIOS·drama 子站（25KB 官网首页）｜当前 drama 域名指向
- /www/wwwroot/huodouai.com/kunlun/ —— 昆仑洞天·东方神话IP宇宙（新站）｜kunlun 域名配置指向但未开放
- /www/wwwroot/huodouai.com/ —— 火斗云智AIOS 总官网（主域）
- /www/wwwroot/api.huodouai.com/、gov.huodouai.com/、console.huodouai.com/、docs.huodouai.com/、status.huodouai.com/ —— 各子域对应站点
- /www/wwwroot/archive/、internal-archive/、huodouai.com.blue/、huodouai.com.green/ —— 归档/备份目录（非线上）

## 四、问题根因（一句话）

drama.huodouai.com 的 nginx 生效配置在 2026-09-14 02:38 被改为指向 `/www/wwwroot/huodouai.com/drama`（官网子站），而昆仑洞天真实主页 `/www/wwwroot/drama.huodouai.com/` 失去域名映射；同时主配置只加载 sites/ 目录，导致面板配置与真实配置长期不一致。

## 五、规划建议（待用户拍板后执行）

### 目标：一域名一职能、主页唯一、模块归位

**方案一（恢复语义，最小改动）**
- drama.huodouai.com → root 恢复 /www/wwwroot/drama.huodouai.com（昆仑洞天·AI短剧工业化流水线主页），把已上线的元法体系入口同步补到该站首页
- 官网保持 huodouai.com 主域；huodouai.com/drama 子站保留为主域下一个模块路径（/drama/），不再占用 drama 域名

**方案二（新站承接，推荐）**
- drama.huodouai.com → root 指向 /www/wwwroot/huodouai.com/kunlun（昆仑洞天·东方神话IP宇宙新站），元法体系入口同步补入
- 老站 /www/wwwroot/drama.huodouai.com 归档为历史版本
- 或另开 kunlun.huodouai.com（补 DNS A 记录）承接新站，drama 域名回归老站——两个昆仑洞天入口二选一，避免双站混乱

**统一收尾（无论选哪个方案）**
- 以 sites/ 目录为唯一配置权威，面板目录不维护或对齐删除，杜绝两套配置
- 未启用的 kunlun/ops/mirror/grafana 四个子域，按需补 DNS 或归档配置
- 首页统一挂「元法体系」一键跳转入口 + 溯源标识（已具备）

## 六、扫描命令留痕（可复现）

- 生效配置目录：`ls /www/server/nginx/conf/sites/`
- 主配置 include 行：`grep -n include /www/server/nginx/conf/nginx.conf`
- 站点标题：`grep -o "<title>[^<]*" /www/wwwroot/*/index.html`
- 域名解析：`getent hosts <域名>`（本地/服务器双侧）
- 公网实测：`curl -sL -o /dev/null -w "%{http_code}" https://<域名>/`

---

Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜ZONGYUAN-ROOT 全域域名台账

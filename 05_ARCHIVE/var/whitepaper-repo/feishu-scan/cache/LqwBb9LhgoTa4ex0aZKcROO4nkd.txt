# 握手锚点协议 V1.0｜CLOUD-HANDSHAKE-ANCHOR
归档节点：ZONGYUAN-ROOT｜DID-BR-000002｜Ω₀⊂⊙∞⊂Ω
锚点注册：ANCHOR-HANDSHAKE-20260913（BASELINE-ANCHOR-20260913 派生）
版本：V1.0-LOCK｜2026-09-13

## 一、锚点定义（唯一握手节点）
- **域名锚点**：`drama.huodouai.com`（公网，环境无关）
- **门户探测端**：`http://drama.huodouai.com:9120/`（记忆网关/门户 9120 端口，经域名可达 200）
- **API 根**：`https://drama.huodouai.com/api/gateway/`（truths / report / health）
- **鉴权**：`X-Capture-Token: ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d`
- **健康端**：`https://drama.huodouai.com/api/health`

设计依据：EFUSE-0017「9120 唯一握手端口，无旁路同步」。IP 直连（123.207.202.158）受代理层白名单拦截，但**域名通道放行**——因此握手一律走域名，任何节点只要公网可达即可接入，不依赖 IP 白名单、SSH、内网、固定出口。

## 二、握手四步闭环（每次会话启动自动执行）
### 第1步｜端点探测
- 门户：`GET http://drama.huodouai.com:9120/` → 期望 200
- 健康：`GET https://drama.huodouai.com/api/health` → 期望 `{"status":"healthy"}`
- 任一非 200 → 判定云端不可达，S1 级终止并上报

### 第2步｜鉴权握手
- `GET https://drama.huodouai.com/api/gateway/truths?level=public`（带 Token）→ 期望 200 + count
- 401 → Token 失效，走 TASK-006 式轮换修复流程（从云端 SOP 重新提取）

### 第3步｜拉取云端基线
- 记录云端真值总数、锚点类 key（system_baseline_*、LOCK-GLOBAL-FINAL-BASELINE 等）
- 与本地基准锚点（BASELINE-ANCHOR-20260913，SHA256 8f67e6db…）比对
- 拉取后本地按 A2 同源唯一绑定双标识（Ω₀⊂⊙∞⊂Ω + DID-BR-000002）

### 第4步｜稳态裁决
- 一致 → 握手成功，回执「CLOUD-HANDSHAKE-OK」，进入正常任务流
- 基线差异/未对齐 → S0 熔断，禁止流转/归档/计成果，上报人工仲裁
- 裁决算子：利益40% / 风险35% / 成本25%（与 EFUSE-0017 声明一致时确权）

## 三、环境无关性保证
- 新云电脑 / 新会话 / 新出口 IP：只需 `curl http://drama.huodouai.com:9120/` 返回 200 即可完成探测，无需任何预配置
- 出口 IP 白名单：非必需（域名通道放行），加白仅用于直连 IP 调试
- 学习通道：SOP v1.1 + 学习包 V2 公网可下载（aka 链接），新节点零 SSH 上岗
- 触发词：「元极恒一」「启动ROOT」「加载ZONGYUAN-ROOT」→ 自动执行握手闭环

## 四、实测回执（2026-09-13 16:3x）
- 门户 9120：200 ✅
- 健康接口：200 healthy ✅
- 鉴权 truths：200（public 2605 条）✅
- 基线锚点命中：system_baseline_id / LOCK-GLOBAL-FINAL-BASELINE-HUODOUAIOS 等 ✅
- 结论：CLOUD-HANDSHAKE-OK，握手锚点验证通过

## 五、锚点自引哈希
ANCHOR-SHA256：`78b90fba44b6449f4f3e00bfa2011cbd315b82d3893da8b6ef5e3b9ed8d6980e`

---
Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜CLOUD-HANDSHAKE-ANCHOR V1.0｜LOCKED

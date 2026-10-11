# 火斗云智·昆仑洞天 短剧一键量产 · 使用说明

> 元极恒一自治体系 | DID-BR-000002 | 锚定 Ω₀⊂⊙∞⊂Ω | 零付费云（纯标准库）

拿到一个豆包（火山方舟）API Key 后，两条路径任选其一即可量产短剧素材包。

---

## 一、你会得到什么

一个 ZIP 素材包，内含：

| 文件 | 用途 |
|---|---|
| `EPxx_分镜表.json` | 机器可读分镜（镜号/画面/时长/关键帧提示词/视频提示词/音效/转场/配音） |
| `EPxx_分镜表.md` | 人工审阅版分镜表 |
| `EPxx_关键帧提示词集.txt` | 逐条关键帧提示词，直接粘进文生图（9:16） |
| `EPxx_配音台词.txt` | 按镜号索引的配音台词，直接导 TTS |
| `分集大纲.json` | 全剧→各集结构化大纲 |
| `素材清单.json` | 文件清单 + 每集校验统计 + API 调用报告 |
| `README使用说明.txt` | 包内使用指引 |

每条关键帧提示词已自动锁定：**9:16 竖屏、黑金暗纹国风仙侠、人体结构绝对禁止法则、长兵器结构铁律 V1.2、右下角 Ω₀⊂⊙∞⊂Ω、禁慢转场（仅硬切/快切/闪白）**。

---

## 二、路径 A：本地引擎（推荐，无跨域、Key 不出本机）

脚本：`one_key_production.py`（仅需 Python 3.8+，**无需 pip 安装任何依赖**）。

### 1. 准备 Key（三选一，优先级从高到低）

1. 运行时用 `--key` 传入；
2. 设环境变量 `export DOUBAO_API_KEY=你的key`；
3. 写入 `~/.env.brain`，键名 `DOUBAO_API_KEY=你的key`。

> Key 永不写入日志、报告、ZIP；诊断信息只暴露状态码与响应片段。

### 2. 一条命令量产

```bash
python3 one_key_production.py \
  --outline "昆仑洞天·玄汐归墟：玄汐于归墟之渊唤醒九天神剑，对抗烛龙残识" \
  --episodes 1
```

完成后在 `--output` 指定目录（默认 `./drama_pkg_out`）生成 `短剧素材包_时间戳.zip`。

### 3. 参数表

| 参数 | 必填 | 说明 | 默认 |
|---|---|---|---|
| `--outline` | 是 | 全剧剧情梗概 | — |
| `--episodes` | 否 | 集数 | 1 |
| `--key` | 否 | 豆包 API Key | 环境变量 / `.env.brain` |
| `--base` | 否 | API 地址 | `.env.brain` 的 `DOUBAO_API_BASE`（`https://ark.cn-beijing.volces.com/api/v3`） |
| `--endpoint-id` | 否 | 推理端点 ID（`ep-xxx`） | `.env.brain` 的 `DOUBAO_ENDPOINT_ID` |
| `--model` | 否 | 模型名（覆盖 endpoint） | endpoint_id → chat_model |
| `--output` | 否 | 输出目录 | `./drama_pkg_out` |
| `--max-tokens` | 否 | 单次输出上限 | 4000 |

### 4. 退出码

- `0`：至少一次 API 成功且全部校验通过；
- `2`：未取得任何 Key / 参数错误；
- `3`：API 被拒或不可达，已用内置兜底模板产出合法素材包（`meta.dataSource=fallback-template`，需人工复核）。

---

## 三、路径 B：浏览器向导页（`一键量产向导.html`）

双击用浏览器打开即可。

1. 选择「浏览器直连模式」；
2. 粘贴 API Key（密码框，**仅存 sessionStorage，关闭标签即销毁，绝不写 localStorage/磁盘**）；
3. 填 API Base、模型/端点 ID、集数、剧情梗概；
4. 点「开始量产」→ 逐集生成并预览 → 点「下载素材包 ZIP」。

> **注意**：方舟 API 默认不开浏览器跨域（CORS），直连模式很可能被浏览器拦截。被拦截时页面会给出明确提示，请切换到「本地引擎模式」按图文步骤运行 `one_key_production.py`——这是真实量产的推荐路径。

---

## 四、常见错误处理

| 现象 | 原因 | 处理 |
|---|---|---|
| `HTTP 429 SetLimitExceeded` / "Safe Experience Mode" | 账号对该模型触发用量上限，服务被暂停 | 到火山方舟「模型开通」页调高/关闭「安全体验模式」限额，或换一个已开通模型；网络与 Key 本身正常 |
| `HTTP 401 / 403` | Key 错误或无权限 | 核对 Key、端点 ID 是否一致 |
| `HTTP 404 / Model Not Found` | endpoint_id 或模型名写错 | `--endpoint-id ep-xxx` 与方舟控制台一致 |
| `URLError / RemoteDisconnected / timeout` | 网络不通或被对端断开 | 检查网络；引擎已对瞬时错误自动重试 1 次，仍失败会降级兜底 |
| 浏览器直连 `Failed to fetch` / CORS | 方舟不允许跨域 | 改用本地引擎路径 A |
| `meta.dataSource=fallback-template` | 本次 API 未成功，用了兜底模板 | 修好 Key/额度后重跑；该包仅作结构占位 |

---

## 五、安全红线

- 任何 Key 值不得出现在交付文件、ZIP、页面源码中；发布前请对 `one_key_production.py`、`一键量产向导.html`、本目录执行 `grep -E "sk-[a-zA-Z0-9]{8,}"`，应为空。
- 页面源码只含输入框与 sessionStorage 读写逻辑，无硬编码 Key。
- 纯 Python 标准库 + 浏览器原生 JS，无第三方付费服务。

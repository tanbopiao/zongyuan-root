# DRAMA-LIVE-VERIFY-20261002 · 一键量产引擎接入工作台真实验证报告

> 元极恒一自治体系 | DID-BR-000002 | 锚定 Ω₀⊂⊙∞⊂Ω
> 日期：2026-10-02 | 目标：把"一键量产引擎"接入短剧生产工作台真实产出（HTTP 接入层 + 页面调用层），核心流水线零重写。

---

## 一、状态：**已完成**（含一处外部阻塞，已如实降级）

| 交付项 | 状态 | 说明 |
|---|---|---|
| `drama_production_server.py` + `start.sh` | 已完成 | HTTP 接入层，包装 `one_key_production.py`，服务常驻 |
| 服务常驻 + PID | 已完成 | PID=**5275**，端口 8086，`live/server.pid` |
| 向导页面"真实执行区" | 已完成 | 页面真实 POST /api/produce → 轮询 → 展示真实产物 |
| 真实跑通 1 集素材包 | 已完成 | ZIP 真实产出并通过校验 |
| drama_validator 校验 | 已完成 | 分镜表 JSON + 关键帧 TXT 均 exit=0 |
| 桌面+移动截图 | 已完成 | 无 console error，健康条全绿 |

---

## 二、真实验证：提交任务 → 轮询 → 产物（curl 记录）

### STEP 0 · 健康自检
```bash
$ curl -s http://127.0.0.1:8086/api/health
{"ok": true, "service": "drama_production_server", "port": 8086,
 "engineExists": true, "validatorExists": true,
 "keyReady": true, "taskCount": 0,
 "artifactsDir": ".../drama-workbench/artifacts_live"}
```
> 注：`keyReady` 只报布尔，绝不回显 key 值。

### STEP 1 · 提交生产任务
```bash
$ curl -s -X POST http://127.0.0.1:8086/api/produce \
    -H 'Content-Type: application/json' \
    --data '{"outline":"昆仑洞天·玄汐归墟：……（玄汐归墟梗概）……","episodes":1}'

{"task_id": "20261002_105144_7f76b4", "status": "queued",
 "poll": "/api/produce/20261002_105144_7f76b4"}
```

### STEP 2 · 轮询状态（queued → running → done）
```
[1] running
[2] done
```
返回结果摘要：
```
exitCode      = 3            # 引擎退出码：全部 API 失败但已用兜底模板产出
needsReview   = true         # 明确标注"需人工复核"
zipName       = 短剧素材包_20261002_105145.zip
zipSizeBytes  = 7453
shotCount     = 10
kfCount       = 10
voCount       = 10
dataSources   = ["fallback-template"]
validator.ran = True  passed=True  exit=0
  汇总(镜级)：PASS=10  WARN=0  FAIL=0  / 共 10 镜
  汇总(条级)：FAIL=0 条  WARN=0 条  | 整体=PASS
```

### STEP 3 · 受控下载端点复测
```bash
$ curl -s -o /tmp/dl.zip -w "http=%{http_code} size=%{size_download}\n" \
    "http://127.0.0.1:8086/api/file?path=<urlencode(ZIP绝对路径)>"
http=200 size=7450~7453
# 下载到本地后 zipfile.ZipFile 可正常打开，7 个条目
```

---

## 三、本次真实产物

**ZIP 绝对路径**：
`/home/user/Doubao/chats/1128121028098/drama-workbench/artifacts_live/短剧素材包_20261002_105145.zip`

**大小**：7453 字节。**内含文件清单（7 项）**：

| 大小 | 文件 |
|---:|---|
| 711 B | 分集大纲.json |
| 9167 B | EP01_分镜表.json |
| 6185 B | EP01_分镜表.md |
| 4602 B | EP01_关键帧提示词集.txt |
| 839 B | EP01_配音台词.txt |
| 1749 B | 素材清单.json |
| 1041 B | README使用说明.txt |

> 含分镜表(JSON/MD)、关键帧提示词集、配音台词、目录规范文件(素材清单/README)，符合要求。

### 校验器输出（独立复跑 drama_validator.py）
```
$ python3 DRM-PIPE-V1.3/drama_validator.py --check-file EP01_分镜表.json
汇总(镜级)：PASS=10  WARN=0  FAIL=0  / 共 10 镜
汇总(条级)：FAIL=0 条  WARN=0 条  | 整体=PASS
JSON_EXIT=0

$ python3 DRM-PIPE-V1.3/drama_validator.py --check-file EP01_关键帧提示词集.txt
汇总(条级)：PASS=10  WARN=0  FAIL=0  / 共 10 条
KF_EXIT=0
```
其中长兵器镜头 3 镜，三级判定均为 `pass`（四条结构铁律关键短语齐全）。

---

## 四、阻塞（如实记录，未伪装成功）

**方舟 API 429（SetLimitExceeded）——外部配额阻塞，非本链路缺陷。**

- 引擎日志原文：
  ```
  HTTP 429: {"error":{"code":"SetLimitExceeded",
  "message":"Your account [2103991240] has reached the set usage limit for the
  [doubao-seed-2-0-lite] model, and the model service has been paused. To continue
  using this model, please visit the Model Activation page to adjust or close the
  \"Safe Experience Mode\". ..."}}
  ```
- 大纲调用 + EP01 分镜调用均命中 429，`anyApiOk=false`。
- **降级行为**：引擎按内置兜底模板产出结构合法的素材包（退出码 3），服务在结果里如实置 `needsReview=true`、`dataSources=["fallback-template"]`，前端页面以金色徽章「兜底模板产出 · 需人工复核」展示，未伪造成功。
- 解决后预期：到方舟控制台关闭/调整 doubao-seed-2-0-lite 的"安全体验模式"限额后重跑同一接口，`dataSource` 即转为 `doubao-api`、退出码 0。本链路代码无需改动。

---

## 五、交付物清单（drama-workbench/ 下）

| 文件 | 说明 |
|---|---|
| `drama_production_server.py` | 新增。HTTP 接入层（stdlib），端点 /api/health、/api/produce、/api/produce/{id}、/api/tasks、/api/file |
| `start.sh` | 新增。常驻启动脚本，写 PID，防重复起 |
| `一键量产向导.html` | 改造。新增"真实执行区"+ 健康条 + 真实产物展示；原命令生成保留为辅助；原件备份于 `_backup/` |
| `live/server.pid` | 服务 PID=5275 |
| `live/tasks/<task_id>.log` | 每次真实生产的完整引擎日志 |
| `live/tasks.json` | 任务注册表 |
| `artifacts_live/短剧素材包_20261002_105145.zip` | 本次真实产物 |
| `DRAMA-LIVE-VERIFY-20261002.md` | 本报告 |

**硬约束核对**：
- 复用优先：分镜/提示词逻辑全部复用 `one_key_production.py`，校验复用 `DRM-PIPE-V1.3/drama_validator.py`，本任务只做 HTTP 接入层 + 页面调用层。
- 不暴露 key：服务只从 `.env.brain` 读（引擎内部），健康检查仅报 `keyReady` 布尔；HTML 中无任何 key。
- 真实可用：ZIP 真实生成、独立校验通过；兜底内容明确标注"需人工复核"。

---

## 六、后补路径（未闭环环节）

1. **方舟模型配额**：429 解除后重跑，产物 dataSource 由 fallback-template 升级为 doubao-api（代码已就绪，无需改）。
2. **配音音频**：本链路产物 `EP01_配音台词.txt` 为文本；接 TTS 转 WAV 后可纳入含配音 ZIP（上一版 101918_含配音.zip 已有先例，非本任务范围）。
3. **任务历史持久化**：当前任务详情存内存，服务重启后 `/api/tasks` 注册表仍在但详情需重跑获取；如需跨重启保留详情，可后续把 result 落盘（非必需）。

Ω₀⊂⊙∞⊂Ω

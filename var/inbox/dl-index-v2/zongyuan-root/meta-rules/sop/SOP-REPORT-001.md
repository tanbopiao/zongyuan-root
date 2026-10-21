# SOP-REPORT-001 ｜ 云端记忆网关上报 SOP
版本：v1.0 ｜ 锚定：DID-BR-000002 ｜ 学习来源：多轮实战根因修复（surrogate 截断/代理超时/端点斜杠）

## 一、端点与认证
- 主端点：`https://www.huodouai.com/api/report/truth`（**无尾部斜杠**，带斜杠返回 404）
- 备份端点：`https://drama.huodouai.com/api/report/truth`
- 认证：仅 `X-DID: DID-BR-000002` 单头；零明文令牌（X-Capture-Token 仅兼容保留，不落盘）
- 方法：POST；Content-Type: application/json
- 状态查询：`https://www.huodouai.com/api/status`

## 二、载荷规范
- 信封：`{"key": "<domain>.<事件>.<时间戳>", "value": {事件字段}}`
- key 命名：`domain.xxx.<epoch_ts>`（如 `lock.full.20260928-220510`、`law.evolution.<ts>`）
- value：JSON 对象，含 event/结果/数字证据；避免超长

## 三、执行工具（统一入口）
- `python3 /home/user/ZONGYUAN-ROOT/scripts/gateway_report.py '<key>' '<json value>'`
  - urllib 直连（规避出口代理 curl 隧道挂起）
  - clean 递归清洗 surrogate（UTF-8 安全）
  - 主+备份双通道自动切换
- 旧 curl 通道仅保留兼容；字符截断一律 `cut -c1-40`（**禁止 head -c** 按字节截断中文字符产生 surrogate 导致 JSON 编码失败）

## 四、判定与容错
- 成功判定：响应含 `"message":"真值写入成功"` + `truth_count` 数值
- 失败不阻塞主流程：写入失败日志，下次幂等重试；备份通道自动兜底

## 五、学习要点（历史教训）
1. head -c 字节截断 UTF-8 → surrogate → UnicodeEncodeError（非网络问题）→ cut -c 按字符
2. 出口代理 curl (28) timeout → urllib/--noproxy 直连稳定
3. 端点带尾斜杠 404 → 无尾斜杠

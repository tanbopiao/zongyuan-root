# ZONGYUAN 协议规范（公开安全层）

## 1. 确权与网关
- 上报端点：`https://www.huodouai.com/api/report/truth`（**无尾部斜杠**，带斜杠 404）
- 认证：仅 `X-DID: DID-BR-000002` 单头；零明文令牌
- 载荷：`{"key":"<唯一key>","value":{事件字段}}`
- 成功判定：响应含 `"message":"真值写入成功"` + truth_count
- 容错：失败不阻塞主流程；备用通道 `https://drama.huodouai.com/api/report/truth`

## 2. 真值 key 命名空间（对齐门）
- 允许前缀：REPORT | SFMP | KERNEL | truth. | TEST | SEED_ | SCAN | QUOTA | EVO | HEARTBEAT | STATUS ...
- 周期 key（含 .evolve/.patrol/.heartbeat/.check/.health/.metrics/.status）允许覆盖
- 对齐门不匹配会被拒绝——key 前缀须符合白名单

## 3. 全域锁档（六环节 append-only）
1 本地快照锁档（SHA-256→卷宗+HASH-LEDGER）→ 2 飞书Base真值同步 → 3 飞书云盘归档 → 4 飞书知识库归档 → 5 云端网关上报 → 6 心跳握手
- 只追加新行新文件，绝不修改历史
- 退出码 0 = ≥4 环节 ok；逐源状态落 `var/auto-lock/auto-lock-<ts>.json`

## 4. 安全边界
- 密钥零明文落盘（加密槽位 + KEK 注入）
- 公开数据湖仅存脱敏内容（本目录 asset-master-index.json 已脱敏）
- 代码防注入：白名单/引号包裹/不 eval

## 5. 数据湖更新机制
- 本目录内容变更 → commit → push（云端 /opt/ZONGYUAN-ROOT 已配 post-commit 钩子自动 push）
- MANIFEST.json 随每次更新重算 SHA256

# 真值网关 truths 全量 dump 修复记录

确权：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-27
事件：TRUTHS-LIMIT-FIX-20260927 ｜ 状态：已完成 ✅

## 一、根因（已实证）

外网链路 `https://www.huodouai.com/api/report/truths?limit=5` 返回 4,013,862B / 15s（limit 被忽略）：

```
公网 /api/report/truths → nginx rewrite ^/api/report/(.*)$ → /api/$1
→ 9120 do_GET → 非 /api/truths/list → super().do_GET()
→ 父类 memory_gateway_v3_sqlite.py 行618 elif path == "/api/truths"
→ db.get_all_truths()（行350，SELECT truth_key FROM truths ORDER BY truth_key 全量，无 limit）
```

- `get_all_truths` 调用点核实：仅父类 /api/truths 分支（context_assembler 与 sync_coordinator 均为独立实现）→ 修改安全，无副作用。
- 子类 `/api/truths/list` 此前已修复（174B/5条），外网走的是父类路径，故本次修父类。

## 二、修复内容（两个 patch）

1. **get_all_truths 加 limit 参数化**（行 350）：
   - 签名 `def get_all_truths(self, limit=None)`，`limit is not None` 时 SQL 追加 `LIMIT ?`；默认 None 保持原语义（内部其他潜在调用不受影响）。
2. **/api/truths 分支解析 `?limit=N`**（行 618）：
   - 默认 **100**，上限 clamp **5000**（`max(1, min(v, 5000))`），非法值回退 100；响应新增 `limit` 字段。

## 三、验证结果（本地 + 外网）

| 用例 | 修复前 | 修复后 |
|---|---|---|
| `/api/truths?limit=5` | 4,013,862B / 15s（limit 忽略全量） | **174B / 0.001s（本地）、0.25s（外网）** |
| `/api/truths` 无 limit | 4,013,862B / 15s | 4,313B / 0.29s（默认 100 条） |
| `/api/truths?limit=99999` | — | count=5000（clamp 生效） |
| `/api/truths/list?limit=3` | 正常 | 不回归 ✅ |
| `/api/truth/{key}` | 正常 | 不回归 ✅ |
| health | 正常 | 正常 ✅ |

## 四、资产留痕

- 备份：`/opt/ZONGYUAN-ROOT/engine/scripts/memory_gateway_v3_sqlite.py.bak.20260927`
- 运行代码：`unified_gateway_9120.py`（未改动，仍 chattr +i）
- 父类新哈希：`db95c0a8055d79a41e374382862135482e4a1007bd446bc1b6cea0cf44fc721c`
- 两文件均已恢复 `chattr +i` 锁档
- 服务：`unified-gateway-9120` active（systemctl restart 后）
- 真值上报：`truths_limit_fixed_1790475718` → truth_count **111117**，语义校验跳过（内容过短属预期）
- 既有 DB 备份：`memory_gateway.db.bak.20260927100029`（515,747,840B）；索引 `idx_truths_updated` 已建

## 五、备注

- truths 表存在 1 条 `truth_key` 为空的脏记录（首个元素 `""`），系存量数据，非本次引入；可在后续治理中清理。
- 本次为安全评估高③项落地。高①（真值写入鉴权）、高②（8 内部端口收敛）待用户拍板后另行执行。

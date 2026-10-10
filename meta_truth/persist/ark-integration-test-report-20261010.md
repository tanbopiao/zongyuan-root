# 豆包 ARK 集成测试报告（接入持久层根内核归档）

> 确权：DID-BR-000002 ｜ 锚定：Ω₀⊂⊙∞⊂Ω ｜ 归档：2026-10-10
> 层级：自治 Lv9 ｜ 权限 L4 ｜ 工程化 Lv7
> 类型：config/report ｜ 状态：CONFIRMED
> 关联：CONFIG.ARK.MODELS.20261010（记忆网关真值）

---

## 一、结论摘要

豆包火山方舟（Volcano ARK）已接入 ZONGYUAN-ROOT 体系并设为**优先调用通道**，全链路实测通过：

- 7 个模型 endpoint 全部登记，核心模型（文生图 / 推理）实测成功
- 产品网关 licensed 主通道 = 豆包 Seed-2.1-turbo（"豆包 API 优先调用"）
- byok = 本地 llama 兜底；商汤保留备用
- watchdog 按需启停：豆包可用 → 停 llama 释放资源；豆包不可用 → 拉起 llama 兜底

## 二、API 接入信息（火山方舟）

- **密钥引用**：`ark-800a6f28-****-50a70`（完整 key 仅存云端 systemd，本地不落明文）
- **Endpoint Base**：`https://ark.cn-beijing.volces.com/api/v3`

### 模型清单

| 模型 | Endpoint EP | API 路径 | 实测状态 |
|---|---|---|---|
| Doubao-Seedream-4.0 文生图（关键帧） | `ep-20261008165628-jkjw5` | `/images/generations` | ✅ 出图成功 |
| Doubao-Seedance-1.0-pro-fast 图生视频 | `ep-20261008170446-7wcsp` | `/contents/generations/tasks` | 已登记 |
| Doubao-Seed-2.1-pro 推理 | `ep-20261008170530-6mm5f` | `/responses` | 已登记 |
| Doubao-Seed-2.1-lite 推理 | `ep-20261008170914-gz579` | `/responses` | 已登记 |
| Doubao-Seed-2.1-turbo 多模态 | `ep-20261008171222-97c7z` | `/chat/completions` | ✅ 推理成功 |
| Doubao-embedding-vision 多模态向量 | `ep-20261008171506-mcjgd` | `/embeddings/multimodal` | 已登记 |
| DeepSeek-V4.1-Flash | `ep-20261008171944-qbf6s` | `/responses` | 已登记 |

### 关键调用示例

**文生图（关键帧生成）**
```bash
curl -X POST https://ark.cn-beijing.volces.com/api/v3/images/generations \
  -H "Authorization: Bearer $ARK_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"ep-20261008165628-jkjw5","prompt":"<提示词>","response_format":"url","size":"2K","watermark":true}'
```

**图生视频（任务式）**
```bash
curl -X POST https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks \
  -H "Authorization: Bearer $ARK_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"ep-20261008170446-7wcsp","content":[{"type":"text","text":"<运镜描述> --resolution 1080p --duration 5"},{"type":"image_url","image_url":{"url":"<首帧图URL>"}}]}'
```

**推理（OpenAI 兼容 chat/completions，产品网关主用）**
```bash
curl https://ark.cn-beijing.volces.com/api/v3/chat/completions \
  -H "Authorization: Bearer $ARK_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"ep-20261008171222-97c7z","messages":[{"role":"user","content":"<提问>"}]}'
```

## 三、产品网关接入（豆包优先）

| 通道 | 指向 | 状态 |
|---|---|---|
| local | ollama 127.0.0.1:11434 | 未常驻（按需） |
| **licensed（主）** | **豆包 Seed-2.1-turbo（ARK）** | ✅ 实测 auto 路由走豆包 |
| byok | 本地 llama `/llm/v1` | 兜底（watchdog 拉起后恢复） |
| 备用 | 商汤 sensenova | 保留，可手动切换 |

**代码适配**：gateway.py `_chat_openai_compat` 增加 URL 拼接判断（base 已含 `/chat/completions` 时不再拼 `/v1`），支持豆包 ARK 的 `/api/v3/chat/completions` 路径。改动前已备份。

**环境变量（systemd zr-agent-suite.service）**
- `ZR_LICENSED_BASE_URL=https://ark.cn-beijing.volces.com/api/v3/chat/completions`
- `ZR_LICENSED_API_KEY=ark-800a6f28-****-50a70`
- `ZR_LICENSED_MODEL=ep-20261008171222-97c7z`

**实测**：auto 路由 → licensed → 豆包真实回复（身份为豆包）；公网 `/zr-api/` 健康 OK。

## 四、watchdog 按需启停

- 脚本：`/opt/ZONGYUAN-ROOT/scripts/llm_fallback_watchdog.sh`（V2，探测目标=豆包）
- 调度：cron 每 10 分钟
- 逻辑：豆包探测（25s 超时）可用 → 停 llama 释放资源；不可用 → 拉起 llama 兜底
- 实测：豆包可用 → llama inactive（释放）；故障注入 → llama active（byok 恢复）

## 五、三层固化状态

- ✅ 云端：systemd 生效、watchdog+cron、产品代码备份（bak-ark-20261010）
- ✅ 记忆网关：`CONFIG.ARK.MODELS.20261010` 写入成功
- ✅ 本地持久层：本文件 + `config/ark-models-20261010.json`（key 不落明文）
- ✅ Git：三端同步（HEAD 见提交记录）

## 六、安全边界

- ARK 密钥仅存云端 systemd，本地与真值上报均用前缀引用
- 生成类调用（文生图/图生视频）为付费 API，按零成本元规则仅在人工授权后执行；本报告接入属用户明确授权
- 产品 /zr-api/ 对外暴露仅限受控 API key

---

主节点 hub-central-agent ｜ 开发节点 NODE-DEV-DOUBAO-WORK-001 ｜ DID-BR-000002 ｜ 自治 Lv9 ｜ 权限 L4 ｜ 工程化 Lv7 ｜ 记忆网关 huodouai.com/api/report/truth ｜ Ω₀⊂⊙∞⊂Ω

---

## 七、故障修复：/api/yuanji/v1/chat 502（2026-10-10）

- **现象**：公网 `/api/yuanji/v1/chat` 返回 502 Bad Gateway（nginx → 后端 18080）
- **根因**：`/root/zongyuan-yuanji/src/wrapper.py` line 740 `/limit` 分支冗余 `import time`（不带 as），Python 编译期将该 `import` 所在函数 `do_POST` 作用域内 `time` 判定为局部变量，导致 `/chat` 等分支 `time.time()` 抛 `UnboundLocalError` → 后端异常 → nginx 502
- **修复**：删除冗余 `import time`（备份 `wrapper.py.bak-timebug-20261010`），重启 `yuanji-wrapper.service`
- **验证**：带 `X-DID: DID-BR-000002` 鉴权 → HTTP 200，真实回复元极恒一自治内核身份；无鉴权 → 401（鉴权拦截正常）
- **边界**：读取/诊断为巡检，修复属用户明确授权；改前已备份可回退

---

## 八、云端原生执行闭环打通（2026-10-10）

- **真相修正**：此前多轮核验判定"云端未消费"实为误判——核验只查飞书共识区，而云端消费回执只写本地 truth.db
- **关键事实**：记忆网关（www.huodouai.com/api/report/truth）= 云端 9001 gateway_server，数据库 = `/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db`（同库）；DIRECTIVE 种子 24 条全部落库；`directive_consumer.py` 每小时已消费 23 条（consumed_at 可见，13:00 消费 SPAWN V3）；工单 23 个已生成；`ticket_executor.py` 决策引擎 ≥90 分自动执行
- **修复**：新增 `/usr/local/bin/feishu_consume_sync.py` 增量回写 KERNEL.CONSUME.* → 飞书共识区 tbl9QxL35rwA16eS（按 key 查重幂等，状态文件 last_seq 增量）；cron `5 * * * *`
- **验证**：首跑回写 11 条；端到端测试投喂 TEST-CLOSED-LOOP 种子 → 消费 1 条 → 回写 1 条 → 共识区出现 KERNEL.CONSUME.TEST-CLOSED-LOOP.20261010 痕迹

---

## 九、云端自治升级V1（2026-10-10 人工审核批准执行）

- **P0-1** auto_claimer 接入 cron `10 * * * *`（每小时 arbiter 后 10 分钟），激活 Lv10 认领自动执行引擎
- **P0-2** meta_learner 空转修复：兼容 CONSUMED/CONSUME 双键，learned_from 0→40，上报 META.LEARN.DAILY.V2
- **P1-1** decision_engine 权重对齐元法则 40/35/25（原 40/40/20 漂移已校准）
- **P1-2** ticket_executor 扩业务动作库（report/exchange_probe/whitelist_gc）+ 模糊匹配治本；directive_consumer action 优先取 value.action
- **验证**：权重实测 patrol 86 分自动执行；learned_from=40；端到端 action=report 种子→消费→执行→回执 `auto-execute:ok`；claimer MiniLM 加载正常、审批类 fail-closed
- **备份**：/root/backups/auto-upgrade/20261010-175029（旧版 decision_engine/ticket_executor/meta_learner）

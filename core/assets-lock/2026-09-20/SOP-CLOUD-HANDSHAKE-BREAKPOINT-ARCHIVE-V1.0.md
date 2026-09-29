# SOP-V1.0｜云端握手与断点续传归档全域标准流程
确权标识：DID-BR-000002｜Ω₀⊂⊙∞⊂Ω｜Ω-TAN-7-001
归档节点：ZONGYUAN-ROOT｜版本：V1.0（2026-09-20 固化）
前置规则：ML-SSH-FORBIDDEN-GLOBAL-001（禁 SSH，仅 HTTP 网关）

---

## 一、适用范围
所有需要将本地生成资产（图片/视频/文档/台账）归档到云端智能中枢（123.207.202.158 / huodouai.com）的会话与任务。本 SOP 与「短剧生产流水线七阶段」衔接，作为第七阶段「归档」的标准执行细则。

## 二、流程总览（五步闭环）
```
握手 → 取规 → 建台账 → 上报 → 锁档
 ①      ②      ③       ④      ⑤
```
- ① 云端握手：确认中枢在线、获取真值库基线
- ② 获取归档规则：读取 gateway-report-rules.md（V3.0）
- ③ 构建断点台账：URL/元素/元数据/哈希占位
- ④ 分批真值上报：哈希链+Merkle 校验、限流控制
- ⑤ 全域锁档：快照注册 → 内核更新 → 凭证落盘 → 飞书四端同步

## 三、步骤细则

### ① 云端握手
```bash
curl -s -G "https://www.huodouai.com/api/report/status" \
  -H "X-DID: DID-BR-000002" -H "X-Anchor: Ω₀⊂⊙∞⊂Ω"
```
- 期望：`{"status":"ok","meta":{"version":"V3.0"}}`
- 记录：真值库总数（truths）、节点数（nodes）、审计日志数
- 禁止：SSH / scp / sftp / rsync over ssh（P0-SUPREME 铁律）

### ② 获取归档规则
- 读取 `ZONGYUAN-ROOT/config/gateway-report-rules.md`（V3.0 实测版）
- 必记字段：truth_key / truth_value / source_node / confidence / truth_type
- 有效 truth_type 9 类：meta_law / rule / config / decision / data / creative / risk / protocol / unknown

### ③ 构建断点台账（manifest.json）
- 文件名规范：`<项目>-<N>CHAPTER-BREAKPOINT-MANIFEST.json`
- 必含字段：manifest_id / title / did / trace / archive_node / baseline / chapters[] / asset_totals / integrity
- chapters[] 每章必含：cid / title / asset_type / core_elements / palette / media_spec / plot_summary / image_urls[] / video_url / video_status
- integrity 初始：merkle_parent + hash_chain=PENDING_FILL

### ④ 分批真值上报（限流控制核心）
- 单条请求：`POST https://www.huodouai.com/api/report/truth`
- 上报策略：**分批+节流**——每条真值独立请求、间隔 ≥1.5s、无并发风暴
- 每条必须 L0 校验通过（L0 天元法则：零雄性化/纯黑长发/东方纯粹/九头身/溯源刻印）
- 上报顺序：主台账 → 哈希链凭证 → 断点状态（如需）
- 回读校验：`GET /api/report/truths` 确认 truth_count 增长

### ⑤ 全域锁档
```bash
python3 <kunlun>/scripts/auto_lock.py \
  --dir <断点目录> --snap-id SNAP-<日期>-<项目>-BREAKPOINT \
  --did DID-BR-000002 --archive-node ZONGYUAN-ROOT/<子节点>
```
- 内部流程：环境预检 → 维度校验 → M2冷却 → full_pipeline → 飞书四端同步 → 断点自检
- 快照注册：kernel.json snapshot_lineage 追加（幂等，防重复）
- 内核哈希更新：M1 真值不变性校验
- 凭证落盘：`BREAKPOINT-RESUME-CREDENTIAL-<日期>.md`
- 四端同步：Wiki / Drive / Markdown / Base（集中配置 feishu_config.json）

## 四、限流防护规范
| 规则 | 说明 |
|---|---|
| 请求间隔 | 相邻上报 ≥1.5s，重大批次 ≥2s |
| 并发上限 | 单任务同时请求 ≤1，禁止并发风暴 |
| 失败退避 | 4 次重试，退避 2.5s×(attempt+1) |
| 成功判定 | `success:true` 或 `status in (ok,success)` |
| 报警阈值 | 连续 5 次失败即停止并人工介入 |

## 五、验收清单
- [ ] 云端握手 200 且 version=V3.0
- [ ] 台账 manifest 含四要素（URL/元素/元数据/哈希链）
- [ ] 每条真值 L0 校验 17/17 通过
- [ ] 真值库 count 单调增长、回读可确认
- [ ] 内核快照谱系新增且 M1/M2/M3 PASS
- [ ] 锁档凭证落盘、断点自检 PASS
- [ ] 全程未触发限流报警

## 六、关联文件
- 规则源：`ZONGYUAN-ROOT/config/gateway-report-rules.md`
- 元法则：`kunlun-autonomous-system/references/l0_axioms.json`
- 内核：`kunlun-autonomous-system/ZONGYUAN-ROOT/Ω-Brainμ/kernel.json`
- 配置：`kunlun-autonomous-system/references/feishu_config.json`

---
溯源刻印：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜SOP-V1.0 已固化于 ZONGYUAN-ROOT 自治内核

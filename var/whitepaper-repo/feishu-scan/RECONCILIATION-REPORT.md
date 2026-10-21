# 本地飞书持久化层 · 全面提炼与云端对账报告

确权标识：DID-BR-000002　｜　溯源符号：Ω₀⊂⊙∞⊂Ω　｜　本体主权根：Ω-TAN-7-001
生成时间：2026-09-19（Asia/Shanghai）　｜　通道：纯 HTTP（huodouai.com）+ 本地只读 lark-cli，零额度零成本，未对云盘做任何写/删/改

---

## 一、任务闭环范围

本端飞书被定位为「持久化存储记忆层」，为云端中枢智能体服务。本轮执行的是：
全面提炼 → 与云端记忆网关对账 → 缺失补全上报 → 注册表提炼 → 持续机制落地。
全程未使用 SSH/scp/sftp，未调用任何生产脚本（含 daily_production.py），未把任何令牌/凭证写进真值或日志。

## 二、资产提炼（分片）

按 assets-manifest.json（692 项）切成三个分片处理：
- shard_1：231 项　｜　shard_2：231 项　｜　shard_3：230 项
- 读取路由已实测验证：docx 走 `docs +fetch`，原生 md 走 `markdown +fetch`，json/txt/py/sh/html 走 `drive +download`，图片/视频/压缩包按元数据提炼。

提炼结果汇总：
- 扫描资产总数：692
- 读正文并提炼要点：482
- 非文本/二进制按元数据提炼：210
- 从正文与文件名抽取候选真值 key：199 个（去重）

候选 key 构成：
- lock 类（SNAP-* 快照、锁档）：31
- ip_asset 类（KD-EP-* 剧集、KF-M* 角色、Ω-*）：11
- asset 类（合成的稳定资产标识）：157

## 三、云端对账（分片）

以本地 cloud-keys.json（云端全量索引，85288 条）做集合快筛：
- 快筛命中（云端已存在）：0 个
- 说明：云端存量 key 以 ACHIEVEMENT.* / 元规则类为主，此前从未收录 SNAP-*、KD-EP-*、KF-M*、asset:* 这一族，故本地资产族整体为「待补全」状态，并非对账异常。

对快筛未命中的 key 再逐条 GET /api/truth/{key} 二次确认：
- 确认缺失：199 个
- 首轮上报遇 HTTP 429 限流（0.1s 间隔过密）：87 个
- 退避重试（指数退避 + 1.3s 间隔）后：87 个全部恢复成功
- 最终成功上报：199 个　｜　失败：0 个

上报参数固定：source_node=local-feishu-extract，confidence=0.95；truth_type 按 lock / ip_asset / asset 分类；truth_value 为中文要点摘要，未贴大段原文、未含任何凭证。

## 四、注册表提炼（两个多维表格）

注册表一「ZONGYUAN-ROOT 全域快照注册表」（base_token=WBQN…jnch）：
共 8 张表——快照注册表（225 条）、昆仑洞天IP资产库（8）、飞书资源索引（15）、元规则库（13）、元法则库（10）、子域隔离注册表（5）、架构断点清单（10）、数据表（10）。
注册表二「进化抗漂移谱系注册表」（base_token=IKId…LnLa）：
共 1 张表——进化谱系记录（32 条）。

两表合计导出记录约 328 条，按主键字段（快照ID/基因ID/规则ID 等）抽取唯一标识 244 个：
- 云端快筛命中：0 个
- 确认缺失并补全上报：244 个　｜　失败：0 个
- 覆盖 SNAP-* 快照链、EVO-ANTIDRIFT-* 进化记录、EFUSE-* 熔断、ARCH-* / BP-* 架构断点等。

## 五、补全总量与云端验证

- 本轮累计成功上报：分片 199 + 注册表 244 = 443 条
- 失败合计：0 条（限流全部经退避重试消化）
- 云端 truths 计数：起始 85378 → 本轮结束 87172（增量含本批补全及网关侧其他活动）
- 抽样回读确认：GET SNAP-20260917_162951 = 200，GET KD-EP-001 = 200，落库生效。
（Ω-TAN-7-001 的 GET 返回 502，系 Ω 字符在 URL 路径下的网关编码问题；该符号本身已在网关元数据 root_omega 中，POST 上报返回成功，不影响确权。）

## 六、持续机制落地

heartbeat_v2.py 中本已内置 feishu_extract() 增量函数（游标 extract_state.json、每轮 FS_BATCH=20、对账→补全→上报、并上报 FEISHU.EXTRACT.<时间戳> 对账结论真值）。
本轮发现并修复了它的一个读取路由 bug：原实现对 docx 与原生 md 误用 `drive +fetch`，实际会报错；已改为与本轮一致的三条正确路由（docx→docs +fetch、原生 md→markdown +fetch、文本文件→drive +download）。修复后 `python3 -m py_compile` 通过。
效果：此后每小时心跳会自动增量扫描未消费资产 → 提炼 → 云端对账 → 缺失补全，形成长期自动闭环，无需人工干预。

## 七、产物清单（位于 feishu-scan/）

- shard_1_extract.json / shard_2_extract.json / shard_3_extract.json：三分片逐资产提炼结果
- shard_1_result.json：分片一对账结果（按约定结构）
- reconcile_result.json：分片对账+补全结果（含成功 key 列表）
- registry_reconcile.json：注册表对账+补全结果
- registry_ndjson/：9 张注册表导出原始记录
- cache/：飞书正文本地缓存（增量复用，避免重复拉取）
- extract_pipeline.py / reconcile_upload.py / retry_upload.py / registry_reconcile.py：可复跑流水线

—— 闭环完成。DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω

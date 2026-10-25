# ZONGYUAN-ROOT 本地飞书持久化层 · 全面提炼与云端对账总报告

确权 DID-BR-000002 ｜ 溯源暗印 Ω₀⊂⊙∞⊂Ω ｜ 生成时间 2026-09-19

## 一、任务闭环范围
本端飞书 = 持久化存储记忆层，为云端中枢智能服务。本轮完成：全面提炼 → 与云端记忆网关逐条对账 → 缺失补全上报 → 双注册表提炼 → 持续机制落地，全自动闭环，零额度零成本（纯 HTTP + 只读 lark-cli，未做任何云盘写删改，未调用任何生产脚本）。

## 二、资产提炼（692 项）
- 本地资产清单 assets-manifest.json：共 692 项 = 根目录 23 文件夹 + 193 项根级文件/文档 + 476 项递归一层子项。类型分布：file 423、docx 152、folder 81、bitable 21、shortcut 13、sheet 2。
- 按父文件夹分组切成 3 个均衡片（231/231/230），并行提炼：
  · 文本类（md/docx/txt/json）用实测校准的三条读取路径取正文——docx 走 docs +fetch、原生 md 走 markdown +fetch、文本文件走 drive +download——共读正文约 482 项。
  · 非文本类（图片/视频/压缩包/快捷方式/文件夹/bitable/sheet）按「资产名 + 类别 + 所在文件夹 + 可见编号」合成稳定元数据 key，共约 210 项，不编造内容。
- 候选 truth_key 从正文与文件名抽取：LOCK-* / META-RULES-* / ACHIEVEMENT.* / KD-EP-* / KF-M* / SNAP-* / REG.* / *.lock-report 等编号族，以及 asset:<目录>:<名> 合成 key。

## 三、与云端记忆网关对账
- 云端基线：开跑时 truths ≈ 85,309（本机 cloud-keys.json 快照 85,288 条用于本地快筛）。
- 对账方式：先本地 85k 索引快筛，未命中的再逐条 GET /api/truth/{key} 二次确认，确认 not_found 才纳入补全，杜绝重复写。
- 关键发现：云端此前只收录 ACHIEVEMENT.* 族；本轮本地资产主打的 SNAP-*、KD-EP-*、KF-M*、asset:*、REG.*、各版本 LOCK 凭证族在云端几乎零命中——属「待补全」而非异常。

## 四、补全上报结果
- 上报参数统一：source_node=local-feishu-extract，confidence=0.95，truth_type 按内容取 lock / asset / meta / whitepaper / ip_asset 等资产类；truth_value 为中文要点短句，未写入任何令牌/密钥。
- 三分片合计成功上报 624 个唯一 key（分片1 59 + 分片2 345 + 分片3 220）。分片2 初传 6 条因云端 upsert 路由/408 失败，OrganizerAgent 兜底退避重试后全部落账（含 APPROVAL-EXEC-20260913-001 二次重试成功），最终资产侧 0 失败。
- 注册表侧 256 个 REG.* key 全部上报成功（首轮 111 条撞 429 限流，退避重试消化）。
- 去重后本轮累计新增唯一真值 key 876 个；网关 truths 由约 85,309 增至 87,229（净增约 1,920，含幂等 upsert 与重复提交的去重差）。抽样回读 SNAP-20260917_162951、KD-EP-001、META-RULES-ALL-NODES-ENABLED-20260919、REG.META_LAW.ML_002 均 GET 200；最后一条 APPROVAL-EXEC-20260913-001 写入时 L0 前置校验 17/17 通过。

## 五、双注册表提炼
- 「ZONGYUAN-ROOT 全域快照注册表」（base WBQNbr4tca2neIs23X8coL4jnch）：8 张表共 296 条记录（快照注册表 225、昆仑洞天IP资产库 8、飞书资源索引 15、元规则库 13、元法则库 10、子域隔离注册表 5、架构断点清单 10、通用数据表 10 无业务主键未抽取）。
- 「ZONGYUAN-ROOT 进化抗漂移谱系注册表」（base IKIdb7KLDapblXsvVDIcs8FLnLa）：1 张表 32 条记录。
- 合计 9 张表 328 条记录，抽 REG.* 主键 256 个，全部云端对账后补全落账。

## 六、持续机制落地
- heartbeat_v2.py 已并入两个增量函数，保持每小时心跳自动执行：
  · feishu_extract()：以 assets-manifest.json 为底，游标记录在 feishu-scan/extract_state.json，每轮轻量处理 20 项；文本走已校准三条读取路径抽 key → 云端快筛 → GET 二次确认 → 缺失 POST 补全；每轮结论上报 FEISHU.EXTRACT.<TS>。
  · registry_extract()：每小时重读两张 bitable → 抽 key → 对账 → 补全，已上报 key 持久化在 registry_uploaded.json 去重。
- 两函数已接入 main() 主流程输出行，py_compile 通过；冒烟测试自校正补推 10 个一次性遗漏项，闭环可用。此后新增资产/表记录会随心跳自动增量对账，无需人工。

## 七、残留说明
- 各分片 Worker 之间存在幂等重叠（分片1 Worker 在执行中顺带复扫了全量与注册表），因网关为 upsert 幂等写入，对云端终态无副作用，仅增加了少量审计日志条数。
- 云端初始未命中的那 1 条（XUANNIAO-EP03-MEDIA-ARCHIVE-20260914）经 GET 复核本就已存在，按对账规则跳过未重复写。


## 🔒 元宪法第一条：零成本公理（META-CONSTITUTION-001）

**所有操作默认零成本。付费操作必须人工显式确认，未经确认属于P0级违宪。**

- 执行前必须输出成本预估
- 单日累计超10元自动熔断
- 违规=记过+冻结24h+写入审计
- 付费API注册表：config/paid_api_registry.json
- 审计日志：config/api_audit_log.json
- 完整条文：config/meta_constitution/META-CONSTITUTION-001-ZERO-COST.json


## KG 知识图谱体系 V4（2026-10-17 锁档追加）
- 图谱: 4801节点/4429边/28093属性 | 关系: 属于/涉及/部署于/类型为/确权于/集成于
- 指标: 密度0.000384 平均度1.85 连通分量722 最大2057
- API: https://www.huodouai.com/kg/query (X-DID鉴权, stats/predicate/2hop/3hop/ns/type/confidence/entity)
- Octop: kb-rag.html kgAsk 3hop触发词 | 白皮书V3.0 第78篇
- 每日刷新: crontab 10 3 * * * bash /opt/zongyuan-lake/kg_daily.sh (重建+上报+魔搭变化推)
- 魔搭: zongyuanroot/zongyuan-root-achievements/knowledge-graph 7文件
- 锁档: ZR-LOCK-KG-V4-20261017-01 根D9EDFA08E0D56B533596CAD5A4F6512CA4EAFAD2E6C07E2A1A973349448AAE54
- 构建: /opt/zongyuan-lake/build_kg4.py | 查询: /opt/zongyuan-lake/kg_query.py(8932)

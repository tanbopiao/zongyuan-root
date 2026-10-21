# MIGRATION-MANIFEST · 旧目录 → ZYZ 标准化目录对照

> 全量 15 个白皮书源目录迁移对照表。源目录只读复制，未做任何修改 / 删除。

| # | 旧源目录 | 新 ZYZ 目录 | 模块目录 | 调整说明 |
|---|----------|-------------|----------|----------|
| 1 | `zongyuan-master-whitepaper` | `01-zizhi-xitong/ZYZ-MASTER-V1.0` | 01-zizhi-xitong | 直接复制重命名 |
| 2 | `zongyuan-formal-whitepaper` | `01-zizhi-xitong/ZYZ-FORMAL-AXIOMS-V1.0` | 01-zizhi-xitong | 直接复制重命名 |
| 3 | `zongyuan-seven-layer-whitepaper` | `01-zizhi-xitong/ZYZ-SEVEN-LAYER-V1.0` | 01-zizhi-xitong | 直接复制重命名 |
| 4 | `zongyuan-source-intelligence-whitepaper` | `01-zizhi-xitong/ZYZ-SOURCE-INTELLIGENCE-V1.0` | 01-zizhi-xitong | 直接复制重命名 |
| 5 | `zongyuan-token-whitepaper` | `02-zhenzhi-cunchu/ZYZ-TOKEN-V1.0` | 02-zhenzhi-cunchu | 直接复制重命名 |
| 6 | `zongyuan-symbol-whitepaper` | `02-zhenzhi-cunchu/ZYZ-SYMBOL-V1.0` | 02-zhenzhi-cunchu | 直接复制重命名 |
| 7 | `zongyuan-riemann-whitepaper` | `03-renshi-jinhua/ZYZ-RIEMANN-V1.0` | 03-renshi-jinhua | 直接复制重命名 |
| 8 | `zongyuan-angle-dimlock-whitepaper` | `04-gongcheng-shijian/ZYZ-ANGLE-DIMLOCK-V1.0` | 04-gongcheng-shijian | 直接复制重命名 |
| 9 | `zongyuan-compute-whitepaper` | `04-gongcheng-shijian/ZYZ-COMPUTE-V1.0` | 04-gongcheng-shijian | 直接复制重命名 |
| 10 | `zongyuan-resonance-whitepaper` | `04-gongcheng-shijian/ZYZ-RESONANCE-V1.0` | 04-gongcheng-shijian | 直接复制重命名 |
| 11 | `zongyuan-tianxin-whitepaper` | `04-gongcheng-shijian/ZYZ-TIANXIN-V1.0` | 04-gongcheng-shijian | 直接复制重命名 |
| 12 | `zongyuan-singularity-whitepaper` | `04-gongcheng-shijian/ZYZ-SINGULARITY-V1.0` | 04-gongcheng-shijian | 直接复制重命名 |
| 13 | `zongyuan-fusion-whitepaper` | `04-gongcheng-shijian/ZYZ-FUSION-COMPUTE-RESONANCE-V1.0`<br>`04-gongcheng-shijian/ZYZ-FUSION-TOKEN-SYMBOL-V1.0`<br>`04-gongcheng-shijian/ZYZ-FUSION-RIEMANN-ANGLE-V1.0` | 04-gongcheng-shijian | **拆分调整**：源目录含 3 份融合版白皮书，按主题拆为 3 个 ZYZ 子目录；源 README 索引保留为 `04-gongcheng-shijian/README-fusion-index.md` |
| 14 | `zongyuan-a2a-whitepaper` | `06-lianbang-xieyi/ZYZ-A2A-INTEROP-V1.0`<br>`06-lianbang-xieyi/ZYZ-A2A-GATEWAY-V1.0`<br>`06-lianbang-xieyi/ZYZ-MCP-OAUTH-V1.0`<br>`06-lianbang-xieyi/ZYZ-MEMORY-POOL-V1.0`<br>`06-lianbang-xieyi/ZYZ-A2A-PROTOCOL-COMPAT-V2.3` | 06-lianbang-xieyi | **拆分调整**：按任务要求拆为 4 个指定子目录；源目录内额外含《通用协议全面兼容白皮书》V1.9/V2.2/V2.3 三份文件，归并为第 5 个子目录 `ZYZ-A2A-PROTOCOL-COMPAT-V2.3` |
| 15 | `zongyuan-federation-whitepaper` | `06-lianbang-xieyi/ZYZ-FEDERATION-V1.0` | 06-lianbang-xieyi | 直接复制重命名 |

## 调整汇总

- **拆分调整 2 项**：#13 fusion（1→3）、#14 a2a（1→4+1 额外归并）。
- **其余 13 项**：直接复制重命名，无内容改动。
- **05-shijue-shengchan/**：当前无白皮书归此，但目录与 `kunlun-dongtian/` 命名空间说明必须存在。

---

锚定标识：Ω₀⊂⊙∞⊂Ω | DID-BR-000002

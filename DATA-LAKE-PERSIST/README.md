# 本地持久层数据湖 LOCAL-PERSIST-DATA-LAKE V1.0
DID-BR-000002 | 2026-09-30

## 定位
承载所有本地持久资产的统一登记与归档规范。**媒体物理文件仅存 LOCAL-PERSIST-MEDIA（不推 Git），数据湖登记引用+指纹；文本内核（索引/清单/账本）推 Gitee+GitHub 双副本。**

## 分层规范
| 层 | 用途 | 内容 |
|---|---|---|
| 00-raw | 原始采集/上传层 | 原始镜像、原始上传、未处理素材 |
| 01-curated | 整理层 | 去重、清洗、分类后数据 |
| 02-refined | 成品层 | 确权资产、锁档文档、成品包 |
| 03-index | 索引层 | MANIFEST-LAKE.json、目录清单 |
| 04-media-registry | 媒体登记层 | MEDIA-REGISTRY.json（引用+sha256） |
| 05-ledger | 账本层 | HASH-LEDGER 联动、确权指纹 |

## 资产登记规范
1. 每次新资产归档：登记 `03-index/MANIFEST-LAKE.json`（或追加 media 域）
2. 媒体资产（>2MB）：仅登记 rel_path + size + sha256，物理文件入 LOCAL-PERSIST-MEDIA/<域>/
3. 文本内核：同步追加 HASH-LEDGER.csv + memory_index.json，推 Gitee/GitHub
4. 资产指纹：sha256 全量计算，登记于 MEDIA-REGISTRY.json

## 当前湖内资产（2026-09-30）
| 域 | 文件数 | 体积 |
|---|---|---|
| unified-image-archive | 265 | 228.6MB |
| zongyuan-root | 44 | 82.7MB |
| kunlun-assets | 33 | 52.0MB |
| zongyuan-total(含网站备份) | 7 | 16.7MB |
| zongyuan-governance | 5 | 0.8MB |
| frontier-tech-page | 2 | 0.2MB |
| **合计** | **356** | **380.9MB** |

## 网站全量备份锚点
- 备份包: LOCAL-PERSIST-MEDIA/zongyuan-total/site-backup-20260929/site-backup-huodouai-20260929.tar.gz (16MB)
- SHA256: ade611c0c8489d04b5e6010b9a1a0784d0297c488c455b086cc6f3813b78a824
- 文件清单: MANIFEST-FILES.txt (434条)

## 规则
- 大体积媒体仅本地保存，不推 Git（LOCAL-PERSIST-MEDIA 已 gitignore）
- 固化资产只读锁档 RO-444
- 确权标识: DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω

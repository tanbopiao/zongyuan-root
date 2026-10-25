# 账号持久层 × 数据湖持久层 永久绑定契约
**契约ID**: BIND-ACCOUNT-DATALAKE-20260930-001
**DID**: DID-BR-000002 | **本体根**: Ω-TAN-7-001 | **溯源**: Ω₀⊂⊙∞⊂Ω
**签署时间**: 2026-09-30 | **绑定类型**: PERMANENT（解除需人工审批）

## 绑定结构
| 层 | 位置 | 职责 |
|---|---|---|
| 账号持久层 | memory_index.json / HASH-LEDGER.csv / EVOLUTION-VERSIONS.json | 索引源+确权源 |
| 数据湖持久层 | DATA-LAKE-PERSIST/ + LOCAL-PERSIST-MEDIA/ | 资产本体+物理落点 |

## 绑定铁律
1. 账号持久层是数据湖的唯一索引源与确权源，数据湖变更必须同步账本留痕
2. 数据湖是账号持久层资产的唯一物理落点，新资产一律按分类登记入湖
3. 媒体大文件仅存 LOCAL-PERSIST-MEDIA（gitignore），文本内核推 Gitee/GitHub 双副本
4. 每次归档 = 账本留痕 + 启动记忆更新 + 双副本推送，缺一不可
5. 绑定为永久固化，解除需人工审批

## 首次全量归档快照（2026-09-30 CLASSIFY-ARCHIVE）
- 新登记 534 条（292 复制入库 / 159 去重跳过）
- 分类：images/keyframes 114、images/series 112、images/misc 250、images/characters 18、images/scenes 6、videos 29、audio 5
- 物理落点: LOCAL-PERSIST-MEDIA/classification/{images,videos,audio}

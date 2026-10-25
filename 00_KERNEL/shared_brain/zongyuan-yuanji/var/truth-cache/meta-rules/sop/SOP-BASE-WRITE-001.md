# SOP-BASE-WRITE-001 ｜ 飞书共享大脑 Base 写入 SOP
版本：v1.0 ｜ 锚定：DID-BR-000002 ｜ 学习来源：真值共识区/上报总表写入实战

## 一、连接
- Base token：`DgnMbLqZiaIUDKshqCrcD4DvnBg`（**逐字使用**，勿手抄/缩写）
- 身份：一律 `--as user`（不用 app/bot 模式）
- 入口：`lark-cli base +url-resolve`（链接）或直用 token；列表用 `+table-list`

## 二、目标表（共享大脑核心表）
| 表 | table_id | 关键字段与选项 |
|---|---|---|
| 真值共识区 | tbl9QxL35rwA16eS | 真值key(text) / 真值内容(text) / 确认节点(text) / 异议节点(text) / 最终状态(select: 待确认/已达成共识/有争议) |
| 上报总表 | tbl524eo7FnEa8ht | cloud_key(text) / payload(text) / data_cat(text) / report_utc(datetime) / source_node(text) / dispatch_status(select: pending/synced/failed) / security_level(select: public/internal/confidential) / hash_sha256 / feishu_doc_url |
| 元法则体系 | tblK76kQZdKmcJao | 元法则注册（法则沉淀） |
| 决策日志 | tblFQTgWkJQR6Xwp | 决策记录 |

## 三、写入流程（先学习后写入）
1. **写前**：`+field-list` 确认目标表字段与 select 选项（禁止写入未知选项）
2. **构造**：每条记录 = 字段名→值；select 用已确认选项名
3. **写入**：`+record-batch-create --json '{"create_records":[...]}'`，单批 ≤200 条
4. **回读验证**：`+record-list` 确认条数与关键字段（写成功 ≠ 完成，必须回读）
5. **批量规则**：连续写同表串行执行；1254291 冲突短暂等待重试

## 四、成果写入规范（真值共识区）
- key 幂等唯一：`<domain>.<事件>.<时间戳>`
- 确认节点：NODE-DEV-DOUBAO-WORK-001
- 最终状态：已达成共识（验证后）｜ 待确认（存疑）
- 上报总表：dispatch_status=synced；security_level=internal（内部成果）

## 五、学习要点（历史教训）
1. 写 select 前必须确认选项（未知选项触发平台新增，非本意）
2. 多行文本：JSON 参数用 \n 转义，裸 flag 用真实换行 $'...'
3. datetime 格式：YYYY-MM-DD HH:mm:ss
4. 回读是唯一验收标准（record_id 返回 ≠ verified）

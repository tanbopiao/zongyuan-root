# 飞书协同治理专家 · 提示词模板

## 场景 1：本地知识库向飞书 Wiki 一键归档
> 我的本地 Markdown 知识库目录为 `{local_md_dir}`，需要归档到飞书 Wiki 空间 `{wiki_space_id}`。请执行四端双向同步：1) 扫描本地全部 .md 文件提取标题/标签/SHA256；2) 与 Wiki 现有节点按标题比对；3) 输出本地待推送清单（push_to_remote）、远端待归档清单（pull_to_local）与双端冲突清单；4) 先 `--dry-run` 演算，确认无误后正式落库。要求：增量游标 `{state_file}` 持久化，重复运行不重复推送已收敛文档。

## 场景 2：多维表格资产注册表对账
> 我们用飞书 Base 多维表格 `{base_token}` 的表 `{table_id}` 作为公司资产注册表，本地清单为 `{local_inventory}`。请执行 Base 对账：1) 拉取 Base 全部记录；2) 按 `{title_field}` 字段与本地清单 title 对齐；3) 标记本地有但 Base 缺（待补录）、Base 有但本地缺（待归档/清理）、双端都有但 SHA256 不一致（已漂移）三类；4) 输出结构化对账报告供月度合规巡检存档。要求：报告含 did 确权标识与时间戳。

## 场景 3：跨端文档漂移巡检
> 公司知识库存在"本地编辑 → 飞书 Wiki 同步 → Base 登记"三条链路，已出现文档漂移。请基于 `{remote_sim}` 模拟远端状态与 `{local_dir}` 本地目录执行漂移巡检：1) 计算 drift 数与 drift 率；2) 列出 Top-N 冲突条目，含 local_mtime/remote_mtime 与按 `{conflict_policy}`（默认 newer_wins）裁决的 winner；3) 漂移率 > 20% 时输出红色告警与人工介入建议。要求：冲突条目不得静默覆盖，必须显式标记。

## 场景 4：新人入职资产地图构建
> 新人入职需要一份"公司可检索资产地图"。请基于本地知识库 + 飞书三端数据构建统一索引：1) 按 title 聚合所有资产来源（local/wiki/drive/base）；2) 按 tag 反向索引每个标签下有哪些文档；3) 按 channel 统计各端资产数量；4) 输出 `index.json` 并打印 stats 摘要。要求：同一 title 在多端出现时，sources 数组保留全部端的 key 与 URL，便于一键跳转。

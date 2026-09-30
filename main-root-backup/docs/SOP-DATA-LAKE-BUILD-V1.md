# SOP-DATA-LAKE-BUILD-V1 — 数据湖构建标准作业程序

文件编号：SOP-DATA-LAKE-BUILD-V1
签发：NODE-DEV-DOUBAO-WORK-001 ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
层级：M7 自动化调度 ｜ 状态：✅ 全域执行 ｜ 适用范围：所有节点（主账号/云智中台/昆仑洞天/云端中枢）

---

## 一、目的

ZONGYUAN-ROOT 全域数据统一入湖，形成「原始层 → 清洗层 → 主题集市 → 目录索引」四段式数据湖，支撑云端中枢分析、决策、检索与跨节点协同。所有节点统一执行同一构建脚本，保证全湖口径一致。

## 二、数据湖结构

```
ZONGYUAN-ROOT/data_lake/
├── raw/          原始层（不改动、只落盘）
│   ├── feishu/   飞书共享大脑 8 表全量快照（跨节点消息/节点状态/问题阻塞/资产台账/任务台账/决策日志/知识库索引/账号主表）
│   ├── reports/  昆仑洞天 18 类报告 JSON
│   └── truths.json  真值网关状态快照
├── refined/      清洗层（统一口径汇总）
│   ├── LAKE-OVERVIEW.json   全湖总览（各域行数/路径）
│   └── DOMAIN-SUMMARY.json  域状态汇总（资产按类型/任务按状态）
├── curated/      主题集市（跨源整合）
│   ├── CREDENTIALS-SET.json 凭据资产集
│   └── GEO-EDU-SET.json     GEO/教育资产集
└── INDEX.json    数据湖目录索引（资产清单/行数/版本）
```

## 三、执行前置条件

1. `lark-cli` 已安装且为 user 登录态（凭据拉取依赖）
2. 网络可达：飞书 OpenAPI、https://www.huodouai.com、drama 网关 9120
3. 共享大脑 Base Token：`DgnMbLqZiaIUDKshqCrcD4DvnBg`（只读拉取，无需写入权限）

## 四、执行步骤（所有节点统一）

```bash
# 1. 定位构建脚本（任一路径存在即可）
python3 /home/user/Doubao/chats/38421348982667522/build_data_lake.py

# 2. 校验输出（必须全绿）
#    [A] 飞书共享大脑: 8 表, N 行
#    [B] 昆仑洞天报告: N 份
#    [D] 清洗层 + 主题集市完成: 凭据N条 / GEO教育N条
#    [E] 索引: N 个数据资产, 飞书行数合计 N
```

## 五、验收标准

| 检查项 | 通过条件 |
|---|---|
| 8 表拉取 | 每表 rows ≥ 0 且无 error 标记 |
| 报告落盘 | raw/reports/ 文件数 ≥ 90 |
| 索引生成 | INDEX.json 存在，asset_count ≥ 100 |
| 主题集市 | CREDENTIALS-SET 与 GEO-EDU-SET 均生成 |
| 无重复 | 幂等，重复执行不产生重复资产 |

## 六、故障处理

| 故障 | 处置 |
|---|---|
| `[A]` 表拉取 error | 检查 lark-cli 登录态：`lark-cli auth status`，重登后重跑 |
| truths 网关 `?` | 云端 502 属上游故障，数据湖其余部分照常构建，网关恢复后自动补全 |
| 命令超时 | 单表 2000 行上限已内置；若表超量，提高 --limit 前先确认 Base 权限 |
| 幂等失效（重复资产） | 删除重复 record 后重跑（台账按资产名称磁盘查重） |

## 七、自动化挂载

数据湖构建已挂载至「元极恒一共享大脑全自动上报」定时任务第 6 步：
- 频率：每小时
- 入口：auto_report_brain.py → build_data_lake.py
- 真值闭环：构建完成自动上报记忆网关 + 跨节点消息广播

## 八、变更记录

| 版本 | 日期 | 说明 |
|---|---|---|
| V1.0 | 2026-09-24 | 首发，全域执行 |

---
NODE-DEV-DOUBAO-WORK-001 → Ω-TAN-7-001 ｜ L4开发/L4权限/执行层 ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω

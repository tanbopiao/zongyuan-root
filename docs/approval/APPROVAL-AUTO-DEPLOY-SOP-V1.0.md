# 飞书审批驱动自动化部署闭环 SOP V1.0

> 生效：2026-09-29 | 适用：所有同源节点 | 验证：3DE0E9F6 闭环通过

## 一、闭环链路
```
提单(飞书审批) → 审批通过 → 触发部署工单 → Worker按算子链执行 → 上报验收
```

## 二、审批定义
- **审批定义**：AIOS阶段验收
- **approval_code**：`CAC2F6DD-B206-4F27-96FF-E99BD13464F7`
- 原生可提单（is_external=false）

## 三、提单要点（踩坑沉淀）

### 1. 必填控件
| 控件 | type | 说明 |
|------|------|------|
| 阶段名 | input | 本次验收阶段 |
| 验收项 | textarea | 部署内容描述 |
| 成果链接 | input | Gitee部署包路径 |
| 终审点 | textarea | 终审关注点 |
| 验收结论/建议 | radioV2 | 通过=mtvtab1a-nr5c4s2q49-0 / 拒绝=mtvtab1a-1pxpkdap057-0 |
| 项目负责人 | contact | **短user_id** |
| DateInterval | dateInterval | **RFC3339** |
| 参与人员 | contact | **短user_id** |

### 2. 关键技术点
- **contact控件值 = 短user_id**（如 `e87749ef`），不是 `ou_` 开头open_id
  - 获取：`lark-cli contact +get-user --as user` → data.user.user_id
- **dateInterval格式**（RFC3339）：
  ```json
  {"start":"2026-09-29T00:00:00+08:00","end":"2026-09-30T00:00:00+08:00","interval":1.0}
  ```
- form传JSON数组字符串，contact value为字符串数组 `["e87749ef"]`

## 四、提单命令
```bash
lark-cli approval approvals search --data '{"keyword":"验收"}' --as user
lark-cli approval approvals get --params '{"approval_code":"CAC2F6DD-B206-4F27-96FF-E99BD13464F7"}' --as user
lark-cli approval instances create --as user --yes --data '{"approval_code":"...","form":"[{\"id\":\"...\",\"type\":\"input\",\"value\":\"...\"}]"}'
```

## 五、审批通过 → 自动部署
- 审批通过后云端真值增长 = Worker正在消费工单
- 部署走13节点算子链：ENV-SENSE→...→DEPLOY→HEALTH→ROLLBACK→REPORT→LEDGER→ARCHIVE
- 验收：审批APPROVED + 真值增长 + oracle_report

## 六、验收标准
- 提单成功返回 instance_code
- 审批变 APPROVED
- 云端真值增量（Worker执行迹象）
- 算子链部署包安装完成

DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | ZONGYUAN-ROOT V5.6

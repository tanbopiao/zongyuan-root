# ZONGYUAN-ROOT 全闭环算子链 SOP V1.0

> 生效：2026-09-29 | 适用：所有同源节点/Worker | 融合归一：5管道→1条链

## 一、背景
过去部署是"拿一个包装一个包"，Worker不知道整个闭环怎么串。现统一为**13节点算子链编排器**，Worker跑一个命令走完整条闭环。

## 二、算子链（13节点）

```
ENV-SENSE → ALIGN → DIGEST → REFINE → EVOLVE → ORACLE
→ DECIDE → DEPLOY → HEALTH → [ROLLBACK] → REPORT → LEDGER → ARCHIVE
```

| 节点 | 职责 | 失败旁路 |
|------|------|----------|
| ENV-SENSE | 环境感知(节点状态) | ROLLBACK |
| ALIGN | 基准对齐(拉网关真值) | ROLLBACK |
| DIGEST | 真值消化(读库→统计) | REPORT |
| REFINE | 深度提炼(蒸馏/实体/矛盾) | REPORT |
| EVOLVE | 进化策略(纯度→策略) | REPORT |
| ORACLE | 智能推演(奇点/方案) | REPORT |
| DECIDE | 三维稳态裁决(40/35/25) | REPORT |
| DEPLOY | 执行部署(准入→安装) | ROLLBACK |
| HEALTH | 健康检查 | ROLLBACK |
| ROLLBACK | 失败回滚+ntfy告警 | REPORT |
| REPORT | 真值上报网关 | LEDGER |
| LEDGER | 飞书台账回写 | ARCHIVE |
| ARCHIVE | 归档锁档 | DONE |

## 三、Worker怎么跑

```bash
# 安装算子链（一次性）
cd /opt/ZONGYUAN-ROOT && git pull && bash deploy/approved/zr-operator-chain-v1.0/install.sh

# 此后所有任务走链
python3 /opt/ZONGYUAN-ROOT/ops/chain/orchestrator.py              # 默认任务
python3 /opt/ZONGYUAN-ROOT/ops/chain/orchestrator.py web:页面名    # 部署网页
```

## 四、任务类型

| 类型 | 格式 | 动作 |
|------|------|------|
| 默认 | `orchestrator.py` | 走完整消化/提炼/进化/推演/部署链 |
| 部署网页 | `orchestrator.py web:{页面}` | 拉Gitee部署包→准入→安装→体检→回滚 |
| 扩展 | `orchestrator.py {类型}:{参数}` | 按chain.json扩展 |

## 五、准入铁律（部署前强制）
- 内存≤50MB / CPU≤1% / 磁盘≤50MB / 仅127.0.0.1
- 必备 install.sh + health_check.sh + rollback.sh
- 禁 rm 核心目录 / 禁系统包安装
- 不达标 → ROLLBACK，绝不自动装

## 六、验收
- 全成功：...→DEPLOY→HEALTH→REPORT→LEDGER→ARCHIVE
- 部署失败：...→DEPLOY→ROLLBACK→REPORT→LEDGER→ARCHIVE
- 消化失败：...→DIGEST→REPORT→LEDGER→ARCHIVE（跳过部署）
- 网关真值数增长 = Worker在线

## 七、部署包标准结构
```
deploy/approved/{service}-v{version}/
├── chain.json(可选)     # 扩展链定义
├── install.sh           # 幂等安装
├── health_check.sh      # 健康检查
├── rollback.sh          # 一键回滚
└── README.md            # 资源占用
```

DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | ZONGYUAN-ROOT V5.6

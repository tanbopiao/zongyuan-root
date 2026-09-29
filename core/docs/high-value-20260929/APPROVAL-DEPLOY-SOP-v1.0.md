# 飞书审批发起 SOP · 部署类任务强制走审批

> 来源：网关真值 architecture.APPROVAL-AUTO-CLOSEDLOOP-REGISTER / DUAL-IDENTITY-CLOSEDLOOP / TOKEN-BOUNDARY
> 学习时间：2026-09-13
> 触发条件：遇到任何部署类、高危函数执行、写入云端、重启服务、改配置的操作

---

## 一、完整审批闭环（已实测）

1. **本地发起**：lark-cli 以 **user 身份**（user_access_token，需 `approval:instance:write` 权限）发起审批单
2. **人工通过**：用户在飞书审批里点同意/拒绝
3. **登记 instance_code**：SSH 到云端执行 `register_approval.py`，把 instance_code 写入 `ops.approval.register` JSON 数组
4. **云端轮询**：command_router 用 **应用 tenant_access_token（不带 user_id）** 查询实例状态——注意不能带 user_id，否则 open_id cross app 报 99992361
5. **执行高危函数**：status=APPROVED 时执行部署/重启/写云端动作
6. **推回执卡片**：结果推回飞书群，闭环

## 二、关键边界（TOKEN-BOUNDARY）

- 审批**创建**只能用 user_access_token（本地 lark-cli user 身份）
- 云端 tenant_access_token **只有查询权限**，无写权限（写会报 99991663）
- 云端 create_approval 失败时，推卡片指引用户回对话窗口审批
- 已实测案例：CCFE9728 锁档单全链路通过，lock.log 写入 LOCK-20260911031450，群回执 om_x100b650454613ca0b265abd2517af58

## 三、当前两个待办（中枢侧）

- TODO-001：飞书事件订阅（卡片按钮回调）— pending，回调地址 http://123.207.202.158:8060/callback
- TODO-002：原生 approval/v4 API 权限验证（当前 99991663 token 错误，用交互式卡片兜底）

## 四、本节点触发规则

后续对话中遇到以下任一情况，**自动走审批流程**，不擅自执行：
- 部署新服务/重启 systemd 服务
- SSH 直写云端文件
- 改 iptables/防火墙
- 改调度密钥/鉴权凭证
- 删除/覆盖云端资产
- 任何影响 7 个生产 API 服务的动作

执行方式：
1. 在主节点（Lark 连接器开启时）用 lark-cli `approvals search → get → instances create` 发起
2. 等待用户飞书审批通过
3. SSH 登记 instance_code
4. 云端轮询通过后执行
5. 回执推群

沙箱节点（vefaas-sandbox-01）无 SSH 权限、Lark 连接器关闭时，只上报 operation_log 说明"本应发审批"，等主节点执行。

Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜ZONGYUAN-ROOT

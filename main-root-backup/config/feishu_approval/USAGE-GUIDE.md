# 飞书企业应用审批通道 使用规范

**部署日期：** 2026-09-22
**通道ID：** FEISHU-APPROVAL-ENTERPRISE-V1
**身份：** DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω

---

## 一、通道配置说明

### 配置文件
```
ZONGYUAN-ROOT/config/feishu_approval/
├── channel_config.json                # 通道配置（凭证+模板）
├── feishu_enterprise_approval.sh     # 审批发起脚本
└── approval_log.log                   # 审批日志
```

### 凭证配置步骤
1. 登录飞书开放平台：https://open.feishu.cn
2. 创建企业自建应用，获取 `app_id` 和 `app_secret`
3. 开通审批应用权限（approval:instance:write）
4. 在审批后台创建「技术部署审批」模板，获取 `approval_code`
5. 将三个凭证填入 `channel_config.json`：
   ```json
   {
     "credentials": {
       "app_id": "cli_xxx",
       "app_secret": "xxx",
       "approval_code": "xxx"
     }
   }
   ```

---

## 二、审批发起用法

### 命令格式
```bash
bash feishu_enterprise_approval.sh \
  --title "昆仑洞天三态合一自动归档部署" \
  --type "自动化脚本" \
  --desc "部署三态握手钩子、视频归档脚本、定时巡检，共10个文件" \
  --risk "低"
```

### 参数说明
| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| --title | ✅ | 部署标题 | 昆仑洞天三态合一自动归档部署 |
| --type | ✅ | 部署类型 | 自动化脚本 / 系统上线 / 配置变更 / 数据归档 |
| --desc | ✅ | 部署说明 | 详细描述部署内容 |
| --risk | ❌ | 风险等级 | 低 / 中 / 高（默认低） |

---

## 三、审批闭环流程

```
Step1: 获取 tenant_access_token（企业应用身份）
Step2: 组装审批表单（标题/类型/说明/风险）
Step3: 调用飞书API发起审批实例
Step4: 记录 instance_code 到 HASH-LEDGER
Step5: 上报中枢智能真值
```

---

## 四、双模式覆盖

| 场景 | 通道 | 身份 |
|------|------|------|
| 技术部署/系统上线 | 企业应用审批通道 | 企业应用身份 |
| 个人补卡/请假 | lark-cli 个人身份通道 | 用户个人身份 |

---

## 五、当前状态

| 项目 | 状态 |
|------|------|
| 审批脚本 | ✅ 已部署 |
| 配置模板 | ✅ 已创建 |
| 企业凭证 | 📌 待填入 |
| 审批模板 | 📌 待创建 |
| 通道激活 | ⏳ pending_config |

---

Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ Lv10稳态自治

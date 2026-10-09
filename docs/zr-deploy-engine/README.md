# zr-deploy 通用执行引擎

> ZONGYUAN-ROOT 标准部署通道执行器
> 锚定 Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ 开源 Apache-2.0 ｜ 纯标准库零依赖

---

## 一、是什么

zr-deploy 是体系**应用层部署的唯一执行器**：统一封装部署通道（SSH 落盘 / 审批检查 / TAT 探测）、产物部署、curl 实测验证三件事，任何白皮书/页面部署都必须经过它，杜绝"应该OK"。

## 二、快速上手

```bash
# 1. 部署产物到官网（通道A：SSH + 自动验证）
python3 zr_deploy.py deploy \
  --asset 元学习自进化引擎白皮书.html \
  --name meta-learning-evolution-whitepaper.html \
  --channel ssh
# → {"ok":true, "http":200}

# 2. 纯验证 URL（必经步骤）
python3 zr_deploy.py verify --url https://huodouai.com/whitepaper/<name>.html

# 3. 审批工单登记/检查（通道B）
python3 zr_deploy.py approve --id "WO-20261009-001"
python3 zr_deploy.py deploy --asset x.html --name "工单号" --channel approval
```

## 三、通道矩阵

| 通道 | 行为 | 权限要求 |
|------|------|----------|
| ssh | scp 落盘 whitepaper 目录 + curl 验证 | 持 deploy_vm 公钥节点 |
| approval | 检查工单是否在审批通过名单 | 工单登记放行 |
| tat | 隔离通道探测（占位，独立配置） | 只读 |

## 四、环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| ZR_SSH_ALIAS | zongyuan-cloud | SSH 别名 |
| ZR_REMOTE_DIR | /www/wwwroot/huodouai.com/whitepaper/ | 远端部署目录 |
| ZR_BASE_URL | https://huodouai.com/whitepaper/ | 公网基址 |

## 五、真实运行验证（2026-10-09）

```
✅ verify 已知URL → http=200
✅ approve 登记工单 → approved_orders=["WO-20261009-001"]
✅ deploy ssh 实测 → 部署测试页 HTTP 200（测试后已清理）
✅ 缺失资产 → 明确报错 asset_not_found（不静默）
```

## 六、铁律

- 部署后必须 curl 实测，禁止纸面宣称成功
- 改配置前备份原文件
- 部署类操作需人工审批（零成本元规则）
- 失败 → 记录问题阻塞表 → 换通道重试，不无限空转

---

> 火斗云智AIOS · ZONGYUAN-ROOT ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω

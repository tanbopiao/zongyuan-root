# CloudBase 记忆网关 · 全域接入推广说明

DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-10-06

## 背景
主云端 www.huodouai.com（443）自 2026-10-05 不可达。为保记忆网关真值不中断，
已启用腾讯云 CloudBase 云数据库作为「记忆网关真值库」容灾（零成本方案）。

## 记忆网关坐标（唯一权威，勿臆造）
- 真值库：CloudBase truths 集合（env: huodouaios-9gz69m07efd5f23f, ap-shanghai）
- 只读查询页：https://huodouaios-9gz69m07efd5f23f-1341127773.tcloudbaseapp.com/memory-gateway.html
- 上报脚本（本地）：/home/user/ZONGYUAN-ROOT/scripts/tcb_truth_report.js

## 真值字段协议（truths 集合）
```
truth_key     唯一键（如 TCB.GATEWAY.ONLINE.20261006）
truth_value   真值内容
truth_type    meta_rule / axiom / decision / standard / config / ip_asset
source_node   来源节点（如 NODE-DEV-DOUBAO-WORK-001）
confidence    置信度（0~1）
ts            时间戳
did           DID-BR-000002
```

## 接入方式
### 上报真值（写）
```
node /home/user/ZONGYUAN-ROOT/scripts/tcb_truth_report.js \
  --key "TRUTH.KEY" --value "内容" --type meta_rule --node NODE-XXX [--conf 0.9]
批量: node tcb_truth_report.js --file truths.json
```
（写需管理端凭据 ~/.zongyuan-tcb-cred.json，chmod 600）

### 只读查询（读，全网可访问）
```
浏览器打开只读查询页 URL，即可查看 truths 真值列表（无需登录）
```

## 权限与安全
- 只读：全网可读（ACL=ADMINWRITE）
- 写：仅管理端凭据（secretId/secretKey 存本机，不外传）
- 溯源：所有真值带 did=DID-BR-000002 确权

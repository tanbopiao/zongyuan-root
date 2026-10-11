# 安全说明 | AtomGit 凭证治理
锚定: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 节点: NODE-DEV-DOUBAO-WORK-001

## 问题
本公开仓 (zongyuan-root-sync, private=false) 曾含多处明文凭证：
- `git_sync_bridge.py` 内嵌 Gitee 密码 / GitHub PAT
- `HANDSHAKE-NODE-MI-V5-001.json` 内嵌 AtomGit 令牌
- 10 个文件含 `api_gateway_key` 明文
- `.auth_credentials` 与 `.secure-backup/*.tar.gz` 被 git 跟踪

## 处置
1. 本节点握手文件一律**只存引用**，凭证走 `/root/.zr-credentials/`（600权限）
2. 已脱敏 `HANDSHAKE-NODE-MI-V5-001.json`
3. 建议：Gitee/GitHub/AtomGit 侧**轮换全部已泄露令牌**
4. 建议：将 `.auth_credentials`、`.secure-backup/` 加入 `.gitignore` 并从索引移除

## 原则
凭证零入库、引用式加载、最小暴露面。

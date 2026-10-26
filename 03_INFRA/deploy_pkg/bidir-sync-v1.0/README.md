# 双向同步引擎 v1.0 — 交付包

## 内容

| 文件 | 说明 |
|---|---|
| signing.py | PBKDF2-HMAC-SHA256 三头签名模块 |
| bidir_sync.py | 双向同步主引擎 (push/pull/diff/state) |
| SKILL.md | 仓库级技能包 |
| whitepaper/ | 技术白皮书 HTML (含 Mermaid 架构图) |

## 快速开始

\`\`\`bash
# 1. 确保 passphrase 可用
export ZR_SIGN_PASSPHRASE=...   # 或放 00_KERNEL/kernel_vault/.yuanji_signing.key

# 2. 预览
python3 bidir_sync.py --dry-run

# 3. 真双向同步
python3 bidir_sync.py --both
\`\`\`

## 契约 & 文档

- 白皮书 HTML: whitepaper/bidir-sync-whitepaper.html
- 云端 API: https://www.huodouai.com/tech/api.html
- 三镜像 Git: AtomGit / Gitee / GitHub

DID-BR-000002 · Ω₀⊂⊙∞⊂Ω · 2026-10-26

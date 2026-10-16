# SD-RND-003 · 全站 HTTPS 证书自动续期与安全收敛

> 主动进化提案 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω
> 提案来源：系统自产（基于近期全站五域证书签发修复后的后续收敛）
> 决策门：风险 low → 自动内审通过（M1: P=0.3U-0.4R-0.3C）

## 提案标题
全站（portal/gov/gallery/loip/qidian）HTTPS 证书自动续期巡检与安全头收敛。

## 优化动因
- 近期已完成五域 LE 证书签发 + HTTPS 上线（均已 200）。
- 证书有 90 天有效期，需自动续期巡检，防过期回退到 http。
- 泛域名 SAN 与 HSTS 预加载可进一步收敛，提升安全基线。

## 方案要点
1. acme.sh 续期 cron：每日校验各域证书剩余天数，<30 天自动续期并 reload nginx。
2. 泛域名 SAN 治理：将五域证书统一收口到主证书 SAN 或分域专属证书，避免到期错配。
3. 安全头收敛：确认 Strict-Transport-Security 一致、全站 https 强制 301。
4. 零成本：复用 acme.sh + 既有 nginx，无新增付费。

## 预期产出
- 证书到期巡检报告（剩余天数矩阵）
- 自动续期 + reload 日志
- 全站 https 强制、HSTS 一致

## 内审
- 决策门：low → auto-approve
- 状态：PASS（评分≥80）

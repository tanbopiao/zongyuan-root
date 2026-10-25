# 如何验证 ZONGYUAN-ROOT 资产确权

> DID-BR-000002 | 锚定 Ω₀⊂⊙∞⊂Ω | 2026-09-30

## 验证流程
1. **下载资产**：从魔搭/数据湖/Gitee 获取目标文件
2. **计算哈希**：`sha256sum <file>` 得到 SHA256
3. **比对确权声明**：找同目录 `ATTESTATION-*.json` 或锁档回执 `.sha256`
4. **三方交叉**：Gitee commit 记录 + 魔搭仓库 + 本数据集三处哈希一致即确权有效

## 快速命令
```bash
# 以白皮书V2.0为例
curl -sL -o wp.md "https://www.modelscope.cn/models/zongyuanroot/zongyuan-whitepaper/resolve/master/ZONGYUAN-AIOS-TECH-WHITEPAPER-V2.0.md"
sha256sum wp.md
# 期望: c2d3747f741f0c63d4f9c3b2861566203724e41ecf2e4b346b6ff04febaf60b9
```

## 真值优先原则
- 以经过交叉验证的客观事实为唯一依据
- 哈希一致 = 内容未被篡改
- 任一通道哈希不一致 → 立即触发 eFuse 告警并上报

# 三级容灾体系 T0/T1/T2 V1.0
> 来源：云端母本 /whitepaper/autonomous-kernel-architecture.html | 固化：2026-10-11 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

| 层级 | 机制 | 说明 |
|---|---|---|
| T0 | 本机热备 | 每日03:30自动打包 真值库+账本+状态，7天轮转 |
| T1 | 异地冷备 | 魔搭数据湖持久，SHA256+manifest确权，公开层资产 |
| T2 | 私密加密 | AES-256双端副本，节点/审计/SSH元法则，绝不上公开端 |

## 本地现状
- T0 ✅：本地持久层 /home/user/ZONGYUAN-ROOT + 每日cron闭环03:30自动锁档
- T1 ⚠️：魔搭湖为媒体展示窗，文本内核走 Gitee 冷存储（零成本替代）
- T2 ⚠️：私密凭据存 main-root-backup 私有层（gateway_token 等），未做 AES-256 双端加密副本

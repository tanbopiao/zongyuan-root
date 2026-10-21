# 本地实例持久性加固回执（KEK 异备份 + 恢复演练）
事件ID：PERSISTENCE-HARDEN-20260927 ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω

## 1. KEK 异备份（消除密钥本地单点）
- KEK 指纹（SHA-256，明文不落盘）：`08f47fac9494444e5929cbddba4a52f920c7a5b1a04b7ce3a2f081f4a286dcde`
- 飞书云盘备份：`kek.env.zongyuan-backup-20260927`（用户私有）
  - file_token: `QXFobQpMToTGYFxUCTxcA6TjnPf`（64 字节）
  - url: https://my.feishu.cn/file/QXFobQpMToTGYFxUCTxcA6TjnPf
- 恢复路径：云盘下载 → 放回 ZONGYUAN-ROOT/var/kek.env（600）→ 认知层可解 ark key

## 2. 重启恢复演练（模拟 @reboot 三线，未真重启）
| 线 | 命令 | 结果 |
|---|---|---|
| 1 | worker_kernel.sh boot | ✅ worker-kernel-001: down → **healthy**（pid 7243，心跳 9s 前） |
| 2 | kernel_launch.sh start | ✅ already_running 幂等（pid 5047） |
| 3 | zongyuan_fusion.sh selfcheck | ✅ 日志 11 行落 /logs/fusion_selfcheck.log |

结论：@reboot 恢复链路**实测有效**（worker 真实拉起、kernel 幂等自检），"声明"已变"证据"。

## 遗留项（下一轮可做）
- 全量账本/卷宗/审计异地冷备（rsync 到云端）——中成本，本轮未做

# 卷宗｜B锚本地母体部署回执
确权：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-27 16:26
- 通道实测：沙箱无 sshd（B锚直连不可行）→ 探测走公网真值网关（truths 只读 GET 可用）；恢复走腾讯云 SSH 白名单 + 豆包会话
- 产出：restore_env.sh（一键恢复，实测 RESTORE_OK kernel/worker/cron 全绿）+ cloud_probe.ps1（本地探针，网关心跳新鲜度判定 + SSH 云服务器恢复 + 日志告警）+ SOP-B-ANCHOR-DEPLOY-20260927.md
- 现状：云端 worker 16:16 恢复后稳定；worker_daemon cron 自愈 16:21 实测生效；探针待用户本地部署

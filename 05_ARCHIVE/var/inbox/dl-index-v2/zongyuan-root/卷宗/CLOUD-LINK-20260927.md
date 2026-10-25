# 卷宗｜沙箱↔云服务器 双向心跳 + 账本双写 落地回执
确权：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-27

## 链路（已实测全通）
- 沙箱 cloud_link.sh（cron */5）：
  ① 心跳上报：沙箱状态{kernel,worker,cron} → 云服务器 /opt/ZONGYUAN-ROOT/meta/sandbox-heartbeat.json（覆盖式）
  ② 云内核心跳读回：读 /opt/ZONGYUAN-ROOT/meta/cloud-heartbeat.json
  ③ 账本双写：audit.jsonl + HASH-LEDGER-MAIN.csv → rsync 云服务器 /opt/ZONGYUAN-ROOT/var/inbox/
- 云服务器 cloud_heartbeat.sh（cron */5）：写 /opt/ZONGYUAN-ROOT/meta/cloud-heartbeat.json（对向心跳）
- 实测：心跳上报 ts=k=up/w=up/c=11；云侧落盘一致；账本双写 OK（audit 38KB + ledger 已同步）

## 关键事实
- kernel 存活检测用 pgrep -f "kernel/main.py"（运行中进程名，非启动脚本）
- 云内核**全面运行中**（勘误修正）：非单一 kernel/main.py 进程，而是 12 个 systemd 服务 + 多引擎分布式体系；真值元序引擎 run.py --daemon 连续运行 3天13小时（CPU 4h46m）；RAG/向量/推理/政务中台/知识图谱全活跃；9120 记忆网关监听中；今天 16:35 内核锚定快照已生成
- 云侧心跳检测已修正（cloud_heartbeat.sh）：core_engine(truth_meta_order_engine)+systemd 服务数+rag 综合判定，实测 kernel=up core_engine=up services=10 rag=up
- SSH 失败不阻塞沙箱主流程（日志留痕）；密钥 600；BatchMode 免交互

## SOP 更新
- SOP-B-ANCHOR-DEPLOY-20260927.md → V1.1（通道现实：沙箱出站 SSH 已通，心跳互报+双写新增）
- SOP-STEADY-STATE-20260927.md → §8 云链路（zongyuan-cloud 通道、cloud_link.sh、故障语义、安全约束）

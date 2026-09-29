# ZONGYUAN-ROOT 文档索引

确权锚点：Ω₀⊂⊙∞⊂Ω ｜ DID：DID-BR-000002

## 核心架构文档

| 文档 | 说明 |
|------|------|
| DUAL_ISOLATION_PROTOCOL.md | 本地云端双隔离协议 |
| CLOUD_ALIGNMENT.md | 本地云端文件对齐说明 |

## 目录索引

```
zongyuan-root/
├── scripts/           # 工具脚本
│   ├── 01-prod/       # 生产运行
│   ├── 02-deploy/     # 部署脚本
│   ├── 03-inspect/    # 巡检检查
│   ├── 04-scan/       # 扫描诊断
│   ├── 05-test/       # 测试调试
│   ├── 06-lock/       # 锁档确权
│   └── 07-sync/       # 同步同步
├── docs/              # 架构文档
├── config/            # 配置文件
├── kernel/            # 内核状态
├── logs/              # 运行日志
└── assets/            # 资产文件
```

## 快速命令

- 部署：`.\scripts\02-deploy\deploy.ps1 <服务名>`
- 健康扫描：`python scripts/full_health_scan.py`
- 本地扫描：`python scripts/local_kernel_scan.py`

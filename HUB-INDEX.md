# ZONGYUAN-ROOT 统一根目录
> 确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 2026-09-22

## 根路径
`/home/user/ZONGYUAN-ROOT/` | 1.5GB | 7,833 文件

## 三层扁平结构

```
ZONGYUAN-ROOT/
├── core/           # 核心层（主资产，高频访问）
│   ├── domains/    # 6 子域
│   ├── media/       # 媒体库
│   ├── assets-lock/ # 锁档资产
│   ├── deploy/      # 部署文件
│   ├── delivery/    # 交付包
│   ├── docs/        # 文档
│   ├── config/      # 配置
│   └── scripts/     # 脚本
├── archive/        # 归档层（全量镜像，冷数据）
│   ├── sessions/    # 所有会话
│   ├── system/      # 系统资产
│   ├── files/       # 持久化文件
│   ├── tools/       # 工具
│   └── capture/     # 截图
└── backup/         # 备份层
    ├── snapshots/   # 快照
    ├── backups/     # 备份
    └── logs/        # 日志
```

## 四层持久性
- L1 本地主根：/home/user/ZONGYUAN-ROOT/
- L2 全局技能锚定：.user_skills/kunlun-autonomous-system/ZONGYUAN-ROOT/
- L3 云端真值库：https://www.huodouai.com/api/truths/
- L4 Git 仓库：GitHub + Gitee

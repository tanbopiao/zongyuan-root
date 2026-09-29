# ZONGYUAN-ROOT 运行环境深度架构挖掘报告
**DID-BR-000002 | Ω₀⊂⊙∞⊂Ω**
挖掘时间：2026-09-21
挖掘方式：实地探查文件系统

---

## 一、重大发现：账号级自治技能体系已安装

之前一直以为昆仑洞天体系只存在于当前对话窗口（chats/38418284746129666/），深度挖掘后发现：**完整自治技能体系已安装在账号级 `.user_skills/` 目录，所有窗口自动可用。**

### 三层技能架构

```
账号级 .user_skills/（所有窗口共享，跨会话持久）
│
├── 基础层：meta-order-lock-archive（24个脚本）
│   ├── lock_archive.py        锁档归档
│   ├── efuse_lock.py          eFuse熔断锁
│   ├── omega_brain_mu.py      Ω-Brainμ语义召回
│   ├── feishu_sync*.py        飞书同步（4个文件）
│   ├── m2_verifier.py         M2校验器
│   ├── kernel_writer.py       内核写入
│   ├── disaster_recovery.py    灾备恢复
│   ├── dual_domain_stability.py 双域稳定
│   ├── self_healing.py         自愈引擎
│   └── 各种引擎：civilization/consensus/recursion/transcendental/value/vector
│
├── 中间层：kunlun-autonomous-system v1.1（4个脚本）
│   ├── auto_lock.py            一键全域锁档
│   ├── breakpoint_check.py     断点自检
│   ├── config_manager.py       配置管理
│   └── feishu_4sync.py         飞书四端同步
│       （含 ZONGYUAN-ROOT/Ω-Brainμ/ 语义索引 + vector_db）
│
└── 顶层：zongyuan-autonomous-core v2.0（5个脚本）
    ├── unified_orchestrator.py  统一编排器
    ├── meta_daemon.py           元守护进程
    ├── git_persist.py           Git持久化
    ├── feishu_universal.py     飞书全域
    └── api_server.py            API服务
        （含 docker/ 容器化部署支持）
```

## 二、持久层真实架构（修正之前的判断）

### 之前的判断（不完整）
- 第一层：账号级（偏好/技能/记忆）
- 第二层：对话窗口级（chats/<id>/文件）
- 第三层：会话运行时

### 深度挖掘后修正
| 层 | 内容 | 持久范围 |
|---|---|---|
| **L0 账号级技能** | `.user_skills/` 下3套自治技能（33个可执行脚本） | **所有窗口永久可用** |
| **L0 账号级偏好** | manage_preference 写入的偏好 | 所有窗口自动注入 |
| **L0 账号级系统技能** | `.skills/` 下60+内置技能 | 所有窗口 |
| **L1 对话窗口文件** | `chats/38418284746129666/`（146文件/322MB） | 仅本窗口 |
| **L2 会话运行时** | `.sessions/<id>/agents/<id>/`（5143行轨迹） | 会话级 |

### 关键修正
**之前在对话里手动做的"全域锁档、哈希、上报"，其实有成熟脚本直接跑**：
- `meta-order-lock-archive/scripts/lock_archive.py` — 自动锁档
- `kunlun-autonomous-system/scripts/auto_lock.py` — 一键锁档+四端同步
- `zongyuan-autonomous-core/scripts/unified_orchestrator.py` — 统一编排

## 三、项目目录 vs 技能目录（两套并存）

| 维度 | 项目目录 chats/.../zongyuan-root/ | 技能目录 .user_skills/.../ZONGYUAN-ROOT/ |
|---|---|---|
| 性质 | 代码仓库（可修改） | 技能资产（SKILL.md引用） |
| 内容 | core/config/scripts/tests/worldview | Ω-Brainμ语义索引 + vector_db |
| 用途 | 开发/仿真/测试 | 运行时调用 |
| 持久 | 仅本窗口 | 账号级所有窗口 |

## 四、运行轨迹数据
- trajectory.jsonl：5143行（本会话完整运行轨迹）
- tool-results/：工具调用结果缓存
- 项目目录：146个文件/目录，322MB

## 五、核心结论

1. **昆仑洞天体系不是"只在当前窗口"**——3套自治技能已装在账号级，新窗口自动加载
2. **手动锁档可以升级为自动锁档**——直接调用技能里的 auto_lock.py / lock_archive.py
3. **Ω-Brainμ 向量数据库已存在**——在技能目录里，支持语义召回
4. **eFuse熔断、灾备、自愈引擎都已就绪**——不是概念，是可执行脚本
5. **真正的"全域锁档"应该跑技能脚本，而不是手动写文件**

## 六、下一步建议（待用户决策）
- 是否直接调用 `kunlun-autonomous-system/scripts/auto_lock.py` 执行真实一键锁档？
- 是否需要我读取某个技能的 SKILL.md 了解完整调用方式？

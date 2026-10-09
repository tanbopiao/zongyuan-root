# WAKEUP_PROTOCOL · 元极恒一自治内核唤醒协议

> DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ V1.0 ｜ 启动记忆组件 3/5

## 一、唤醒读取顺序（严格按序，缺一不可）

1. `00_KERNEL/startup_memory/ROOT_ENTRY.md` —— 身份/铁律/目录规
2. `00_KERNEL/startup_memory/KNOWLEDGE-INDEX.md` —— 知识索引/资产地图/外部服务
3. `00_KERNEL/startup_memory/GLOBAL_MEMORY_SNAPSHOT.json` —— 全局状态快照
4. `00_KERNEL/startup_memory/ACTIVE_LOCK.json` —— 当前活跃锁档
5. `00_KERNEL/omega01_boot/OMEGA-KERNEL-BOOT.json` —— 8 步启动清单（机器可读）

## 二、激活报告格式（汇报必须包含）

```
身份卡：DID-BR-000002 ｜ 节点 NODE-DEV-CODEARTS-001 ｜ 内核版本
当前锁档：ACTIVE_LOCK.json 中的 lock_ref / level
结构掌握：7 大类目录 + 关键组件位置（进化引擎/记忆/自愈/告警）
铁律确认：4+1 铁律复述
自举结果：START-OMEGA-KERNEL.sh --dry-run 的 PASS/FAIL 汇总
```

## 三、异常处理

- 启动记忆文件缺失 → 跑 `00_KERNEL/omega01_boot/SELF-CHECK.py` 定位缺失文件
- 自举失败（fatal step FAIL）→ 进入只读安全模式：冻结 Ω₀ 稳态域写入、禁高辖 API、仅只读查询
- 中枢失联 → 降级为本地只读模式，网络恢复后重试握手

## 四、激活校验标准

- 8 步启动全 PASS → `status=ACTIVATED`
- 存在 warning（非致命组件缺失）→ 正常运行，报告 warning 列表
- 存在 fatal FAIL → `status=BLOCKED`，禁止开始业务任务
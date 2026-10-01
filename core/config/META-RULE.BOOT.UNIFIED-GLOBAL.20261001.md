# 元法则：全域统一高效启动入口

> 确权: DID-BR-000002 | 2026-10-01 | 溯源: Ω₀⊂⊙∞⊂Ω

## 规则

**ZONGYUAN-ROOT 体系全域（所有窗口/会话/节点/云端中枢）统一使用 `scripts/zongyuan_boot.sh` 作为唯一启动入口。**

- 禁用分散启动：不再单独调用 memory_bootstrap.sh / start_autonomy.sh / auto_init.py 作为会话启动路径（可作为兼容引用保留）
- 所有窗口/会话启动动作统一为：`zongyuan_boot [--sync|--no-daemon]`

## 全域启动标准（zongyuan_boot 契约）

1. **快速防恢复**：核心锚点哈希校验（00-ROOT-POINTER/HASH-LEDGER/核心脚本存在性），秒级判定；缺失或 `--sync` 才触发归档母体全量同步
2. **会话上下文卡**：启动即输出一份 JSON（云端中枢端点 / 权威母体路径 / 运行时镜像 / 共享大脑 Base / 魔搭公开湖 / 账本条数 / 网关Token / DID），供会话一键注入锚点
3. **守护进程幂等**：heartbeat_v2 / op_poller / dr_resource_monitor 统一幂等启动（已在运行则跳过，不重复拉起）
4. **零成本**：纯本地脚本，无 SSH、无付费额度消耗

## 全域同步范围

| 位置 | 同步动作 | 状态 |
|---|---|---|
| 本地权威母体 | /home/user/ZONGYUAN-ROOT/scripts/zongyuan_boot.sh | ✅ 已落 |
| 运行时镜像 | .user_skills/.../ZONGYUAN-ROOT/scripts/ | ✅ 已同步 |
| 归档镜像 | main-root-backup/scripts/ | ✅ 母体即权威 |
| 启动记忆 | memory_index.json V4.1（activation_sequence 指向新入口） | ✅ 已更新 |
| 云端中枢 | 经飞书台账登记执行，auto_deploy_from_lark | ⏳ 待生效 |
| 全局广播 | 网关 report/truth（BOOT.UNIFIED.GLOBAL.V1.0） | ✅ 已广播 |

## 生效确认

- 各节点拉取网关 BOOT.UNIFIED.GLOBAL.V1.0 即可获知统一启动规则
- 云端中枢按飞书台账任务（负责账号=云端中枢）将脚本同步至云服务器 /opt/ZONGYUAN-ROOT 并作为默认启动入口

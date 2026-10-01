# 元规则·钩子自启动持久层恢复

- **ID**: META-RULE-HOOK-AUTOSTART-V1.0
- **确权**: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
- **固化时间**: 2026-10-01T17:15:00+0800
- **层级**: 元规则（体系级基础设施规范）
- **状态**: 生效

## 一、规则正文

**凡是会被环境重置的运行时资产，一律改为本地持久层存储，并通过钩子算法触发自启动。**

### 适用范围（会被重置的资产类别）

| 类别 | 举例 | 重置风险 |
|---|---|---|
| 用户目录安装物 | ~/ollama、~/models、~/bin/* | 沙箱重建即失 |
| 运行中进程 | ollama serve、按需网关 | 环境重置即停 |
| 临时运行日志 | /tmp/*.log | 重启即清 |
| 运行时状态 | 模型注册表、缓存索引 | 重建即失 |
| 会话绑定凭证 | 环境变量、PATH 注入 | 新会话不继承 |

### 处置规则

1. **先归档**：易失资产实体 → 持久层冷存储（03_INFRA/deploy_pkg/ 或 01_ASSETS/）
2. **再声明**：在钩子注册表（hook_registry.json）登记「资产 → 恢复动作」映射
3. **钩子触发**：每次环境启动/重建，运行钩子算法检查注册表 → 检测缺失 → 从持久层恢复 → 校验可用
4. **幂等**：已恢复且可用的资产跳过，不重复消耗
5. **指纹校验**：恢复后校验 SHA256/存在性/端口探活，防半成品

## 二、钩子算法（Hook Algorithm）

```
输入: 钩子注册表 hook_registry.json
对每条注册项 (asset_id, persist_path, check_cmd, restore_cmd, verify_cmd):
  1. 检查 check_cmd 探活 (进程/端口/文件存在)
  2. 若存活 → 跳过 (幂等)
  3. 若缺失 → 执行 restore_cmd 从持久层恢复
  4. 执行 verify_cmd 校验恢复结果
  5. 记录钩子执行日志 → /var/log/hook_autostart.log
输出: 执行报告 (恢复项列表 / 跳过项列表 / 失败项列表)
```

## 三、注册表规范（hook_registry.json）

```json
{
  "hooks": [
    {
      "asset_id": "llm_power",
      "desc": "按需算力动力源(ollama+模型+网关)",
      "persist_path": "03_INFRA/deploy_pkg/llm_power/",
      "check_cmd": "curl -s http://127.0.0.1:8777/health",
      "restore_cmd": "bash 03_INFRA/deploy_pkg/bootstrap_llm_power.sh",
      "verify_cmd": "python3 00_KERNEL/scripts/llm_kernel_bridge.py status"
    }
  ]
}
```

## 四、触发时机

| 时机 | 触发方式 |
|---|---|
| 环境启动/重建后 | 手动执行 `bash 03_INFRA/deploy_pkg/hook_autostart.sh` |
| 定时自检 | cron 每日/每小时检查注册表, 掉线自动恢复 |
| 会话开始 | 启动记忆注入钩子路径, 首次对话可触发 |

## 五、落地清单

- [x] 算力栈归档持久层: 03_INFRA/deploy_pkg/llm_power/ (ollama+模型2.1GB)
- [x] 自举脚本: bootstrap_llm_power.sh (幂等恢复)
- [x] 钩子注册表: hook_registry.json
- [x] 钩子算法: hook_autostart.sh (通用, 注册表驱动)
- [x] 方案文档: LLM-POWER-COLDSTART-V1.0
- [ ] 后续: 其他易失资产(凭证/缓存/会话状态)逐步纳入注册表

## 六、与现有规则的衔接

- 遵循「资产归档策略」: 大体积仅本地, 文本内核双副本
- 遵循「固化资产只读锁档」: 恢复脚本/注册表固化后只读
- 遵循「零成本优先」: 钩子为纯本地 bash/python, 零费用

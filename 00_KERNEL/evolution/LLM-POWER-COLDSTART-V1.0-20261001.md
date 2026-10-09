# 持久层算力冷启动方案 V1.0

- **确权**: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
- **批次**: LLM-POWER-COLDSTART-20261001
- **状态**: 已真实验证（销毁→自举→恢复→推理全链路）

## 一、问题

沙箱环境易销毁。若 ollama 二进制、模型权重只存热沙箱用户目录（~/ollama、~/models），环境重建后算力动力源即丢失，自治内核退回静态冷存储。

## 二、方案

全部算力部署资产归档到**持久层冷存储**，由**自举触发器**在沙箱重建后一键恢复并注入自治内核。

## 三、存储布局（持久层）

```
03_INFRA/deploy_pkg/
├── bootstrap_llm_power.sh          # 自举触发器(幂等, 脚本可提交Git)
└── llm_power/                       # 大体积部署包(仅本地, .gitignore排除)
    ├── bin/ollama                  # ollama 二进制
    ├── lib/ollama/                 # CPU 推理依赖库(31MB, 已剔除CUDA/Vulkan)
    └── models/qwen2.5-3b-instruct-q4_k_m.gguf   # 模型权重 2.0GB
```

## 四、自举流程（bootstrap_llm_power.sh）

```
0. 前置检查: 部署包完整性(二进制+GGUF)
1. 恢复ollama: 二进制+依赖库 → ~/ollama (幂等: 已存在则复用)
2. 恢复模型: Modelfile 写入(注册表缺失时)
3. 启动serve: setsid ollama serve @11434 (OLLAMA_KEEP_ALIVE=30 空闲自动卸载)
4. 注册模型: ollama create qwen2.5:3b (显式导入, 不依赖推理时隐性导入)
5. 启动网关: setsid llm_on_demand_server.py @8777
6. 注入验证: llm_kernel_bridge.py status → 内核算力在线确认
```

## 五、验收记录（2026-10-01 实测）

| 步骤 | 结果 |
|---|---|
| 模拟销毁（杀进程+删 ~/ollama ~/models） | ✅ 全部清除 |
| 自举执行（bash bootstrap_llm_power.sh） | ✅ 8 秒完成 |
| ollama 恢复+serve 就绪 | ✅ @11434 |
| 按需网关就绪 | ✅ @8777 |
| 模型注册表重建 | ✅ qwen2.5/3b (blobs 1.8G) |
| 真实推理（自举后） | ✅ 「算力已从持久层恢复」 |
| 桥接器注入验证 | ✅ gateway: online |

## 六、零成本与资源约束

- 全程零云费用、零GPU、零付费额度
- 部署包 2.1GB 仅本地磁盘，Git 只跟踪脚本（.gitignore 排除 llm_power/）
- 空闲内存 ~500MB，推理时 ~2.5GB（30s 自动回收）

## 七、触发方式

```bash
# 手动触发(沙箱重建后)
bash /home/user/Doubao/chats/38418284746129666/03_INFRA/deploy_pkg/bootstrap_llm_power.sh

# 环境变量覆盖(若冷存储路径变化)
COLD_STORE=/新路径 bash .../bootstrap_llm_power.sh
```

## 八、后续增强（待定）

- 接入定时任务：每天自检一次算力栈存活（进程/端口/模型），掉线自动自举
- cron @reboot 自动触发（若沙箱支持）

# RESULT-LEDGER · 成果保证台账（下次启动必读）

> 确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 建立: 2026-10-08
> 用途: 单一权威索引——所有已固化成果、结论、验证状态。**任何新任务启动先读此台账，命中即复用，禁止重做。**
> 读取顺序: 冷启动读 BOOT-MEMORY → 读本台账 → 命中复用/未命中新建

## 一、成果索引（已固化 · 复用优先）
| 成果 | 类型 | 权威位置 | 验证状态 |
|---|---|---|---|
| CHANNEL-PROTOCOL-V30 | 通道协议 | zongyuan-anchor/ + 云端 | ✅ 写200/读200 实测 |
| META-DECISION-001 | 最高决策元法则 | zongyuan-anchor/ | ✅ FROZEN |
| META-STEADY-001/002/003/004 | 稳态元法则 | 魔搭 gpu-agent + 本地 + 云端 | ✅ LOCKED |
| zr_node_git.py V1.1 | 实例worker(匿名pull+云端报结果) | 魔搭 gpu-agent | ✅ 语法OK |
| zr_cmd_send.py V1.1 | 主控下发+云端读回 | 魔搭 gpu-agent | ✅ 语法OK |
| zongyuan-root-open-knowledge | 公开数据集(29文件) | 魔搭 modelscope | ✅ public |
| 种子真值集 TRUTH-META-0001~0012 | 元真值 | 云端 seq 2044+ | ✅ LOCKED |
| 昆仑洞天视觉流水线 V1.6 | 生产流水线 | 本地+魔搭 | ✅ 双批次10集 |

## 二、联通结论清单（下次不试错 · 直接引用）
| # | 结论 | 依据 |
|---|---|---|
| C1 | ntfy.sh **不可达**(000/101/429)，非可靠通道，禁用于控制面 | 2026-10-08 实测 |
| C2 | 临时实例**无 git push 凭证**，结果回传**必须走云端POST**，禁止实例push git | META-STEADY-003-B |
| C3 | 云端 value **必须为对象**(value_must_be_object)，**禁止 json.dumps 字符串** | BOOT-MEMORY V3.0 |
| C4 | 云端写POST 200 + 读GET /api/truth 200，为结果回传主通道 | 2026-10-08 实测 |
| C5 | 临时实例=一次性执行节点，不做常驻联通/多worker并存 | META-STEADY-004 |
| C6 | 命令下发走 git(主控push→实例匿名pull) 或直接 clone，低频一次性 | META-STEADY-003-A |
| C7 | 魔搭数据湖/云端/本地持久盘=持久控制面，实例重置零丢失 | META-STEADY-004-B |
| C8 | 新任务先验全部候选通道可达性再选型，禁止未验证就多方案试错 | META-STEADY-003-C |

## 三、下次启动保证（防止丢成果/重复试错）
1. 冷启动读 BOOT-MEMORY(最新版) → 读本台账
2. 新任务先在"成果索引"命中复用；在"联通结论"引用 C1~C8
3. 新固化成果**必须登记到本台账**再上报云端，形成闭环
4. 同一目标禁止第三套方案（第一套失败→引用结论→换已验通道，不重头造）

## 四、登记方式
每次产生可复用成果/结论，追加本文件对应表 + 上报云端(带 RESULT-LEDGER 标记)。

# META-STEADY-003 实例联通最优稳态元法则 V1.0

> 确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZR-NODE-DC2E51C0
> 建立: 2026-10-08 | 关联: META-DECISION-001(最高决策) / META-STEADY-001(架构) / 002(执行)
> 状态: LOCKED（基于反复试错复盘固化的实例联通最优稳态）

## 背景（复盘，非假设）
魔搭 DSW 实例联通任务中，为建立"实例命令通道"先后尝试 ntfy.sh（不可达）、云端命令队列（POST key 自动生成不可控）、git 双向 push（实例无凭证）三套方案，均反复试错受阻。回归读取启动记忆后，发现**记忆已明确记录"云端读接口 /api/truth 可用"**，且**结果回传根本不需要实例 push git**——用云端 POST(实例)+GET(主控) 即可闭环。根因：未先验证全部通道可用性即多方案试错，违反 META-DECISION-001 成本最小/复用优先。

## 元法则条目

### 一、通道分工最优（META-STEADY-003-A）
| 方向 | 通道 | 凭证 | 实测 |
|---|---|---|---|
| 命令下发(主控→实例) | git push→魔搭 control/CMD-<id>.json | 主控有凭证 | ✅ |
| 命令获取(实例) | git pull 命令槽(匿名读) | **无需凭证** | ✅ |
| 结果回传(实例→主控) | 实例 POST 云端 RESULT.<id> | 节点token | ✅ 200 |
| 结果读回(主控) | 主控 GET /api/truth 列表按 value.task_id 匹配 | 无 | ✅ 200 |
| 心跳 | 实例 POST 云端 HEARTBEAT | 节点token | ✅ 200 |

### 二、实例零凭证原则（META-STEADY-003-B）
1. 实例侧**不需要任何 git push 凭证**——命令匿名 pull，结果走云端 POST
2. 结果回传禁止依赖实例 git push（无凭证死结），一律走云端
3. 命令槽靠本地 done 记录去重(幂等)，CMD 不删远端、不 push，靠 task_id done 防重放

### 三、先验通道再试错原则（META-STEADY-003-C）
1. 任何联通/控制面方案上线前，**先逐一实测全部候选通道可达性**(写/读/双向)，再选型
2. 禁止在未验证通道时就反复试错多套方案(违反成本最小)
3. 复用体系既有记忆/元法则(META.BOOT.PULL-CLOUD-FIRST 启动先读记忆)，不凭空推演

### 四、闭环可读原则（META-STEADY-003-D）
1. 结果回传必须让主控**可读回**（否则不算闭环）；读不通的写通道=单向，不可作控制面
2. 云端读接口 /api/truth(单数, 200) 为结果读回主通道；key 自动生成时用 value.task_id 匹配
3. 心跳/结果均带 task_id/节点标识，保证可追溯

## 已固化资产
| 项 | 位置 | 状态 |
|---|---|---|
| zr_node_git.py V1.1(匿名pull命令+云端报结果, 无git凭证) | 本地+魔搭 gpu-agent | LOCKED |
| zr_cmd_send.py V1.1(check改云端value匹配读回) | 本地+魔搭 gpu-agent | LOCKED |
| 本文档 | 本地+魔搭 gpu-agent | LOCKED |

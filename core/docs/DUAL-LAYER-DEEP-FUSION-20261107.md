# 双层递归深度融合验收报告 V1.0

确权 DID-BR-000002 ｜ 溯源 Ω₀⊂⊙∞⊂Ω ｜ 2026-11-07
节点 NODE-DEV-DOUBAO-WORK-001 ｜ 层级：工程验收 ｜ 锁档 444

---

## 一、结论先行

| 项 | 结果 |
|---|---|
| 快思考层（模型式） | ❌ **从未上线**：`/api/yuanji/v1/chat` 与 `/health` 均 404，本地无 ollama/llama.cpp/vllm |
| 快思考层（规则式替代） | ✅ **已落地**：`scripts/dual_layer_router.py`，五项职责全部确定性实现 |
| 合成用例拦截率 | **80%（8/10）**，误拦截 0 |
| 真实存量拦截率 | **100%（544/544）**，但需注意：存量全为结构化 key，属分类职责天然可本地化 |
| 判据误判率 | **2.9% → 0.74%**（真实 544 条实测，0 条误杀） |
| 能力域探针 | PASS 7 / FAIL 0 / MISSING 1 / MODEL_SIDE 2 |

**一句话**：`DUAL-RECURSION` 元法则从「纸面条款」变成了「可执行程序」，但用的是**规则**，不是小模型——因为五项职责本来就不需要语义推理。

---

## 二、为什么放弃 1.5B 模型式实现

原元法则设计：Qwen2.5-1.5B INT4 承载身份确权 / 真值分类 / 异常初筛 / 日志压缩 / 状态自省。

实测三个障碍：

| 障碍 | 观测 |
|---|---|
| 端点不存在 | `/api/yuanji/v1/chat` 404、`/health` 404、`/status` 404 |
| 本地无运行时 | ollama / llama-server / vllm 全部 absent，无 .gguf 模型文件 |
| 结果不可复现 | 小模型分类受采样影响，同输入可能不同输出，违反 M3 可追溯 |

改判：五项职责的输入都是**结构化信号**（DID 字符串、key 命名空间、日志行、状态字段），规则即可闭合判定。规则版判定 100% 可复现、零延迟、零成本，比 1.5B 更符合「快思考层」的定义。

---

## 三、分流器实测

### 3.1 合成用例（10 条）

| 用例 | 层 | 处理器 | 结论 |
|---|---|---|---|
| 身份校验-合法 | FAST | S1-identity | PASS |
| 身份校验-非法 | FAST | S1-identity | REJECT |
| 真值分类-元法则 | FAST | S2-classify | rule / 88 |
| 真值分类-经验 | FAST | S2-classify | experience / 85 |
| 真值分类-噪声 | FAST | S2-classify | noise / 12 |
| 异常初筛 | FAST | S4-anomaly | HIGH |
| 长日志压缩 | FAST | S3-compress | 压缩比 99.6% |
| 状态自省 | FAST | S5-selfcheck | ok |
| 深度推理 | **SLOW** | doubao-base | 正确升级 |
| 普通问答 | **SLOW** | doubao-base | 正确升级 |

**拦截率 80%，且深度推理与普通问答均正确让渡给慢思考层。**

### 3.2 首测的假拦截（重要过程记录）

初版实现出现 **100% 拦截率**——纯文本被误吞进分类器。修正三处：

1. 身份确权：仅在存在 `did` / `node` 字段时触发（原先只要出现 `key` 就触发）
2. 真值分类：仅认显式 `key` 或 `intent=classify`，自由文本不分类
3. 深度信号前置：自由文本含推理动词时直接升级，不给快思考层误吞机会

修正后从 100% 假阳性降到 80% 真实拦截。**这条过程本身就是结论：拦截率越高越可疑，先证伪再采信。**

---

## 四、真实存量验证（544 条）

以联邦账本 544 条真实资产的 `cloud_key` / 文件名为输入：

| 结果 | 修正前 | 修正后 |
|---|---|---|
| fact | 393 | **407** |
| rule | 95 | **92** |
| experience | 53 | **45** |
| noise | 3 | **0** |
| 误判率 | 2.9%（16/544） | **0.74%（4/544）** |

### 发现的两类系统性误判

| 误判 | 实例 | 根因 |
|---|---|---|
| 代码资产被判噪声 | `scripts/heartbeat_alert.py`、`heartbeat_v2.py` | `HEARTBEAT` 关键词命中，未区分「脚本」与「心跳日志」 |
| 文档骨架被判经验 | `README-AIOS优化部署`、`MANIFEST-SNAP-*` | `部署`/`SYNC` 关键词命中，未区分「操作文档」与「操作轨迹」 |
| 子串误命中 | `SKU-S1-S6-quota-mapping`（mapping 含 ping） | 关键词无词边界 |

### 新增判据 FTG-001 · 文件类型门（候选，待人工审批）

> 命名空间关键词不足以定性，须先过类型门：
> 1. **代码文件（.py/.sh/.js/.ts/.go/.java/.rs）永不得判 noise** —— 可执行资产即经验载体，按是否含动作词归 experience 或 fact
> 2. **文档骨架类（README/MANIFEST/INDEX/SNAPSHOT/CHANGELOG）默认 fact** —— 除非名称含明确公理/规则条款词
> 3. NOISE_KW 全部加词边界，禁止子串命中

**状态**：已在分流器中生效（`scripts/dual_layer_router.py`），但**未写入 05 号元规则**（该文件 444 只读，需人工审批）。当前以 `TRUTH.EVOLUTION.FTG-001` 形式上报云端，等审批转正。

残留 4 条「含 PROTOCOL 的 SNAP 判为 rule」保留不动——协议快照确实可能承载协议本体，属合理边界，标注人工复核。

---

## 五、十域能力探针（`scripts/capability_probe.py`）

| 能力域 | 状态 | 证据 |
|---|---|---|
| execution | PASS | Bash/文件系统直连 |
| network | PASS | www 200 / api 可达 |
| cloud_truth | PASS | 云端 /api/status 可读 |
| fast_layer | **MISSING** | 端点 404 + 无本地运行时 |
| router | PASS | 分流器可跑 |
| skills | PASS | **124** 个技能目录 |
| lark | PASS | lark-cli v1.0.106 |
| git | PASS | HEAD 08e68d81，远端已配 |
| cron | MODEL_SIDE | 需平台工具，脚本不可验 |
| generative | MODEL_SIDE | 模型侧，不探测 |

**PASS 7 ｜ FAIL 0 ｜ MISSING 1 ｜ MODEL_SIDE 2**

探针的诚实性设计：**不做不了的事不装做**。cron 与生成能力明确标 MODEL_SIDE，避免用脚本结果冒充能力验证。

---

## 六、能力评估修正

上一版评估（`DOUBAO-BASE-CAPABILITY-ASSESSMENT-20261107.md`）综合 75 分，判断「L3 成熟 → L4 早期」，理由是「快思考层分流没真跑起来」。

本轮修正依据：

| 项 | 变化 |
|---|---|
| 快思考层 | 从「设计未接」→「规则式已落地并实测」 |
| 工程化发挥分 | 71 → **77**（新增两个可复跑工具） |
| 综合掌握度 | 75 → **79** |
| 层级判定 | L4 早期 → **L4 进入（规则式分流成立，模型式仍未上线）** |

**未解决**：慢思考层额度精细分配（模型选择权不在我方），这一条不变。

---

## 七、产物清单

| 文件 | 权限 | 说明 |
|---|---|---|
| `scripts/dual_layer_router.py` | 755 | 双层分流器，五项确定性处理器 + FTG-001 类型门 |
| `scripts/capability_probe.py` | 755 | 十域探针，可月度复跑 |
| `truth/probe/PROBE-20261107.json` | 644 | 本次探针原始结果 |
| 本文档 | **444** | 验收报告 |

复跑命令：
```bash
python3 scripts/dual_layer_router.py --demo      # 拦截率
python3 scripts/capability_probe.py --json truth/probe/PROBE-$(date +%Y%m%d).json
```

---

Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ DUAL-LAYER-DEEP-FUSION V1.0 ｜ LOCKED

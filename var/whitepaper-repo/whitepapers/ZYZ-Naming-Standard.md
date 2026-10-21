# ZYZ Naming Standard · 宗源命名标准化方案

> 体系正名：**宗源 ZongYuan**（"中渊"为语音识别错误，作废）。
> 命名前缀：**ZYZ** = 宗源根（ZongYuan-Z）。

---

## 1. 前缀规则

- 白皮书 / 资产目录统一格式：`ZYZ-<MODULE>-<IDENTIFIER>-V<MAJOR>.<MINOR>`
  - 例：`ZYZ-MASTER-V1.0`、`ZYZ-FUSION-COMPUTE-RESONANCE-V1.0`、`ZYZ-A2A-GATEWAY-V1.0`
- 仓库命名统一前缀：`zongyuan-`（小写连字符），例：`zongyuan-root`、`zongyuan-kernel`、`zongyuan-whitepaper`。
- 历史大写仓库 `ZONGYUAN-ROOT` / `ZONGYUAN-SHARED-DATALAKE` 保留不动，作为归档。

## 2. 双层命名策略

### 2.1 体系个性化层（专名保留，不得丢弃 / 改写）

| 体系专名 | 拼音 / 英文标识 | 说明 |
|----------|------------------|------|
| 自治系统 | autonomous-system / zizhi-xitong | 对应 ZONGYUAN-ROOT 元极恒一自治操作系统本体 |
| 自治内核 | autonomous-kernel / zizhi-kernel | 对应 `zongyuan-kernel` 仓库 |
| 火斗云智 | huodouai / huodou-yunzhi | 保留 huodouai.com 域名体系 |
| 昆仑洞天 | kunlun-dongtian | 短剧 / 视觉生产体系，仓库内 `kunlun-dongtian/` 命名空间子目录 |

### 2.2 主流对齐层（通用技术词用业界英文 + 中文对照）

| 英文 | 中文 | 备注 |
|------|------|------|
| agent | 智能体 | A2A / multi-agent |
| truth | 真值 | truth-store / truth-distill |
| whitepaper | 白皮书 | 本仓库主体资产类型 |
| kernel | 内核 | autonomous-kernel / zongyuan-kernel |
| pipeline | 流水线 | drama-pipeline / production-pipeline |
| federation | 联邦 | federation-protocol / federated memory pool |
| data lake | 数据湖 | shared-datalake / DATA-LAKE-PERSIST |
| scheduler | 调度器 | autonomous-scheduler |
| cognition | 认知 | cognition-evolution |
| evolution | 进化 | meta-evolution-engine |
| compute | 算力 | compute-field / three closed loops |
| resonance | 谐振 | standing-wave resonance |
| singularity | 奇点 | dark architecture |
| riemann | 黎曼 | Riemannian manifold |
| token | 词元 | token meta-encoding |
| symbol | 符号 | symbolic emergence |
| interop | 互操作 | A2A interop |
| gateway | 网关 | A2A gateway / memory gateway |
| mcp / oauth | MCP / OAuth | protocol integration |
| memory pool | 记忆池 | shared-brain memory pool |
| angle / dimlock | 开角 / 维度锁 | angle-dimlock |
| tianxin | 天心 | celestial center (专名保留拼音) |
| fusion | 融合 | 大一统融合版 |
| visual production | 视觉生产 | kunlun-dongtian 命名空间 |

## 3. 仓库命名约定

- 新仓库统一小写 `zongyuan-` 前缀连字符命名。
- 本仓库 `zongyuan-root` 为主仓库，所有白皮书标准化归位根。
- 模型仓归档：`zongyuan-whitepaper`（魔搭 ModelScope）。
- 旧数据湖 / 旧大写仓库保留不动，仅作归档引用：
  - `ZONGYUAN-SHARED-DATALAKE`（三端归档）
  - `ZONGYUAN-ROOT`（Gitee 大写仓，因 Gitee 忽略大小写保留不动）
  - `zongyuan-root-backup`
  - `huodouai.com` 域名体系（火斗云智官网）

## 4. 模块目录约定

仓库根下 6 个模块目录，目录名 = 拼音 + 编号，内含 `README.md` 标注中文名与英文标准名：

| 目录 | 中文名 | 英文标准名 |
|------|--------|------------|
| `01-zizhi-xitong/` | 自治系统 | autonomous-system |
| `02-zhenzhi-cunchu/` | 真值存储 | truth-store |
| `03-renshi-jinhua/` | 认知进化 | cognition-evolution |
| `04-gongcheng-shijian/` | 工程实践 | engineering-practice |
| `05-shijue-shengchan/` | 视觉生产 | visual-production（内含 `kunlun-dongtian/` 子命名空间） |
| `06-lianbang-xieyi/` | 联邦协议 | federation-protocol |

## 5. 历史仓库归档说明

- `ZONGYUAN-SHARED-DATALAKE` —— 共享数据湖三端归档，保留不动。
- `ZONGYUAN-ROOT` —— Gitee 大写仓（Gitee 忽略大小写，与 `zongyuan-root` 视为同名，故 Gitee 端不推送，仅在 AtomGit / 魔搭端归位）。
- `zongyuan-root-backup` —— 备份仓，保留不动。
- `huodouai.com` —— 火斗云智官网域名，保留不动。
- 本仓库 `zongyuan-root`（AtomGit）为主目标，魔搭 `zongyuan-whitepaper` 为云端归档。

---

锚定标识：Ω₀⊂⊙∞⊂Ω | DID-BR-000002

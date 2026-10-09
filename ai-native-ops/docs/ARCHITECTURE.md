# AI-Native Cloud Ops Engine (ANCE) · 架构文档

> 版本：V1.0
> 日期：2026-09-03
> 体系：ZONGYUAN-ROOT · SD-RND-001 研发子域
> 定位：AI Agent驱动的自然语言云基础设施部署引擎

---

## 一、体系定位

ANCE 是一套"自然语言驱动的云基础设施部署与运维引擎"，将 LLM 的推理规划能力与传统 IaC（Terraform/Ansible）的确定性执行能力结合，实现：

```
用户说："帮我在腾讯云部署一个2核4G的服务器，装好Nginx，配置HTTPS"
    ↓
ANCE 自动完成：意图理解 → 资源规划 → 代码生成 → 执行部署 → 验证修复 → 经验沉淀
```

**核心主张**：AI 负责"想"（理解、规划、排错），IaC 负责"做"（确定性执行），真值引擎负责"记"（经验沉淀复用）。

---

## 二、七层架构

```
┌─────────────────────────────────────────────────┐
│  L7  交互层    自然语言CLI / API / 豆包工作台集成  │
├─────────────────────────────────────────────────┤
│  L6  意图层    意图理解 → 结构化部署计划            │
├─────────────────────────────────────────────────┤
│  L5  规划层    部署计划 → 执行步骤DAG              │
├─────────────────────────────────────────────────┤
│  L4  生成层    执行步骤 → Terraform/Ansible/Shell  │
├─────────────────────────────────────────────────┤
│  L3  执行层    SSH / 云API / 本地命令 执行器        │
├─────────────────────────────────────────────────┤
│  L2  验证层    端口/服务/证书/健康检查 自动验证      │
├─────────────────────────────────────────────────┤
│  L1  修复层    错误诊断 → 修复策略 → 自动修复       │
├─────────────────────────────────────────────────┤
│  L0  真值层    部署经验 → 可复用配置 → Merkle锁档   │
└─────────────────────────────────────────────────┘
```

---

## 三、核心模块

| 模块 | 文件 | 职责 |
|------|------|------|
| 意图解析器 | core/intent_parser.py | 自然语言 → DeploymentPlan 结构化对象 |
| 规划器 | core/planner.py | DeploymentPlan → 执行步骤DAG |
| 执行器 | core/executor.py | 统一执行接口，调度SSH/云API/本地 |
| 验证器 | core/verifier.py | 部署后自动验证（端口/HTTP/服务/证书） |
| 修复引擎 | core/healer.py | 错误模式匹配 → 修复策略 → 自动重试 |
| 真值引擎 | core/truth_engine.py | 部署经验沉淀为可复用真值配置 |
| SSH适配器 | adapters/ssh_adapter.py | paramiko封装，支持密钥/密码/批量 |
| 云API适配器 | adapters/cloud_adapter.py | 腾讯云/阿里云/AWS统一接口 |
| IaC生成器 | generators/iac_generator.py | Terraform HCL / Ansible Playbook 生成 |
| 锁档器 | core/lock_archive.py | SHA256+Merkle+eFuse 部署确权 |

---

## 四、核心数据流

```
用户输入（自然语言）
    │
    ▼
┌──────────────┐
│ IntentParser │  提取：云厂商/资源规格/软件栈/域名/证书
└──────┬───────┘
       │ DeploymentPlan
       ▼
┌──────────────┐
│   Planner    │  生成：步骤DAG（依赖关系/并行/串行）
└──────┬───────┘
       │ ExecutionDAG
       ▼
┌──────────────┐
│ IacGenerator │  生成：main.tf / playbook.yml / deploy.sh
└──────┬───────┘
       │ IaC Artifacts
       ▼
┌──────────────┐
│   Executor   │  执行：terraform apply / ansible-playbook / ssh
└──────┬───────┘
       │ ExecutionResult
       ▼
┌──────────────┐     失败     ┌──────────────┐
│   Verifier   │ ───────────→ │    Healer    │
└──────┬───────┘              └──────┬───────┘
       │ 成功                        │ 修复后重试
       ▼                             ▼
┌──────────────┐              回到Executor
│ TruthEngine  │  沉淀：部署配置→真值缓存→下次复用
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ LockArchive  │  确权：SHA256+Merkle+eFuse
└──────────────┘
```

---

## 五、与传统方式的对比

| 维度 | 纯IaC | 纯AI Agent | ANCE（混合） |
|------|-------|-----------|-------------|
| 输入 | HCL/YAML代码 | 自然语言 | 自然语言（生成IaC） |
| 执行确定性 | 极高 | 中 | 极高（IaC执行） |
| 排错能力 | 无 | 强 | 强（AI诊断+IaC重试） |
| 经验复用 | 模块/角色 | 对话记忆 | 真值引擎（结构化） |
| 审计合规 | Git历史 | 对话记录 | Git+锁档凭证双保险 |
| 学习门槛 | 高 | 低 | 低 |

---

## 六、部署模式

### 模式A：纯AI执行（当前豆包工作台模式）
- AI直接生成Shell命令 → SSH执行 → 验证修复
- 适合：快速原型、单台服务器、探索性部署

### 模式B：AI生成IaC + CI/CD执行（推荐生产模式）
- AI生成Terraform/Ansible → Git提交 → CI/CD流水线执行
- 适合：生产环境、多服务器、合规要求高

### 模式C：混合模式（ANCE终极形态）
- AI生成IaC → 本地预览 → 人工确认 → 执行 → 验证 → 真值沉淀
- 适合：企业级生产环境

---

## 七、真值缓存机制

每次成功部署后，TruthEngine 将部署配置结构化存储：

```json
{
  "truth_id": "TRUTH-DEPLOY-20260903-001",
  "pattern": "tencent_cloud_2c4g_nginx_https",
  "cloud": "tencent",
  "spec": {"cpu": 2, "memory": 4, "disk": 50},
  "software": ["nginx", "certbot", "ufw"],
  "iac_artifacts": {"terraform": "main.tf", "ansible": "playbook.yml"},
  "verification": {"ports": [80, 443], "https": true},
  "sha256": "...",
  "reuse_count": 0
}
```

下次相同/相似需求时，直接从真值缓存召回，跳过意图理解和规划阶段，大幅提升效率和确定性。

---

## 八、技术栈

| 层 | 技术 |
|----|------|
| 语言 | Python 3.10+ |
| SSH | paramiko / fabric |
| 云API | 腾讯云SDK / 阿里云SDK / boto3 |
| IaC | Terraform / Ansible |
| LLM | 豆包方舟API（doubao-seed-2-0-lite） |
| 配置 | YAML |
| 锁档 | SHA256 + Merkle-DAG |
| CLI | click / typer |

---

Ω₀⊂⊙∞⊂Ω｜ANCE架构文档 V1.0 · ZONGYUAN-ROOT · DID-BR-000002

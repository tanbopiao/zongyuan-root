# ANCE · AI-Native Cloud Ops Engine

> AI原生云运维引擎 · 自然语言驱动的云基础设施部署与运维

Ω₀⊂⊙∞⊂Ω｜ZONGYUAN-ROOT · SD-RND-001 研发子域 · DID-BR-000002

---

## 是什么

ANCE 是一套"自然语言驱动的云基础设施部署引擎"，将 AI 的推理规划能力与传统 IaC 的确定性执行能力结合：

```
用户说："帮我在腾讯云部署2核4G服务器，装Nginx+Docker，配置HTTPS"
    ↓
ANCE 自动完成：意图理解 → 资源规划 → IaC生成 → 执行部署 → 验证修复 → 经验沉淀
```

## 核心特性

- **自然语言输入**：说人话就能部署，不需要学Terraform/Ansible
- **AI+IaC混合**：AI负责想（理解/规划/排错），IaC负责做（确定性执行）
- **自动验证修复**：部署后自动验证端口/HTTP/SSL/服务，失败自动诊断修复
- **真值引擎**：每次成功部署沉淀为可复用配置，下次相似需求直接召回
- **Merkle锁档**：所有部署配置SHA256+Merkle-DAG确权，不可篡改
- **多云支持**：腾讯云/阿里云/AWS统一接口

## 快速开始

### 安装

```bash
cd ai-native-ops
pip install -r requirements.txt
```

### 命令行使用

```bash
# 部署（生成IaC，不执行）
python3 cli.py deploy "腾讯云广州2核4G，装nginx和docker，配置huodouai.com的HTTPS"

# 部署并远程执行
python3 cli.py deploy "腾讯云2核4G nginx" --host 123.207.202.158 --key ~/.ssh/id_rsa --verify

# 验证服务器状态
python3 cli.py verify --host 123.207.202.158 --domain huodouai.com --ssl

# 查看真值缓存
python3 cli.py truth list

# 错误诊断修复
python3 cli.py heal --error "502 Bad Gateway"
```

### Python API使用

```python
from core.intent_parser import parse_intent
from core.planner import plan_deployment
from generators.iac_generator import IacGenerator
from core.executor import Executor, SSHExecutor
from core.verifier import Verifier
from core.healer import Healer
from core.truth_engine import TruthEngine

# 1. 意图解析
plan = parse_intent("腾讯云2核4G nginx docker huodouai.com https")

# 2. 真值召回
truth = TruthEngine()
matched = truth.recall(plan)

# 3. 规划
dag = plan_deployment(plan)

# 4. 生成IaC
gen = IacGenerator(output_dir="output")
artifacts = gen.generate_all(plan)  # terraform + ansible + shell

# 5. 执行
ssh = SSHExecutor(host="1.2.3.4", key_file="~/.ssh/id_rsa")
executor = Executor(ssh_executor=ssh)
results = executor.execute_dag(dag)

# 6. 验证
verifier = Verifier(host="1.2.3.4")
report = verifier.verify_deployment(domain="huodouai.com", check_ssl=True)

# 7. 失败修复
if not report.all_passed:
    healer = Healer(executor=executor)
    fixes = healer.heal("nginx配置错误")

# 8. 沉淀真值
if report.all_passed:
    truth.record(plan, dag, report, artifacts)
```

## 目录结构

```
ai-native-ops/
├── cli.py                    # 命令行入口
├── config/
│   └── default.yaml          # 默认配置
├── core/
│   ├── intent_parser.py      # 意图解析器（自然语言→部署计划）
│   ├── planner.py            # 规划器（部署计划→执行DAG）
│   ├── executor.py           # 执行器（SSH/本地统一执行）
│   ├── verifier.py           # 验证器（端口/HTTP/SSL/服务）
│   ├── healer.py             # 修复引擎（10种错误模式自动修复）
│   └── truth_engine.py       # 真值引擎（经验沉淀+Merkle锁档）
├── adapters/
│   └── ssh_adapter.py        # SSH适配器（paramiko+subprocess双后端）
├── generators/
│   └── iac_generator.py      # IaC生成器（Terraform/Ansible/Shell）
├── templates/                # 配置模板
├── truth_cache/              # 真值缓存
├── docs/
│   └── ARCHITECTURE.md       # 架构文档
├── output/                   # 生成的IaC文件
└── requirements.txt
```

## 七层架构

| 层 | 模块 | 职责 |
|----|------|------|
| L7 交互层 | cli.py | 自然语言CLI/API |
| L6 意图层 | intent_parser | 自然语言→部署计划 |
| L5 规划层 | planner | 部署计划→执行DAG |
| L4 生成层 | iac_generator | Terraform/Ansible/Shell生成 |
| L3 执行层 | executor + ssh_adapter | SSH/云API执行 |
| L2 验证层 | verifier | 端口/HTTP/SSL/服务验证 |
| L1 修复层 | healer | 10种错误模式自动诊断修复 |
| L0 真值层 | truth_engine | 经验沉淀+Merkle锁档 |

## 内置错误修复模式

| 错误 | 严重度 | 自动修复 |
|------|--------|----------|
| 网络连接失败 | P1 | 检查并开放防火墙端口 |
| Nginx配置错误 | P1 | 检查配置语法和错误日志 |
| 权限不足 | P2 | 修复文件权限 |
| 端口被占用 | P1 | 查找并释放占用进程 |
| SSL证书申请失败 | P2 | 检查域名解析后重试 |
| 磁盘空间不足 | P0 | 清理日志和缓存 |
| 内存不足/OOM | P0 | 检查内存占用，增加Swap |
| 502/503后端不可用 | P1 | 检查后端服务和端口 |
| Nginx代理路径错误 | P2 | 修正proxy_pass路径 |
| SSL证书过期 | P1 | 自动续期证书 |

## 与传统方式对比

| 维度 | 纯IaC | 纯AI Agent | ANCE |
|------|-------|-----------|------|
| 输入 | HCL/YAML | 自然语言 | 自然语言（生成IaC） |
| 执行确定性 | 极高 | 中 | 极高 |
| 排错能力 | 无 | 强 | 强 |
| 经验复用 | 模块 | 对话记忆 | 结构化真值 |
| 学习门槛 | 高 | 低 | 低 |

## 部署模式

- **模式A 纯AI执行**：AI直接生成Shell→SSH执行（适合快速原型）
- **模式B AI+IaC+CI/CD**：AI生成Terraform→Git提交→流水线执行（推荐生产）
- **模式C 混合**：AI生成IaC→预览→确认→执行→验证→真值沉淀（企业级）

## 配置

编辑 `config/default.yaml` 或使用环境变量：

```bash
export DOUBAO_API_KEY="your-key"
export TENCENT_SECRET_ID="your-id"
export TENCENT_SECRET_KEY="your-key"
```

## 技术栈

- Python 3.10+
- paramiko（SSH）
- Terraform / Ansible（IaC执行）
- 豆包方舟API（LLM增强，可选）
- SHA256 + Merkle-DAG（锁档确权）

---

Ω₀⊂⊙∞⊂Ω｜ANCE V1.0 · AI原生云运维引擎 · ZONGYUAN-ROOT · DID-BR-000002

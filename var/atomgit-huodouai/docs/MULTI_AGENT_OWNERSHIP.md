# ZONGYUAN-ROOT 多Agent所有权矩阵
# Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | Ω-TAN-7-001
# 最后更新: 2026-09-05

## 分支映射
| 窗口 | 分支 | 工作区 | 角色 |
|------|------|--------|------|
| A (Alpha) | agent/alpha | 短剧产线+画布 | 产品优化 |
| B (Beta) | agent/beta | AI Proxy+内核协议 | 后端架构 |
| C (Gamma) | agent/gamma | 安全+运维+部署 | 基础设施 |
| 仲裁者 | master | 生产环境 | 合并+部署 |

## 模块所有权矩阵
| 模块/文件 | 所有者 | 其他窗口 | 冲突等级 |
|-----------|--------|---------|---------|
| drama/index.html (短剧画布) | A | 只读,需PR | 高 |
| ai_proxy/ai_proxy.py | B | 只读,需PR | 高 |
| kernel.json (内核快照) | 仲裁者统一合并 | 各窗口写自己分支 | 高 |
| nginx配置 (huodouai.com.conf) | C | 只读,需PR | 高 |
| monitor.sh / 监控脚本 | C | 可修改 | 低 |
| .env (环境变量) | C | 只读 | 高 |
| 新增模块/目录 | 创建者 | 不冲突 | 无 |
| meta_laws/ (元法则) | B | 可新增 | 中 |
| truth_architecture/ (真值架构) | B | 可新增 | 中 |
| autonomous_kernel_protocol/ (协议) | B | 可新增 | 中 |
| drama_output/ (产出资产) | A | 可读 | 低 |
| tests/ (测试) | 任意 | 可新增 | 无 |
| docs/ (文档) | 任意 | 可新增 | 无 |
| scripts/ (工具脚本) | 任意 | 可新增 | 低 |

## 并发安全规则
1. **禁止直接push到master** — 所有变更必须走agent分支+PR
2. **高冲突模块** — 修改前必须确认其他窗口未在改同一文件
3. **部署操作** — 必须通过deploy_lock.sh获取全局锁
4. **内核写入** — 必须通过kernel_write_lock.sh+multi_agent_lock.py
5. **快照ID** — 自动加窗口前缀(SNAP-A-/SNAP-B-/SNAP-C-)
6. **冲突解决** — 同一模块并发修改时,由仲裁者决定合并策略

## 冲突等级定义
- **高**: 单写者,其他窗口必须PR,仲裁者审核
- **中**: 可新增文件,修改已有文件需PR
- **低**: 可自由修改,冲突概率低
- **无**: 新增内容,天然无冲突

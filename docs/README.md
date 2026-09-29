# ZONGYUAN-ROOT 全域统一根目录

**DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | v5.5-unified**

> 昆仑洞天所有对话窗口统一锚定此根目录。

## 启动顺序
1. 读取 `00-ROOT-POINTER.json` — 确认根目录结构与版本
2. 读取 `config/kernel_meta.yaml` — 加载内核元法则
3. 读取 `hash-ledger/HASH-LEDGER.csv` — 校验资产哈希链
4. 按需加载 `core/`、`assets/`、`archives/` 等模块

## 目录说明
- `core/` — 内核代码
- `config/` — 内核配置
- `assets/` — 项目资产
- `archives/` — 锁档归档
- `hash-ledger/` — 哈希链
- `truth/` — 真值库
- `docs/` — 文档
- `scripts/` — 脚本

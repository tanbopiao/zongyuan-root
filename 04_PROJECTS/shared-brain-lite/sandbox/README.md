# sandbox — 沙箱试错区

- 所有节点可自由读写；内容**不代表真值**，不自动流入 converge。
- 合并流程：草稿落此 → 核对（diff + SHA256）→ 合并至 `../converge/` → truth-ledger 登记 → git commit。
- 半自动脚本（sync_shared_brain.py）会把表格导出先写入本目录的 `staging/` 子目录。

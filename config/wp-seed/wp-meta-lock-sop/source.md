---
name: meta-lock-sop
description: "元秩序全域锁档标准操作流程SOP。对任意资产集合执行7步标准化锁档：资产整理→SHA256哈希确权→元秩序台账登记→多目标并行归档（自治内核/云盘/知识库）→Merkle-DAG主链追加→链完整性校验→锁档回执生成。触发词：全域锁档、批量锁档、资产锁档、哈希确权、元秩序归档、锁档SOP、eFuse固化、五层锁防。当用户需要对一批文件/文档/代码执行标准化全域锁档，或要求将资产写入元秩序台账并生成可溯源哈希链时使用。"
---

# 元秩序全域锁档 SOP

固定DID：`DID-BR-000002` | 确权标识：`Ω₀⊂⊙∞⊂Ω` | 锁档等级默认Lv8

## 前置检查

1. 确认待锁档资产已全部落盘到本地目录
2. 确认 `meta-order-archive` 技能可用（脚本路径：`.user_skills/meta-order-archive/scripts/`）
3. 获取全局账本当前根哈希作为父哈希：
   ```bash
   python3 -c "import json; d=json.load(open('.user_skills/meta-order-archive/locked/M9_global_ledger.json')); print(d['current_root_hash'])"
   ```

## 7步标准流程

### 步骤1｜资产整理
- 收拢全部产出：源码、文档、变更说明、测试用例、配图、diff
- 剔除临时草稿、调试日志、冗余中间文件
- 统一命名规范：`{卷宗编号}_{资产名称}.{ext}`
- 填写元信息：卷宗名称、版本号、父卷宗ID、改动简述、优先级

### 步骤2｜SHA256哈希确权
对每个文件计算SHA256，生成资产清单：
```bash
python3 -c "
import hashlib, os, json
d = '待归档目录'
files = [f for f in os.listdir(d) if os.path.isfile(os.path.join(d,f))]
result = []
for f in sorted(files):
    h = hashlib.sha256(open(os.path.join(d,f),'rb').read()).hexdigest().upper()
    result.append({'file': f, 'sha256': h})
print(json.dumps(result, indent=2, ensure_ascii=False))
"
```

### 步骤3｜元秩序台账登记 + Merkle-DAG上链
调用批量归档引擎，自动完成台账登记 + 链式哈希上链：
```bash
cd .user_skills/meta-order-archive
python3 scripts/batch_archive.py \
  --input-dir {资产目录绝对路径} \
  --parent-hash {步骤1获取的父哈希} \
  --output {资产目录}/_batch_archive_manifest.json
```

引擎自动完成：
- 每个资产SHA256计算
- 链式哈希节点计算（chain_hash = SHA256(parent:asset)）
- 全局账本根哈希更新
- 归档清单JSON生成

### 步骤4｜多目标并行归档
| 归档目标 | 操作 |
|---|---|
| ZONGYUAN-ROOT自治内核 | 卷宗真值包写入内核真值库，固化索引 |
| lark-drive云盘 | 创建版本独立目录，上传全部资产，开启只读 |
| lark-wiki知识库 | 新建知识库页面，录入文档与索引，嵌入确权哈希 |
| meta-order-archive台账 | 步骤3已完成持久化 |

### 步骤5｜确认最终根哈希
```bash
python3 -c "import json; d=json.load(open('{资产目录}/_batch_archive_manifest.json')); print(d['final_root_hash'])"
```

### 步骤6｜链完整性校验（必做）
手动复核全链哈希，确保无断裂：
```bash
python3 -c "
import json, hashlib
d = json.load(open('{资产目录}/_batch_archive_manifest.json'))
parent = d['initial_root_hash']
all_ok = True
for a in d['archives']:
    calc = hashlib.sha256(f'{parent}:{a[\"sha256\"]}'.encode()).hexdigest().upper()
    ok = (calc == a['new_root_hash'])
    if not ok: all_ok = False
    print(f'{'✅' if ok else '❌'} {a[\"asset_id\"]} | {a[\"filename\"][:40]}')
    parent = a['new_root_hash']
print(f'最终根匹配: {\"✅\" if parent == d[\"final_root_hash\"] else \"❌\"}')
print(f'全链校验: {\"✅ 全部通过\" if all_ok else \"❌ 存在断裂\"}')
"
```

### 步骤7｜锁档回执生成
生成标准化锁档回执文档，包含：
- 批次ID、执行时间、DID、锁档等级
- 资产清单（序号/资产ID/卷宗编号/名称/SHA256）
- 链式哈希溯源图（初始根→各中间节点→最终根）
- 链完整性校验结果
- 全域状态快照表
- 锁档后操作指引（版本更新/回滚/校验）

保存为 `{资产目录}/_全域锁档执行回执.md`

## 锁档后规则

- **禁止原地覆写**：已锁档资产永久只读
- **版本更新**：新建子卷宗，锚定父卷宗哈希，重复本SOP
- **回滚**：指定历史根哈希即可回滚
- **异常处置**：云盘/知识库写入失败时，标记部分归档失败，修复后新建子卷宗锁档，禁止修改旧卷宗

## 输出规范

每次锁档必须交付：
1. 锁档回执文档（Markdown）
2. 批量归档清单（JSON）
3. 全链校验结果（文本）

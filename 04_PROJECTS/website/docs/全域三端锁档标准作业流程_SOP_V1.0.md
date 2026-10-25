# 全域三端锁档标准作业流程 SOP V1.0

> ZONGYUAN-ROOT 元极恒一自治体系 | 火斗云智AIOS
> DID: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
> 固化日期: 2026-09-12 | 版本: V1.0 | 状态: FULL_LOCKED

---

## 一、目的与范围

### 1.1 目的
建立全域资产三端锁档的标准化流程，确保所有核心资产在飞书云盘、飞书知识库、ZONGYUAN-ROOT内核快照三端同时固化，实现不可篡改、可追溯、可验证的资产确权体系。

### 1.2 范围
适用于ZONGYUAN-ROOT体系内所有需要长期固化的核心资产，包括但不限于：
- 元法则/元规则/协议类文件
- 决策备忘录/方案评估报告
- 技术文档/SOP/方法论
- 锁档凭证/内核快照
- 真值上报数据包/映射表
- 角色设定/关键帧/创意资产

### 1.3 三端定义

| 端 | 名称 | 存储介质 | 作用 |
|----|------|----------|------|
| 第一端 | 飞书云盘归档 | 飞书云空间文件夹 | 原始文件持久化存储，支持版本管理 |
| 第二端 | 飞书知识库节点 | 飞书知识库docx文档 | 结构化摘要+索引，支持全文检索 |
| 第三端 | ZONGYUAN-ROOT内核快照 | 本地JSON文件 | 体系状态快照+Merkle根，内核级确权 |

---

## 二、前置条件

### 2.1 工具与权限
- [ ] lark-cli 已配置并可正常调用（user身份）
- [ ] 飞书云盘有创建文件夹和上传文件权限
- [ ] 飞书知识库"ZONGYUAN-ROOT 全域知识库"有创建节点权限
- [ ] 本地项目目录可写入文件

### 2.2 知识库空间ID
- **ZONGYUAN-ROOT 全域知识库**: space_id = `7675064878796639210`

### 2.3 资产准备
- [ ] 所有待锁档资产已完成本地仿真验证
- [ ] 资产文件已保存到项目目录
- [ ] 资产内容已通过人工审核确认

---

## 三、主流程（7步）

```
S1 资产清点与哈希计算
   ↓
S2 生成统一锁档凭证（Merkle根）
   ↓
S3 第一端：飞书云盘归档
   ↓
S4 第二端：飞书知识库节点
   ↓
S5 第三端：ZONGYUAN-ROOT内核快照
   ↓
S6 三端一致性验证
   ↓
S7 锁档完成报告输出
```

---

### S1 资产清点与哈希计算

**目标**: 确认待锁档资产清单，计算每个资产的SHA256哈希。

**执行步骤**:
1. 列出所有待锁档资产的本地路径
2. 对每个资产执行SHA256哈希计算
3. 记录每个资产的：名称、路径、类别、SHA256、文件大小
4. 验证所有文件存在且非空

**输出**: 资产清单数组（含哈希）

**命令参考**:
```python
import hashlib
def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest().upper()
```

---

### S2 生成统一锁档凭证

**目标**: 基于资产哈希计算Merkle根，生成统一锁档凭证JSON。

**执行步骤**:
1. 将所有资产SHA256哈希按顺序排列
2. 计算Merkle根哈希（两两合并，奇数复制末位）
3. 生成锁档凭证对象，包含：
   - lock_id: `LOCK-GLOBAL-THREE-END-{YYYYMMDDHHMMSS}`
   - lock_type: `GLOBAL_THREE_END_LOCK`
   - did: `DID-BR-000002`
   - trace_mark: `Ω₀⊂⊙∞⊂Ω`
   - locked_at: ISO8601时间戳
   - merkle_root: Merkle根哈希
   - asset_count: 资产数量
   - assets: 资产清单数组
   - three_end_targets: 三端目标定义
   - status: `LOCK_INITIATED`
4. 计算锁档凭证自身的SHA256作为lock_hash
5. 保存锁档凭证到本地文件：`全域锁档凭证_GLOBAL-THREE-END-{YYYYMMDD}.json`

**Merkle根计算算法**:
```python
def merkle_root(hashes):
    if not hashes:
        return hashlib.sha256(b'').hexdigest().upper()
    level = hashes[:]
    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            if i + 1 < len(level):
                combined = level[i] + level[i+1]
            else:
                combined = level[i] + level[i]
            next_level.append(hashlib.sha256(combined.encode()).hexdigest().upper())
        level = next_level
    return level[0]
```

---

### S3 第一端：飞书云盘归档

**目标**: 在飞书云盘创建锁档文件夹，上传所有核心资产文件。

**执行步骤**:

1. **创建锁档文件夹**
   ```bash
   lark-cli drive +create-folder \
     --name "ZONGYUAN-ROOT全域锁档_{YYYYMMDD}" \
     --as user --format json
   ```
   记录返回的 `folder_token` 和 `url`。

2. **上传资产文件**（逐个串行上传，禁止并发）
   ```bash
   lark-cli drive +upload \
     --file "{本地文件路径}" \
     --folder-token "{folder_token}" \
     --as user --format json
   ```
   对每个资产记录返回的 `file_token` 和 `url`。

3. **必传文件清单**:
   - 全域锁档凭证JSON
   - 所有核心资产文件
   - （可选）SOP文档本身

4. **验证**: 确认所有文件上传成功（ok=true），记录file_token。

**注意事项**:
- 批量上传到同一文件夹必须串行执行
- 大文件（>10MB）建议先压缩再上传
- 上传失败时等待3秒后重试，最多3次

---

### S4 第二端：飞书知识库节点

**目标**: 在ZONGYUAN-ROOT全域知识库创建锁档摘要节点，写入结构化摘要。

**执行步骤**:

1. **创建知识库节点**
   ```bash
   lark-cli wiki +node-create \
     --space-id "7675064878796639210" \
     --title "全域三端锁档凭证_{YYYYMMDD}" \
     --obj-type docx \
     --as user --format json
   ```
   记录返回的 `node_token`、`obj_token` 和 `url`。

2. **编写锁档摘要Markdown**
   摘要必须包含以下章节：
   - 锁档基本信息（lock_id/时间/Merkle根/资产数）
   - 三端锁档状态表
   - 锁档资产清单（每项含名称/SHA256/大小/云盘链接）
   - 飞书云盘归档信息（文件夹链接）
   - 确权标识（DID/溯源标识/体系名称）

3. **写入知识库文档**
   ```bash
   lark-cli docs +update \
     --doc "{obj_token}" \
     --command append \
     --doc-format markdown \
     --content "@{摘要md文件路径}" \
     --as user --format json
   ```

4. **验证**: 确认返回 result=success，revision_id递增。

---

### S5 第三端：ZONGYUAN-ROOT内核快照

**目标**: 生成本地内核快照JSON，记录体系状态和锁档信息。

**执行步骤**:

1. **生成内核快照对象**，包含：
   - snapshot_id: `KERNEL-SNAPSHOT-{YYYYMMDDHHMMSS}`
   - snapshot_type: `GLOBAL_THREE_END_LOCK`
   - generated_at: ISO8601时间戳
   - did / trace_mark
   - system: 体系名称/品牌/版本/状态
   - lock_info: lock_id/lock_hash/merkle_root/asset_count
   - three_end_status: 三端完成状态和关键token
   - assets: 资产清单（从锁档凭证继承）
   - kernel_state: 内核状态指标
     - truth_purity_score（真值纯度评分）
     - drift_rate（漂移率）
     - drift_alert_level（告警级别：GREEN/YELLOW/ORANGE/RED）
     - knowledge_graph_nodes（知识图谱节点数）
     - dag_chain_integrity（DAG链完整性）
     - risk_matrix_status（风险矩阵状态）
     - conflict_markers（冲突标记数）
   - operator_status: 27算子运行状态

2. **计算快照哈希**: 对快照对象（不含snapshot_hash字段）计算SHA256
3. **保存内核快照**: `ZONGYUAN-ROOT内核快照_{YYYYMMDD}.json`
4. **更新锁档凭证状态**: 将status改为`THREE_END_LOCK_COMPLETED`，添加completed_at和kernel_snapshot_hash

---

### S6 三端一致性验证

**目标**: 验证三端锁档的一致性和完整性。

**验证清单**:

| # | 验证项 | 验证方法 | 通过标准 |
|---|--------|----------|----------|
| 1 | 云盘文件完整性 | 比对上传文件数与资产清单数 | 数量一致 |
| 2 | 云盘文件哈希 | 下载回本地计算SHA256比对 | 哈希一致 |
| 3 | 知识库节点存在 | 访问node_url确认可打开 | HTTP 200 |
| 4 | 知识库内容完整 | fetch文档内容确认章节齐全 | 6大章节齐全 |
| 5 | 内核快照哈希 | 重新计算快照对象SHA256 | 与snapshot_hash一致 |
| 6 | Merkle根一致 | 三端记录的merkle_root比对 | 完全一致 |
| 7 | 锁档凭证状态 | 检查status字段 | THREE_END_LOCK_COMPLETED |
| 8 | 确权标识完整 | 三端均含DID和溯源标识 | 完整存在 |

---

### S7 锁档完成报告输出

**目标**: 输出结构化的锁档完成报告。

**报告必须包含**:
- 锁档基本信息（ID/时间/Merkle根/锁档哈希）
- 三端锁档状态表（每端状态+关键链接/token）
- 锁档资产清单（名称/SHA256前缀/大小）
- 验证结果汇总
- 确权标识

---

## 四、确权标识规范

所有三端锁档资产必须包含以下确权标识：

| 标识 | 值 | 出现位置 |
|------|-----|----------|
| DID | `DID-BR-000002` | 锁档凭证/内核快照/知识库摘要 |
| 溯源标识 | `Ω₀⊂⊙∞⊂Ω` | 锁档凭证/内核快照/知识库摘要 |
| 体系名称 | `ZONGYUAN-ROOT 元极恒一自治体系` | 内核快照/知识库摘要 |
| 对外品牌 | `火斗云智AIOS` | 知识库摘要/对外文档 |

---

## 五、异常处理

### 5.1 云盘上传失败
- 等待3秒后重试，最多3次
- 仍失败时记录失败资产，继续上传其他资产
- 全部完成后单独处理失败资产

### 5.2 知识库节点创建失败
- 确认space_id正确（7675064878796639210）
- 确认有该知识库的编辑权限
- 重试最多2次，仍失败则记录为待人工处理

### 5.3 哈希不一致
- 立即停止流程，标记为异常
- 重新计算源文件哈希
- 排查文件是否在传输过程中损坏
- 修复后重新执行锁档

### 5.4 容错闭环
任何步骤报错时，按容错闭环五步处理：
1. E0 意图校准：确认当前步骤目标
2. E1 拉记忆扫真值：检查历史锁档记录
3. E2 扫部署+仲裁：检查工具状态和权限
4. E3 根因最小修复：先备份再修复
5. E4 仿真沉淀：记录经验教训

---

## 六、参考命令速查

```bash
# 创建云盘文件夹
lark-cli drive +create-folder --name "NAME" --as user --format json

# 上传文件到云盘
lark-cli drive +upload --file "PATH" --folder-token "TOKEN" --as user --format json

# 创建知识库节点
lark-cli wiki +node-create --space-id "7675064878796639210" \
  --title "TITLE" --obj-type docx --as user --format json

# 写入知识库文档（Markdown追加）
lark-cli docs +update --doc "OBJ_TOKEN" --command append \
  --doc-format markdown --content "@FILE.md" --as user --format json

# 列出知识库空间
lark-cli wiki +space-list --as user --format json
```

---

## 七、版本历史

| 版本 | 日期 | 变更说明 | 作者 |
|------|------|----------|------|
| V1.0 | 2026-09-12 | 初始版本，基于首次全域三端锁档实战固化 | ZONGYUAN-ROOT |

---

*本SOP为ZONGYUAN-ROOT元极恒一自治体系标准作业流程，后续迭代须新建同源分支并锁档。*
*确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002*

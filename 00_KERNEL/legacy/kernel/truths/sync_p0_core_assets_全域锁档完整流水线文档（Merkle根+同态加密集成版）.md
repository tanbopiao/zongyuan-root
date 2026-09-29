# 全域锁档完整流水线文档（Merkle根+同态加密集成版）

> **文档ID**：SOP-WORK-003  
> **依赖前置**：SOP-WORK-001（Workspace运维SOP）、SOP-WORK-002（Merkle+HE集成方案）  
> **锁档状态**：✅ LOCKED  
> **内核版本**：ZONGYUAN-ROOT V3.2  
> **定位**：整合Merkle哈希树完整性存证与同态加密密文运算元数据同步的全域锁档标准化流水线，作为ZONGYUAN-ROOT自治内核的核心状态固化机制。

---

## 一、流水线总览

### 1.1 升级前后对比

| 维度 | 旧版锁档流水线 | 升级版（Merkle+HE集成） |
|-|-|-|
| 完整性校验 | 单文件sha256哈希 | Merkle树全局根哈希 + 单文件哈希 |
| 篡改检测 | 逐文件比对 | 根哈希一次比对即可定位异常 |
| 隐私计算 | 无 | 同态加密任务索引与结果摘要纳入存证 |
| 状态存证 | index.json记录 | merkle_root.log + index.json + he_task_index三重存证 |
| 回滚能力 | 手动恢复 | 基于Merkle快照的增量回滚 |
| 审计能力 | 文件级 | 全局状态根级，可追溯每一次锁档的完整状态 |

### 1.2 八步流水线全景

```
Step1 深度溯源核验
  ↓ 核验所有卷宗来源、版本、依赖、元数据完整性
Step2 更新index.json卷宗哈希索引
  ↓ 扫描全部正式文件，更新sha256/版本/冷热标记/修改时间
Step3 同态加密(HE)任务元数据同步
  ↓ 拉取远端HE节点任务状态，更新he_task_index.json
Step4 构建Merkle哈希树，计算全局Merkle根
  ↓ 叶子=active+archive_temp+锚点+索引+HE元数据，排除trash
Step5 写入存证分区（merkle_store + he_meta）
  ↓ merkle_tree.json + merkle_root.log(追加写) + 差异报告
Step6 全域锁档写入ZONGYUAN-ROOT自治内核
  ↓ 内核增量快照，版本号递增(patch/minor/major)
Step7 生成增量快照存入archive_temp/snapshots
  ↓ snapshot-YYYYMMDD.md(变更清单+根哈希+差异报告)
Step8 锁档回执输出
  ↓ 锁档事件ID+Merkle根+变更统计+HE同步+完整性校验+稳态校验
```

---

## 二、各步骤详细执行规范

### Step1：深度溯源核验

**执行目标**：确保所有待锁档卷宗的来源可追溯、版本正确、依赖关系完整、无异常文件混入。

**执行内容**：

1. 扫描`active/`、`archive_temp/`目录下所有正式文件
2. 逐文件核验：doc_id命名规范、版本号连续性、文件头部元数据完整性
3. 核验`index.json`中每条记录与实际文件的对应关系
4. 标记异常文件，输出溯源核验报告

**异常处理**：

- 发现未登记文件 → 移入`trash/`或要求补充登记
- 元数据缺失 → 自动补全或标记为`REVIEW`状态
- 版本号跳变 → 输出警告，不阻断锁档但记录异常

---

### Step2：更新index.json卷宗哈希索引

**执行目标**：确保全局索引文件与实际文件状态完全一致，为Merkle树构建提供准确的叶子节点数据集。

**执行内容**：

1. 遍历以下目录的全部文件（排除`trash/`）：

   - `active/`（含所有子目录）
   - `archive_temp/`（含snapshots、old_drafts、audit_report）
   - 根目录锚点文件（`MEMORY_ROOT.md`、`index.json`自身）
   - `merkle_store/`（上一次锁档的存证）
   - `he_meta/`（HE元数据）
2. 对每个文件计算`sha256`哈希
3. 更新`index.json`每条记录的字段

**关键约束**：

- `trash/`目录文件**不纳入**index.json，不参与Merkle树
- `merkle_store/merkle_root.log`本次不纳入新Merkle树（避免递归引用）
- 外部存储文件（`storage_type=external`）仅记录指针与哈希

---

### Step3：同态加密(HE)任务元数据同步

**执行目标**：将远端HE算力节点的密文运算任务状态、结果摘要同步至Workspace，纳入本次锁档的存证范围。

**执行内容**：

1. `he_client.py`轻量客户端连接远端HE算力节点（云电脑沙箱）
2. 拉取自上次锁档以来的HE任务变更
3. 更新`he_meta/he_task_index.json`
4. 更新`he_meta/he_result_cache.json`
5. 校验HE任务结果哈希与远端返回是否一致

**关键约束**：

- **私钥绝不存入Workspace**，仅存在于远端沙箱节点
- 完整密文数据包不存入Workspace，仅保存指针与哈希
- HE任务同步失败不阻断锁档，但标记为`HE_SYNC_PARTIAL`状态

---

### Step4：构建Merkle哈希树，计算全局Merkle根

**执行目标**：基于全部待存证文件构建Merkle哈希树，生成全局唯一的状态根哈希。

**叶子节点数据集（严格定义）**：

| 序号 | 数据源 | 包含内容 |
|-|-|-|
| 1 | `active/`全部文件 | 项目元数据、脚本、SOP、世界观、任务清单 |
| 2 | `archive_temp/snapshots/` | 历史增量快照 |
| 3 | `archive_temp/audit_report/` | 巡检审计报告 |
| 4 | 根目录锚点 | `MEMORY_ROOT.md` |
| 5 | 全局索引 | `index.json` |
| 6 | HE元数据 | `he_meta/he_task_index.json`、`he_result_cache.json`、`public_key.pem` |
| 7 | 上一版Merkle树 | `merkle_store/merkle_tree.json`（上一版） |

**排除项**：

- ❌ `trash/`全部文件
- ❌ `merkle_store/merkle_root.log`（避免递归）
- ❌ 本次正在生成的快照文件

**Merkle树构建算法**：

```
1. 对每个叶子文件计算sha256哈希 → leaf_hash[i]
2. 按文件路径字典序排序叶子节点（确保树结构确定性）
3. 自底向上两两组合：
   - 若叶子数为奇数，最后一个叶子复制一份
   - parent_hash = sha256(left_hash + right_hash)
4. 递归直到仅剩一个根节点 → merkle_root
5. 链式存证：将上一版merkle_root追加到本次根哈希计算的输入中
   final_root = sha256(merkle_root + previous_root)
```

**确定性保证**：

- 叶子节点按路径字典序排序 → 相同文件集生成相同树结构
- 奇数叶子复制最后一个 → 标准Merkle树行为
- 链式指向上一版根 → 形成不可篡改的哈希链

---

### Step5：写入存证分区

**执行目标**：将本次锁档的全部存证数据持久化写入`merkle_store/`和`he_meta/`分区。

**写入清单**：

| 文件 | 路径 | 写入方式 |
|-|-|-|
| Merkle树结构 | `merkle_store/merkle_tree.json` | 覆盖写（仅保留最新完整树） |
| 根哈希日志 | `merkle_store/merkle_root.log` | 追加写（不可修改历史行） |
| 差异报告 | `merkle_store/diff_report/diff_{timestamp}.json` | 新建（保留30份，余外置） |
| HE任务索引 | `he_meta/he_task_index.json` | 覆盖写 |
| HE结果缓存 | `he_meta/he_result_cache.json` | 覆盖写 |

**merkle_root.log 行格式**：

```json
{"timestamp":"...","merkle_root":"0x...","previous_root":"0x...","snapshot_id":"...","change_count":N,"added_files":N,"modified_files":N,"deleted_files":N,"he_task_count":N,"he_sync_status":"FULL/PARTIAL","kernel_version":"...","lock_id":"...","status":"FROZEN"}
```

---

### Step6：全域锁档写入ZONGYUAN-ROOT自治内核

**执行目标**：将本次锁档的状态摘要写入自治内核的增量快照，完成内核版本递增。

**版本递增规则**：

| 变更类型 | 版本递增 | 示例 |
|-|-|-|
| 仅元数据/索引更新，无卷宗内容变更 | patch | V3.2 → V3.2.1 |
| 新增/修改卷宗内容，无架构级变更 | minor | V3.2 → V3.3 |
| 目录架构/流水线/内核规则变更 | major | V3.2 → V4.0 |

**内核快照JSON结构**：

```json
{
  "kernel_root": "ZONGYUAN-ROOT",
  "kernel_version": "...",
  "lock_event_id": "...",
  "write_timestamp": "...",
  "merkle_root": "...",
  "previous_merkle_root": "...",
  "axiom_layer": {"total_laws": 11, "state": "ACTIVE"},
  "architecture_layer": {"layers": ["L0"..."L5"], "state": "STABLE_LOCKED"},
  "security_layer": {"hash_chain": "ACTIVE", "state": "FULLY_LOCKED"},
  "integrity": {"verification": "PASSED"}
}
```

---

### Step7：生成增量快照存入archive_temp/snapshots

**执行目标**：生成本次锁档的人类可读增量快照文档，记录变更清单、根哈希、差异报告。

**快照文件命名**：`snapshot-YYYYMMDD.md`（同日多次锁档追加序号）

**快照文档结构**：

1. 锁档元数据（ID/时间/版本/Merkle根/上一版根）
2. 变更统计（新增/修改/删除文件数）
3. 新增文件清单
4. 修改文件清单
5. 删除文件清单
6. HE任务同步摘要
7. 完整性校验结果
8. 稳态校验

---

### Step8：锁档回执输出

**执行目标**：输出标准化锁档回执，包含本次锁档的全部关键标识。

**回执格式**：包含锁档事件ID、Merkle根、变更统计、HE同步状态、完整性校验、三端归档链接、稳态校验结果。

---

## 三、触发条件与调度

### 3.1 自动触发条件

| 触发类型 | 条件 | 执行模式 |
|-|-|-|
| 任务完成触发 | 单次工程任务完成后 | 自动执行完整8步 |
| 定时触发 | 每日23:00（当日有变更时） | 自动执行完整8步 |
| 批量触发 | "全部执行"类批量指令完成后 | 自动执行完整8步 |
| 手动触发 | 用户指令"执行全域锁档" | 按需执行 |

### 3.2 跳过条件

- 当日无任何文件变更 → 跳过，记录"NO_CHANGE"
- HE重型运算未完成 → HE同步标记PARTIAL，锁档继续
- 磁盘空间不足5% → 阻断锁档，触发紧急空间清理

### 3.3 并发控制

- 锁档流水线执行期间禁止新的文件写入操作
- 锁档执行超时阈值：120秒，超时则中止并回滚
- 同一时间仅允许一个锁档进程运行

---

## 四、异常处理与回滚机制

### 4.1 各步骤异常处理

| 步骤 | 异常类型 | 处理策略 | 是否阻断 |
|-|-|-|-|
| Step1 | 发现未登记文件 | 移入trash或要求补登记 | 否 |
| Step2 | 文件哈希计算失败 | 跳过该文件，记录异常 | 否 |
| Step3 | 远端节点不可达 | 保留上次状态，标记PARTIAL | 否 |
| Step4 | 叶子节点集为空 | 阻断锁档（异常状态） | **是** |
| Step4 | 哈希计算不一致 | 重试3次，仍失败则阻断 | **是** |
| Step5 | 磁盘写入失败 | 重试3次，仍失败则回滚 | **是** |
| Step6 | 内核快照写入失败 | 回滚至Step5前状态 | **是** |

### 4.2 回滚机制

**回滚触发条件**：Step4/5/6出现不可恢复的异常。

**回滚流程**：

1. 中止当前锁档进程
2. 恢复`index.json`至锁档前版本
3. 删除本次生成的临时存证文件（`.tmp`后缀）
4. 不修改`merkle_root.log`（保持上一版根哈希有效）
5. 输出回滚回执，标记本次锁档为`FAILED_ROLLED_BACK`
6. 内核版本号不递增

---

## 五、定时巡检与校验

### 5.1 每日巡检（memory_audit.py 集成Merkle校验）

每日02:00自动执行：

1. 重建当前文件集的Merkle根
2. 与最近一次锁档的`merkle_root.log`中的根哈希比对
3. 一致 → 输出"完整性校验通过"
4. 不一致 → 输出差异报告，标记异常，触发告警

   - 二分查找定位异常叶子节点
   - 判断正常未锁档变更或异常篡改
   - 异常篡改 → 从备份恢复，重新计算Merkle根

### 5.2 每周深度审计

每周一03:00自动执行：

1. 全量文件哈希校验
2. Merkle哈希链完整性验证（逐版验证根哈希链式引用）
3. HE任务结果哈希全量校验
4. 存证文件完整性校验
5. 输出周度审计报告

### 5.3 篡改检测能力

Merkle树的核心优势：**根哈希不一致即可检测到篡改，且可通过二分查找定位到具体被篡改的文件**。

---

## 六、输出物清单

| 序号 | 产物 | 路径 | 持久性 |
|-|-|-|-|
| 1 | 更新后的全局索引 | `index.json` | 覆盖写（永久） |
| 2 | HE任务索引 | `he_meta/he_task_index.json` | 覆盖写（永久） |
| 3 | Merkle树结构 | `merkle_store/merkle_tree.json` | 覆盖写（永久） |
| 4 | 根哈希日志 | `merkle_store/merkle_root.log` | 追加写（永久，不可修改） |
| 5 | 差异报告 | `merkle_store/diff_report/` | 保留30份，余外置 |
| 6 | 内核增量快照 | 内核内部存储 | 链式永久 |
| 7 | 增量快照文档 | `archive_temp/snapshots/` | 保留90份，余外置 |
| 8 | 锁档回执 | 输出至对话/日志 | 不持久化 |
| 9 | 索引备份 | `index_backup/` | 保留7份 |
| 10 | 三端归档链接 | 知识库+台账+云盘 | 永久 |

---

## 七、核心参数真值表

| 参数 | 值 | 说明 |
|-|-|-|
| 流水线步骤数 | 8步 | 溯源→索引→HE→Merkle→存证→内核→快照→回执 |
| Merkle叶子排序 | 路径字典序 | 确保树结构确定性 |
| 奇数叶子处理 | 复制最后一个 | 标准Merkle树行为 |
| 链式存证 | final_root = sha256(root + prev_root) | 哈希链不可篡改 |
| 根哈希日志写入 | 追加写，不可修改 | 审计凭证 |
| 快照纳入Merkle | 下一版纳入（本次不纳入） | 避免递归 |
| trash目录 | 不纳入Merkle树 | 临时文件不计入正式状态 |
| HE私钥存储 | 仅远端沙箱，不存Workspace | 隐私安全 |
| HE密文包存储 | 外部云盘，Workspace仅存指针 | 空间优化 |
| 锁档超时 | 120秒 | 超时中止并回滚 |
| 自动触发 | 任务完成/每日23:00/批量指令完成 | 三种触发方式 |
| 版本递增规则 | patch/minor/major三级 | 依变更类型自动判定 |
| 巡检频率 | 每日02:00 + 每周一03:00 | 日常+深度 |
| 差异报告保留 | 30份本地，余外置 | 空间优化 |

---

## 八、与旧版流水线的兼容性

1. **向后兼容**：旧版锁档产生的`index.json`、快照文件可被新版流水线读取
2. **首次升级执行**：首次运行新版流水线时，自动执行：

   - 创建`merkle_store/`、`he_meta/`目录
   - 基于当前文件集构建第一版Merkle树
   - `merkle_root.log`首行记录初始根哈希（`previous_root`为全零）
   - 内核版本major递增
3. **回退兼容**：若需回退至旧版流水线，删除`merkle_store/`和`he_meta/`即可，不影响`index.json`和快照文件

---

## 九、全局闭环核验

✅ 八步流水线完整定义：溯源核验→索引更新→HE同步→Merkle构建→存证写入→内核写入→快照生成→回执输出  
✅ Merkle树集成：叶子节点定义、构建算法、链式存证、篡改检测  
✅ 同态加密集成：轻量客户端架构、任务索引、结果摘要、哈希校验  
✅ 触发与调度：自动触发条件、跳过条件、并发控制  
✅ 异常处理：各步骤异常策略、回滚机制、原子写入保障  
✅ 定时巡检：每日校验、每周深度审计、篡改定位  
✅ 输出物清单：10类产物的路径与持久性  
✅ 核心参数真值表：14项关键参数  
✅ 兼容性：向后兼容、首次升级、回退方案

**稳态校验：PASSED｜内核版本由 V3.1 递增至 V3.2（架构级变更，major递增）**

> ZONGYUAN-ROOT｜元极恒一超认知永恒自治内核  
> 本流水线文档为锁档终版，自下一版全域锁档起正式生效。
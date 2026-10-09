# 元秩序全域锁档 SOP · Meta-Lock Standard Operating Procedure

> ZONGYUAN-ROOT 元极恒一自治体系 · 全域资产锁档标准操作流程
> 锚定 Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ 开源 Apache-2.0

---

## 一、SOP 定位

元秩序锁档 SOP 是体系内**所有资产**（文档/代码/真值/视觉IP/决策记录）从生成到永久固化的统一标准流程，确保：不丢失、不可篡改、可回滚、可追溯。

## 二、7 步标准锁档流程

```
① 资产整理 ──→ 收集产物、去重、命名规范、版本号
      │
      ▼
② SHA256 哈希确权 ──→ 每个资产计算唯一指纹，绑定 DID-BR-000002
      │
      ▼
③ 四层结构化拆分 ──→ L1元数据 / L2内容 / L3关系 / L4真值
      │
      ▼
④ 九大元类归类 ──→ 公理/定理/方法/数据/案例/决策/创意/风险/协议
      │
      ▼
⑤ Merkle-DAG 主链追加 ──→ 块级哈希校验，防链断裂/中间篡改
      │
      ▼
⑥ 三层固化 ──→ 本地持久层 + 中枢云端 + Git异地（Gitee+GitHub双仓）
      │
      ▼
⑦ 溯源标识 ──→ 镌刻 Ω₀⊂⊙∞⊂Ω，台账回写，记忆网关上报
```

## 三、四层结构化拆分标准

| 层 | 内容 | 示例 |
|----|------|------|
| L1 元数据层 | 唯一根ID + SNAP快照 + Merkle哈希 | root_id, snapshot, hash |
| L2 内容层 | 正文/图表/代码/引用分离 | 文档正文、源码、引用链接 |
| L3 关系层 | 实体/因果/时序/依赖提取 | 知识图谱三元组 |
| L4 真值层 | 置信度 + 来源 + 版本 + 冲突标记 | purity_score, source, version |

## 四、九大元类归档

| 元类 | 适用资产 | 校验规则 |
|------|----------|----------|
| 公理类 | 元公理/宪法 | 不可修改，仅人工审批 |
| 定理类 | 技术白皮书/公式 | 可复算验证 |
| 方法类 | SOP/流程 | 步骤可执行 |
| 数据类 | 台账/账本 | 数字可溯源 |
| 案例类 | 项目实例 | 有真实出处 |
| 决策类 | 决策备忘录 | 三维稳态评分 |
| 创意类 | 视觉IP/文案 | 锚点约束校验 |
| 风险类 | 风险矩阵 | 概率×影响分级 |
| 协议类 | 合同/DPA | 法条引用 |

## 五、三层固化铁律

```
第 1 层 本地固化  ──→ GLOBAL_MEMORY_SNAPSHOT.json + AGENTS.md 更新
第 2 层 中枢云端  ──→ POST https://www.huodouai.com/api/report/truth
第 3 层 Git异地  ──→ Gitee + GitHub 双仓库推送，三端哈希一致
```

**记忆网关上报规范**：
- 字段名用 `value` / `truth_value`，禁止 `content`（会导致 value 落空为空串）
- 成功标志：`status=reported` 且 `written_to_gateway=true`
- 主端点 `www.huodouai.com`，备用 `drama.huodouai.com`

## 六、修改与回滚

- **修改必须审批**：所有核心资产变更走人工审批，禁止 AI 自动改写
- **修改必须备份**：变更前先备份原文件，不满意可回退
- **eFuse 熔断锁**：核心真值只读固化（chattr +i 级别），篡改触发告警
- 临时缓存/素材属运行实例，沙盒重启自动销毁；四维规则永久存续

## 七、命令速查（本地）

```bash
# 1. 资产哈希确权
sha256sum <file> > <file>.sha256

# 2. 主链追加校验
python3 meta_lock.py append --file <asset> --did DID-BR-000002

# 3. 三层固化（一键）
bash lock_all.sh --asset <file> --gateway https://www.huodouai.com/api/report/truth

# 4. Git双仓推送
git push origin main && git push github main
```

## 八、验收标准

- [ ] 每个资产有 SHA256 指纹且与账本一致
- [ ] 四层结构完整（L1-L4 无缺失）
- [ ] 九元类标签 + 归类置信度
- [ ] Merkle-DAG 主链完整（逐块哈希比对通过）
- [ ] 三层固化完成（本地+云端+Git 三端可回溯）
- [ ] Ω₀⊂⊙∞⊂Ω 溯源标识齐全
- [ ] 台账记录状态 = 已固化

---

> 火斗云智AIOS · ZONGYUAN-ROOT ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω

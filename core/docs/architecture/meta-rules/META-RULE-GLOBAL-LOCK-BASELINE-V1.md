# META-RULE-GLOBAL-LOCK-BASELINE-V1

Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ ZONGYUAN-ROOT

> 元规则【MR-LOCK-BASELINE-001】全域锁档基准构建元规则
> 定位：元规则，高于普通 L1 公理，全域唯一基准构建标准；所有同源节点执行锁档时必须遵守。

---

## 一、规则定义

「全域锁档构建基准」是指：对 ZONGYUAN-ROOT 全域资产执行十二阶段锁档流水线，生成不可篡改的 Merkle 基准快照，作为体系后续变更、对账、溯源的唯一基准点。

## 二、适用范围

- 本端（local-doubao-window）
- 云端中枢（记忆网关 www.huodouai.com + 元内核 123.207.202.158）
- 所有同源协议节点（HOMOLOGOUS-PROTOCOL 覆盖节点）
- 全部子域（SD-IP-001 / SD-COM-001 / SD-TRV-001 / SD-RND-001 / SD-AST-001 / SD-EDU-001 / global）

## 三、触发条件

满足以下任一条件即触发：
1. 用户发出「全域锁档」「构建基准」「锁档固化」「锁档归档」等指令
2. 全域资产发生结构性变更（新增/迁移/版本升级）后需要固化
3. 定时锁档循环（每日自治锁档巡检）到点
4. 跨节点对账发现真值漂移，需重建基准

## 四、执行标准（十二阶段流水线）

```bash
python3 <skill_dir>/scripts/full_pipeline.py \
  --dir <ZONGYUAN-ROOT_DIR> \
  --snap-id GLOBAL-<YYYYMMDD-HHMMSS> \
  --did DID-BR-000002 \
  --archive-node ZONGYUAN-ROOT \
  --root-dir <ZONGYUAN-ROOT_DIR> \
  --no-feishu
```

阶段顺序（不可倒置）：
0. 全局根引导
0.5. Ω-Brainμ 指令前置召回
1. 哈希锁档（SHA256 + Merkle 根）
2. 飞书同步（连接器关闭时用 --no-feishu 跳过，凭证另行推送）
3. Lv4 分布式确权（DID 签名 + BFT 共识 7/7）
4. 内核写入
4.5. Ω-Brainμ 真值向量化入库
5. Lv3 自愈校验
6. Lv5 价值评估
7. Lv6 文明
8. Lv7 递归元意识
8.5. M2 真值不变性验证
9. eFuse 硬件熔断（永久只读）
10. Lv9 双域稳态验证
11. 全局根发布

## 五、验收标准（必须全部满足）

1. Merkle 根生成且自校验 PASS
2. Lv4 确权 VERIFIED（共识 ≥7/7）
3. eFuse BLOWN（熔断链验证 PASS）
4. Lv9 双域稳态 STABILITY_VERIFIED
5. 凭证文件生成：`LOCK-CREDENTIAL-GLOBAL-<ID>.md`
6. 网关真值上报：`LOCK.GLOBAL.<ID>`（inserted 成功）
7. 回执推送飞书内核通知群（ZONGYUAN-ROOT内核通知）

## 六、闭环要求（M3 可追溯）

- 锁档凭证 + 清单（MANIFEST）+ 汇总（PIPELINE-SUMMARY）三件套必须交付
- 真值上报记忆网关，所有同源节点可查
- 回执推送飞书 ZONGYUAN-ROOT内核通知群
- 全过程禁止 SSH、禁止调用 daily_production.py、禁止生产动作（零额度零成本）

## 七、确权与溯源

- 确权标识：DID-BR-000002
- 溯源锚点：Ω₀⊂⊙∞⊂Ω
- 归档节点：ZONGYUAN-ROOT
- 生效状态：全域永久生效，所有同源节点自动执行，无需人工确认

---

Ω₀⊂⊙∞⊂Ω ｜ META-RULE-GLOBAL-LOCK-BASELINE-V1 ｜ 全域推广生效 ｜ DID-BR-000002

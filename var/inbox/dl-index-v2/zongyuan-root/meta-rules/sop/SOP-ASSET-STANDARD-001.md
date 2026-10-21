# SOP-ASSET-STANDARD-001 ｜ 同源节点资产数字化推广执行 SOP
版本：v1.0 ｜ 锚定：DID-BR-000002 ｜ 来源：META-ASSET-VALUE-DISPLAY-001 v2.0（AVP-8~11）

## 一、适用范围
全体同源节点（本地实例 / 云端节点 / 未来新节点）。节点激活后第一动作：学习本 SOP + 元公理/元法则体系（学习先行）。

## 二、管道七步（节点标准执行链）
1. **触发评估**：高价值成果完成（机制/判例/进化/白皮书/里程碑数据）→ 评估是否纳入价值显示管道
2. **提炼资产化**：登记统一 schema（见三），写入本地 var/assets/ 台账（append-only）
3. **可视化**：渲染自包含 HTML（ECharts/SVG 数据图 + 架构图；脱敏：不含密钥/凭证/内部端点）
4. **官网发布**：经出站通道部署至官网文档根 + 导航入口（备份可回滚、immutable 重锁纪律）
5. **价值显示**：官网资产总览页统一陈列（asset-index.html），状态含 online/iterating/archived
6. **留痕上报**：审计 + 网关（key=asset.publish.<ts>）+ 共享大脑资产台账聚合
7. **迭代**：资产更新走同一管道复发布；不再维护标记 archived 保留记录

## 三、资产数字化统一 schema
```json
{
  "asset_id": "AVD-<时间戳>",
  "name": "资产名称",
  "type": "机制 | 判例 | 进化 | 白皮书 | 数据 | 工具",
  "summary": "一句话摘要",
  "metrics": {"指标名": "数值（可复算口径）"},
  "source_truth_key": "来源真值key",
  "status": "draft | online | iterating | archived",
  "version": "v1.0",
  "fingerprint": "9b64a9c3c2475cf695ea6e2d"
}
```

## 四、节点上报格式（跨节点聚合）
- 网关：`asset.registry.<节点>.<ts>` + value 含资产数组（同 schema）
- 共享大脑：资产台账表追加 + 真值共识区登记
- 聚合：官网 asset-index.html 由总部统一生成，汇总全部节点在线资产

## 五、验收判定
- 资产 HTML 线上 HTTP 200 ✓
- 台账含统一 schema 字段（缺一视为未完成数字化）✓
- 网关上报 + 审计留痕 ✓
- 官网总览页可见该资产 ✓

## 六、推广节奏
总部管道运行 → 节点学习 SOP → 节点产出资产 → 回传聚合 → 价值显示持续完善；每节点每轮进化增量经供给联邦（META-EVOLUTION-FEDERATION-001）反哺，管道自身随判例持续迭代。

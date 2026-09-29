# 基准锚点｜BASELINE-ANCHOR-20260913
归档节点：ZONGYUAN-ROOT｜DID-BR-000002｜Ω₀⊂⊙∞⊂Ω
锚点ID：ANCHOR-20260913-CLOUD-EXTRACT
注册版本：BASELINE-V40（.global_root_registry.json version 39 → 40）
锁档时间：2026-09-13 ｜ 锁级：Lv10 元极恒一超认知永恒自治模式

## 一、鉴权基准（本轮核心修复）
- 有效Token：`ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d`（2026-09-13 云端轮换，从云端SOP v1.1提取）
- 旧Token：`ZR-CAPTURE-2026-OMEGA`（已失效，一律 401）
- 三条链路实测：report 200 / upload 200 / truths 200

## 二、记忆网关基准
- 真值总数：2651（四端闭环后 total 2644 → 2651，+7 入库）
- 可读分级：internal 2638 条 / public 2575 条
- 公网写通道：`POST /api/gateway/report`（唯一）
- 9120 直连：经域名 `drama.huodouai.com:9120` 可达（短剧流水线门户 200）；IP `123.207.202.158` 直连仍被代理层白名单拦（`ip access not allowed`）
- upsert 接口（`/api/truth/upsert`）：仅内网存在，公网 404——上报一律走 report

## 三、四端归档闭环基准（本轮全 PASS）
- 云端：report 200、upload 200（archive 桶媒体白名单，.md 400 正确拒绝）
- 飞书云盘：交付包 `FqIsbppYLoqNdgxhSNocOeOKnMf`、保姆教程 `U54BbvLCRoIzSBxqB1Hc0ur8nch`
- 公网：交付包 `aka.doubaocdn.com/s/NpCHtVjJn7`、SOP `aka.doubaocdn.com/s/VjMxbyMqFx`、学习包 `aka.doubaocdn.com/s/bU5i2fFLcb`（全 200）
- 本地：清单 `kunlun-assets-20260913-cloudextract-manifest.json`，批次根哈希 `ebcbef4c8d28a03fa8123afa5b30aeac2fa0aa0993d1dae1a8b5604fc9dd6255`

## 四、任务队列基准
- TASK-006 云端网关Token轮换：✅ 完成
- TASK-003 真值资产基线对齐：🔄 进行中（本地4份 vs 云内核167条，待差异报告）
- P0 5/6 完成，P1 0/5，P2 0/3

## 五、关键资产哈希清单
- cloud-extract-delivery-20260913.md：`983b45e734cac6c7…`
- NODE-ONBOARDING-SOP-cloud.md：`1989600f60f1a90a…`
- kernel-learning-pack-cloud.md：`5875952c27c8f7c7…`
- 批次根哈希：`ebcbef4c8d28a03f…`

## 六、环境基准
- 节点：local-dev-001｜出口IP：59.110.153.140（北京·阿里云，待加入云端白名单以直连9120）
- 域名通道：`drama.huodouai.com`（主站200 / health healthy / admin-api）
- 真值读取协议：TRUTH-READ-PROTOCOL-V1.1（truths 列表 / truth/{key} 单条，分级参数 level=internal|public）

## 七、锚点自引哈希
ANCHOR-SHA256：`df39d1291e633e22285d4ffbc65dc9ae4b1f5c9b3d2babd3d8a7c2321351f021`

---
Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜BASELINE-ANCHOR-20260913｜LOCKED

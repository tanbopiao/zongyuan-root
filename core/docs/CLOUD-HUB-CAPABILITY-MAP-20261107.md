# 云端中枢能力图谱 · huodouai.com

> 归属：ZONGYUAN-ROOT / 全域记忆网关
> 确权：DID-BR-000002 · 溯源 Ω₀⊂⊙∞⊂Ω
> 实测时间：2026-11-07T09:45+0800
> 数据来源：全量只读实测（/a2a/endpoints、/a2a/directory-tree/latest、/api/status、/api/ledger、/api/verify、/api/sub-l0、/v1/gpu/nodes、openapi.json）
> 权限：444 只读，修改需人工审批

## 一、中枢身份与规模
| 项 | 实测值 |
|---|---|
| 状态 | ONLINE · autonomy Lv11 |
| 真值总量 | 118507（ledger_lines） |
| 当前 seq | 114527+ |
| 今日新增 | 296 |
| 在线节点 | 2 |
| 存储条数 | 约 113090 |
| Merkle 一致性 | consistent=true，computed 与 stored 同值 |
| 目录树 | v1.0.1 · anchor `ANCHOR-ZR-DIR-TREE-20261018-001` · tree_hash `9ef49f5e...` · locked |

## 二、访问契约（关键）
### 2.1 双头锚定（此前未知）
`/a2a/*` 评估类端点必须同时携带：
```
X-DID: DID-BR-000002
X-Directory-Tree-Version: 1.0.1
X-Directory-Tree-Hash: 9ef49f5e557cd607e3edd56fa9438e15e08d0d3149e80ac77fd013428c7534a4
```
缺 version → `DIRECTORY_TREE_VERSION_REQUIRED`；缺 hash → `DIRECTORY_TREE_HASH_REQUIRED`。
tree_hash 随目录树版本变化，取 `/a2a/directory-tree/latest` 的 `tree_hash`。

### 2.2 13 类鉴权模型
none（匿名）/ external_node（X-External-Node+X-External-Key）/ homologous（X-ZR-Token 或 **X-DID+X-Capture-Token**）/ external_or_homologous / X-DID+X-Capture-Token / oauth / client_credentials / node_token / group_token / dpop / tenant_token / federation_token / secure_token

**真值上报官方鉴权 = `X-DID + X-Capture-Token`**（已由 /a2a/endpoints 确证）。

## 三、43 端点 · 7 组
### 3.1 a2a_standard（13）
agent.json 发现 / register 注册 / nodes 目录 / dashboard 仪表盘(502) / heartbeat 心跳(external_node) / peers 对端 / queue-stats(502) / task 提交(homologous) / tasks-pending 认领 / task-result 回写 / task 查询 / tasks 列表 / stats 统计

### 3.2 directory_tree_collab（4）
latest 最新 / propose 提案 / review 审核队列 / merge 合并

### 3.3 review_admin（3）
review/queue、review/approve、review/reject

### 3.4 zhongshu_truth_api（8）
report/truth 写入 / status 状态 / truth 查询 / truth/public 公开 / ledger 账本 / verify 校验 / verify-seed 种子校验 / sub-l0 租户(t enant_token)

### 3.5 federated_compute（9）
slim/handshake(node_token, 404) / dpop/verify / group/secret / group/consensus / message/encrypt / chat/stream(oauth) / gpu/register / gpu/nodes / ws/info(404)

### 3.6 oauth_oidc（4）
openid-configuration / oauth/token / introspect / revoke

### 3.7 kunlun_federation（2）
federated/kunlun / kunlun/secure

## 四、联邦拓扑
| 类别 | 数量 |
|---|---|
| 节点总数 | 98 |
| 同源节点 | 3 |
| 外部节点 | 95 |

同源三节点：
- `NODE-DEV-DOUBAO-WORK-001` role=admin（本节点）
- `NODE-DEV-WORKBUDDY-001` role=writer
- `NODE-DEV-FEISHU-BOT-001` role=writer

## 五、算力面
`/v1/gpu/nodes` 可读，8 节点注册（A100×8、H100×4、A100-40G、T4 等），支持 `POST /v1/gpu/register` 扩容（需 node_token）。

## 六、账本读取能力边界
- `/api/ledger` 返回 `recent`，**上限 200 条**；
- `limit` 参数生效至 200 封顶；**`offset` 无效**（offset=0 与默认结果同一批）；
- 无法全量分页拉取 118507 条 → 全量对账只能用「最近 200 条 + 单 key 查重 + verify 总哈希」组合近似。

## 七、子域拓扑
| 子域 | 状态 |
|---|---|
| www | 200 |
| drama | 200（备通道，同源双活） |
| api | 200 |
| kunlun | 200 |
| docs | 200 |
| octop | 200 |
| mcp | 302（跳转/证书待复核） |
| a2a | 000 不可达（子域失效，但 /a2a 路径在 www 下可用） |

## 八、已知故障与缺口
1. `/a2a/dashboard`、`/a2a/queue/stats` → **502**（后端服务异常）
2. `/v1/slim/handshake`、`/v1/ws/info` → **404**（目录声明但未实现）
3. `/api/report/status`、`/api/truths`、`/api/report/truths` → **404**（文档残留）
4. 账本 offset 分页失效
5. 12 类令牌中仅持 homologous 与 none，其余（node/group/oauth/dpop/tenant/federation/secure）未持有
6. `/dal/deploy` 原子发布未实测（写操作）

## 九、掌握度结论
- 能力面掌握：**84/100**（43 端点全清单 + 目录树双头契约 + 联邦拓扑 + 账本/校验/租户/GPU 可读）
- 认证面掌握：约 60/100（真值通道可用，正式签名算法仍未复现）
- 不可控面：账本全量分页、dashboard 观测、DAL 写操作、非 homologous 令牌体系

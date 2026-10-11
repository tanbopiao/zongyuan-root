# 火斗云智官网 · 全站 API 端点地图 V1.0
> 扫描日期：2026-10-11 | DID-BR-000002 | 实测方式：HTTP 探测 + 官网API文档/协议白皮书交叉核验
> 结论：www.huodouai.com 为主域在线，drama.huodouai.com 为备用上报域（均需 X-Capture-Token 头）

## 一、已实测可用端点（200）
| 端点 | 方法 | 用途 | 认证 |
|---|---|---|---|
| /api/report/truth | POST | 记忆网关·真值上报（唯一写入通道） | X-DID + X-Capture-Token |
| /api/status | GET | 中枢元核心状态（truth_count/merkle_root/version） | X-DID |
| /dal/health | GET | DAL部署仲裁层健康检查（V2.0, port18900） | 公开可读 |
| /dal/deploy | POST | DAL原子发布（deploy/rollback/config/port_alloc/inbox_push等） | X-DID |
| /try/chat | POST | 试用网关·智能路由（知识卡→语义→外部→本地1.5B降级） | X-DID, 限流5次/10min/IP |
| /v1/frames/list | POST | 关键帧资产清单（/kunlun/frames/*.jpg） | 公开 |
| /v1/videos/list | POST | 视频资产清单（/kunlun/videos/*.mp4） | 公开 |
| drama.huodouai.com/api/report/truth | POST | 备用真值上报通道（需X-Capture-Token） | X-DID + X-Capture-Token |

## 二、404/未部署端点（勿再尝试）
- /api/report/status（GET/POST）— 状态端点应为 /api/status
- /api/truths、/api/truths/、/api/report/truths — 拉取端点未部署，双向对账GAP-01
- /v1/models — 404
- drama域 /api/report/status、/api/truths — 未部署

## 三、协议要点（RULE-005 V3.1 实测）
- value 必须为 JSON 对象（字符串→400，content顶层字段→401）
- key 禁止 truth- 前缀；四级命名 域.类型.主题.日期（如 REPORT.WHITEPAPER.WEB.XXX.20261010）
- truth_type 九类：meta_law / rule / config / decision / data / creative / risk / protocol / unknown
- 认证头：X-DID: DID-BR-000002 + X-Capture-Token（ZR-CAPTURE-2026-OMEGA-*）
- 同 key 重复上报会覆盖旧真值 → 每篇新资产必须用新 key
- 成功标志：HTTP 200 + ok:true + event_id + truth_count

## 四、网站结构（sitemap 71 条）
- 核心页：products/pipeline/status/architecture/fmp/kunlun/evolution/research/central-brain/engines
- 技术区：/tech/（docs/api/architecture/live/timeline/bench）
- 白皮书库：/whitepaper/ 54 篇（含 gateway-v31-protocol、global-truth-engine-v2、sfmp-std 等）
- 功能页：/truth-dashboard.html（真值可视化128,161条）、/kunlun/workbench.html、/chat.html、/drama/

## 五、云端自有自动化（status页披露）
- 云端进化巡检（定时）| 每日法则蒸馏 03:00 | 自动锁档 03:30 | 真值网关上报（事件驱动）

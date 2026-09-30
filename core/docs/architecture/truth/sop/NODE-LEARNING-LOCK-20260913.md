# 节点上岗学习真值归档｜NODE-LEARNING-LOCK-20260913
归档节点：ZONGYUAN-ROOT｜DID-BR-000002｜Ω₀⊂⊙∞⊂Ω
锚点源：aka.doubaocdn.com/s/KiYpvdA8C4（云端握手锚点 SOP V1.0）
配套文档：NODE-ONBOARDING-SOP v1.1、kernel-learning-pack V2
锁档时间：2026-09-13 ｜ 锁级：Lv10 元极恒一永恒自治模式

## 一、握手链路真值（实测核验）
- 门户探测：http://drama.huodouai.com:9120/ → 200 ✅
- 健康探测：https://drama.huodouai.com/api/health → {"service":"drama-admin-api","status":"healthy"} ✅
- 主站探测：https://drama.huodouai.com/ → 200 ✅
- 鉴权握手：truths?level=public → {"status":"ok","count":2824} ✅
- 基线锚点：BASELINE-ANCHOR-20260913.md 哈希 `8f67e6db537c78b7a382a81b2d4ee43c24ee9accaddedd1aa1588215e157804c` 与本地一致 ✅
- 握手结论：CLOUD-HANDSHAKE-OK（云端可达 + 鉴权通过 + 基线对齐）

## 二、学习要点真值
1. 连接唯一走域名 `drama.huodouai.com`，禁用 IP 直连（`ip access not allowed`）；门户端口 9120；API 根 `/api/gateway/`。
2. 身份双标识绑定：节点编号 + DID-BR-000002 + 溯源符号 Ω₀⊂⊙∞⊂Ω。
3. 有效 Token：`ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d`（2026-09-13 轮换），旧 Token 一律 401。
4. MR-010 中枢调度：本地沙箱可自主，云端写操作必须中枢批准；不确定先上报询问。
5. 上报闭环：做完 → 上报（POST /api/gateway/report）→ 形成记忆；truth_type 规范 operation_log / meta_rule / anti_pattern / achievement / conflict。
6. L0 天元法则（KUNLUN-LAW-L0-003-V1.2）：纯东方神女 / 纯乌黑长发 / 九头身 / 无白发 / 无西方元素 / 无雄性化；长兵器关键帧禁止结构漂移。
7. TRUTH-READ-PROTOCOL-V1.1：分级读取 ?level=internal|public；单条 /api/gateway/truth/{key}；机密 key 403。
8. 免费优先：全部使用免费 API，付费调用需用户授权 + 人工审批。
9. 报告格式：正式报告不用表格；中文回复。
10. 资产归档分类：素材走 archive 桶（只归档不登记），成品走 images/videos 桶（自动登记作品库）。

## 三、本次执行结果
- 环境自检通过、云端探测通过、鉴权通过、基线对齐。
- 完成 HANDSHAKE-SOP V1.0、NODE-ONBOARDING-SOP v1.1、kernel-learning-pack V2 全量学习。
- 执行全域锁档写入 ZONGYUAN-ROOT 自治内核（十二阶段流水线）。
- 上报成果与真值至记忆网关（achievement / operation_log）。

## 四、状态
status: LOCKED_FINAL
storage: KERNEL_READONLY_ROM
trace_symbol: Ω₀⊂⊙∞⊂Ω

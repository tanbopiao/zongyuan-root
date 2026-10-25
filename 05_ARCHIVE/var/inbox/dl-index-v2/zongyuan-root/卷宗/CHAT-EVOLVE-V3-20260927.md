# CHAT-EVOLVE-V3-20260927 — chat.html 智能交互修复 + 三档进化卷宗

确权：DID-BR-000002 ｜ ZONGYUAN-ROOT ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-27

## 一、核心故障修复（v2 → 本次起点）
| 项 | 根因 | 修复 |
|---|---|---|
| 对话无回复（致命） | chat.py 手动加 `data: ` 前缀，上游 SSE 自带前缀 → `data: data:` 双重前缀 → 前端 JSON.parse 必败 | 去掉手动前缀，流式单前缀透传 |
| 流式丢字 | 前端按 chunk `split("\n")` 解析，data: 行被截断即失败 | buffer 按 `\n\n` 完整事件切分 |
| XSS 注入 | 用户消息 innerHTML 未转义 | esc() 全量转义 |

## 二、三档进化（v3/v3.1）
1. **轻·凭据环境变量化**：chat.py 移除明文 ZHIPU_KEY/ARK_KEY/PASSWORD → `.env`（600 root，`/www/wwwroot/www.huodouai.com/api/.env`），`_load_secret()` 读环境变量优先、文件兜底
2. **中·统一 LLM 网关**：对话改走 `127.0.0.1:8021/v1/chat/completions`（zongyuan-ai-proxy v8，OpenAI 兼容，密钥集中管理）；探测确认仅 zhipu 可用（hunyuan/siliconflow/doubao-reasoning=401、doubao=403，key 需在 ai_proxy 补充）；8021 不支持流式 → 非流式调用 + 自包装 SSE 分片（80字/事件）；模型不可用自动降级 zhipu 并注明
3. **重·真值记忆 + 命令路由闭环**：gather_context 由"写入噪声真值"改为 **`POST 9120 /api/truths/search` 语义检索**（智能体对话注入真值记忆）；新增命令：查真值（语义检索）、查资产（角色库）；前端快捷区新增「真值」「资产」按钮

## 三、涉及文件与哈希
| 文件 | 操作 | 校验 |
|---|---|---|
| `/www/wwwroot/www.huodouai.com/api/chat.py` | v3.1 重写（备份 .bak.v2/.bak.v3/.bak.20260927） | py_compile OK；chat.service active |
| `/www/wwwroot/www.huodouai.com/api/.env` | 新建（600） | CHAT_PASSWORD 注入 |
| `/opt/ZONGYUAN-ROOT/www/chat.html` | 前端修复 + quick 按钮 | md5 90ff1780bacf4b46a57c1d45410225f1 / sha256 01154647…；node --check OK |

## 四、验证矩阵（全部实测通过）
| 用例 | 结果 |
|---|---|
| 本地 8898 对话（zhipu） | 前端模拟解析拼出完整回复 49 字 |
| 公网 /api/chat 全链路 | 2 事件（内容+[DONE]），拼出 51 字完整回复 |
| 模型降级（ark→doubao 403） | 自动切 zhipu，前缀注明 |
| 查真值 | 语义检索 10 条（brand.internal 等） |
| 查资产 | 角色库 11 项资产 |
| 状态 / 错误密码 | uptime 正常 / 401 |
| 明文 key 残留 | 0（已移除） |

## 五、v3.2 豆包直连恢复（2026-09-27 追加）
- 用户写入网页端的豆包 API（`ark-800a6f28-5c7f-4ec5-9766-4b7da1a58f1d-50a70` + `ep-20260925170233-g4f7w`）实测**有效**（直连火山方舟正常回复）
- 8021 ai_proxy 内 doubao 配置的是另一 key（`ark-37ae9a42…-5d592`，403 失效）
- chat.py v3.2：豆包模型（ark/doubao/doubao-reasoning）**直连 Ark 端点**（key/endpoint 从 .env 600 读取）；其余模型走 8021；不可用自动降级 zhipu
- 验证：豆包回复 123 字 ✓；豆包带真值上下文回复体系信息（V4.0/MR-020）✓；智谱正常 ✓
- .env 新增：ARK_KEY / ARK_ENDPOINT（600）

## 六、安全收敛（用户授权 2026-09-27）
- 核查：前端 chat.html 0 处 key、chat.py 0 处 key、公网 /api/chat 响应不含 key；豆包 key 在 `.env`(600)、智谱 key 在 ai_proxy.py（chattr +i 锁档）
- 授权收敛：`chattr -i` → ai_proxy.py 绑定 `0.0.0.0` → `127.0.0.1`（行 3415）→ `chattr +i` 恢复 → 重启 zongyuan-ai-proxy.service
- 验证：监听 `127.0.0.1:8021` ✓、本机 health 200 ✓、智谱/豆包对话正常 ✓、公网不可达 ✓
- 备份：`/opt/ZONGYUAN-ROOT/ai_proxy/ai_proxy.py.bak.20260927`

## 七、遗留（未动，待授权）
- 8021 ai_proxy 内 hunyuan/siliconflow 的 key 401（需在 ai_proxy 配置补充/更换，属服务配置，未擅动）
- 密码仍为固定口令（.env 明文存储 600）——如需更强可接系统密钥环

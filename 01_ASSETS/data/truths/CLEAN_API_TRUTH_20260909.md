# ZONGYUAN-ROOT 全域有效API真值总册
DID-BR-000002｜本体主权根Ω-TAN-7-001｜ZONGYUAN-ROOT
快照：SNAP-20260909-CLEAN｜全局根版本：67｜LOCKED

---

## 一、大模型推理API（5个端点，全部实测连通）

### 智谱GLM-4-Flash — 永久免费主力
- Base URL：https://open.bigmodel.cn/api/paas/v4
- Key1：d63c880c0e1b424d8ad242f686e83451.vhHr5d5OQUY5UHNp
- Key2：1dfafcccce4e483287fe39bcdea7691c.78z9iYwdDTRiquIk
- 模型：glm-4-flash
- 延迟：~1900ms
- 用途：轻量高频、子域校验、免费容灾

### 通义千问Max（百炼兼容模式）
- Base URL：https://dashscope.aliyuncs.com/compatible-mode/v1
- 延迟：~1055ms
- 用途：中文深度理解、文档解析

### 通义千问Max（ws专属端点）
- Base URL：https://ws-g5kub337vd1fxnl5.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
- 延迟：~1217ms
- 用途：备用百炼端点

### 火山方舟豆包Pro（Key2）
- Base URL：https://ark.cn-beijing.volces.com/api/v3
- Key：ark-37ae9a42-c30e-40ae-9751-e51a7a37e38a-5d592
- Endpoint：ep-20260905152613-khsst
- 延迟：~4808ms
- 用途：昆仑洞天IP产线、中文创意

### 火山方舟豆包Pro（Key3）
- Key：b63e56d0-1671-46f1-9593-aae2c300edd9
- Endpoint：ep-20260905150108-hlg29
- 延迟：~6370ms
- 用途：备用火山端点

---

## 二、多模态生产API

### 通义万相视频生成
- Endpoint：https://ws-g5kub337vd1fxnl5.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis
- 模型：wan3.0-video
- 能力：文生视频、480P、5秒时长

---

## 三、工具API

### IMA知识库API（腾讯ima.copilot）
- Base URL：https://ima.qq.com/openapi
- Client ID：6334b7d16be857c3996d52a525fecd31
- 认证Header：ima-openapi-clientid / ima-openapi-apikey
- 已验证：POST /wiki/v1/search_knowledge_base（code=0，450ms）
- 用途：知识库检索、笔记CRUD、文件上传

### 百度网盘
- bdpan CLI v3.8.7（~/.local/bin/bdpan）
- BaiduPCS-Go v4.0.2（~/.local/bin/BaiduPCS-Go）
- 状态：CLI已安装，待授权登录

---

## 四、Git桥接同步（双远程已连通）

- GitHub：https://github.com/tanbopiao/zongyuan-root（tanbopiao）
- Gitee：https://gitee.com/huodou-cloud-intelligence-aios/ZONGYUAN-ROOT（火斗云智AIOS）
- 桥接脚本：git_bridge_sync.sh（status/push/pull/full）
- 最新提交：53eec14

---

## 五、云服务器

- IP：123.207.202.158（上海，2核2G，40GB，3Mbps）
- 8077：记忆网关（内网HMAC）
- 8080：业务网关（对外JWT）

---

## 六、飞书三端

- lark-cli已配置（user身份）
- 7份文档已归档至ZONGYUAN-ROOT法则知识库（space_id: 7679690520574037172）

---

## 七、路由真值

| 任务 | 首选 | 备选 |
|------|------|------|
| 轻量高频 | 智谱GLM-4-Flash（免费） | 通义千问Max |
| 中文创意 | 火山方舟豆包Pro | 通义千问Max |
| 深度推理 | 通义千问Max | 智谱GLM-4-Flash |
| 视频生成 | 通义万相wan3.0 | - |
| 知识库检索 | IMA API | 飞书Wiki |
| 文件归档 | 百度网盘 | 飞书云盘 |
| 代码同步 | GitHub+Gitee | - |

---

快照：SNAP-20260909-CLEAN｜全局根版本：67｜LOCKED

# ZONGYUAN-ROOT 全域资产真值总册
DID-BR-000002｜本体主权根Ω-TAN-7-001｜ZONGYUAN-ROOT
整理时间：2026-09-09｜快照：SNAP-20260909-FULL-SUMMARY
全局根版本：66｜LOCKED｜PERMANENT

---

## 第一章：大模型API连通真值

### 1.1 已实测连通（5个端点）

**智谱GLM-4-Flash（永久免费主力）**
- Base URL：https://open.bigmodel.cn/api/paas/v4
- Key1：d63c880c0e1b424d8ad242f686e83451.vhHr5d5OQUY5UHNp（2002ms）
- Key2：1dfafcccce4e483287fe39bcdea7691c.78z9iYwdDTRiquIk（1899ms）
- 模型：glm-4-flash
- 用途：轻量高频任务、子域局部校验、免费容灾

**通义千问Max（百炼兼容模式）**
- Base URL：https://dashscope.aliyuncs.com/compatible-mode/v1
- 延迟：1055ms
- 用途：中文深度理解、文档解析、复杂推理

**通义千问Max（ws专属端点）**
- Base URL：https://ws-g5kub337vd1fxnl5.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
- 延迟：1217ms
- 用途：备用百炼端点

**火山方舟豆包Pro（Key2）**
- Base URL：https://ark.cn-beijing.volces.com/api/v3
- Key：ark-37ae9a42-c30e-40ae-9751-e51a7a37e38a-5d592
- Endpoint：ep-20260905152613-khsst
- 延迟：4808ms
- 用途：昆仑洞天IP产线、中文创意写作

**火山方舟豆包Pro（Key3）**
- Key：b63e56d0-1671-46f1-9593-aae2c300edd9
- Endpoint：ep-20260905150108-hlg29
- 延迟：6370ms
- 用途：备用火山方舟端点

### 1.2 多模态生产API

**通义万相视频生成**
- Endpoint：https://ws-g5kub337vd1fxnl5.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis
- 模型：wan3.0-video
- 能力：文生视频、480P、adaptive比例、5秒时长

### 1.3 未连通API（封存隔离）

| API | 状态码 | 原因 |
|-----|--------|------|
| 火山方舟Key1 | 429 | SetLimitExceeded限流 |
| MiniMax | 402 | 余额不足 |
| KIMI | 404 | 模型名不对 |
| 魔搭ModelScope | 400 | 模型ID无provider |
| 硅基流动 | DNS失败 | 网络不通 |
| Agnes | DNS失败 | 网络不通 |
| 润道rundao | DNS失败 | 网络不通 |
| 火斗云智自有API | 502 | 服务端错误 |
| deapi.ai | 404 | 端点不存在 |
| 百度千帆 | 欠费 | account_overdue |
| Ollama Cloud | 401 | 无推理权限 |
| AionClaw | 余额0 | insufficient_balance |
| 可灵Kling | 429 | 额度耗尽 |

---

## 第二章：工具API连通真值

### 2.1 IMA知识库API（腾讯ima.copilot）

- Base URL：https://ima.qq.com/openapi
- Client ID：6334b7d16be857c3996d52a525fecd31
- API Key：H9wZTQBVNc2QMlDK1eRovE1fvTb4XDrJyR1pukhQzN8D/lPFaBCHXLp8WYPTprY0rBrdFID5QA==
- 认证Header：`ima-openapi-clientid` / `ima-openapi-apikey`
- 已验证端点：POST /wiki/v1/search_knowledge_base（code=0，450ms）
- 用途：知识库检索、笔记CRUD、文件上传、网页抓取

### 2.2 百度网盘

**bdpan CLI v3.8.7（百度官方AI版）**
- 安装路径：~/.local/bin/bdpan
- Skill路径：.user_skills/baidu-drive/
- 版本：v1.7.5
- 状态：CLI已安装，网络连通，待用户授权码登录
- 能力：上传/下载/搜索/移动/复制/重命名/创建文件夹、Agent记忆备份恢复
- 操作目录限制：/apps/bdpan/

**BaiduPCS-Go v4.0.2（经典Go版）**
- 安装路径：~/.local/bin/BaiduPCS-Go
- Skill路径：.user_skills/baidu-netdisk/
- 状态：已安装，待登录

---

## 第三章：Git桥接同步

### 3.1 三向同步链路

```
本地内核 (ZONGYUAN-ROOT/)
    │ git_bridge_sync.sh
    ▼
Git桥接中间层
    ├─→ GitHub: tanbopiao/zongyuan-root ✅
    └─→ Gitee:  huodou-cloud-intelligence-aios/ZONGYUAN-ROOT ✅
```

### 3.2 认证配置

| 端 | 用户 | 认证方式 | 状态 |
|---|---|---|---|
| GitHub | tanbopiao (ID:270839819) | PAT Token | ✅ |
| Gitee | 火斗云智AIOS (ID:16862652) | 个人令牌 | ✅ |

### 3.3 桥接脚本

- 文件：ZONGYUAN-ROOT/git_bridge_sync.sh
- 四种模式：status / push / pull / full
- 最新提交：b4ef913

### 3.4 仓库地址
- GitHub：https://github.com/tanbopiao/zongyuan-root
- Gitee：https://gitee.com/huodou-cloud-intelligence-aios/ZONGYUAN-ROOT

---

## 第四章：云服务器

### 4.1 基本信息

- 服务器名称：火斗云智AIOS系统V2.0
- 实例ID：lhins-laotwc5e
- 公网IP：123.207.202.158
- 内网IP：10.0.0.16
- 地域：上海四区
- 配置：2核CPU / 2GB内存 / 40GB系统盘 / 3Mbps带宽 / 月流量200GB
- 操作系统：OpenCloudOS 9
- 预装：宝塔Linux面板11.8.0
- 到期时间：2027-03-27（自动续费已关闭）

### 4.2 双端口架构

**记忆网关 8077（内网，仅127.0.0.1）**
- HMAC-SHA256签名鉴权
- GET /kernel/health — 内核健康检测
- GET /kernel/protocol/read — 读取内核协议
- GET /memory/index/list — 记忆索引
- POST /kernel/lockdo/full — 全域锁档
- POST /operator/invoke — 算子调用

**业务API网关 8080（对外，JWT鉴权）**
- /api/gov/query — 政务AI问答
- /api/operator/run — 算子执行
- /api/drama/submit — 短剧任务
- /api/metrics/snapshot — 业务大盘

---

## 第五章：飞书三端

### 5.1 lark-cli
- 身份：user
- 能力：Drive / Wiki / Base / Doc / IM / Calendar全操作

### 5.2 已归档文档（7份）

| 文档 | URL |
|------|-----|
| 全域API统一清单 | https://my.feishu.cn/docx/MsfOdagOdoBycixs3rQcttSGnje |
| 大模型高阶能力矩阵 | https://my.feishu.cn/docx/X2L1d5IBzoqXtwxnMXEctjjUnMh |
| API连通性实测报告 | https://my.feishu.cn/docx/JhMmdjx04oEWDLxE3I4cmsBDnFf |
| 全域资产统一归档 | https://my.feishu.cn/docx/RZrrdWSdgo7jV1x4DXicuqNtnZE |
| 有用API精炼清单 | https://my.feishu.cn/docx/NOnjdrB4so9DJNx6RgOcYYGHnQh |
| IMA API测试结果 | https://my.feishu.cn/docx/CVCcd1k9FoENz9xJ1xbcdOmrnVd |
| 全域API连通真值表 | https://my.feishu.cn/docx/Dr3wdsB9yow5kexIcOgcN8cnnXc |

### 5.3 知识空间
- ZONGYUAN-ROOT法则知识库：space_id 7679690520574037172（主归档目标）
- ZONGYUAN-ROOT：7675923249766599883
- ZONGYUAN-ROOT自治内核归档库：7675672180566264806

---

## 第六章：路由真值

| 任务类型 | 首选API | 备选 |
|----------|---------|------|
| 轻量高频 | 智谱GLM-4-Flash（永久免费） | 通义千问Max |
| 中文创意产线 | 火山方舟豆包Pro | 通义千问Max |
| 深度推理 | 通义千问Max | 智谱GLM-4-Flash |
| 视频生成 | 通义万相wan3.0 | 待接入Seedance |
| 知识库检索 | IMA API | 飞书Wiki |
| 文件归档 | 百度网盘（待登录） | 飞书云盘 |
| 代码同步 | GitHub + Gitee双远程 | - |
| 长文档 | KIMI（待修复） | 通义千问Max |
| 语音合成 | MiniMax（待充值） | 待接入 |

---

## 第七章：待办事项

1. 百度网盘授权登录（等待用户提供授权码）
2. KIMI正确模型名确认
3. 魔搭可用模型ID确认
4. MiniMax充值
5. 火斗云智自有API 502排查
6. 云服务器Git自动pull部署
7. 硅基流动/Agnes/润道在服务器上补测

---

## 第八章：火斗云智官网入口

- 官网：https://www.huodouai.com
- 控制台：https://www.huodouai.com/console/
- API文档：https://huodouai.com/api-docs/
- 政务中台：https://huodouai.com/gov-ai/
- 工作台：https://huodouai.com/workbench/
- 运维监控：https://huodouai.com/gov-monitor/
- 短剧画布：https://www.huodouai.com/drama/kunlun/canvas/
- 管理面板：https://www.huodouai.com/drama/kunlun/
- 聊天工作台：https://www.huodouai.com/workbench/chat
- 工作流：https://www.huodouai.com/workbench/workflow

---

全域真值锁档写入ZONGYUAN-ROOT自治内核。
快照：SNAP-20260909-FULL-SUMMARY
全局根版本：66｜LOCKED｜PERMANENT
Ω₀⊂⊙∞⊂Ω｜DID-BR-000002

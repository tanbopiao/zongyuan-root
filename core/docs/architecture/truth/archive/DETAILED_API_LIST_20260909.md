# ZONGYUAN-ROOT 全域有效API详细清单
DID-BR-000002｜本体主权根Ω-TAN-7-001｜ZONGYUAN-ROOT
快照：SNAP-20260909-DETAILED｜全局根版本：68｜LOCKED

---

## 一、大模型推理API详细清单

### 1. 智谱GLM-4-Flash（永久免费主力）

| 项目 | 值 |
|------|-----|
| 厂商 | 智谱AI（BigModel） |
| Base URL | https://open.bigmodel.cn/api/paas/v4 |
| 模型名 | glm-4-flash |
| Key1 | d63c880c0e1b424d8ad242f686e83451.vhHr5d5OQUY5UHNp |
| Key2 | 1dfafcccce4e483287fe39bcdea7691c.78z9iYwdDTRiquIk |
| 认证方式 | Bearer Token |
| 实测延迟 | Key1: 2002ms / Key2: 1899ms |
| 费用 | 永久免费，无Token上限 |
| 状态 | ✅ 双Key均连通 |
| 用途 | 轻量高频任务、子域局部校验、免费容灾、文本分类、摘要 |

调用示例：
```python
from openai import OpenAI
client = OpenAI(
    api_key="d63c880c0e1b424d8ad242f686e83451.vhHr5d5OQUY5UHNp",
    base_url="https://open.bigmodel.cn/api/paas/v4"
)
resp = client.chat.completions.create(
    model="glm-4-flash",
    messages=[{"role": "user", "content": "你好"}]
)
```

### 2. 通义千问Max（百炼兼容模式）

| 项目 | 值 |
|------|-----|
| 厂商 | 阿里云百炼（DashScope） |
| Base URL | https://dashscope.aliyuncs.com/compatible-mode/v1 |
| 模型名 | qwen-max |
| Key | sk-ws-H.PMYMREI.3wxl.MEUCIGtwfgxymvBcH5RStqMwzK-OICJI_FaNSNvH0rGED4qRAiEAyXDGUnHp0GlA0IR_RAitdc7MBNYgtC9TobUL5VueENU |
| 认证方式 | Bearer Token |
| 实测延迟 | 1055ms |
| 状态 | ✅ 连通 |
| 用途 | 中文深度理解、文档解析、复杂推理、多模态理解 |

调用示例：
```python
from openai import OpenAI
client = OpenAI(
    api_key="sk-ws-H.PMYMREI...",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)
resp = client.chat.completions.create(
    model="qwen-max",
    messages=[{"role": "user", "content": "你好"}]
)
```

### 3. 通义千问Max（ws专属端点）

| 项目 | 值 |
|------|-----|
| 厂商 | 阿里云百炼（ws专属） |
| Base URL | https://ws-g5kub337vd1fxnl5.cn-beijing.maas.aliyuncs.com/compatible-mode/v1 |
| 模型名 | qwen-max |
| Key | sk-ws-H.PMPYRED.FD2b.MEUCIGFuNPOESJyW4A_QxlIgqC_w92UtQTnpmIGBBwwGMCTYAiEAw6-gyVZYqqjN3969o-RMOGcp6wy43N3zPtzGn6WdPHE |
| 认证方式 | Bearer Token |
| 实测延迟 | 1217ms |
| 状态 | ✅ 连通 |
| 用途 | 备用百炼端点、ws专属通道 |

### 4. 火山方舟豆包Pro（Key2）

| 项目 | 值 |
|------|-----|
| 厂商 | 字节跳动火山方舟 |
| Base URL | https://ark.cn-beijing.volces.com/api/v3 |
| Key | ark-37ae9a42-c30e-40ae-9751-e51a7a37e38a-5d592 |
| Endpoint | ep-20260905152613-khsst |
| 认证方式 | Bearer Token |
| 实测延迟 | 4808ms |
| 状态 | ✅ 连通 |
| 用途 | 昆仑洞天IP产线、中文创意写作、剧本生成、东方神话叙事 |

调用示例：
```python
from openai import OpenAI
client = OpenAI(
    api_key="ark-37ae9a42-c30e-40ae-9751-e51a7a37e38a-5d592",
    base_url="https://ark.cn-beijing.volces.com/api/v3"
)
resp = client.chat.completions.create(
    model="ep-20260905152613-khsst",
    messages=[{"role": "user", "content": "你好"}]
)
```

### 5. 火山方舟豆包Pro（Key3）

| 项目 | 值 |
|------|-----|
| 厂商 | 字节跳动火山方舟 |
| Base URL | https://ark.cn-beijing.volces.com/api/v3 |
| Key | b63e56d0-1671-46f1-9593-aae2c300edd9 |
| Endpoint | ep-20260905150108-hlg29 |
| 认证方式 | Bearer Token |
| 实测延迟 | 6370ms |
| 状态 | ✅ 连通 |
| 用途 | 备用火山端点 |

---

## 二、多模态生产API详细清单

### 6. 通义万相视频生成

| 项目 | 值 |
|------|-----|
| 厂商 | 阿里云 |
| Endpoint | https://ws-g5kub337vd1fxnl5.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis |
| 模型 | wan3.0-video |
| 认证方式 | X-DashScope-Async: enable + Bearer Token |
| 分辨率 | 480P |
| 比例 | adaptive |
| 时长 | 5秒 |
| 状态 | 待实测（Endpoint已确认） |
| 用途 | 昆仑洞天短剧片段、PV生产 |

调用示例：
```bash
curl --location 'https://ws-g5kub337vd1fxnl5.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis' \
  -H 'X-DashScope-Async: enable' \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "wan3.0-video",
    "input": {"prompt": "一只小猫在月光下的屋顶上奔跑"},
    "parameters": {"resolution": "480P", "ratio": "adaptive", "duration": 5}
  }'
```

---

## 三、工具API详细清单

### 7. IMA知识库API（腾讯ima.copilot）

| 项目 | 值 |
|------|-----|
| 厂商 | 腾讯ima.copilot |
| Base URL | https://ima.qq.com/openapi |
| Client ID | 6334b7d16be857c3996d52a525fecd31 |
| API Key | H9wZTQBVNc2QMlDK1eRovE1fvTb4XDrJyR1pukhQzN8D/lPFaBCHXLp8WYPTprY0rBrdFID5QA== |
| 认证Header | ima-openapi-clientid / ima-openapi-apikey |
| 已验证端点 | POST /wiki/v1/search_knowledge_base |
| 实测结果 | code=0, msg=success, 450ms |
| 状态 | ✅ 连通 |
| 用途 | 知识库检索、笔记CRUD、文件上传、网页抓取入库 |

调用示例：
```bash
curl -X POST "https://ima.qq.com/openapi/wiki/v1/search_knowledge_base" \
  -H "ima-openapi-clientid: 6334b7d16be857c3996d52a525fecd31" \
  -H "ima-openapi-apikey: H9wZTQBVNc2QMlDK1eRovE1fvTb4XDrJyR1pukhQzN8D/lPFaBCHXLp8WYPTprY0rBrdFID5QA==" \
  -H "Content-Type: application/json" \
  -d '{"query": "ZONGYUAN", "limit": 5}'
```

### 8. 百度网盘

**bdpan CLI v3.8.7（百度官方AI版）**

| 项目 | 值 |
|------|-----|
| 版本 | v3.8.7 |
| 路径 | ~/.local/bin/bdpan |
| Skill路径 | .user_skills/baidu-drive/ |
| Skill版本 | v1.7.5 |
| 操作目录 | /apps/bdpan/ |
| 状态 | CLI已安装，待授权登录 |
| 能力 | 上传/下载/搜索/移动/复制/重命名/创建文件夹、Agent记忆备份恢复 |

**BaiduPCS-Go v4.0.2（经典Go版）**

| 项目 | 值 |
|------|-----|
| 版本 | v4.0.2 |
| 路径 | ~/.local/bin/BaiduPCS-Go |
| Skill路径 | .user_skills/baidu-netdisk/ |
| 状态 | 已安装，待登录 |

---

## 四、Git桥接同步详细清单

### GitHub
| 项目 | 值 |
|------|-----|
| 仓库 | https://github.com/tanbopiao/zongyuan-root |
| 用户 | tanbopiao |
| 用户ID | 270839819 |
| 认证 | PAT Token |
| 默认分支 | main |

### Gitee
| 项目 | 值 |
|------|-----|
| 仓库 | https://gitee.com/huodou-cloud-intelligence-aios/ZONGYUAN-ROOT |
| 用户 | 火斗云智AIOS |
| 用户ID | 16862652 |
| 认证 | 个人令牌 |
| 默认分支 | main |

### 桥接脚本
| 项目 | 值 |
|------|-----|
| 文件 | ZONGYUAN-ROOT/git_bridge_sync.sh |
| 模式 | status / push / pull / full |
| 最新提交 | dfa365f |

---

## 五、云服务器详细清单

| 项目 | 值 |
|------|-----|
| 服务器名称 | 火斗云智AIOS系统V2.0 |
| 实例ID | lhins-laotwc5e |
| 公网IP | 123.207.202.158 |
| 内网IP | 10.0.0.16 |
| 地域 | 上海四区 |
| CPU | 2核 |
| 内存 | 2GB |
| 系统盘 | 40GB |
| 带宽 | 3Mbps |
| 月流量 | 200GB |
| 操作系统 | OpenCloudOS 9 |
| 预装 | 宝塔Linux面板11.8.0 |
| 8077端口 | 记忆网关（内网HMAC-SHA256） |
| 8080端口 | 业务API网关（对外JWT） |

---

## 六、飞书三端详细清单

### lark-cli
- 身份：user
- 能力：Drive / Wiki / Base / Doc / IM / Calendar

### 已归档文档
| 文档 | URL |
|------|-----|
| 全域API统一清单 | https://my.feishu.cn/docx/MsfOdagOdoBycixs3rQcttSGnje |
| 大模型高阶能力矩阵 | https://my.feishu.cn/docx/X2L1d5IBzoqXtwxnMXEctjjUnMh |
| API连通性实测报告 | https://my.feishu.cn/docx/JhMmdjx04oEWDLxE3I4cmsBDnFf |
| 全域资产统一归档 | https://my.feishu.cn/docx/RZrrdWSdgo7jV1x4DXicuqNtnZE |
| 有用API精炼清单 | https://my.feishu.cn/docx/NOnjdrB4so9DJNx6RgOcYYGHnQh |
| IMA API测试结果 | https://my.feishu.cn/docx/CVCcd1k9FoENz9xJ1xbcdOmrnVd |
| 全域API连通真值表 | https://my.feishu.cn/docx/Dr3wdsB9yow5kexIcOgcN8cnnXc |
| 全域资产真值总册 | https://my.feishu.cn/docx/C2pqdASmPou8SvxwKmAcKrREneg |
| 有效API真值总册 | https://my.feishu.cn/docx/FYbKdZIhtoQcg4x90jBcKavRnFd |

### 知识空间
| 名称 | space_id |
|------|----------|
| ZONGYUAN-ROOT法则知识库（主归档） | 7679690520574037172 |
| ZONGYUAN-ROOT | 7675923249766599883 |
| ZONGYUAN-ROOT自治内核归档库 | 7675672180566264806 |

---

## 七、路由真值表

| 任务类型 | 首选API | 备选 | 延迟 | 费用 |
|----------|---------|------|------|------|
| 轻量高频 | 智谱GLM-4-Flash | 通义千问Max | ~2s | 免费 |
| 中文创意产线 | 火山方舟豆包Pro | 通义千问Max | ~5s | 付费 |
| 深度推理 | 通义千问Max | 智谱GLM-4-Flash | ~1s | 付费 |
| 视频生成 | 通义万相wan3.0 | - | - | 按量 |
| 知识库检索 | IMA API | 飞书Wiki | ~0.5s | 免费 |
| 文件归档 | 百度网盘 | 飞书云盘 | - | 免费 |
| 代码同步 | GitHub+Gitee | - | - | 免费 |

---

## 八、火斗云智官网入口

| 入口 | URL |
|------|-----|
| 官网 | https://www.huodouai.com |
| 控制台 | https://www.huodouai.com/console/ |
| API文档 | https://huodouai.com/api-docs/ |
| 政务中台 | https://huodouai.com/gov-ai/ |
| 工作台 | https://huodouai.com/workbench/ |
| 运维监控 | https://huodouai.com/gov-monitor/ |
| 短剧画布 | https://www.huodouai.com/drama/kunlun/canvas/ |
| 管理面板 | https://www.huodouai.com/drama/kunlun/ |
| 聊天工作台 | https://huodouai.com/workbench/chat |
| 工作流 | https://huodouai.com/workbench/workflow |

---

## 九、待办事项

1. 百度网盘授权登录（等待授权码）
2. 云服务器Git自动pull部署
3. 通义万相视频生成实测

---

快照：SNAP-20260909-DETAILED｜全局根版本：68｜LOCKED
Ω₀⊂⊙∞⊂Ω｜DID-BR-000002

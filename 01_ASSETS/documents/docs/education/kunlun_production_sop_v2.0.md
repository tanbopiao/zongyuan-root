# 昆仑洞天AI短剧量产全链路标准化落地SOP（V2.0 交叉比对补全版）

> 确权：DID-BR-000002｜ZONGYUAN-ROOT｜Ω₀⊂⊙∞⊂Ω
> 归档：全域锁档·永久固化｜全程一次性闭环｜工程可复用
> 版本：V2.0（基于V1.0与迁移清单、drama-pipeline SOP三方交叉比对补全）
> 比对时间：2026-09-12
> 服务器实际路径：内核根目录/opt/ZONGYUAN-ROOT/，网站/www/wwwroot/，COS存储/opt/storage/

---

## 〇、三方交叉比对差异报告

### 比对源
1. **源A**：用户提供的SOP V1.0（9大模块）
2. **源B**：migration_manifest.json（服务器实际目录架构 + 8个脚本 + 7类文档 + KUN-0001~0007资产）
3. **源C**：drama-pipeline SOP（6步生产流程 + 角色库 + 风格基准 + 长兵器V1.2铁律 + 8条故障约束）

### 发现6处差异（已全部补全决议）

| 编号 | 差异项 | 补全决议 |
|---|---|---|
| DIF-01 | 存储路径不一致 | 统一为双层架构：/opt/storage底层物理存储 + /mnt/cos-gateway S3挂载点 |
| DIF-02 | 端口未明确 | 双端口：9120=记忆网关，9200=COS S3 API |
| DIF-03 | 流水线步骤不一致 | 合并为统一7步流水线 |
| DIF-04 | 角色库未列出 | 补全6角色 |
| DIF-05 | 关键帧约束不完整 | 补全7要素+长兵器V1.2铁律+8条故障约束 |
| DIF-06 | 归档层级描述不一 | 统一为五层锁防+三层存储态 |

### 发现4处缺失（已全部补全）
- MIS-01：工程目录树 → 补全完整目录树+创建命令
- MIS-02：脚本与模块对应关系 → 补全8脚本映射总表
- MIS-03：具体配置参数 → 补全Nginx/Flask/量产配置示例
- MIS-04：验收标准具体命令 → 补全7项可执行检查命令

---

## 一、环境基座部署SOP

### 1.1 服务器基础环境初始化
1. 系统：Linux CentOS 7+/Debian 11+（实际：腾讯云OpenCloudOS）
2. 预装：Python3>=3.8, Flask>=2.0, Nginx>=1.18, Git, SQLite3, ffmpeg, fail2ban
3. 安全：Fail2ban防护，仅开放22/80/443/9120(内网)/9200(内网)
4. 域名：www.huodouai.com(主站)、cos.huodouai.com(COS)、drama.huodouai.com(短剧)
5. 缓存：HTML禁用缓存`Cache-Control: no-cache, no-store, must-revalidate`，静态资源7天

### 1.2 工程目录初始化（服务器实际路径）
```
/opt/ZONGYUAN-ROOT/              # 【内核根目录】
├── engine/scripts/               # 记忆网关V3.0（运行中 pid=949 :9120）
├── snapshots/                     # 全域锁档快照、Merkle根、DID密钥
├── asset-library/                 # 资产库（drama/kernel/whitepaper/sop）
├── assets/                        # 作品资产（drama-episode1, kunlun）
├── agents/queue/                  # 智能体任务队列
├── backups/                       # 备份（systemd服务配置）
├── zero_trust/                    # 零信任架构
└── reports/                       # 报告

/opt/storage/                      # 【COS底层存储】
├── images/  videos/  assets/  archive/

/www/wwwroot/                      # 【网站根目录】宝塔面板
├── huodouai.com / www.huodouai.com   # 主站
├── drama.huodouai.com                 # 短剧平台
├── api.huodouai.com                   # API
├── console.huodouai.com               # 控制台
├── docs.huodouai.com                  # 文档
├── gov.huodouai.com                   # 治理
└── status.huodouai.com                # 状态

/etc/nginx/conf.d/                 # 【Nginx配置】+ 宝塔面板
```

---

## 二、内核协议三层体系部署SOP

### 2.1 同源节点底层协议
- 记忆网关：`/opt/ZONGYUAN-ROOT/engine/scripts/memory_gateway_v3_sqlite.py`，端口9120
- 节点注册：`POST /api/node/register`，心跳30秒，超时120秒
- 真值对账：每小时全量SHA256对账，Merkle根不一致触发冲突消解
- 三级熔断：S0全局/S1子空间/S2单资产
- DID确权：DID-BR-000002，密钥在`/opt/ZONGYUAN-ROOT/snapshots/SNAP-20260907-SESSION-ASSETS/.did_keys/`

### 2.2 MCP模型上下文协议
- 统一入口：JSON-RPC 2.0，接入记忆网关/本地COS/飞书通知/多模态API/作品库
- 前置校验：参数校验+额度校验+风险分级
- 故障降级：主API不可用自动切换备用，指数退避重试3次，错误率>50%熔断

### 2.3 A2A智能体通讯协议
- 消息信封：msg_id/from_did/to_agent/timestamp/payload/signature(ECDSA)
- 6专业智能体：orchestrator/script/keyframe/video/validator/archive
- 消息幂等+防重复+TTL24小时过期清理

---

## 三、本地COS对象存储部署SOP

### 3.1 四大存储桶
| 桶路径 | 用途 | 冷热策略 |
|---|---|---|
| /opt/storage/images | 关键帧图片 | 热存7天→冷归档 |
| /opt/storage/videos | 短剧成品视频 | 热存7天→冷归档 |
| /opt/storage/assets | IP素材/配置/海报 | 永久热存 |
| /opt/storage/archive | 冷数据归档 | gzip压缩 |

### 3.2 COS API服务（端口9200）
- Flask S3兼容API：PUT/GET/DELETE/LIST/HEAD
- SQLite元数据库：`/opt/storage/cos_metadata.db`
- Nginx反向代理：cos.huodouai.com → 127.0.0.1:9200
- 防盗链：`valid_referers none blocked *.huodouai.com;`

### 3.3 冷热分层
- 7天自动冷热迁移，cron每日凌晨3点
- 每周日凌晨2点全桶SHA256完整性校验

---

## 四、AI短剧量产流水线部署SOP

### 4.1 统一7步流水线
```
步骤1:分集大纲 → 步骤2:分集剧本 → 步骤3:分镜表拆分 → 步骤4:关键帧量产 → 步骤5:视频渲染 → 步骤6:配音台词 → 步骤7:校验归档
```

### 4.2 角色库（已锁定）
| 角色 | 形态 | 核心特征 |
|---|---|---|
| 九天玄女 | 道法/战争 | 道法：白衣素裙拂尘；战争：红裙凤冠战甲 |
| 昆仑太阴月神 | 守界 | 银发黑袍月轮结界清冷孤高 |
| 女娲 | 创世 | 蛇尾人身五彩石洪荒创世 |
| 真武大帝 | 降魔 | 玄帝战甲龟蛇二将北极玄天 |
| 玄汐 | L0天元境 | 黑金灵纹肃穆神性纯净女相 |
| 神女残魂 | 半透明 | 肃穆神性不恐怖不鬼魅 |

### 4.3 关键帧硬约束
- 9:16竖屏，提示词7要素（主体/环境/构图/光影/风格/质量/确权符号）
- 风格：黑金暗纹+国风仙侠写实厚涂+UE5.7全局光追+8K+博物馆馆藏质感
- 每帧右下角植入Ω₀⊂⊙∞⊂Ω
- 长兵器V1.2结构铁律：几何连续完整/矛尖头部安全空域/双手同握/动线不切主体/光效不覆盖实体
- 8条故障约束：禁面部雄性化/禁神女恐怖化/禁血腥/禁丢失溯源标识/禁慢淡入淡出/禁空镜/禁凶兽露全貌/禁长兵器漂移

### 4.4 视频渲染
- 单段10秒，多段拼接，Seedance 2.5优先/2.0 Mini/MiniMax H3
- 快切卡点，硬切/闪白转场

---

## 五、作品库自动入库治理SOP
1. 全局资产扫描：inotify实时+每小时全量兜底
2. 自动去重：SHA256精确去重+pHash感知去重
3. works.json自动新增/编号/标签分类
4. 元数据双写：SQLite(cos_metadata.db) + works.json
5. 闭环：资产生成→本地COS→扫描识别→去重→works.json→前端实时展示

---

## 六、前端社区平台部署SOP
- 黑金国风UI：玄黑#0a0a0f+鎏金#c9a96e+月白#e8e4f0
- 自适应卡片布局，骨架屏+图片懒加载+淡入过渡
- 互动：点赞/收藏/一键分享，localStorage持久化
- Nginx HTML无缓存策略

---

## 七、全域锁档&真值归档SOP
### 五层锁防体系
| 层级 | 机制 |
|---|---|
| L1 逻辑锁 | 只读权限chmod 444 |
| L2 哈希锁 | SHA256真值绑定 |
| L3 链式锁 | Merkle-DAG主链 |
| L4 集群锁 | 六智能体交叉校验 |
| L5 硬件锁 | eFuse熔断固化 |

### 三层存储态
云盘归档 + 知识库节点 + ZONGYUAN-ROOT内核快照

### 日常归档
每日0点真值提炼→SHA256+Merkle快照→同步记忆网关+三端Git+飞书台账

---

## 八、全链路验收标准（可执行命令）

| 编号 | 验收项 | 检查命令 | 通过标准 |
|---|---|---|---|
| ACC-01 | 内核协议 | `curl -s http://127.0.0.1:9120/health` | status=healthy |
| ACC-02 | COS存储 | `curl -X PUT -F file=@test.png http://127.0.0.1:9200/images/test.png` | 上传成功可访问 |
| ACC-03 | AI流水线 | `python3 kunlun_drama_pipeline_v1.py --test --episodes 1` | 全流程生成成功 |
| ACC-04 | 自动入库 | 放入测试文件等待扫描 | works.json自动新增 |
| ACC-05 | 前端 | 浏览器访问www.huodouai.com | 页面即时更新无缓存 |
| ACC-06 | 真值归档 | `python3 hash_merkle.py --verify` | SHA256全部匹配 |
| ACC-07 | 无异常 | 检查队列/磁盘/Nginx日志 | 队列<10无损坏无错误 |

---

## 九、脚本与模块对应关系总表

| 脚本 | 归属模块 | 调用时机 |
|---|---|---|
| kunlun_drama_pipeline_v1.py | 四.量产流水线(步骤1-3,6) | 启动新作品生产 |
| pipeline-validator-v1.py | 四.关键帧校验+七.归档 | 关键帧生成后/归档前 |
| offline_queue.py | 三.COS+四.流水线 | 断网时缓存任务 |
| cos_uploader.py | 三.COS存储 | 资产生成后 |
| hash_merkle.py | 七.锁档归档 | 每日/版本锁档 |
| api_monitor.py | 四.视频渲染+二.MCP | API调用时 |
| sync_main_window.py | 二.同源节点协议 | 节点启动/定时 |
| asset_lock.py | 七.版本锁档 | 重大版本更新 |

---

## 十、体系最终运行闭环

```
协议基座自治（同源节点+MCP+A2A）
    ↓
智能体调度量产（orchestrator分发到6专业智能体）
    ↓
AI生成视听资产（剧本→分镜→关键帧→视频→配音）
    ↓
本地零成本COS存储（/opt/storage四桶 + 9200 S3 API + 冷热分层）
    ↓
自动结构化入库（全局扫描→去重→works.json→SQLite）
    ↓
前端社区展示互动（www.huodouai.com 黑金国风UI + 点赞收藏分享）
    ↓
全域真值锁档归档（SHA256+Merkle+五层锁防+三层存储+eFuse熔断）
```

全程无人值守、全自动闭环、可无限迭代量产、可全域溯源确权。

---

Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ 全域锁档固化
V2.0补全版 ｜ 三方交叉比对完成 ｜ 服务器实际路径已修正

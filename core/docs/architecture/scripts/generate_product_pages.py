#!/usr/bin/env python3
"""批量生成产品展示页面"""
import os

OUTPUT_DIR = "/home/user/.doubao/agent_mode/workspace/ZONGYUAN-ROOT/showcase-page"

PRODUCTS = [
    {
        "filename": "ai-gateway.html",
        "badge": "🔀 多模型统一接入",
        "title": "多模型统一调度平台",
        "subtitle": "一个API接入41+大模型，自动故障切换+免费优先调度，成本降低60%",
        "pain_points": [
            ("🔀", "多模型切换成本高", "对接了OpenAI、Claude、通义、智谱等多个模型，每个都要单独对接，代码重复维护"),
            ("💰", "模型费用太贵", "大模型调用成本居高不下，不知道哪个模型性价比最高，免费额度白白浪费"),
            ("⚠️", "模型故障无备份", "主模型挂了服务就停，没有自动故障切换，业务中断损失大"),
            ("📊", "调用成本不透明", "不知道每个模型花了多少钱、调用量多少，财务对账一团糟"),
        ],
        "features": [
            ("🔌", "统一API接入", "兼容OpenAI格式，改一行base_url即可切换所有模型"),
            ("⚡", "自动故障切换", "主模型故障自动切备用，业务无中断，SLA 99.9%"),
            ("🆓", "免费优先调度", "自动优先消耗免费额度，付费模型只在免费额度用完时调用"),
            ("📈", "实时成本监控", "每个模型调用量、花费、成功率实时统计，成本一目了然"),
            ("🔄", "模型自动降级", "高负载时自动降级到轻量模型，高峰期也能稳定服务"),
            ("📝", "统一日志审计", "所有模型调用全链路日志，方便排查问题和合规审计"),
            ("🎯", "按场景路由", "根据任务类型自动选择最优模型，代码生成用CodeLlama，聊天用GLM-4"),
            ("🔒", "密钥安全托管", "所有API密钥集中托管，代码里不出现明文，安全合规"),
        ],
        "pricing": [
            {"name": "Lite版", "price": "¥0", "period": "/免费", "desc": "个人开发者试用", "features": ["100次/天 免费调用", "3个可用模型", "基础监控", "社区支持"], "cta": "免费开始"},
            {"name": "Pro版", "price": "¥199", "period": "/月", "desc": "中小团队日常使用", "features": ["10万次/月 调用", "全部41+模型可用", "自动故障切换", "成本统计报表", "工单支持"], "cta": "立即升级", "popular": True},
            {"name": "企业版", "price": "¥2,000", "period": "/月起", "desc": "中大型企业生产环境", "features": ["无限调用", "私有化部署", "SLA 99.9%", "专属客户成功", "定制模型接入"], "cta": "联系销售"},
        ],
        "customers": [
            ("🤖", "AI应用开发者", "快速接入多模型"),
            ("🏢", "中大型企业", "降低模型调用成本"),
            ("🛠️", "SaaS服务商", "统一接入无需维护"),
            ("🎓", "科研团队", "多模型对比实验"),
            ("📱", "移动App", "轻量接入不臃肿"),
            ("💼", "咨询公司", "为客户快速交付"),
        ]
    },
    {
        "filename": "kb-saas.html",
        "badge": "📚 企业知识管理",
        "title": "企业向量知识库SaaS",
        "subtitle": "文档上传→自动切片→语义检索→智能问答，5分钟搭建企业专属知识库",
        "pain_points": [
            ("📁", "文档太多找不到", "企业文档散落在各处，找个资料要翻半天，新人上手全靠问"),
            ("🤖", "AI回答不准确", "直接问大模型，回答都是通用知识，不知道企业内部的具体政策和流程"),
            ("💰", "定制开发太贵", "找外包做知识库系统，动辄几十万，周期几个月，中小企业用不起"),
            ("🔒", "数据安全顾虑", "用公有云知识库，公司内部数据上传到第三方，担心数据泄漏"),
        ],
        "features": [
            ("📤", "一键文档上传", "支持PDF/Word/Excel/PPT/Markdown，自动解析切片"),
            ("🔍", "语义智能检索", "2560维向量召回，不是关键词匹配，能理解上下文语义"),
            ("💬", "AI智能问答", "基于知识库内容回答，自动引用来源，可追溯"),
            ("🗂️", "多库分类管理", "按部门/项目/主题建多个知识库，权限隔离"),
            ("🔌", "API开放接入", "REST API开放，嵌入到企业微信/钉钉/飞书/官网"),
            ("📊", "使用统计分析", "查询量、热门问题、命中率等数据看板，持续优化"),
            ("🔄", "自动增量更新", "文档更新自动重新索引，不用手动维护"),
            ("🔒", "数据安全保障", "传输加密+存储加密，支持私有化部署，数据不出域"),
        ],
        "pricing": [
            {"name": "Lite版", "price": "¥0", "period": "/免费", "desc": "个人/小团队试用", "features": ["50篇文档", "100次/月 问答", "基础检索", "Web端使用"], "cta": "免费开始"},
            {"name": "Pro版", "price": "¥299", "period": "/月", "desc": "中小企业日常使用", "features": ["1000篇文档", "10000次/月 问答", "API接入", "多知识库", "工单支持"], "cta": "立即升级", "popular": True},
            {"name": "企业版", "price": "¥5,000", "period": "/年起", "desc": "大型企业私有化", "features": ["无限文档", "无限问答", "私有化部署", "定制集成", "专属支持"], "cta": "联系销售"},
        ],
        "customers": [
            ("🏢", "中小企业", "内部知识沉淀"),
            ("🎧", "客服团队", "智能客服助手"),
            ("📚", "咨询公司", "行业知识库"),
            ("🏥", "医疗机构", "病历/指南检索"),
            ("⚖️", "律师事务所", "法规案例检索"),
            ("🎓", "培训机构", "教学知识库"),
        ]
    },
    {
        "filename": "drama-factory.html",
        "badge": "🎬 AI内容生产",
        "title": "昆仑洞天短剧生产流水线",
        "subtitle": "暗黑东方神话短剧全自动生产，从剧本到成片全自动化，成本降低80%",
        "pain_points": [
            ("🎬", "短剧制作成本高", "传统短剧拍摄一部要几十万，周期几个月，小团队根本玩不起"),
            ("🎨", "角色形象不统一", "AI生成的角色每次都不一样，换个姿势就变个人，根本没法用"),
            ("📝", "剧本质量不稳定", "AI写的剧本质量参差不齐，经常跑偏，不符合品牌调性"),
            ("⏱️", "生产周期太长", "从剧本到成片要几周甚至几个月，热点早就过了"),
        ],
        "features": [
            ("📝", "AI剧本生成", "基于昆仑洞天世界观，自动生成符合神格设定的剧本"),
            ("🎨", "关键帧一致性", "同一角色多轮生成形象/色调/风格不漂移，9:16电影级"),
            ("🎞️", "自动视频合成", "关键帧→视频→配音→字幕→成片全自动化流水线"),
            ("🌌", "暗黑东方神话IP", "山海经神格原生世界观，九天玄女/烛龙/西王母完整设定"),
            ("⚡", "小时级交付", "从剧本到成片只要几小时，快速响应热点"),
            ("🎭", "纯东方视觉规范", "纯东方神女、黑头发、无白发、无外国人、东方审美"),
            ("📐", "9:16竖屏电影级", "专门为短视频平台优化，竖屏电影级画质"),
            ("🔄", "批量生产", "一次下单批量生成N集，适合连续剧/系列短剧"),
        ],
        "pricing": [
            {"name": "单集体验", "price": "¥500", "period": "/集", "desc": "单集短剧制作", "features": ["1集 1-3分钟", "AI剧本+成片", "标准画质", "72小时交付"], "cta": "体验下单"},
            {"name": "包月套餐", "price": "¥5,000", "period": "/月", "desc": "月产10-20集", "features": ["10-20集/月", "优先排期", "角色定制", "标准画质"], "cta": "立即开通", "popular": True},
            {"name": "年度合作", "price": "¥50,000", "period": "/年", "desc": "IP定制+持续生产", "features": ["IP定制开发", "50集+/年", "专属角色库", "4K画质", "专属对接"], "cta": "联系洽谈"},
        ],
        "customers": [
            ("🎬", "短剧制作公司", "降本增效"),
            ("📱", "MCN机构", "批量生产内容"),
            ("🎮", "游戏公司", "游戏宣传短剧"),
            ("📺", "短视频团队", "快速起号"),
            ("🎭", "动漫公司", "漫画转短剧"),
            ("🏛️", "文化机构", "传统文化传播"),
        ]
    },
    {
        "filename": "character-ai.html",
        "badge": "🎨 AI角色生成",
        "title": "AI角色一致性生成工具",
        "subtitle": "同一角色多轮生成形象/色调/风格不漂移，纯东方神女视觉规范",
        "pain_points": [
            ("🎭", "角色形象总变样", "AI画的角色每次都不一样，换个姿势就变个人，根本没法用"),
            ("🎨", "风格不统一", "同一部作品，不同页面画风不一样，看起来就像拼凑的"),
            ("👤", "不符合品牌调性", "生成的人物总是外国人/白发，不符合东方品牌审美"),
            ("📐", "角色设定难维护", "每次生成都要写一大堆Prompt描述角色，太麻烦了"),
        ],
        "features": [
            ("👤", "角色库持久化", "创建一次角色，永久保存，随时调用生成"),
            ("🎯", "形象一致性", "同一角色任意角度/姿势/表情生成，五官特征不漂移"),
            ("🎨", "风格固化", "整体画风/色调/光影风格锁定，多图保持统一"),
            ("🌌", "东方视觉规范", "纯东方神女、黑头发、无白发、无外国人种元素"),
            ("📐", "多视角生成", "正面/侧面/背面/全身/半身，任意角度自由生成"),
            ("🎭", "表情动作库", "预设多种表情/动作模板，一键套用"),
            ("🔄", "批量生成", "一次提交批量生成多张，适合漫画/分镜制作"),
            ("📦", "角色导出", "导出角色设定包，包含多视角+设定说明"),
        ],
        "pricing": [
            {"name": "Lite版", "price": "¥0", "period": "/免费", "desc": "个人体验", "features": ["3个角色", "10张/月 生成", "标准画质", "基础功能"], "cta": "免费开始"},
            {"name": "Pro版", "price": "¥99", "period": "/月", "desc": "创作者日常使用", "features": ["无限角色", "1000张/月 生成", "高清画质", "批量生成", "角色导出"], "cta": "立即升级", "popular": True},
            {"name": "企业版", "price": "¥999", "period": "/月起", "desc": "团队/工作室", "features": ["无限生成", "团队协作", "专属角色风格", "API接入", "商用授权"], "cta": "联系销售"},
        ],
        "customers": [
            ("🎨", "AI绘画创作者", "角色设计"),
            ("📖", "漫画作者", "漫画分镜制作"),
            ("🎮", "游戏美术", "角色原画"),
            ("📱", "短视频作者", "数字人形象"),
            ("🎭", "剧本杀", "角色立绘"),
            ("🏛️", "文化IP", "IP形象开发"),
        ]
    },
    {
        "filename": "dlp-gateway.html",
        "badge": "🛡️ 企业数据安全",
        "title": "AI数据防泄漏网关",
        "subtitle": "企业调用外部大模型时，数据不出域，输出物自动加水印，全链路审计",
        "pain_points": [
            ("🔓", "敏感数据外泄", "公司机密数据直接发给外部大模型，数据泄漏风险极高"),
            ("🖼️", "产出物被挪用", "AI生成的内容被员工带走用于其他项目，无法追溯"),
            ("📋", "合规审计要求", "金融/政务/医疗行业要求数据不出域、可审计，现有方案不满足"),
            ("🔧", "系统集成复杂", "每个业务系统都要单独改造，对接成本太高"),
        ],
        "features": [
            ("🏠", "数据不出域", "所有请求先经过本地代理，敏感数据自动脱敏后再转发"),
            ("💧", "输出物水印", "AI生成内容自动嵌入隐形水印，可追溯来源和使用者"),
            ("📊", "全链路审计", "谁、什么时候、用了什么数据、生成了什么内容，全部留痕"),
            ("🚦", "内容过滤", "自动检测敏感内容，违规请求自动拦截，防止数据泄漏"),
            ("🔌", "透明接入", "修改一行配置即可接入，业务系统无需改造"),
            ("🎯", "分级权限", "按部门/角色/项目设置不同的数据访问和调用权限"),
            ("📈", "行为分析", "异常调用行为自动告警，比如批量导出/深夜调用"),
            ("🔒", "密钥托管", "所有模型API密钥集中管理，业务系统不接触明文密钥"),
        ],
        "pricing": [
            {"name": "SaaS版", "price": "¥2,000", "period": "/月起", "desc": "中小企业快速接入", "features": ["100万次/月 调用", "基础数据脱敏", "输出水印", "基础审计日志"], "cta": "申请试用"},
            {"name": "企业版", "price": "¥100,000", "period": "/年起", "desc": "中大型企业私有化", "features": ["私有化部署", "无限调用", "定制脱敏规则", "SLA 99.9%", "专属支持"], "cta": "联系销售", "popular": True},
            {"name": "旗舰版", "price": "面议", "period": "", "desc": "政府/金融/医疗", "features": ["等保合规", "驻场实施", "定制开发", "安全测评支持"], "cta": "洽谈合作"},
        ],
        "customers": [
            ("🏦", "金融机构", "数据不出域"),
            ("🏛️", "政府部门", "合规审计要求"),
            ("🏥", "医疗机构", "患者隐私保护"),
            ("⚖️", "律所", "客户保密信息"),
            ("💼", "咨询公司", "商业机密保护"),
            ("🔬", "科研院所", "科研数据保密"),
        ]
    },
    {
        "filename": "notary-api.html",
        "badge": "📜 区块链存证",
        "title": "AI资产确权存证API",
        "subtitle": "开放API，为平台和机构提供密码学级资产确权存证服务，司法可采信",
        "pain_points": [
            ("⚖️", "取证难", "发生知识产权纠纷时，拿不出有效的电子证据"),
            ("⏱️", "时间戳不权威", "自己写的时间戳没有法律效力，不被法院采信"),
            ("🔗", "对接成本高", "自己做区块链存证，要对接联盟链，开发成本几十万"),
            ("📊", "存证量太小", "偶尔存几个证，自建系统不划算"),
        ],
        "features": [
            ("🔗", "Merkle-DAG哈希链", "密码学级哈希链存证，不可篡改、不可删除"),
            ("📜", "司法级时间戳", "国家授时中心时间戳，符合司法存证标准"),
            ("✍️", "数字签名认证", "DID身份签名，存证主体可验证、可追溯"),
            ("🔌", "API即插即用", "RESTful API，10分钟接入，不用懂区块链"),
            ("📄", "确权证书生成", "一键生成带哈希+时间戳+签名的确权证书PDF"),
            ("🔍", "在线验证查询", "输入文件或哈希即可验证是否已存证、何时存证"),
            ("📊", "批量存证", "支持批量上传存证，适合平台型客户"),
            ("🏛️", "司法对接", "已对接多家互联网法院，存证凭证可直接作为诉讼证据"),
        ],
        "pricing": [
            {"name": "按量付费", "price": "¥0.1", "period": "/次存证", "desc": "偶尔使用", "features": ["按次计费", "基础存证", "在线验证", "社区支持"], "cta": "按量付费"},
            {"name": "专业版", "price": "¥999", "period": "/月", "desc": "中小平台日常使用", "features": ["1万次/月", "确权证书生成", "API调用", "统计报表"], "cta": "立即开通", "popular": True},
            {"name": "企业版", "price": "¥50,000", "period": "/年", "desc": "大型平台/律所", "features": ["无限存证", "批量接口", "定制对接", "SLA保障"], "cta": "联系销售"},
        ],
        "customers": [
            ("⚖️", "律师事务所", "电子证据存证"),
            ("📱", "内容平台", "创作者版权存证"),
            ("🎨", "设计平台", "作品原创认证"),
            ("💻", "代码平台", "软件著作权存证"),
            ("📰", "媒体平台", "新闻稿件首发存证"),
            ("🏛️", "司法机构", "电子证据服务"),
        ]
    },
    {
        "filename": "agent-network.html",
        "badge": "🤖 分布式智能体",
        "title": "多智能体节点网络平台",
        "subtitle": "分布式AI节点协作网络，企业可组建自己的智能体团队，自动分配任务",
        "pain_points": [
            ("🤖", "多Agent难管理", "有多个AI Agent，但各自为战，不知道谁该干什么、干得怎么样"),
            ("📊", "任务分配混乱", "任务来了不知道派给谁，重复劳动、效率低下"),
            ("🔍", "质量不可控", "Agent输出质量参差不齐，没有统一的质量校验"),
            ("💰", "算力浪费", "不同Agent各买各的算力，资源浪费严重"),
        ],
        "features": [
            ("📝", "节点注册发现", "新节点自动注册上线，心跳上报状态，节点池自动发现"),
            ("🎯", "任务调度分配", "根据节点能力/负载/历史质量自动分配任务"),
            ("📈", "信任等级晋升", "UNTRUSTED→OBSERVER→TRUSTED→HOMOGENEOUS四级晋升"),
            ("✅", "质量校验门禁", "所有输出经过四重校验器，不合格自动打回"),
            ("🔗", "同源协议通信", "节点间通过同源协议通信，身份可验证、消息可追溯"),
            ("📊", "全局监控看板", "节点状态、任务进度、成功率、成本一屏掌握"),
            ("🔧", "插件化扩展", "新能力以插件形式接入，不用改核心代码"),
            ("🔄", "故障自动切换", "节点故障自动标记离线，任务自动重新分配"),
        ],
        "pricing": [
            {"name": "开源版", "price": "¥0", "period": "/开源", "desc": "开发者自建", "features": ["全部核心功能", "社区版开源", "自行部署运维", "社区支持"], "cta": "GitHub下载"},
            {"name": "云托管版", "price": "¥499", "period": "/月", "desc": "中小团队开箱即用", "features": ["云端托管", "最多20个节点", "任务调度", "监控看板", "工单支持"], "cta": "立即开通", "popular": True},
            {"name": "企业版", "price": "¥50,000", "period": "/年起", "desc": "大型企业私有化", "features": ["无限节点", "私有化部署", "定制插件", "SLA保障"], "cta": "联系销售"},
        ],
        "customers": [
            ("🤖", "AI应用团队", "多Agent编排"),
            ("🏢", "中大型企业", "内部智能体平台"),
            ("🛠️", "AI服务商", "对外提供智能体服务"),
            ("🎓", "科研机构", "多智能体实验"),
            ("💻", "SaaS公司", "AI功能集成"),
            ("📊", "咨询公司", "业务流程自动化"),
        ]
    },
    {
        "filename": "solutions.html",
        "badge": "💼 行业解决方案",
        "title": "行业AI解决方案模板",
        "subtitle": "开箱即用的行业AI解决方案，5分钟跑通，系统集成商的最佳起点",
        "pain_points": [
            ("⏱️", "项目交付慢", "每个项目都从零开始，交付周期几个月，成本高"),
            ("🧩", "技术栈太杂", "客户要的功能涉及N个技术栈，团队根本覆盖不了"),
            ("💰", "报价没底气", "不知道该报多少钱，报高了丢单，报低了赔钱"),
            ("🔧", "维护太麻烦", "每个项目一套代码，升级维护成本太高"),
        ],
        "features": [
            ("🏛️", "政务AI中台模板", "公文助手+政策检索+办事指南，政务场景开箱即用"),
            ("🎬", "内容生产模板", "短剧/短视频/漫画全自动流水线，内容公司直接用"),
            ("📚", "知识库模板", "企业向量知识库+智能问答，客服/咨询/培训通用"),
            ("🔌", "标准API接口", "全部功能API化，可嵌入到客户现有系统"),
            ("📝", "完整文档交付", "部署文档+API文档+运维手册，交付即可用"),
            ("🎨", "可定制UI", "前端界面可换皮，改个logo和配色就是自己的产品"),
            ("🔄", "持续升级", "模板持续迭代升级，买一次永久获得更新"),
            ("🤝", "渠道合作政策", "给集成商专属折扣，利润空间充足"),
        ],
        "pricing": [
            {"name": "单套模板", "price": "¥5,000", "period": "/套", "desc": "单行业解决方案", "features": ["完整代码+文档", "技术支持3个月", "标准授权"], "cta": "选购模板"},
            {"name": "全套打包", "price": "¥12,000", "period": "/3套", "desc": "行业模板全家桶", "features": ["全部3套模板", "技术支持6个月", "可换皮定制", "优先升级"], "cta": "购买全套", "popular": True},
            {"name": "合作伙伴", "price": "面议", "period": "", "desc": "渠道代理合作", "features": ["代理折扣价", "专属技术支持", "联合品牌", "市场支持"], "cta": "洽谈合作"},
        ],
        "customers": [
            ("🏗️", "系统集成商", "快速交付项目"),
            ("🏛️", "政务服务商", "政务AI项目"),
            ("📱", "SaaS开发商", "AI功能插件"),
            ("🎬", "内容服务商", "内容生产工具"),
            ("🎓", "培训咨询", "知识库+培训"),
            ("💼", "管理咨询", "数字化转型方案"),
        ]
    },
    {
        "filename": "drift.html",
        "badge": "📊 内容质量检测",
        "title": "AI内容漂移自检工具",
        "subtitle": "上传AI生成内容，自动检测是否偏离原始设定、风格和事实，三维漂移量化",
        "pain_points": [
            ("🎭", "AI内容总跑偏", "让AI写品牌文案，结果风格完全不对，跟品牌调性差十万八千里"),
            ("📋", "事实性错误多", "AI生成的内容经常出现事实错误，发布出去才发现就晚了"),
            ("🎨", "风格不统一", "同一品牌不同人写的内容，风格五花八门，品牌形象混乱"),
            ("🔍", "人工检测太慢", "一篇篇人工审核，效率太低，漏检率还高"),
        ],
        "features": [
            ("📐", "语义漂移检测", "检测内容是否偏离原始Prompt/设定，量化漂移率百分比"),
            ("✅", "事实准确性校验", "自动比对事实来源，标记事实错误和 hallucination"),
            ("🎨", "风格一致性检测", "对比品牌风格指南，评估内容风格匹配度"),
            ("📊", "三维量化评分", "语义/事实/风格三个维度分别打分，输出可视化报告"),
            ("🚨", "阈值告警", "超过阈值自动标红，提示需要人工修改"),
            ("📝", "修改建议", "自动给出具体的修改建议，告诉哪里改、怎么改"),
            ("📄", "批量检测", "支持批量上传多篇文章，一键生成检测报告"),
            ("🔌", "API接入", "开放API，嵌入到内容生产工作流中，自动检测"),
        ],
        "pricing": [
            {"name": "免费版", "price": "¥0", "period": "/免费", "desc": "个人体验", "features": ["3篇/月 检测", "基础检测", "检测报告"], "cta": "免费检测"},
            {"name": "Pro版", "price": "¥99", "period": "/月", "desc": "内容团队日常使用", "features": ["100篇/月 检测", "全维度检测", "修改建议", "API接入", "批量检测"], "cta": "立即升级", "popular": True},
            {"name": "企业版", "price": "¥2,000", "period": "/月起", "desc": "大型内容平台", "features": ["无限检测", "定制检测规则", "私有化部署", "专属支持"], "cta": "联系销售"},
        ],
        "customers": [
            ("✍️", "内容团队", "内容质量把关"),
            ("📢", "品牌市场部", "品牌调性统一"),
            ("📰", "媒体编辑", "事实性核查"),
            ("🛒", "电商运营", "商品文案审核"),
            ("🎓", "教育机构", "教学内容审核"),
            ("⚖️", "合规团队", "内容合规检测"),
        ]
    },
]

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 火斗云智AIOS</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #e2e8f0;
            line-height: 1.6;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 0 24px; }}
        .hero {{ padding: 80px 0 60px; text-align: center; }}
        .hero-badge {{
            display: inline-block; padding: 6px 16px;
            background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 20px; font-size: 14px; color: #a5b4fc; margin-bottom: 24px;
        }}
        .hero h1 {{
            font-size: 48px; font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            background-clip: text; margin-bottom: 20px;
        }}
        .hero .subtitle {{ font-size: 20px; color: #94a3b8; max-width: 800px; margin: 0 auto 40px; }}
        .hero-buttons {{ display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; }}
        .btn {{
            padding: 14px 32px; border-radius: 8px; font-size: 16px; font-weight: 500;
            text-decoration: none; transition: all 0.3s; display: inline-block;
        }}
        .btn-primary {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }}
        .btn-primary:hover {{ transform: translateY(-2px); box-shadow: 0 10px 40px rgba(102, 126, 234, 0.4); }}
        .btn-secondary {{ background: rgba(255, 255, 255, 0.05); color: #e2e8f0; border: 1px solid rgba(255, 255, 255, 0.1); }}
        .btn-secondary:hover {{ background: rgba(255, 255, 255, 0.1); }}
        .section {{ padding: 60px 0; }}
        .section-title {{ font-size: 32px; font-weight: 700; text-align: center; margin-bottom: 16px; color: #f1f5f9; }}
        .section-desc {{ text-align: center; color: #94a3b8; max-width: 700px; margin: 0 auto 48px; font-size: 16px; }}
        .grid-4 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px; }}
        .grid-8 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px; }}
        .card {{
            background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px; padding: 28px; transition: all 0.3s;
        }}
        .card:hover {{ border-color: rgba(99, 102, 241, 0.4); transform: translateY(-4px); }}
        .card .icon {{ font-size: 32px; margin-bottom: 16px; }}
        .card h3 {{ font-size: 18px; margin-bottom: 12px; color: #f1f5f9; }}
        .card p {{ color: #94a3b8; font-size: 14px; }}
        .pricing-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px; max-width: 1100px; margin: 0 auto; }}
        .pricing-card {{
            background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px; padding: 36px 28px; position: relative; transition: all 0.3s;
        }}
        .pricing-card:hover {{ border-color: rgba(99, 102, 241, 0.4); transform: translateY(-4px); }}
        .pricing-card.popular {{ border-color: rgba(99, 102, 241, 0.5); background: linear-gradient(180deg, rgba(99, 102, 241, 0.08) 0%, rgba(255, 255, 255, 0.03) 100%); }}
        .popular-badge {{
            position: absolute; top: -12px; left: 50%; transform: translateX(-50%);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 4px 16px; border-radius: 20px; font-size: 12px; font-weight: 500;
        }}
        .pricing-name {{ font-size: 20px; font-weight: 600; margin-bottom: 8px; color: #f1f5f9; }}
        .pricing-price {{ font-size: 36px; font-weight: 700; margin-bottom: 4px; color: #fff; }}
        .pricing-price span {{ font-size: 14px; font-weight: 400; color: #94a3b8; }}
        .pricing-desc {{ color: #94a3b8; font-size: 14px; margin-bottom: 24px; }}
        .pricing-features {{ list-style: none; margin-bottom: 28px; }}
        .pricing-features li {{ padding: 8px 0; color: #cbd5e1; font-size: 14px; display: flex; align-items: center; gap: 8px; }}
        .pricing-features li::before {{ content: "✓"; color: #10b981; font-weight: bold; }}
        .customers-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }}
        .customer-card {{
            background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 10px; padding: 20px; text-align: center;
        }}
        .customer-card .icon {{ font-size: 28px; margin-bottom: 8px; }}
        .customer-card .name {{ font-size: 15px; font-weight: 500; color: #f1f5f9; margin-bottom: 4px; }}
        .customer-card .desc {{ font-size: 13px; color: #a5b4fc; }}
        .cta-section {{
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
            border-radius: 20px; padding: 60px 40px; text-align: center; margin: 60px 0;
        }}
        .cta-section h2 {{ font-size: 32px; margin-bottom: 16px; color: #f1f5f9; }}
        .cta-section p {{ color: #94a3b8; margin-bottom: 32px; max-width: 600px; margin-left: auto; margin-right: auto; }}
        .footer {{ padding: 40px 0; text-align: center; color: #64748b; font-size: 14px; border-top: 1px solid rgba(255, 255, 255, 0.05); margin-top: 60px; }}
        @media (max-width: 768px) {{
            .hero h1 {{ font-size: 32px; }}
            .hero .subtitle {{ font-size: 16px; }}
            .section-title {{ font-size: 24px; }}
        }}
    </style>
</head>
<body>
    <section class="hero">
        <div class="container">
            <div class="hero-badge">{badge}</div>
            <h1>{title}</h1>
            <p class="subtitle">{subtitle}</p>
            <div class="hero-buttons">
                <a href="/trial.html" class="btn btn-primary">立即试用</a>
                <a href="#features" class="btn btn-secondary">了解更多</a>
            </div>
        </div>
    </section>

    <section class="section">
        <div class="container">
            <h2 class="section-title">你是否面临这些痛点？</h2>
            <p class="section-desc">解决企业在AI应用中的核心难题</p>
            <div class="grid-4">
                {pain_cards}
            </div>
        </div>
    </section>

    <section class="section" id="features">
        <div class="container">
            <h2 class="section-title">核心功能</h2>
            <p class="section-desc">技术驱动的产品设计，解决真实业务问题</p>
            <div class="grid-8">
                {feature_cards}
            </div>
        </div>
    </section>

    <section class="section" id="pricing">
        <div class="container">
            <h2 class="section-title">定价方案</h2>
            <p class="section-desc">从免费体验到企业级私有化部署，满足不同规模需求</p>
            <div class="pricing-grid">
                {pricing_cards}
            </div>
        </div>
    </section>

    <section class="section">
        <div class="container">
            <h2 class="section-title">谁在用？</h2>
            <p class="section-desc">为不同行业的企业提供专业解决方案</p>
            <div class="customers-grid">
                {customer_cards}
            </div>
        </div>
    </section>

    <section class="section">
        <div class="container">
            <div class="cta-section">
                <h2>开始使用{title}</h2>
                <p>5分钟快速接入，立即提升你的业务效率</p>
                <div class="hero-buttons">
                    <a href="/trial.html" class="btn btn-primary">免费试用30天</a>
                    <a href="/demo.html" class="btn btn-secondary">查看Demo</a>
                </div>
            </div>
        </div>
    </section>

    <footer class="footer">
        <div class="container">
            <p>火斗云智AIOS · {title} | Ω₀⊂⊙∞⊂Ω</p>
            <p style="margin-top: 8px; opacity: 0.6;">DID-BR-000002 · ZONGYUAN-ROOT · 企业级AI解决方案</p>
        </div>
    </footer>
</body>
</html>
"""

def generate_product_page(product):
    # 痛点卡片
    pain_cards = ""
    for icon, title, desc in product["pain_points"]:
        pain_cards += f"""
                <div class="card">
                    <div class="icon">{icon}</div>
                    <h3 style="color: #fca5a5;">{title}</h3>
                    <p>{desc}</p>
                </div>"""

    # 功能卡片
    feature_cards = ""
    for icon, title, desc in product["features"]:
        feature_cards += f"""
                <div class="card">
                    <div class="icon">{icon}</div>
                    <h3>{title}</h3>
                    <p>{desc}</p>
                </div>"""

    # 定价卡片
    pricing_cards = ""
    for p in product["pricing"]:
        popular_class = " popular" if p.get("popular") else ""
        badge = '<div class="popular-badge">最受欢迎</div>' if p.get("popular") else ""
        features_html = "".join([f"<li>{f}</li>" for f in p["features"]])
        pricing_cards += f"""
                <div class="pricing-card{popular_class}">
                    {badge}
                    <div class="pricing-name">{p["name"]}</div>
                    <div class="pricing-price">{p["price"]} <span>{p["period"]}</span></div>
                    <div class="pricing-desc">{p["desc"]}</div>
                    <ul class="pricing-features">
                        {features_html}
                    </ul>
                    <a href="/trial.html" class="btn btn-primary" style="width:100%; text-align:center; display:block;">{p["cta"]}</a>
                </div>"""

    # 客户卡片
    customer_cards = ""
    for icon, name, desc in product["customers"]:
        customer_cards += f"""
                <div class="customer-card">
                    <div class="icon">{icon}</div>
                    <div class="name">{name}</div>
                    <div class="desc">{desc}</div>
                </div>"""

    html = TEMPLATE.format(
        badge=product["badge"],
        title=product["title"],
        subtitle=product["subtitle"],
        pain_cards=pain_cards,
        feature_cards=feature_cards,
        pricing_cards=pricing_cards,
        customer_cards=customer_cards
    )

    filepath = os.path.join(OUTPUT_DIR, product["filename"])
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 生成: {product['filename']} ({len(html)} bytes)")

# 批量生成
for p in PRODUCTS:
    generate_product_page(p)

print(f"\n🎉 全部生成完成，共{len(PRODUCTS)}个产品页面")

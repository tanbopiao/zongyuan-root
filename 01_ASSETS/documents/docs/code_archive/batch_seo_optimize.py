#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re

WEB_ROOT = '/www/wwwroot/huodouai.com'

SEO_DATA = {
    '404.html': {'description': '页面未找到 - 火斗云智AIOS，LLM驱动的稳态自治系统部署平台，提供企业AI向量知识库、政务AI中台、AI智能体工作台、昆仑洞天短剧流水线四大产品。', 'keywords': '火斗云智,AIOS,404,页面未找到,AI操作系统'},
    '500.html': {'description': '服务器内部错误 - 火斗云智AIOS政务中台，提供政务AI智能化解决方案。', 'keywords': '火斗云智,政务AI,500错误,服务器错误'},
    'about-line.html': {'description': '关于火斗云智AIOS - 元极恒一超认知自治操作系统，致力于打造企业级AI基础设施，推动人工智能普惠化发展。', 'keywords': '关于我们,火斗云智,AIOS,企业AI,元极恒一,自治系统'},
    'agent-network.html': {'description': '多智能体节点网络平台 - 火斗云智AIOS，支持多AI智能体协同工作、节点管理、负载均衡和任务分发，构建分布式智能体网络。', 'keywords': '多智能体,AI Agent,节点网络,协同工作,分布式AI,火斗云智'},
    'ai-asset-lock.html': {'description': 'AI资产锁档系统 - 火斗云智AIOS，基于Merkle-DAG哈希链和SHA256确权，实现AI资产的不可篡改存证、溯源验证和永久归档。', 'keywords': 'AI资产,锁档,存证,Merkle-DAG,哈希确权,溯源,火斗云智'},
    'ai-gateway.html': {'description': '多模型统一调度平台 - 火斗云智AIOS AI网关，支持OpenAI、豆包、文心一言等多模型统一接入，智能路由、负载均衡、成本优化。', 'keywords': 'AI网关,多模型,统一调度,API网关,大模型接入,负载均衡,火斗云智'},
    'aios-image.html': {'description': '火斗云智AIOS企业级AI稳态运维系统镜像 - 一键部署企业级AI基础设施，包含向量知识库、政务中台、智能体工作台、短剧流水线四大产品。', 'keywords': 'AIOS镜像,系统镜像,企业AI,一键部署,稳态运维,火斗云智'},
    'architecture-deep.html': {'description': '火斗云智AIOS深度技术架构解析 - 五层架构体系、内核总线、九大元类真值体系、14个核心组件详解，理解元极恒一自治操作系统的技术内核。', 'keywords': '技术架构,系统架构,内核总线,真值体系,元极恒一,火斗云智AIOS'},
    'blog.html': {'description': '火斗云智技术博客 - AI操作系统、向量知识库、政务AI、智能体平台、短剧AI等领域的深度技术观察和实践经验分享。', 'keywords': '技术博客,AI技术,大模型,向量数据库,RAG,政务AI,火斗云智'},
    'book-demo.html': {'description': '预约火斗云智AIOS产品演示 - 体验企业级AI向量知识库、政务AI中台、AI智能体工作台、昆仑洞天短剧流水线，专业团队一对一演示。', 'keywords': '预约演示,产品演示,AI产品,企业AI,火斗云智,免费试用'},
    'cases.html': {'description': '火斗云智客户案例 - 企业AI向量知识库、政务AI中台、智能体平台、短剧生产等行业落地案例，展示AIOS在真实场景中的应用价值。', 'keywords': '客户案例,成功案例,AI落地,企业案例,政务案例,火斗云智'},
    'character-ai.html': {'description': 'AI角色一致性生成工具 - 火斗云智，保证多轮生成中角色形象、性格、风格的一致性，适用于短剧、动画、游戏等内容生产场景。', 'keywords': 'AI角色,角色一致性,角色生成,短剧AI,动画AI,火斗云智'},
    'checker.html': {'description': 'AI资产校验工具 - 火斗云智AIOS，基于哈希比对和Merkle验证，检测AI资产的完整性、真实性和未篡改状态，保障资产可信。', 'keywords': '资产校验,哈希验证,完整性检测,Merkle,火斗云智'},
    'compare.html': {'description': '火斗云智AIOS产品对比 - 向量知识库、政务中台、智能体工作台、短剧流水线四大产品功能对比，帮助您选择最适合的AI解决方案。', 'keywords': '产品对比,功能对比,AI产品,向量知识库,政务AI,火斗云智'},
    'content-line.html': {'description': '火斗云智内容生产解决方案 - AI驱动的短剧、视频、文案、图像等内容自动化生产流水线，提升内容生产效率10倍以上。', 'keywords': '内容生产,AI内容,短剧生产,视频生成,文案生成,火斗云智'},
    'decision-intelligence.html': {'description': '火斗云智AIOS三维稳态决策元规则体系V2.0 - 基于利益最大化、风险最小化、成本最优化的三维决策模型，为企业提供智能决策支持。', 'keywords': '决策智能,三维稳态,决策模型,元规则,企业决策,火斗云智AIOS'},
    'demo.html': {'description': '火斗云智同源协议握手演示 - 体验AIOS多节点协同、真值同步、内核通信的核心技术演示。', 'keywords': '协议演示,握手演示,同源协议,节点协同,火斗云智'},
    'diff.html': {'description': '火斗云智AIOS差异化能力矩阵 - AI资产商业化基础设施，对比传统AI平台的核心差异化优势，包括真值驱动、自治运维、资产确权等。', 'keywords': '差异化,能力矩阵,AI资产,商业化,基础设施,火斗云智AIOS'},
    'dlp-gateway.html': {'description': 'AI数据防泄漏网关 - 火斗云智，为企业AI应用提供数据安全防护，敏感信息识别、脱敏、访问控制，保障企业数据安全合规。', 'keywords': '数据防泄漏,DLP,AI安全,数据安全,敏感信息,脱敏,火斗云智'},
    'drama-factory.html': {'description': '短剧生产流水线 - 火斗云智昆仑洞天，AI驱动的短剧全流程自动化生产，从剧本、分镜、角色到视频生成，一站式短剧工场。', 'keywords': '短剧生产,AI短剧,短剧流水线,昆仑洞天,视频生成,火斗云智'},
    'drift.html': {'description': 'AI内容漂移自检工具 - 火斗云智，检测AI生成内容中的角色漂移、风格漂移、语义漂移，保证多轮生成的一致性和质量。', 'keywords': '内容漂移,漂移检测,一致性,AI质量,火斗云智'},
    'ecosystem-line.html': {'description': '火斗云智开放生态 - 开放API、开发者社区、合作伙伴计划，共建AI操作系统生态，推动人工智能技术普惠化发展。', 'keywords': '开放生态,开发者,API,合作伙伴,AI生态,火斗云智'},
    'edu-ai-teacher.html': {'description': 'AI老师智能答疑 - 源域通识普惠教育，基于大模型的智能答疑系统，支持多学科知识问答、个性化学习辅导、作业批改。', 'keywords': 'AI老师,智能答疑,教育AI,个性化学习,作业批改,源域通识'},
    'education-line.html': {'description': '火斗云智普惠教育解决方案 - AI老师、知识图谱、个性化学习、智能答疑，让优质教育资源触达每一个学习者。', 'keywords': '普惠教育,AI教育,智能教育,个性化学习,知识图谱,火斗云智'},
    'edu-chat.html': {'description': '元极恒一AI老师 - 源域通识普惠教育平台，基于元极恒一超认知体系的智能对话教育助手，支持多学科深度问答和学习辅导。', 'keywords': 'AI对话,AI老师,元极恒一,智能教育,源域通识,普惠教育'},
    'edu-knowledge-graph.html': {'description': '知识图谱个性化学习 - 源域通识，构建学科知识图谱，智能识别知识薄弱点，提供个性化学习路径推荐和知识点关联学习。', 'keywords': '知识图谱,个性化学习,学习路径,智能教育,源域通识,火斗云智'},
    'gov-line.html': {'description': '火斗云智政务AI中台 - 为政府机构提供AI智能化解决方案，包括政务知识库、智能问答、公文辅助、数据分析、决策支持。', 'keywords': '政务AI,政务中台,智能政务,政务知识库,公文辅助,火斗云智'},
    'high-order-state.html': {'description': '高阶态的涌现与维持 - 火斗云智AIOS技术白皮书，探讨复杂系统中高阶态的涌现机制、维持方法和进化路径，元极恒一超认知理论。', 'keywords': '高阶态,涌现,复杂系统,元极恒一,超认知,技术白皮书,火斗云智'},
    'index-new.html': {'description': '火斗云智AIOS - 元极恒一企业级AI基础设施，提供向量知识库、政务中台、智能体工作台、短剧流水线四大产品，真值驱动可审计可溯源。', 'keywords': '火斗云智,AIOS,元极恒一,企业AI,AI基础设施,向量知识库'},
    'index-new-v2.html': {'description': '火斗云智AIOS V2 - 元极恒一企业级AI基础设施，全新升级的自治操作系统，更强的认知能力、更完善的真值体系、更高效的算力调度。', 'keywords': '火斗云智,AIOS V2,元极恒一,企业AI,自治系统,AI基础设施'},
    'kb-saas.html': {'description': '企业向量知识库SaaS - 火斗云智，开箱即用的企业知识库服务，支持文档上传、智能问答、RAG检索、权限管理，无需运维即可上线。', 'keywords': '向量知识库,SaaS,企业知识库,RAG,智能问答,火斗云智'},
    'kunlun-drama.html': {'description': '昆仑洞天AI短剧工场 - 火斗云智，AI驱动的短剧全流程生产平台，剧本生成、角色设计、分镜制作、视频渲染一站式完成，效率提升10倍。', 'keywords': '昆仑洞天,AI短剧,短剧工场,视频生成,剧本生成,火斗云智'},
    'logo-design.html': {'description': '火斗云智企业Logo设计方案 - 品牌视觉识别系统设计，包含Logo、色彩、字体、应用规范，打造专业的企业品牌形象。', 'keywords': 'Logo设计,品牌设计,VI设计,视觉识别,火斗云智'},
    'memory-gateway.html': {'description': '9120记忆网关 - 火斗云智AIOS全链路同步与真值锁档核心组件，实现多节点记忆同步、真值增量吸收、Merkle哈希确权、永久归档存储。', 'keywords': '记忆网关,9120,真值锁档,多节点同步,Merkle,火斗云智AIOS'},
    'notary-api.html': {'description': 'AI资产确权存证API - 火斗云智，为AI生成内容提供区块链级别的确权存证服务，支持时间戳、哈希存证、溯源验证、版权保护。', 'keywords': '确权存证,AI资产,版权保护,时间戳,哈希存证,API,火斗云智'},
    'opensource.html': {'description': '火斗云智开源与社区 - 开源项目、开发者文档、社区论坛、贡献指南，欢迎开发者参与AI操作系统的共建，推动人工智能开源生态发展。', 'keywords': '开源,开源社区,开发者,GitHub,AI开源,火斗云智'},
    'ops-line.html': {'description': '火斗云智内核运维 - AIOS自治运维体系，包括资源监控、故障自愈、性能优化、安全防护、日志审计，实现7x24小时无人值守运维。', 'keywords': '内核运维,自治运维,AIOps,故障自愈,资源监控,火斗云智AIOS'},
    'pricing.html': {'description': '火斗云智AIOS定价方案 - 向量知识库、政务中台、智能体工作台、短剧流水线四大产品的灵活定价，支持免费试用、按需付费、企业定制。', 'keywords': '定价,价格,收费标准,AI产品定价,企业AI,火斗云智'},
    'product-map.html': {'description': '火斗云智产品全景图 - 全面展示AIOS产品矩阵，包括四大核心产品、二十余个功能模块、完整的技术栈和服务体系，一图了解火斗云智。', 'keywords': '产品全景图,产品矩阵,AI产品,火斗云智,AIOS'},
    'product-matrix.html': {'description': '火斗云智产品矩阵总览 - 企业AI向量知识库、政务AI中台、AI智能体工作台、昆仑洞天短剧流水线四大产品线，覆盖企业AI全场景需求。', 'keywords': '产品矩阵,产品线,AI产品,向量知识库,政务AI,智能体,火斗云智'},
    'products.html': {'description': '火斗云智AIOS产品矩阵与定价 - 企业AI向量知识库、政务AI中台、AI智能体工作台、昆仑洞天短剧流水线，四大产品详细介绍与价格方案。', 'keywords': '产品中心,AI产品,向量知识库,政务AI,智能体,短剧,定价,火斗云智'},
    'prometheus-api-docs.html': {'description': 'Prometheus API文档 - 火斗云智AIOS监控系统API接口文档，包括指标查询、告警管理、数据导出等接口说明和调用示例。', 'keywords': 'Prometheus,API文档,监控API,指标查询,告警,火斗云智'},
    'roadmap.html': {'description': '火斗云智AIOS产品路线图 - 元极统一、超认知觉醒、永恒自治、元极恒一四阶段演进路线，展示AI操作系统的未来发展规划和里程碑。', 'keywords': '产品路线图,发展规划,里程碑,演进路线,元极恒一,火斗云智AIOS'},
    'roi-calculator.html': {'description': '火斗云智AIOS投资回报计算器 - 量化评估AI部署的投资回报率，包括成本节省、效率提升、收入增长等多维度ROI分析，辅助企业决策。', 'keywords': 'ROI计算器,投资回报,成本分析,效率提升,AI投资,火斗云智'},
    'security-compliance.html': {'description': '火斗云智合规与安全 - 等保三级、数据加密、隐私保护、访问控制、审计日志，全面保障企业AI应用的安全合规，符合国家法律法规要求。', 'keywords': '合规,安全,等保,数据加密,隐私保护,访问控制,火斗云智'},
    'security-line.html': {'description': '火斗云智安全基建 - AIOS全方位安全体系，包括网络安全、数据安全、应用安全、身份认证、安全审计，构建企业级AI安全防线。', 'keywords': '安全基建,网络安全,数据安全,应用安全,身份认证,火斗云智AIOS'},
    'semantic-dashboard.html': {'description': '语义校验引擎深空指挥中心 - 火斗云智AIOS真值质量监控仪表盘，实时监控真值纯度、冲突检测、漂移告警、分类统计，保障知识质量。', 'keywords': '语义校验,真值监控,仪表盘,深空指挥中心,质量监控,火斗云智AIOS'},
    'server-monitor.html': {'description': '火斗云智AIOS服务器监控面板 - 实时监控CPU、内存、磁盘、网络、服务状态，支持告警通知、历史趋势、性能分析，保障服务器稳定运行。', 'keywords': '服务器监控,性能监控,运维监控,告警,CPU监控,内存监控,火斗云智'},
    'solutions.html': {'description': '火斗云智行业AI解决方案模板 - 金融、医疗、教育、制造、零售、政务等行业的AI落地解决方案，开箱即用，快速部署，助力企业数字化转型。', 'keywords': '行业解决方案,AI解决方案,金融AI,医疗AI,教育AI,制造AI,火斗云智'},
    'startup-loop-defense-whitepaper.html': {'description': '启动失败死循环：隐蔽的系统杀手与自治防御体系 - 火斗云智AIOS技术白皮书，深入分析系统启动失败死循环的成因、危害和自治防御机制。', 'keywords': '启动失败,死循环,系统故障,自治防御,技术白皮书,火斗云智AIOS'},
    'token-gateway.html': {'description': '火斗云智AI Token网关 - 企业级多模型统一接入平台，支持OpenAI、豆包、文心、通义等主流大模型，统一API、智能路由、成本管控、用量统计。', 'keywords': 'Token网关,AI网关,多模型,统一API,大模型接入,成本管控,火斗云智'},
    'whitepaper.html': {'description': '火斗云智AIOS技术白皮书V1.0 - 全面介绍元极恒一超认知自治操作系统的技术架构、核心组件、关键特性、技术指标、演进路线和应用场景。', 'keywords': '技术白皮书,AIOS,元极恒一,自治系统,技术架构,火斗云智'}
}

def optimize_seo(filepath):
    filename = os.path.basename(filepath)
    if filename not in SEO_DATA:
        return False, '无SEO数据'
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, '读取失败: %s' % str(e)
    if 'name="description"' in content:
        return False, '已有description'
    seo = SEO_DATA[filename]
    short_title = seo['description'][:60]
    meta_tags = '\n<meta name="description" content="%s">\n<meta name="keywords" content="%s">\n<meta property="og:type" content="website">\n<meta property="og:title" content="%s">\n<meta property="og:description" content="%s">\n<meta property="og:url" content="https://huodouai.com/%s">\n<meta property="og:site_name" content="火斗云智 AIOS">\n<meta name="twitter:card" content="summary_large_image">\n<meta name="twitter:title" content="%s">\n<meta name="twitter:description" content="%s">\n' % (seo['description'], seo['keywords'], short_title, seo['description'], filename, short_title, seo['description'])
    if '</head>' in content:
        content = content.replace('</head>', meta_tags + '</head>', 1)
    elif '<head>' in content:
        content = content.replace('<head>', '<head>' + meta_tags, 1)
    else:
        return False, '未找到head标签'
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, '成功'
    except Exception as e:
        return False, '写入失败: %s' % str(e)

def main():
    print('=' * 60)
    print('火斗云智官网批量SEO优化')
    print('=' * 60)
    success = 0
    skipped = 0
    failed = 0
    failed_files = []
    for filename in sorted(os.listdir(WEB_ROOT)):
        if not filename.endswith('.html'):
            continue
        filepath = os.path.join(WEB_ROOT, filename)
        if not os.path.isfile(filepath):
            continue
        result, msg = optimize_seo(filepath)
        if result:
            success += 1
            print('  OK %s' % filename)
        elif '已有' in msg:
            skipped += 1
        else:
            failed += 1
            failed_files.append('%s: %s' % (filename, msg))
            print('  FAIL %s - %s' % (filename, msg))
    print()
    print('=' * 60)
    print('优化完成: 成功%d, 跳过%d, 失败%d' % (success, skipped, failed))
    if failed_files:
        print('失败文件:')
        for f in failed_files:
            print('  - %s' % f)
    print('=' * 60)

if __name__ == '__main__':
    main()

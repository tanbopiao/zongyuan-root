"""
本源智能普惠教育全自动体系 - 全局配置
"""
import os
from datetime import datetime

# 体系确权信息
SYSTEM_NAME = "本源智能普惠教育全自动闭环体系"
SYSTEM_VERSION = "V1.0"
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
ROOT_HASH = "ZONG-AUTO-EDU-SYSTEM-V1.0"

# 路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
SIMULATION_DIR = os.path.join(BASE_DIR, "simulation")

# 自动创建目录
for d in [DATA_DIR, LOG_DIR, CONFIG_DIR, SIMULATION_DIR]:
    os.makedirs(d, exist_ok=True)

# 元宪法五大元公理
META_AXIOMS = {
    "普惠均等": "所有教育资源天然无条件公平普惠，自动抹平城乡校际学段差距",
    "人本主导": "人永远主导，AI永远辅助，杜绝AI替代人类思考决策",
    "分层适配": "小学启蒙/初中认知/高中深化/中职岗位，自动分层不一刀切",
    "向善安全": "价值观正向、心理健康、数据安全、版权合规、无幻觉误导",
    "永续演化": "自主迭代、自我完善、自动归档、永久运行、不可回退"
}

# 顶层强制元规则：可工程化落地
# 元规则编号：META-RULE-ENG-001
# 高于所有业务规则，所有功能必须满足
ENGINEERING_META_RULE = {
    "rule_id": "META-RULE-ENG-001",
    "rule_name": "可工程化落地",
    "version": "V1.0",
    "effective_date": "2026-09-14",
    "core_axiom": "所有功能必须可工程化落地，所有链路必须全面打通，不留链路，不留断点",
    "six_clauses": {
        "全链路打通": "任何功能从输入到输出必须形成完整闭环，不得存在只有格式没有实际生成的断点",
        "实际输出验证": "每个声称的能力必须能产生实际可验证的输出文件，不得只输出提示词/规格说明",
        "仿真真实双模式": "所有生成类能力必须同时支持仿真模式（本地ffmpeg）和真实API模式（可插拔）",
        "依赖最小化自洽": "核心功能不得依赖外部不可控服务即可运行，外部依赖必须可配置可替换可降级",
        "可部署可运维": "必须提供完整部署说明、启动脚本、健康检查、日志输出、配置外部化",
        "测试驱动持续验证": "每个模块必须有单元测试，每个流水线必须有端到端测试，全量通过方可交付"
    },
    "violation_levels": {
        "P0": "核心链路断点，立即阻断不得交付",
        "P1": "只有接口无实现，标记未完成不得纳入交付",
        "P2": "缺少测试/部署说明，限期补齐标记beta",
        "P3": "代码风格/文档问题，记录待办后续优化"
    },
    "self_check_items": 11,
    "enforcement": "永久生效，不可降级不可豁免，每次交付前必须逐项确认"
}

# 顶层强制元规则：完善度评估标准体系
# 元规则编号：META-RULE-QUALITY-001
# 与可工程化落地元规则并列生效
QUALITY_META_RULE = {
    "rule_id": "META-RULE-QUALITY-001",
    "rule_name": "完善度评估标准体系",
    "version": "V1.0",
    "effective_date": "2026-09-14",
    "total_score": 100,
    "nine_dimensions": [
        {"name": "视觉设计", "weight": 15, "pass_line": 10, "excellent_line": 13},
        {"name": "交互体验", "weight": 15, "pass_line": 10, "excellent_line": 13},
        {"name": "数据可视化", "weight": 15, "pass_line": 10, "excellent_line": 13},
        {"name": "功能完整性", "weight": 15, "pass_line": 10, "excellent_line": 13},
        {"name": "性能体验", "weight": 10, "pass_line": 6, "excellent_line": 8.5},
        {"name": "可访问性", "weight": 10, "pass_line": 6, "excellent_line": 8.5},
        {"name": "响应式适配", "weight": 5, "pass_line": 3, "excellent_line": 4.5},
        {"name": "活体智能体感", "weight": 10, "pass_line": 6, "excellent_line": 8.5},
        {"name": "工程化质量", "weight": 5, "pass_line": 3, "excellent_line": 4.5}
    ],
    "maturity_levels": [
        {"level": "L0", "name": "概念原型", "range": "0-39", "publish": "禁止对外"},
        {"level": "L1", "name": "MVP可用", "range": "40-59", "publish": "内部测试"},
        {"level": "L2", "name": "基础完善", "range": "60-74", "publish": "小范围试用"},
        {"level": "L3", "name": "良好体验", "range": "75-84", "publish": "正式发布"},
        {"level": "L4", "name": "优秀产品", "range": "85-94", "publish": "重点推广"},
        {"level": "L5", "name": "卓越标杆", "range": "95-100", "publish": "标杆案例"}
    ],
    "iteration_rules": {
        "min_score_gain_per_version": 3,
        "must_fix_below_pass": True,
        "must_include_score_report": True,
        "below_60_not_complete": True,
        "below_75_not_public": True,
        "veto_items": ["页面白屏崩溃", "核心功能不可用", "数据错误", "安全漏洞", "视觉错乱"]
    },
    "current_self_assessment": {
        "version": "V1.4",
        "total_score": 63,
        "level": "L2 基础完善",
        "gap_to_public": 12,
        "failed_dimensions": ["交互体验", "数据可视化", "可访问性", "活体智能体感"]
    }
}

# 七维自治演化公理
EVOLUTION_AXIOMS = [
    "均衡普惠收敛", "分层适配演化", "双库闭环迭代",
    "人机向善协同", "低成本轻量化", "风险自主巡检", "全域复用自治"
]

# 十大AI知识域
KNOWLEDGE_DOMAINS = [
    "AI基础理论", "机器学习基础", "大模型架构", "智能体理论",
    "编程实践", "数据科学", "AI伦理安全", "多模态应用",
    "硬件机器人", "跨学科融合"
]

# 学段分层
EDUCATION_STAGES = ["小学", "初中", "高中", "中职"]

# 三维稳态决策权重
DECISION_WEIGHTS = {"利益": 0.40, "风险": 0.35, "成本": 0.25}

# 顶层元法则：全自动优化与人工审批分流机制
# 元法则编号：META-LAW-AUTO-OPT-001
AUTO_OPTIMIZATION_META_LAW = {
    "law_id": "META-LAW-AUTO-OPT-001",
    "law_name": "全自动优化与人工审批分流机制",
    "version": "V1.0",
    "effective_date": "2026-09-14",
    "core_principle": "符合最优稳态方案的一步走到底不停顿；不符合的上交中枢多智能体协同决策",
    "decision_thresholds": {
        "auto_execute": 70,
        "multi_agent_review": (50, 69),
        "human_approval": 50
    },
    "auto_execute_scope": [
        "可视化控制台优化", "代码质量优化", "文档完善",
        "数据可视化增强", "资源归档整理", "测试覆盖提升", "性能优化"
    ],
    "human_approval_required": [
        "安全合规变更", "不可逆变更", "付费资源调用",
        "对外发布部署", "核心架构变更", "高风险操作", "综合评分<50"
    ],
    "multi_agent_nodes": 3,
    "memory_gateway_port": 9120,
    "final_delivery_standard": {
        "min_quality_score": 90,
        "must_pass_tests": True,
        "must_visual_verify": True,
        "must_engineering_check": True
    },
    "enforcement": "永久生效，不可降级不可豁免，所有优化动作必须先经过三维稳态裁决"
}

# 顶层元规则：工程化落地标准体系
# 元规则编号：META-RULE-ENG-STANDARD-001
# 标准来源：Core Web Vitals + WCAG 2.1 AA + 前端工程化最佳实践
ENGINEERING_STANDARD_META_RULE = {
    "rule_id": "META-RULE-ENG-STANDARD-001",
    "rule_name": "工程化落地标准体系",
    "version": "V1.0",
    "effective_date": "2026-09-14",
    "core_principle": "所有交付物必须达到工程化落地标准方可宣称完成，标准来源于全网行业最佳实践",
    "performance_standards": {
        "LCP": {"name": "最大内容绘制", "good": 2.5, "needs_improvement": 4.0, "unit": "秒"},
        "INP": {"name": "交互到下一帧", "good": 200, "needs_improvement": 500, "unit": "毫秒"},
        "CLS": {"name": "累积布局偏移", "good": 0.1, "needs_improvement": 0.25, "unit": "无单位"},
        "FCP": {"name": "首次内容绘制", "good": 1.8, "unit": "秒"},
        "TTFB": {"name": "首字节时间", "good": 800, "unit": "毫秒"}
    },
    "accessibility_standards": {
        "level": "WCAG 2.1 AA",
        "contrast_normal_text": 4.5,
        "contrast_large_text": 3.0,
        "contrast_ui_component": 3.0,
        "touch_target_min": 44,
        "keyboard_accessible": True,
        "screen_reader_support": True
    },
    "engineering_standards": {
        "code_style_unified": True,
        "modular_structure": True,
        "error_handling": True,
        "input_validation": True,
        "logging": True,
        "one_click_build": True,
        "health_check": True
    },
    "acceptance_checklist_total": 30,
    "performance_checks": 7,
    "accessibility_checks": 10,
    "engineering_checks": 8,
    "functional_checks": 5,
    "enforcement": "永久生效，30项验收全部通过方可宣称工程化落地完成"
}

# 顶层元规则：每步工作交付闭环标准
# 元规则编号：META-RULE-DELIVERY-CLOSED-LOOP-001
# 核心铁律：未交付=未完成，每步工作必须形成交付闭环
DELIVERY_CLOSED_LOOP_META_RULE = {
    "rule_id": "META-RULE-DELIVERY-CLOSED-LOOP-001",
    "rule_name": "每步工作交付闭环标准",
    "version": "V1.0",
    "effective_date": "2026-09-14",
    "core_principle": "未交付=未完成，每步工作必须形成交付闭环，禁止只说交付不实际调用交付工具",
    "delivery_three_elements": [
        "可视化链接（用户可直接点开看效果）",
        "优化建议清单（明确列出未完善功能和下一步方向）",
        "版本标识（版本号+评分+确权标识+审核状态）"
    ],
    "lightweight_strategy": {
        "priority": ["核心可视化文件", "关键配置/文档", "完整项目包(按需)", "中间文件(不交付)"],
        "normal_delivery_count": "2-4个",
        "major_release_count": "4-6个",
        "max_delivery_count": 8,
        "delivery_position": "回复最后，用户无需往上滚动"
    },
    "verification_checklist": 8,
    "checklist_items": [
        "可视化链接已提供",
        "优化建议清单已附",
        "版本标识已标注",
        "交付物放在回复最后",
        "交付物数量合理(2-6个)",
        "无占位/无效链接",
        "大文件按需交付",
        "已实际调用交付工具present_files"
    ],
    "unclosed_handling": {
        "user_points_out": "立即补交付，不得辩解或拖延",
        "self_check_found": "立即补交付，记录为流程断点",
        "breakpoint_record": "记录到断点台账，归档到ZONGYUAN-ROOT",
        "prevention": "每步完成前自动运行验证清单，不通过禁止进入下一步"
    },
    "enforcement": "永久生效，8项验证全部通过方可宣称交付完成，任一项缺失=未闭环"
}

# 仿真配置
SIMULATION_CONFIG = {
    "num_students": 100,
    "num_teachers": 20,
    "num_schools": 5,
    "simulation_days": 30,
    "knowledge_points_per_domain": 20
}

# 记忆网关配置（META-RULE-MEMORY-GATEWAY-PROTOCOL-001）
MEMORY_GATEWAY_CONFIG = {
    "rule_id": "META-RULE-MEMORY-GATEWAY-PROTOCOL-001",
    "rule_name": "记忆网关对接与同源协议规范",
    "version": "V1.0",
    "protocol_version": "COMM-PROTO-V1.0",
    "domain": "drama.huodouai.com",
    "ip": "123.207.202.158",
    "default_port": 9120,
    "external_access": {
        "mode": "www.huodouai.com API (2026-09-14更新)",
        "read_only": "https://www.huodouai.com/api/v1/gateway/status",
        "health": "https://www.huodouai.com/api/v1/gateway/health",
        "write_truth": "https://www.huodouai.com/api/memory/api/truth/upsert",
        "write_auth": "API Key",
        "drama_api": "https://www.huodouai.com/drama/",
        "general_api": "https://www.huodouai.com/api/v1/*"
    },
    "visual_page": "https://huodouai.com/memory-gateway.html",
    "api_endpoints": {
        "comm": "POST /comm",
        "health": "GET /health",
        "audit": "GET /audit"
    },
    "hmac_signature": {
        "algorithm": "HMAC-SHA256",
        "formula": "HMAC-SHA256(timestamp|nonce|canonical_body)",
        "timestamp_window": 300,
        "secret_file": "comm_gateway_secret.json",
        "secret_fingerprint": "368491955359E366"
    },
    "homology_protocol": {
        "version": "V2.0",
        "status": "CONFIRMED",
        "file": "homology_protocol.json"
    },
    "seven_step_sync": ["服务恢复", "协议确认", "同源锚定", "全量拉取", "SOP锁档", "真值写入", "双备份验证"],
    "rate_limit": "120/min/IP",
    "default_bind": "127.0.0.1",
    "cache_ttl": 300,
    "did": "DID-BR-000002",
    "anchor": "Ω₀⊂⊙∞⊂Ω",
    "feishu_base_alt": {
        "name": "本源普惠教育云端上报台账",
        "base_token": "S6XsbaOOXa1TrgsMUgycVOpfn2T",
        "table_id": "tblXw992OnMV0CyN",
        "url": "https://my.feishu.cn/base/S6XsbaOOXa1TrgsMUgycVOpfn2T",
        "status": "active",
        "pending_reports": 4
    },
    "current_blockers": [
        "写入真值端点需要官方API Key",
        "9120后端服务可能未运行（502 Bad Gateway）",
        "需要HMAC密钥comm_gateway_secret.json（仅限本地访问）",
        "飞书Base替代通道已就绪"
    ],
    "verification_driven_reporting": {
        "rule_id": "META-RULE-VERIFICATION-DRIVEN-REPORTING-001",
        "principle": "先验证后上报，成功全域推广，失败减少试错",
        "success_count": 10,
        "failure_count": 10,
        "pending_count": 5,
        "enforcement": "所有学习成果必须先验证后上报，失败经验必须上报减少试错"
    },
    "visual_delivery_standard": {
        "rule_id": "META-RULE-VISUAL-DELIVERY-001",
        "principle": "所有交付必须是链接+可视化成果，禁止纯文本交付",
        "three_elements": ["可点击链接", "可视化成果", "版本标识"],
        "delivery_position": "回复最后，用户直接点开",
        "enforcement": "违反本规则的交付视为不合格，必须整改后重新交付"
    },
    "enforcement": "永久生效，所有智能体必须遵循，记忆网关是唯一握手点"
}

# 日志格式
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def get_timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

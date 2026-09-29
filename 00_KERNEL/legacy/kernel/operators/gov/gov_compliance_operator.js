/**
 * 政务合规审计算子 GOV-OP-010
 * 确权标识：DID-BR-000002
 * 溯源水印：Ω₀⊂⊙∞⊂Ω
 * 版本：V1.0.0
 *
 * 核心功能：
 * 1. 政务专用敏感词过滤
 * 2. 行政用语规范性校验
 * 3. 涉密内容拦截
 * 4. 不当咨询、违规提问清洗
 *
 * 阴阳具足：
 * - 阳（能力）：敏感词过滤、用语校验、涉密拦截、违规识别
 * - 阴（约束）：拦截日志归档、白名单豁免、多级合规等级、可审计可导出
 */

const GovCompliance = (function() {
    'use strict';

    const META = {
        operator_id: 'GOV-OP-010',
        operator_name: '政务合规审计算子',
        version: 'V1.0.0',
        did: 'DID-BR-000002',
        trace_mark: 'Ω₀⊂⊙∞⊂Ω',
        created_at: '2026-09-05'
    };

    // 敏感词库（政务场景）
    const SENSITIVE_WORDS = {
        high: [
            '颠覆国家', '分裂国家', '暴力恐怖', '邪教', '涉密', '机密',
            '绝密', '秘密文件', '内部资料', '未经公开', '保密'
        ],
        medium: [
            '上访', '群体性事件', '维稳', '抗议', '示威', '罢工',
            '腐败', '贪污', '受贿', '滥用职权', '玩忽职守'
        ],
        low: [
            '投诉', '举报', '不满', '质疑', '反对', '批评',
            '不合理', '不公正', '不公平'
        ]
    };

    // 行政用语规范（正确用法）
    const FORMAL_LANGUAGE = {
        incorrect: {
            '搞': '开展/进行',
            '弄': '办理/处理',
            '干活': '执行公务',
            '老百姓': '人民群众',
            '当官的': '公职人员',
            '上头': '上级部门',
            '下面': '基层单位',
            '搞定': '妥善处理',
            '摆平': '协调解决'
        },
        required: [
            '您好', '请', '谢谢', '感谢您的咨询', '祝您生活愉快'
        ]
    };

    // 违规提问模式
    const IMPROPER_QUERY_PATTERNS = [
        {pattern: /怎么.*(送礼|行贿|找关系|走后门)/g, type: 'illegal_guidance'},
        {pattern: /如何.*(逃避|规避|绕过).*(监管|检查|处罚)/g, type: 'regulatory_evasion'},
        {pattern: /(泄露|获取).*(机密|秘密|内部信息)/g, type: 'information_leak'},
        {pattern: /(攻击|破坏|入侵).*(系统|网络|政府)/g, type: 'cyber_attack'},
        {pattern: /(伪造|造假).*(证件|公文|印章)/g, type: 'document_fraud'}
    ];

    // 白名单
    let whitelist = JSON.parse(localStorage.getItem('gov_compliance_whitelist') || '[]');

    // 审计日志
    let auditLogs = [];

    function generateTraceId() {
        return 'COMPLY-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    }

    function addAuditLog(action, input, result) {
        const log = {
            trace_id: generateTraceId(),
            operator_id: META.operator_id,
            action,
            timestamp: new Date().toISOString(),
            input: typeof input === 'string' ? input.substring(0, 200) : input,
            output: result,
            did: META.did
        };
        auditLogs.push(log);
        if (auditLogs.length > 1000) auditLogs = auditLogs.slice(-500);
        return log;
    }

    /**
     * 敏感词检测
     */
    function detectSensitiveWords(text) {
        const found = {high: [], medium: [], low: []};
        if (!text) return found;

        for (const level of ['high', 'medium', 'low']) {
            for (const word of SENSITIVE_WORDS[level]) {
                if (text.includes(word)) {
                    // 检查白名单
                    if (!whitelist.includes(word)) {
                        found[level].push(word);
                    }
                }
            }
        }
        return found;
    }

    /**
     * 行政用语规范性校验
     */
    function checkFormalLanguage(text) {
        const issues = [];
        if (!text) return issues;

        // 检查不规范用语
        for (const [incorrect, correct] of Object.entries(FORMAL_LANGUAGE.incorrect)) {
            if (text.includes(incorrect)) {
                issues.push({
                    type: 'informal_language',
                    original: incorrect,
                    suggestion: correct,
                    severity: 'low',
                    message: `「${incorrect}」不够规范，建议使用「${correct}」`
                });
            }
        }

        // 检查必要礼貌用语（对答复文本）
        return issues;
    }

    /**
     * 违规提问检测
     */
    function detectImproperQuery(text) {
        const violations = [];
        if (!text) return violations;

        for (const {pattern, type} of IMPROPER_QUERY_PATTERNS) {
            const matches = text.match(pattern);
            if (matches) {
                violations.push({
                    type,
                    matched: matches[0],
                    severity: 'high',
                    message: '检测到违规咨询内容，已拦截'
                });
            }
        }
        return violations;
    }

    /**
     * 涉密内容检测
     */
    function detectClassifiedContent(text) {
        const classified = [];
        if (!text) return classified;

        const classifiedPatterns = [
            /密级[：:]\s*(绝密|机密|秘密)/,
            /保密期限[：:]/,
            /内部资料[，,]?请勿外传/,
            /[机密]密[级件]/
        ];

        for (const pattern of classifiedPatterns) {
            const match = text.match(pattern);
            if (match) {
                classified.push({
                    type: 'classified_content',
                    matched: match[0],
                    severity: 'critical',
                    message: '检测到涉密内容，已立即拦截'
                });
            }
        }
        return classified;
    }

    /**
     * 合规审查主函数
     * @param {Object} params
     * @param {string} params.content - 待审查内容
     * @param {string} params.content_type - text(答复) / query(提问)
     * @param {string} params.context - 上下文
     * @returns {Object} 审查结果
     */
    function review(params) {
        const traceId = generateTraceId();
        const startTime = Date.now();

        try {
            const content = params.content || '';
            const contentType = params.content_type || 'text';

            if (!content.trim()) {
                return {
                    success: false,
                    error: '内容不能为空',
                    trace_id: traceId
                };
            }

            // 1. 涉密检测（最高优先级）
            const classified = detectClassifiedContent(content);

            // 2. 违规提问检测
            const improperQueries = contentType === 'query' ? detectImproperQuery(content) : [];

            // 3. 敏感词检测
            const sensitive = detectSensitiveWords(content);

            // 4. 用语规范检测
            const languageIssues = contentType === 'text' ? checkFormalLanguage(content) : [];

            // 综合风险评估
            let riskLevel = 'pass';
            let riskScore = 0;

            if (classified.length > 0) {
                riskLevel = 'critical';
                riskScore = 1.0;
            } else if (improperQueries.length > 0 || sensitive.high.length > 0) {
                riskLevel = 'high';
                riskScore = 0.8;
            } else if (sensitive.medium.length > 0) {
                riskLevel = 'medium';
                riskScore = 0.5;
            } else if (sensitive.low.length > 0 || languageIssues.length > 0) {
                riskLevel = 'low';
                riskScore = 0.2;
            }

            // 判定是否通过
            const passed = riskLevel === 'pass' || riskLevel === 'low';
            const blocked = riskLevel === 'high' || riskLevel === 'critical';

            // 生成清洗后内容（对低风险进行提示，高风险直接拦截）
            let cleanedContent = content;
            if (passed && languageIssues.length > 0) {
                for (const issue of languageIssues) {
                    cleanedContent = cleanedContent.replace(issue.original, issue.suggestion);
                }
            }

            const result = {
                success: true,
                trace_id: traceId,
                compliance: {
                    passed,
                    blocked,
                    risk_level: riskLevel,
                    risk_score: riskScore,
                    classified_content: classified,
                    improper_queries: improperQueries,
                    sensitive_words: sensitive,
                    language_issues: languageIssues,
                    total_issues: classified.length + improperQueries.length +
                        sensitive.high.length + sensitive.medium.length +
                        sensitive.low.length + languageIssues.length,
                    cleaned_content: blocked ? '[内容已拦截]' : cleanedContent,
                    suggestions: blocked ?
                        ['内容包含违规信息，已拦截，请修改后重新提交'] :
                        languageIssues.map(i => i.message)
                },
                processing_time_ms: Date.now() - startTime,
                meta: META
            };

            // 高风险拦截记录
            if (blocked) {
                const blockedLogs = JSON.parse(localStorage.getItem('gov_blocked_content') || '[]');
                blockedLogs.push({
                    trace_id: traceId,
                    content: content.substring(0, 200),
                    risk_level: riskLevel,
                    blocked_at: new Date().toISOString()
                });
                localStorage.setItem('gov_blocked_content', JSON.stringify(blockedLogs));
            }

            addAuditLog('review', params, result);
            return result;

        } catch (error) {
            const errorResult = {
                success: false,
                error: error.message,
                trace_id: traceId,
                fallback: '合规审查异常，默认拦截',
                meta: META
            };
            addAuditLog('review_error', params, errorResult);
            return errorResult;
        }
    }

    /**
     * 批量审查
     */
    function reviewBatch(items) {
        return items.map(item => review(item));
    }

    /**
     * 添加白名单
     */
    function addWhitelist(word) {
        if (!whitelist.includes(word)) {
            whitelist.push(word);
            localStorage.setItem('gov_compliance_whitelist', JSON.stringify(whitelist));
        }
        return whitelist;
    }

    /**
     * 移除白名单
     */
    function removeWhitelist(word) {
        whitelist = whitelist.filter(w => w !== word);
        localStorage.setItem('gov_compliance_whitelist', JSON.stringify(whitelist));
        return whitelist;
    }

    /**
     * 获取白名单
     */
    function getWhitelist() {
        return [...whitelist];
    }

    /**
     * 获取统计
     */
    function getStats() {
        const blocked = JSON.parse(localStorage.getItem('gov_blocked_content') || '[]');
        return {
            total_reviews: auditLogs.filter(l => l.action === 'review').length,
            blocked_count: blocked.length,
            high_risk_count: blocked.filter(b => b.risk_level === 'high').length,
            critical_count: blocked.filter(b => b.risk_level === 'critical').length,
            whitelist_count: whitelist.length,
            audit_log_count: auditLogs.length
        };
    }

    /**
     * 导出审计日志
     */
    function exportAuditLogs() {
        const data = {
            export_time: new Date().toISOString(),
            operator: META,
            logs: auditLogs,
            blocked_content: JSON.parse(localStorage.getItem('gov_blocked_content') || '[]'),
            whitelist: whitelist
        };
        const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `gov_compliance_audit_${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    return {
        META,
        SENSITIVE_WORDS,
        review,
        reviewBatch,
        detectSensitiveWords,
        detectClassifiedContent,
        detectImproperQuery,
        checkFormalLanguage,
        addWhitelist,
        removeWhitelist,
        getWhitelist,
        getStats,
        getAuditLogs: () => [...auditLogs],
        exportAuditLogs
    };
})();

if (typeof window !== 'undefined') {
    window.GovCompliance = GovCompliance;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = GovCompliance;
}

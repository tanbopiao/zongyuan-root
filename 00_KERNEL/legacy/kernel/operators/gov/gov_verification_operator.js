/**
 * 政务政策真值核验算子 GOV-OP-011
 * 确权标识：DID-BR-000002
 * 溯源水印：Ω₀⊂⊙∞⊂Ω
 * 版本：V1.0.0
 *
 * 核心功能：
 * 1. AI答复文本与原始政策知识库条文比对校验
 * 2. 计算内容匹配置信分
 * 3. 标记不一致、篡改、新增虚构内容
 * 4. 异常结果打上待人工复核标签
 * 5. 幻觉案例自动投递至L-1涌现治理库归档
 *
 * 阴阳具足：
 * - 阳（能力）：真值核验、置信度评分、差异标记、幻觉识别
 * - 阴（约束）：校验失败降级人工复核、幻觉案例归档、完整审计日志
 */

const GovVerification = (function() {
    'use strict';

    // 算子元数据
    const META = {
        operator_id: 'GOV-OP-011',
        operator_name: '政策真值核验算子',
        version: 'V1.0.0',
        did: 'DID-BR-000002',
        trace_mark: 'Ω₀⊂⊙∞⊂Ω',
        created_at: '2026-09-05'
    };

    // 配置
    const CONFIG = {
        apiBase: '/gov-api',
        verificationEndpoint: '/api/gov/verification',
        hallucinationEndpoint: '/api/gov/hallucination',
        minConfidenceScore: 0.7,      // 最低置信度阈值
        highRiskThreshold: 0.5,       // 高风险阈值
        maxDiffLength: 1000,          // 最大差异文本长度
        autoReviewThreshold: 0.6      // 低于此值自动转人工复核
    };

    // 审计日志
    let auditLogs = [];

    /**
     * 生成唯一traceId
     */
    function generateTraceId() {
        return 'VERIFY-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * 添加审计日志
     */
    function addAuditLog(action, data, result) {
        const log = {
            trace_id: generateTraceId(),
            operator_id: META.operator_id,
            action: action,
            timestamp: new Date().toISOString(),
            input: data,
            output: result,
            did: META.did
        };
        auditLogs.push(log);
        // 限制日志数量
        if (auditLogs.length > 1000) {
            auditLogs = auditLogs.slice(-500);
        }
        return log;
    }

    /**
     * 文本预处理：去除空白、标准化标点
     */
    function preprocessText(text) {
        if (!text) return '';
        return text
            .replace(/\s+/g, ' ')
            .replace(/[，。！？；：""''（）【】]/g, function(m) {
                const map = {'，':',', '。':'.', '！':'!', '？':'?', '；':';', '：':':', '"':'"', '"':'"', ''':"'", ''':"'", '(':'(', ')':')', '【':'[', '】':']'};
                return map[m] || m;
            })
            .trim()
            .toLowerCase();
    }

    /**
     * 计算文本相似度（基于字符级n-gram）
     */
    function calculateSimilarity(text1, text2) {
        if (!text1 || !text2) return 0;
        const t1 = preprocessText(text1);
        const t2 = preprocessText(text2);
        if (t1 === t2) return 1.0;
        if (t1.length < 2 || t2.length < 2) return 0;

        // 2-gram集合
        const grams1 = new Set();
        const grams2 = new Set();
        for (let i = 0; i < t1.length - 1; i++) grams1.add(t1.substr(i, 2));
        for (let i = 0; i < t2.length - 1; i++) grams2.add(t2.substr(i, 2));

        // Jaccard相似度
        let intersection = 0;
        grams1.forEach(g => { if (grams2.has(g)) intersection++; });
        const union = grams1.size + grams2.size - intersection;
        return union > 0 ? intersection / union : 0;
    }

    /**
     * 提取关键信息点（数字、日期、机构名称等）
     */
    function extractKeyPoints(text) {
        if (!text) return [];
        const points = [];

        // 提取数字
        const numbers = text.match(/\d+(\.\d+)?%?/g) || [];
        numbers.forEach(n => points.push({type: 'number', value: n}));

        // 提取日期
        const dates = text.match(/\d{4}年\d{1,2}月\d{1,2}日|\d{4}-\d{1,2}-\d{1,2}/g) || [];
        dates.forEach(d => points.push({type: 'date', value: d}));

        // 提取机构名称（简单匹配）
        const orgs = text.match(/[市县区镇]?[人民政]+府|[\u4e00-\u9fa5]{2,10}(局|委员会|办公室|中心|管理处)/g) || [];
        orgs.forEach(o => points.push({type: 'org', value: o}));

        return points;
    }

    /**
     * 比对关键信息点差异
     */
    function compareKeyPoints(aiPoints, refPoints) {
        const diffs = [];
        const aiValues = aiPoints.map(p => p.value);
        const refValues = refPoints.map(p => p.value);

        // AI中有但参考中没有的（可能是虚构）
        aiPoints.forEach(p => {
            if (!refValues.includes(p.value)) {
                diffs.push({
                    type: 'potential_fabrication',
                    point_type: p.type,
                    value: p.value,
                    severity: p.type === 'number' ? 'high' : 'medium',
                    message: `AI输出的${p.type}「${p.value}」在政策原文中未找到`
                });
            }
        });

        return diffs;
    }

    /**
     * 真值核验主函数
     * @param {Object} params - 参数
     * @param {string} params.ai_text - AI生成的答复文本
     * @param {Array} params.policy_reference - 参考政策文本数组
     * @param {string} params.policy_id - 政策ID（可选）
     * @returns {Object} 核验结果
     */
    async function verify(params) {
        const traceId = generateTraceId();
        const startTime = Date.now();

        try {
            // 输入校验
            if (!params.ai_text || !params.ai_text.trim()) {
                return {
                    success: false,
                    error: 'AI文本不能为空',
                    trace_id: traceId,
                    audit: addAuditLog('verify', params, {success: false, error: 'empty_input'})
                };
            }

            const aiText = params.ai_text;
            const references = params.policy_reference || [];

            // 如果没有参考文本，调用后端API获取
            let refTexts = references;
            if (refTexts.length === 0 && params.policy_id) {
                try {
                    const response = await fetch(`${CONFIG.apiBase}/api/gov/policy/search?q=${encodeURIComponent(params.policy_id)}`);
                    const data = await response.json();
                    if (data.success && data.data && data.data.policies) {
                        refTexts = data.data.policies.map(p => p.content || p.full_text || '');
                    }
                } catch (e) {
                    console.warn('获取政策参考失败:', e);
                }
            }

            // 计算与每个参考文本的相似度
            const similarities = refTexts.map(ref => ({
                reference: ref.substring(0, 100) + (ref.length > 100 ? '...' : ''),
                score: calculateSimilarity(aiText, ref),
                full_ref: ref
            })).sort((a, b) => b.score - a.score);

            const bestMatch = similarities[0];
            const overallScore = bestMatch ? bestMatch.score : 0;

            // 提取关键信息点并比对
            const aiPoints = extractKeyPoints(aiText);
            const refPoints = bestMatch ? extractKeyPoints(bestMatch.full_ref) : [];
            const keyPointDiffs = compareKeyPoints(aiPoints, refPoints);

            // 风险评估
            let riskLevel = 'low';
            let riskScore = 1 - overallScore;

            if (overallScore < CONFIG.highRiskThreshold) {
                riskLevel = 'high';
            } else if (overallScore < CONFIG.minConfidenceScore) {
                riskLevel = 'medium';
            }

            // 关键点差异增加风险
            const highRiskDiffs = keyPointDiffs.filter(d => d.severity === 'high');
            if (highRiskDiffs.length > 0) {
                riskLevel = 'high';
                riskScore = Math.min(1, riskScore + highRiskDiffs.length * 0.1);
            }

            // 判定是否需要人工复核
            const needReview = overallScore < CONFIG.autoReviewThreshold || highRiskDiffs.length > 0;

            // 标记差异内容
            const diffHighlights = [];
            if (bestMatch && overallScore < 0.8) {
                // 简单标记：找出AI文本中与参考差异较大的句子
                const aiSentences = aiText.split(/[。！？；\n]/).filter(s => s.trim().length > 5);
                aiSentences.forEach(sentence => {
                    const sim = calculateSimilarity(sentence, bestMatch.full_ref);
                    if (sim < 0.3) {
                        diffHighlights.push({
                            text: sentence.trim(),
                            similarity: sim.toFixed(2),
                            type: sim < 0.1 ? 'potential_fabrication' : 'low_similarity'
                        });
                    }
                });
            }

            const result = {
                success: true,
                trace_id: traceId,
                verification: {
                    overall_score: parseFloat(overallScore.toFixed(4)),
                    risk_level: riskLevel,
                    risk_score: parseFloat(riskScore.toFixed(4)),
                    need_human_review: needReview,
                    best_match: bestMatch ? {
                        similarity: parseFloat(bestMatch.score.toFixed(4)),
                        reference_preview: bestMatch.reference
                    } : null,
                    all_matches: similarities.slice(0, 3).map(s => ({
                        similarity: parseFloat(s.score.toFixed(4)),
                        reference_preview: s.reference
                    })),
                    key_point_diffs: keyPointDiffs,
                    diff_highlights: diffHighlights.slice(0, 10),
                    hallucination_detected: riskLevel === 'high' || diffHighlights.filter(d => d.type === 'potential_fabrication').length > 0
                },
                processing_time_ms: Date.now() - startTime,
                meta: META
            };

            // 如果检测到幻觉，自动投递到涌现治理库
            if (result.verification.hallucination_detected) {
                await reportHallucination({
                    ai_text: aiText,
                    verification_result: result.verification,
                    policy_id: params.policy_id,
                    trace_id: traceId
                });
            }

            addAuditLog('verify', params, result);
            return result;

        } catch (error) {
            const errorResult = {
                success: false,
                error: error.message,
                trace_id: traceId,
                fallback: '降级到人工复核',
                meta: META
            };
            addAuditLog('verify_error', params, errorResult);
            return errorResult;
        }
    }

    /**
     * 报告幻觉案例到涌现治理库
     */
    async function reportHallucination(data) {
        try {
            const hallucinationCase = {
                case_id: 'HALLU-' + Date.now(),
                type: 'policy_hallucination',
                severity: data.verification_result.risk_level,
                ai_text: data.ai_text.substring(0, 500),
                verification_score: data.verification_result.overall_score,
                policy_id: data.policy_id,
                trace_id: data.trace_id,
                detected_at: new Date().toISOString(),
                status: 'pending_review',
                did: META.did
            };

            // 本地存储（L-1涌现层）
            const cases = JSON.parse(localStorage.getItem('gov_hallucination_cases') || '[]');
            cases.push(hallucinationCase);
            localStorage.setItem('gov_hallucination_cases', JSON.stringify(cases));

            // 尝试上报后端
            try {
                await fetch(`${CONFIG.apiBase}${CONFIG.hallucinationEndpoint}/report`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(hallucinationCase)
                });
            } catch (e) {
                console.warn('幻觉上报后端失败，已本地存储:', e);
            }

            return hallucinationCase;
        } catch (e) {
            console.error('幻觉报告失败:', e);
            return null;
        }
    }

    /**
     * 批量核验
     */
    async function verifyBatch(items) {
        const results = [];
        for (const item of items) {
            const result = await verify(item);
            results.push(result);
        }
        return {
            success: true,
            total: items.length,
            passed: results.filter(r => r.success && r.verification && !r.verification.need_human_review).length,
            need_review: results.filter(r => r.success && r.verification && r.verification.need_human_review).length,
            failed: results.filter(r => !r.success).length,
            results: results
        };
    }

    /**
     * 获取核验统计
     */
    function getStats() {
        const cases = JSON.parse(localStorage.getItem('gov_hallucination_cases') || '[]');
        return {
            total_verifications: auditLogs.filter(l => l.action === 'verify').length,
            hallucination_cases: cases.length,
            pending_review: cases.filter(c => c.status === 'pending_review').length,
            high_risk_count: cases.filter(c => c.severity === 'high').length,
            audit_log_count: auditLogs.length
        };
    }

    /**
     * 获取审计日志
     */
    function getAuditLogs(limit = 50) {
        return auditLogs.slice(-limit);
    }

    /**
     * 导出审计日志
     */
    function exportAuditLogs() {
        const data = {
            export_time: new Date().toISOString(),
            operator: META,
            logs: auditLogs,
            hallucination_cases: JSON.parse(localStorage.getItem('gov_hallucination_cases') || '[]')
        };
        const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `gov_verification_audit_${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    // 公开接口
    return {
        META,
        CONFIG,
        verify,
        verifyBatch,
        reportHallucination,
        getStats,
        getAuditLogs,
        exportAuditLogs,
        calculateSimilarity,
        extractKeyPoints,
        preprocessText
    };
})();

// 挂载到全局
if (typeof window !== 'undefined') {
    window.GovVerification = GovVerification;
}

// Node.js环境导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GovVerification;
}

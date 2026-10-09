/**
 * 政务政策版本生命周期算子 GOV-OP-016
 * 确权标识：DID-BR-000002
 * 溯源水印：Ω₀⊂⊙∞⊂Ω
 * 版本：V1.0.0
 *
 * 核心功能：
 * 1. 政策版本管理（草稿/待审/生效/废止）
 * 2. 政策生效日期自动校验
 * 3. 废止政策自动标记
 * 4. 政策变更历史追溯
 *
 * 阴阳具足：
 * - 阳（能力）：版本流转、生效校验、废止标记、历史追溯、变更对比
 * - 阴（约束）：生效日期不可篡改、废止不可删除、变更全程留痕、审计可导出
 */

const GovPolicyLifecycle = (function() {
    'use strict';

    const META = {
        operator_id: 'GOV-OP-016',
        operator_name: '政策版本生命周期算子',
        version: 'V1.0.0',
        did: 'DID-BR-000002',
        trace_mark: 'Ω₀⊂⊙∞⊂Ω',
        created_at: '2026-09-05'
    };

    // 政策状态枚举
    const STATUS = {
        DRAFT: 'draft',           // 草稿
        PENDING: 'pending',       // 待审核
        ACTIVE: 'active',         // 已生效
        EXPIRED: 'expired',       // 已过期
        REPEALED: 'repealed',     // 已废止
        ARCHIVED: 'archived'      // 已归档
    };

    // 状态流转规则
    const TRANSITIONS = {
        [STATUS.DRAFT]: [STATUS.PENDING, STATUS.ARCHIVED],
        [STATUS.PENDING]: [STATUS.ACTIVE, STATUS.DRAFT],
        [STATUS.ACTIVE]: [STATUS.EXPIRED, STATUS.REPEALED],
        [STATUS.EXPIRED]: [STATUS.ARCHIVED],
        [STATUS.REPEALED]: [STATUS.ARCHIVED],
        [STATUS.ARCHIVED]: []
    };

    // 本地存储key
    const STORAGE_KEY = 'gov_policy_lifecycle';

    // 审计日志
    let auditLogs = [];

    function generatePolicyVersionId() {
        return 'POL-VER-' + Date.now().toString(36).toUpperCase() + '-' +
            Math.random().toString(36).substr(2, 4).toUpperCase();
    }

    function generateTraceId() {
        return 'LIFE-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    }

    function addAuditLog(action, input, result) {
        const log = {
            trace_id: generateTraceId(),
            operator_id: META.operator_id,
            action,
            timestamp: new Date().toISOString(),
            input,
            output: result,
            did: META.did
        };
        auditLogs.push(log);
        if (auditLogs.length > 1000) auditLogs = auditLogs.slice(-500);
        return log;
    }

    /**
     * 加载政策版本数据
     */
    function loadPolicies() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
        } catch (e) {
            return {};
        }
    }

    /**
     * 保存政策版本数据
     */
    function savePolicies(policies) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(policies));
    }

    /**
     * 创建政策版本
     * @param {Object} params
     * @param {string} params.policy_id - 政策ID
     * @param {string} params.title - 政策标题
     * @param {string} params.content - 政策内容
     * @param {string} params.effective_date - 生效日期
     * @param {string} params.expiry_date - 失效日期（可选）
     * @param {string} params.author - 创建人
     * @returns {Object} 政策版本
     */
    function createVersion(params) {
        const traceId = generateTraceId();

        try {
            if (!params.policy_id || !params.title) {
                return {success: false, error: '政策ID和标题不能为空', trace_id: traceId};
            }

            const policies = loadPolicies();
            const policyId = params.policy_id;

            // 初始化政策
            if (!policies[policyId]) {
                policies[policyId] = {
                    policy_id: policyId,
                    title: params.title,
                    versions: [],
                    current_version: null,
                    created_at: new Date().toISOString()
                };
            }

            const version = {
                version_id: generatePolicyVersionId(),
                version_number: policies[policyId].versions.length + 1,
                title: params.title,
                content: params.content || '',
                content_hash: params.content ?
                    hashCode(params.content) : null,
                status: STATUS.DRAFT,
                effective_date: params.effective_date || null,
                expiry_date: params.expiry_date || null,
                author: params.author || 'system',
                reviewer: null,
                review_comment: '',
                change_log: params.change_log || '初始版本',
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                did: META.did
            };

            policies[policyId].versions.unshift(version);
            policies[policyId].title = params.title;
            policies[policyId].updated_at = new Date().toISOString();

            savePolicies(policies);
            addAuditLog('create_version', params, version);

            return {
                success: true,
                trace_id: traceId,
                policy: policies[policyId],
                version: version,
                message: '政策版本创建成功'
            };

        } catch (error) {
            return {success: false, error: error.message, trace_id: traceId};
        }
    }

    /**
     * 状态流转
     */
    function transitionStatus(policyId, versionId, newStatus, params = {}) {
        const traceId = generateTraceId();

        try {
            const policies = loadPolicies();
            const policy = policies[policyId];

            if (!policy) {
                return {success: false, error: '政策不存在', trace_id: traceId};
            }

            const version = policy.versions.find(v => v.version_id === versionId);
            if (!version) {
                return {success: false, error: '版本不存在', trace_id: traceId};
            }

            // 校验状态流转合法性
            const allowed = TRANSITIONS[version.status] || [];
            if (!allowed.includes(newStatus)) {
                return {
                    success: false,
                    error: `不允许从 ${version.status} 流转到 ${newStatus}`,
                    allowed_transitions: allowed,
                    trace_id: traceId
                };
            }

            // 生效校验：生效日期不能晚于当前日期
            if (newStatus === STATUS.ACTIVE) {
                if (!version.effective_date) {
                    return {success: false, error: '生效政策必须设置生效日期', trace_id: traceId};
                }
                const effectiveDate = new Date(version.effective_date);
                if (effectiveDate > new Date()) {
                    return {
                        success: false,
                        error: `生效日期 ${version.effective_date} 晚于当前日期，暂不能生效`,
                        trace_id: traceId
                    };
                }
            }

            const oldStatus = version.status;
            version.status = newStatus;
            version.updated_at = new Date().toISOString();

            if (params.reviewer) version.reviewer = params.reviewer;
            if (params.review_comment) version.review_comment = params.review_comment;

            // 如果是生效，设置为当前版本
            if (newStatus === STATUS.ACTIVE) {
                // 将其他生效版本置为过期
                policy.versions.forEach(v => {
                    if (v.version_id !== versionId && v.status === STATUS.ACTIVE) {
                        v.status = STATUS.EXPIRED;
                        v.updated_at = new Date().toISOString();
                    }
                });
                policy.current_version = version.version_id;
            }

            // 记录变更历史
            if (!version.transition_history) {
                version.transition_history = [];
            }
            version.transition_history.push({
                from: oldStatus,
                to: newStatus,
                operator: params.reviewer || 'system',
                comment: params.review_comment || '',
                timestamp: new Date().toISOString()
            });

            savePolicies(policies);
            addAuditLog('transition', {policyId, versionId, oldStatus, newStatus}, version);

            return {
                success: true,
                trace_id: traceId,
                version: version,
                message: `状态已从 ${oldStatus} 变更为 ${newStatus}`
            };

        } catch (error) {
            return {success: false, error: error.message, trace_id: traceId};
        }
    }

    /**
     * 提交审核
     */
    function submitForReview(policyId, versionId, submitter) {
        return transitionStatus(policyId, versionId, STATUS.PENDING, {reviewer: submitter});
    }

    /**
     * 审核通过并生效
     */
    function approveAndActivate(policyId, versionId, reviewer, comment = '') {
        return transitionStatus(policyId, versionId, STATUS.ACTIVE, {reviewer, review_comment: comment});
    }

    /**
     * 驳回
     */
    function reject(policyId, versionId, reviewer, comment = '') {
        return transitionStatus(policyId, versionId, STATUS.DRAFT, {reviewer, review_comment: comment});
    }

    /**
     * 废止政策
     */
    function repeal(policyId, versionId, operator, reason = '') {
        return transitionStatus(policyId, versionId, STATUS.REPEALED, {reviewer: operator, review_comment: reason});
    }

    /**
     * 自动检查过期政策
     */
    function checkExpired() {
        const policies = loadPolicies();
        const now = new Date();
        const expired = [];

        for (const policyId in policies) {
            const policy = policies[policyId];
            for (const version of policy.versions) {
                if (version.status === STATUS.ACTIVE && version.expiry_date) {
                    const expiryDate = new Date(version.expiry_date);
                    if (expiryDate < now) {
                        version.status = STATUS.EXPIRED;
                        version.updated_at = now.toISOString();
                        if (!version.transition_history) version.transition_history = [];
                        version.transition_history.push({
                            from: STATUS.ACTIVE,
                            to: STATUS.EXPIRED,
                            operator: 'system_auto',
                            comment: '自动过期检测',
                            timestamp: now.toISOString()
                        });
                        expired.push({
                            policy_id: policyId,
                            version_id: version.version_id,
                            title: version.title,
                            expiry_date: version.expiry_date
                        });
                    }
                }
            }
        }

        if (expired.length > 0) {
            savePolicies(policies);
        }

        return {
            checked: true,
            expired_count: expired.length,
            expired_policies: expired
        };
    }

    /**
     * 获取政策版本列表
     */
    function getPolicyVersions(policyId) {
        const policies = loadPolicies();
        const policy = policies[policyId];
        return policy ? policy.versions : [];
    }

    /**
     * 获取当前生效版本
     */
    function getCurrentVersion(policyId) {
        const policies = loadPolicies();
        const policy = policies[policyId];
        if (!policy || !policy.current_version) return null;
        return policy.versions.find(v => v.version_id === policy.current_version) || null;
    }

    /**
     * 版本对比
     */
    function compareVersions(policyId, versionId1, versionId2) {
        const versions = getPolicyVersions(policyId);
        const v1 = versions.find(v => v.version_id === versionId1);
        const v2 = versions.find(v => v.version_id === versionId2);

        if (!v1 || !v2) {
            return {success: false, error: '版本不存在'};
        }

        return {
            success: true,
            version1: {id: v1.version_id, number: v1.version_number, status: v1.status},
            version2: {id: v2.version_id, number: v2.version_number, status: v2.status},
            content_changed: v1.content_hash !== v2.content_hash,
            title_changed: v1.title !== v2.title,
            effective_date_changed: v1.effective_date !== v2.effective_date,
            change_log_v1: v1.change_log,
            change_log_v2: v2.change_log
        };
    }

    /**
     * 获取所有政策概览
     */
    function getAllPolicies() {
        const policies = loadPolicies();
        return Object.values(policies).map(p => ({
            policy_id: p.policy_id,
            title: p.title,
            version_count: p.versions.length,
            current_version: p.current_version,
            current_status: p.versions.find(v => v.version_id === p.current_version)?.status || 'none',
            created_at: p.created_at,
            updated_at: p.updated_at
        }));
    }

    /**
     * 获取统计
     */
    function getStats() {
        const policies = loadPolicies();
        const allVersions = Object.values(policies).flatMap(p => p.versions);

        return {
            total_policies: Object.keys(policies).length,
            total_versions: allVersions.length,
            by_status: {
                draft: allVersions.filter(v => v.status === STATUS.DRAFT).length,
                pending: allVersions.filter(v => v.status === STATUS.PENDING).length,
                active: allVersions.filter(v => v.status === STATUS.ACTIVE).length,
                expired: allVersions.filter(v => v.status === STATUS.EXPIRED).length,
                repealed: allVersions.filter(v => v.status === STATUS.REPEALED).length,
                archived: allVersions.filter(v => v.status === STATUS.ARCHIVED).length
            },
            audit_log_count: auditLogs.length
        };
    }

    /**
     * 简单哈希函数
     */
    function hashCode(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return hash.toString(16);
    }

    /**
     * 导出政策生命周期数据
     */
    function exportData() {
        const data = {
            export_time: new Date().toISOString(),
            operator: META,
            policies: loadPolicies(),
            stats: getStats(),
            audit_logs: auditLogs
        };
        const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `gov_policy_lifecycle_${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
        return data;
    }

    return {
        META,
        STATUS,
        TRANSITIONS,
        createVersion,
        transitionStatus,
        submitForReview,
        approveAndActivate,
        reject,
        repeal,
        checkExpired,
        getPolicyVersions,
        getCurrentVersion,
        compareVersions,
        getAllPolicies,
        getStats,
        exportData,
        getAuditLogs: () => [...auditLogs]
    };
})();

if (typeof window !== 'undefined') {
    window.GovPolicyLifecycle = GovPolicyLifecycle;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = GovPolicyLifecycle;
}

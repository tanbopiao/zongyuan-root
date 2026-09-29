/**
 * 政务会话超时自动回收算子 GOV-OP-012
 * 确权标识：DID-BR-000002
 * 溯源水印：Ω₀⊂⊙∞⊂Ω
 * 版本：V1.0.0
 *
 * 核心功能：
 * 1. 会话超时自动检测
 * 2. 超时前预警提示
 * 3. 超时后自动清理会话数据
 * 4. 敏感信息防残留
 *
 * 阴阳具足：
 * - 阳（能力）：超时检测、预警提示、自动回收、会话续期、活跃统计
 * - 阴（约束）：敏感数据强制清除、回收日志留痕、不可恢复、隐私保护
 */

const GovSessionTimeout = (function() {
    'use strict';

    const META = {
        operator_id: 'GOV-OP-012',
        operator_name: '会话超时自动回收算子',
        version: 'V1.0.0',
        did: 'DID-BR-000002',
        trace_mark: 'Ω₀⊂⊙∞⊂Ω',
        created_at: '2026-09-05'
    };

    // 默认配置
    const DEFAULT_CONFIG = {
        timeout_minutes: 30,           // 超时时间（分钟）
        warning_minutes: 5,            // 超时前预警（分钟）
        check_interval_seconds: 30,    // 检测间隔（秒）
        max_sessions: 100,             // 最大会话数
        sensitive_keys: [              // 敏感信息字段
            'password', 'token', 'api_key', 'secret',
            'id_card', 'phone', 'email', 'address',
            'session_id', 'cookie'
        ]
    };

    // 会话存储key
    const STORAGE_KEY = 'gov_sessions';
    const RECOVERY_LOG_KEY = 'gov_session_recovery_logs';

    // 定时器
    let checkTimer = null;
    let warningCallback = null;
    let timeoutCallback = null;

    // 审计日志
    let auditLogs = [];

    function generateSessionId() {
        return 'SES-' + Date.now().toString(36).toUpperCase() + '-' +
            Math.random().toString(36).substr(2, 6).toUpperCase();
    }

    function generateTraceId() {
        return 'TIMEOUT-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
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
     * 加载会话
     */
    function loadSessions() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
        } catch (e) {
            return {};
        }
    }

    /**
     * 保存会话
     */
    function saveSessions(sessions) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
    }

    /**
     * 加载回收日志
     */
    function loadRecoveryLogs() {
        try {
            return JSON.parse(localStorage.getItem(RECOVERY_LOG_KEY) || '[]');
        } catch (e) {
            return [];
        }
    }

    /**
     * 保存回收日志
     */
    function saveRecoveryLogs(logs) {
        localStorage.setItem(RECOVERY_LOG_KEY, JSON.stringify(logs.slice(-500)));
    }

    /**
     * 清除敏感信息
     */
    function sanitizeSensitiveData(data) {
        if (!data || typeof data !== 'object') return data;

        const sanitized = {...data};
        for (const key of DEFAULT_CONFIG.sensitive_keys) {
            if (sanitized[key]) {
                sanitized[key] = '***REDACTED***';
            }
        }
        // 递归处理嵌套对象
        for (const key in sanitized) {
            if (sanitized[key] && typeof sanitized[key] === 'object') {
                sanitized[key] = sanitizeSensitiveData(sanitized[key]);
            }
        }
        return sanitized;
    }

    /**
     * 创建会话
     * @param {Object} params
     * @param {string} params.user_id - 用户ID
     * @param {Object} params.data - 会话数据
     * @param {number} params.timeout_minutes - 自定义超时时间（可选）
     * @returns {Object} 会话
     */
    function createSession(params) {
        const traceId = generateTraceId();

        try {
            const sessions = loadSessions();

            // 检查最大会话数
            if (Object.keys(sessions).length >= DEFAULT_CONFIG.max_sessions) {
                // 回收最旧的会话
                const oldestId = Object.keys(sessions).reduce((a, b) =>
                    sessions[a].last_active < sessions[b].last_active ? a : b
                );
                recoverSession(oldestId, 'max_sessions_exceeded');
            }

            const sessionId = generateSessionId();
            const now = Date.now();
            const timeoutMs = (params.timeout_minutes || DEFAULT_CONFIG.timeout_minutes) * 60 * 1000;

            const session = {
                session_id: sessionId,
                user_id: params.user_id || 'anonymous',
                data: sanitizeSensitiveData(params.data || {}),
                created_at: new Date(now).toISOString(),
                last_active: new Date(now).toISOString(),
                expires_at: new Date(now + timeoutMs).toISOString(),
                timeout_minutes: params.timeout_minutes || DEFAULT_CONFIG.timeout_minutes,
                status: 'active',
                activity_count: 1,
                did: META.did
            };

            sessions[sessionId] = session;
            saveSessions(sessions);

            addAuditLog('create_session', params, {session_id: sessionId});

            return {
                success: true,
                trace_id: traceId,
                session: session,
                message: '会话创建成功'
            };

        } catch (error) {
            return {success: false, error: error.message, trace_id: traceId};
        }
    }

    /**
     * 会话活跃（续期）
     */
    function touchSession(sessionId) {
        const traceId = generateTraceId();

        try {
            const sessions = loadSessions();
            const session = sessions[sessionId];

            if (!session) {
                return {success: false, error: '会话不存在或已回收', trace_id: traceId};
            }

            if (session.status !== 'active') {
                return {success: false, error: `会话状态为 ${session.status}，无法续期`, trace_id: traceId};
            }

            const now = Date.now();
            const timeoutMs = session.timeout_minutes * 60 * 1000;

            session.last_active = new Date(now).toISOString();
            session.expires_at = new Date(now + timeoutMs).toISOString();
            session.activity_count++;

            saveSessions(sessions);
            addAuditLog('touch_session', {sessionId}, {expires_at: session.expires_at});

            return {
                success: true,
                trace_id: traceId,
                session: session,
                remaining_minutes: Math.round((new Date(session.expires_at) - now) / 60000)
            };

        } catch (error) {
            return {success: false, error: error.message, trace_id: traceId};
        }
    }

    /**
     * 回收会话
     */
    function recoverSession(sessionId, reason = 'timeout') {
        const traceId = generateTraceId();

        try {
            const sessions = loadSessions();
            const session = sessions[sessionId];

            if (!session) {
                return {success: false, error: '会话不存在', trace_id: traceId};
            }

            // 记录回收日志
            const recoveryLog = {
                session_id: sessionId,
                user_id: session.user_id,
                reason: reason,
                created_at: session.created_at,
                last_active: session.last_active,
                activity_count: session.activity_count,
                recovered_at: new Date().toISOString(),
                trace_id: traceId
            };

            const logs = loadRecoveryLogs();
            logs.push(recoveryLog);
            saveRecoveryLogs(logs);

            // 删除会话
            delete sessions[sessionId];
            saveSessions(sessions);

            addAuditLog('recover_session', {sessionId, reason}, recoveryLog);

            return {
                success: true,
                trace_id: traceId,
                recovery: recoveryLog,
                message: `会话已回收（原因：${reason}）`
            };

        } catch (error) {
            return {success: false, error: error.message, trace_id: traceId};
        }
    }

    /**
     * 检查超时会话
     */
    function checkTimeouts() {
        const sessions = loadSessions();
        const now = Date.now();
        const warnings = [];
        const timeouts = [];

        for (const sessionId in sessions) {
            const session = sessions[sessionId];
            if (session.status !== 'active') continue;

            const expiresAt = new Date(session.expires_at).getTime();
            const remainingMs = expiresAt - now;
            const warningMs = DEFAULT_CONFIG.warning_minutes * 60 * 1000;

            if (remainingMs <= 0) {
                // 已超时
                timeouts.push(sessionId);
            } else if (remainingMs <= warningMs) {
                // 即将超时
                warnings.push({
                    session_id: sessionId,
                    user_id: session.user_id,
                    remaining_minutes: Math.ceil(remainingMs / 60000)
                });
            }
        }

        // 回收超时会话
        for (const sessionId of timeouts) {
            recoverSession(sessionId, 'auto_timeout');
        }

        // 触发预警回调
        if (warnings.length > 0 && warningCallback) {
            try {
                warningCallback(warnings);
            } catch (e) {
                console.error('预警回调异常:', e);
            }
        }

        // 触发超时回调
        if (timeouts.length > 0 && timeoutCallback) {
            try {
                timeoutCallback(timeouts);
            } catch (e) {
                console.error('超时回调异常:', e);
            }
        }

        return {
            checked: true,
            active_sessions: Object.keys(sessions).length,
            warning_count: warnings.length,
            timeout_count: timeouts.length,
            warnings: warnings,
            timed_out: timeouts
        };
    }

    /**
     * 启动自动检测
     */
    function startAutoCheck(config = {}) {
        if (checkTimer) {
            stopAutoCheck();
        }

        const interval = (config.check_interval_seconds || DEFAULT_CONFIG.check_interval_seconds) * 1000;
        checkTimer = setInterval(() => {
            checkTimeouts();
        }, interval);

        addAuditLog('start_auto_check', config, {interval_seconds: interval / 1000});

        return {
            success: true,
            interval_seconds: interval / 1000,
            message: '会话超时自动检测已启动'
        };
    }

    /**
     * 停止自动检测
     */
    function stopAutoCheck() {
        if (checkTimer) {
            clearInterval(checkTimer);
            checkTimer = null;
            addAuditLog('stop_auto_check', {}, {});
            return {success: true, message: '自动检测已停止'};
        }
        return {success: true, message: '自动检测未运行'};
    }

    /**
     * 设置预警回调
     */
    function onWarning(callback) {
        warningCallback = callback;
    }

    /**
     * 设置超时回调
     */
    function onTimeout(callback) {
        timeoutCallback = callback;
    }

    /**
     * 获取活跃会话
     */
    function getActiveSessions() {
        const sessions = loadSessions();
        return Object.values(sessions).filter(s => s.status === 'active');
    }

    /**
     * 获取会话详情
     */
    function getSession(sessionId) {
        const sessions = loadSessions();
        return sessions[sessionId] || null;
    }

    /**
     * 获取回收日志
     */
    function getRecoveryLogs(limit = 50) {
        return loadRecoveryLogs().slice(-limit).reverse();
    }

    /**
     * 获取统计
     */
    function getStats() {
        const sessions = loadSessions();
        const logs = loadRecoveryLogs();
        const active = Object.values(sessions).filter(s => s.status === 'active');

        return {
            total_sessions: Object.keys(sessions).length,
            active_sessions: active.length,
            total_recovered: logs.length,
            today_recovered: logs.filter(l =>
                l.recovered_at && l.recovered_at.startsWith(new Date().toISOString().slice(0, 10))
            ).length,
            auto_check_running: checkTimer !== null,
            audit_log_count: auditLogs.length
        };
    }

    /**
     * 批量回收所有会话
     */
    function recoverAll(reason = 'manual_clear_all') {
        const sessions = loadSessions();
        const count = Object.keys(sessions).length;

        for (const sessionId in sessions) {
            recoverSession(sessionId, reason);
        }

        return {
            success: true,
            recovered_count: count,
            message: `已回收全部 ${count} 个会话`
        };
    }

    /**
     * 导出数据
     */
    function exportData() {
        const data = {
            export_time: new Date().toISOString(),
            operator: META,
            stats: getStats(),
            active_sessions: getActiveSessions(),
            recovery_logs: getRecoveryLogs(100),
            audit_logs: auditLogs
        };
        const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `gov_session_timeout_${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
        return data;
    }

    return {
        META,
        DEFAULT_CONFIG,
        createSession,
        touchSession,
        recoverSession,
        checkTimeouts,
        startAutoCheck,
        stopAutoCheck,
        onWarning,
        onTimeout,
        getActiveSessions,
        getSession,
        getRecoveryLogs,
        getStats,
        recoverAll,
        exportData,
        getAuditLogs: () => [...auditLogs]
    };
})();

if (typeof window !== 'undefined') {
    window.GovSessionTimeout = GovSessionTimeout;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = GovSessionTimeout;
}

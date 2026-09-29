/**
 * 政务运营统计算子 GOV-OP-017
 * 确权标识：DID-BR-000002
 * 溯源水印：Ω₀⊂⊙∞⊂Ω
 * 版本：V1.0.0
 *
 * 核心功能：
 * 1. 访问量统计（PV/UV/页面分布）
 * 2. 功能使用统计（问答次数/政策查询/公文生成）
 * 3. 用户活跃度统计
 * 4. 数据可视化报表生成
 *
 * 阴阳具足：
 * - 阳（能力）：多维度统计、实时计数、趋势分析、排行榜、报表导出
 * - 阴（约束）：隐私保护（匿名化）、数据最小化、统计口径一致、审计留痕
 */

const GovAnalytics = (function() {
    'use strict';

    const META = {
        operator_id: 'GOV-OP-017',
        operator_name: '运营统计算子',
        version: 'V1.0.0',
        did: 'DID-BR-000002',
        trace_mark: 'Ω₀⊂⊙∞⊂Ω',
        created_at: '2026-09-05'
    };

    // 存储key
    const STORAGE_KEY = 'gov_analytics_data';
    const EVENT_KEY = 'gov_analytics_events';

    // 审计日志
    let auditLogs = [];

    function generateTraceId() {
        return 'ANALYTICS-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
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
     * 生成匿名用户ID（隐私保护）
     */
    function getAnonymousUserId() {
        let uid = localStorage.getItem('gov_anon_uid');
        if (!uid) {
            uid = 'anon_' + Math.random().toString(36).substr(2, 12);
            localStorage.setItem('gov_anon_uid', uid);
        }
        return uid;
    }

    /**
     * 加载统计数据
     */
    function loadData() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY) || getDefaultData());
        } catch (e) {
            return getDefaultData();
        }
    }

    /**
     * 默认数据结构
     */
    function getDefaultData() {
        return {
            total_pv: 0,
            total_uv: 0,
            unique_visitors: [],
            page_views: {},
            function_usage: {
                chat: 0,
                policy_search: 0,
                doc_generate: 0,
                guide_query: 0,
                compliance_check: 0
            },
            daily_stats: {},
            hourly_stats: {},
            user_sessions: 0,
            avg_session_duration: 0,
            created_at: new Date().toISOString()
        };
    }

    /**
     * 保存统计数据
     */
    function saveData(data) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    }

    /**
     * 记录事件
     */
    function recordEvent(eventType, data = {}) {
        const traceId = generateTraceId();
        try {
            const events = JSON.parse(localStorage.getItem(EVENT_KEY) || '[]');
            const event = {
                event_id: 'EVT-' + Date.now().toString(36).toUpperCase(),
                event_type: eventType,
                anonymous_user_id: getAnonymousUserId(),
                data: data,
                timestamp: new Date().toISOString(),
                trace_id: traceId
            };
            events.push(event);
            // 最多保留10000条事件
            if (events.length > 10000) {
                events.splice(0, events.length - 10000);
            }
            localStorage.setItem(EVENT_KEY, JSON.stringify(events));
            addAuditLog('record_event', {eventType, data}, event);
            return {success: true, trace_id: traceId, event};
        } catch (error) {
            return {success: false, error: error.message, trace_id: traceId};
        }
    }

    /**
     * 记录页面访问（PV）
     */
    function trackPageView(pageName) {
        const data = loadData();
        const today = new Date().toISOString().slice(0, 10);
        const hour = new Date().getHours();
        const uid = getAnonymousUserId();

        // 总PV
        data.total_pv++;

        // UV（匿名）
        if (!data.unique_visitors.includes(uid)) {
            data.unique_visitors.push(uid);
            data.total_uv = data.unique_visitors.length;
        }

        // 页面分布
        data.page_views[pageName] = (data.page_views[pageName] || 0) + 1;

        // 每日统计
        if (!data.daily_stats[today]) {
            data.daily_stats[today] = {pv: 0, uv: 0, visitors: []};
        }
        data.daily_stats[today].pv++;
        if (!data.daily_stats[today].visitors.includes(uid)) {
            data.daily_stats[today].visitors.push(uid);
            data.daily_stats[today].uv = data.daily_stats[today].visitors.length;
        }

        // 每小时统计
        if (!data.hourly_stats[today]) {
            data.hourly_stats[today] = {};
        }
        data.hourly_stats[today][hour] = (data.hourly_stats[today][hour] || 0) + 1;

        saveData(data);
        recordEvent('page_view', {page: pageName});

        return {success: true, page: pageName, total_pv: data.total_pv};
    }

    /**
     * 记录功能使用
     */
    function trackFunctionUsage(functionName, details = {}) {
        const data = loadData();

        if (data.function_usage[functionName] !== undefined) {
            data.function_usage[functionName]++;
        } else {
            data.function_usage[functionName] = 1;
        }

        saveData(data);
        recordEvent('function_usage', {function: functionName, details});

        return {
            success: true,
            function: functionName,
            count: data.function_usage[functionName]
        };
    }

    /**
     * 记录会话开始
     */
    function trackSessionStart() {
        const data = loadData();
        data.user_sessions++;
        sessionStorage.setItem('gov_session_start', Date.now().toString());
        saveData(data);
        recordEvent('session_start', {});
        return {success: true, session_count: data.user_sessions};
    }

    /**
     * 记录会话结束
     */
    function trackSessionEnd() {
        const startTime = parseInt(sessionStorage.getItem('gov_session_start') || '0');
        if (startTime === 0) return {success: false, error: '无活跃会话'};

        const duration = Date.now() - startTime;
        const data = loadData();

        // 更新平均会话时长
        const totalDuration = data.avg_session_duration * (data.user_sessions - 1) + duration;
        data.avg_session_duration = Math.round(totalDuration / data.user_sessions);

        saveData(data);
        sessionStorage.removeItem('gov_session_start');
        recordEvent('session_end', {duration_ms: duration});

        return {
            success: true,
            duration_ms: duration,
            avg_duration_ms: data.avg_session_duration
        };
    }

    /**
     * 获取总览统计
     */
    function getOverview() {
        const data = loadData();
        const today = new Date().toISOString().slice(0, 10);
        const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);

        const todayStats = data.daily_stats[today] || {pv: 0, uv: 0};
        const yesterdayStats = data.daily_stats[yesterday] || {pv: 0, uv: 0};

        // 计算环比
        const pvChange = yesterdayStats.pv > 0 ?
            ((todayStats.pv - yesterdayStats.pv) / yesterdayStats.pv * 100).toFixed(1) : 'N/A';
        const uvChange = yesterdayStats.uv > 0 ?
            ((todayStats.uv - yesterdayStats.uv) / yesterdayStats.uv * 100).toFixed(1) : 'N/A';

        return {
            total_pv: data.total_pv,
            total_uv: data.total_uv,
            today_pv: todayStats.pv,
            today_uv: todayStats.uv,
            yesterday_pv: yesterdayStats.pv,
            yesterday_uv: yesterdayStats.uv,
            pv_change_percent: pvChange,
            uv_change_percent: uvChange,
            total_sessions: data.user_sessions,
            avg_session_duration_ms: data.avg_session_duration,
            avg_session_duration_min: Math.round(data.avg_session_duration / 60000)
        };
    }

    /**
     * 获取页面访问排行
     */
    function getPageRanking(limit = 10) {
        const data = loadData();
        const pages = Object.entries(data.page_views)
            .map(([name, count]) => ({page: name, views: count}))
            .sort((a, b) => b.views - a.views)
            .slice(0, limit);
        return pages;
    }

    /**
     * 获取功能使用排行
     */
    function getFunctionRanking() {
        const data = loadData();
        const functions = Object.entries(data.function_usage)
            .map(([name, count]) => ({function: name, count}))
            .sort((a, b) => b.count - a.count);
        return functions;
    }

    /**
     * 获取近7天趋势
     */
    function getWeeklyTrend() {
        const data = loadData();
        const trend = [];

        for (let i = 6; i >= 0; i--) {
            const date = new Date(Date.now() - i * 86400000).toISOString().slice(0, 10);
            const dayData = data.daily_stats[date] || {pv: 0, uv: 0};
            trend.push({
                date,
                pv: dayData.pv,
                uv: dayData.uv
            });
        }

        return trend;
    }

    /**
     * 获取24小时分布
     */
    function getHourlyDistribution() {
        const data = loadData();
        const today = new Date().toISOString().slice(0, 10);
        const hourly = data.hourly_stats[today] || {};
        const distribution = [];

        for (let h = 0; h < 24; h++) {
            distribution.push({
                hour: h,
                views: hourly[h] || 0
            });
        }

        return distribution;
    }

    /**
     * 生成运营报表
     */
    function generateReport() {
        const traceId = generateTraceId();
        const report = {
            report_id: 'RPT-' + Date.now().toString(36).toUpperCase(),
            generated_at: new Date().toISOString(),
            trace_id: traceId,
            overview: getOverview(),
            page_ranking: getPageRanking(10),
            function_ranking: getFunctionRanking(),
            weekly_trend: getWeeklyTrend(),
            hourly_distribution: getHourlyDistribution(),
            did: META.did
        };

        addAuditLog('generate_report', {}, report);
        return report;
    }

    /**
     * 导出报表
     */
    function exportReport(format = 'json') {
        const report = generateReport();
        const content = JSON.stringify(report, null, 2);

        if (format === 'json') {
            const blob = new Blob([content], {type: 'application/json;charset=utf-8'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `政务运营报表_${new Date().toISOString().slice(0,10)}.json`;
            a.click();
            URL.revokeObjectURL(url);
        }

        return report;
    }

    /**
     * 重置统计数据（管理员操作）
     */
    function resetData() {
        const traceId = generateTraceId();
        const defaultData = getDefaultData();
        saveData(defaultData);
        localStorage.setItem(EVENT_KEY, '[]');
        addAuditLog('reset_data', {}, {success: true});
        return {success: true, trace_id: traceId, message: '统计数据已重置'};
    }

    /**
     * 获取统计
     */
    function getStats() {
        const data = loadData();
        const events = JSON.parse(localStorage.getItem(EVENT_KEY) || '[]');
        return {
            total_pv: data.total_pv,
            total_uv: data.total_uv,
            total_events: events.length,
            total_sessions: data.user_sessions,
            tracked_pages: Object.keys(data.page_views).length,
            tracked_functions: Object.keys(data.function_usage).length,
            audit_log_count: auditLogs.length
        };
    }

    return {
        META,
        trackPageView,
        trackFunctionUsage,
        trackSessionStart,
        trackSessionEnd,
        recordEvent,
        getOverview,
        getPageRanking,
        getFunctionRanking,
        getWeeklyTrend,
        getHourlyDistribution,
        generateReport,
        exportReport,
        resetData,
        getStats,
        getAnonymousUserId,
        getAuditLogs: () => [...auditLogs]
    };
})();

if (typeof window !== 'undefined') {
    window.GovAnalytics = GovAnalytics;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = GovAnalytics;
}

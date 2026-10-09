/**
 * 政务人工复核工单流转算子 GOV-OP-015
 * 确权标识：DID-BR-000002
 * 溯源水印：Ω₀⊂⊙∞⊂Ω
 * 版本：V1.0.0
 *
 * 核心功能：
 * 1. AI可疑答复自动转人工工单
 * 2. 工单状态管理：待审核/审核通过/驳回/重生成
 * 3. 复核意见留痕
 * 4. 工单闭环流转
 *
 * 阴阳具足：
 * - 阳（能力）：工单创建、状态流转、意见留痕、超时预警、重复合并
 * - 阴（约束）：超时自动预警、重复工单合并、完整溯源绑定、审计日志
 */

const GovReview = (function() {
    'use strict';

    const META = {
        operator_id: 'GOV-OP-015',
        operator_name: '人工复核工单流转算子',
        version: 'V1.0.0',
        did: 'DID-BR-000002',
        trace_mark: 'Ω₀⊂⊙∞⊂Ω',
        created_at: '2026-09-05'
    };

    // 工单状态枚举
    const STATUS = {
        PENDING: 'pending',           // 待审核
        IN_REVIEW: 'in_review',       // 审核中
        APPROVED: 'approved',         // 审核通过
        REJECTED: 'rejected',         // 驳回
        REGENERATE: 'regenerate',     // 重生成
        CLOSED: 'closed'              // 已关闭
    };

    // 工单优先级
    const PRIORITY = {
        LOW: 'low',
        MEDIUM: 'medium',
        HIGH: 'high',
        CRITICAL: 'critical'
    };

    // 超时阈值（毫秒）
    const TIMEOUT = {
        pending: 24 * 60 * 60 * 1000,      // 待审核24小时
        in_review: 4 * 60 * 60 * 1000      // 审核中4小时
    };

    // 本地存储key
    const STORAGE_KEY = 'gov_review_workorders';

    // 审计日志
    let auditLogs = [];

    function generateWorkOrderId() {
        return 'WO-' + Date.now().toString(36).toUpperCase() + '-' +
            Math.random().toString(36).substr(2, 6).toUpperCase();
    }

    function generateTraceId() {
        return 'REVIEW-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
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
     * 加载所有工单
     */
    function loadWorkOrders() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
        } catch (e) {
            return [];
        }
    }

    /**
     * 保存工单
     */
    function saveWorkOrders(orders) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(orders));
    }

    /**
     * 创建工单
     * @param {Object} params
     * @param {string} params.content - 可疑内容
     * @param {Object} params.risk_info - 风险信息
     * @param {string} params.user_id - 用户ID
     * @param {string} params.session_id - 会话ID
     * @param {string} params.source - 来源（verification/compliance/manual）
     * @param {string} params.priority - 优先级
     * @returns {Object} 工单
     */
    function createWorkOrder(params) {
        const traceId = generateTraceId();

        try {
            const orders = loadWorkOrders();

            // 重复工单检测（相同内容+用户，30分钟内）
            const existing = orders.find(o =>
                o.content === params.content &&
                o.user_id === params.user_id &&
                o.status === STATUS.PENDING &&
                Date.now() - new Date(o.created_at).getTime() < 30 * 60 * 1000
            );

            if (existing) {
                addAuditLog('create_duplicate', params, {merged: existing.work_order_id});
                return {
                    success: true,
                    merged: true,
                    work_order: existing,
                    message: '检测到重复工单，已合并'
                };
            }

            const workOrder = {
                work_order_id: generateWorkOrderId(),
                trace_id: traceId,
                content: params.content,
                content_preview: (params.content || '').substring(0, 200),
                risk_info: params.risk_info || {},
                risk_level: params.risk_info?.risk_level || 'medium',
                user_id: params.user_id || 'anonymous',
                session_id: params.session_id || '',
                source: params.source || 'manual',
                priority: params.priority ||
                    (params.risk_info?.risk_level === 'high' ? PRIORITY.HIGH :
                     params.risk_info?.risk_level === 'critical' ? PRIORITY.CRITICAL : PRIORITY.MEDIUM),
                status: STATUS.PENDING,
                review_history: [],
                reviewer: null,
                review_comment: '',
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                deadline: new Date(Date.now() + TIMEOUT.pending).toISOString(),
                did: META.did
            };

            orders.unshift(workOrder);
            saveWorkOrders(orders);

            addAuditLog('create', params, workOrder);

            return {
                success: true,
                merged: false,
                work_order: workOrder,
                message: '工单创建成功'
            };

        } catch (error) {
            return {
                success: false,
                error: error.message,
                trace_id: traceId
            };
        }
    }

    /**
     * 更新工单状态
     */
    function updateStatus(workOrderId, newStatus, params = {}) {
        const traceId = generateTraceId();

        try {
            const orders = loadWorkOrders();
            const index = orders.findIndex(o => o.work_order_id === workOrderId);

            if (index === -1) {
                return {success: false, error: '工单不存在', trace_id: traceId};
            }

            const order = orders[index];
            const oldStatus = order.status;

            // 状态流转记录
            order.review_history.push({
                from_status: oldStatus,
                to_status: newStatus,
                reviewer: params.reviewer || 'system',
                comment: params.comment || '',
                timestamp: new Date().toISOString()
            });

            order.status = newStatus;
            order.updated_at = new Date().toISOString();

            if (params.reviewer) order.reviewer = params.reviewer;
            if (params.comment) order.review_comment = params.comment;

            // 审核通过/驳回后关闭
            if (newStatus === STATUS.APPROVED || newStatus === STATUS.REJECTED) {
                order.status = STATUS.CLOSED;
                order.closed_at = new Date().toISOString();
            }

            orders[index] = order;
            saveWorkOrders(orders);

            addAuditLog('update_status', {workOrderId, oldStatus, newStatus}, order);

            return {
                success: true,
                work_order: order,
                trace_id: traceId
            };

        } catch (error) {
            return {
                success: false,
                error: error.message,
                trace_id: traceId
            };
        }
    }

    /**
     * 审核通过
     */
    function approve(workOrderId, reviewer, comment = '') {
        return updateStatus(workOrderId, STATUS.APPROVED, {reviewer, comment});
    }

    /**
     * 驳回
     */
    function reject(workOrderId, reviewer, comment = '') {
        return updateStatus(workOrderId, STATUS.REJECTED, {reviewer, comment});
    }

    /**
     * 请求重生成
     */
    function requestRegenerate(workOrderId, reviewer, comment = '') {
        return updateStatus(workOrderId, STATUS.REGENERATE, {reviewer, comment});
    }

    /**
     * 开始审核
     */
    function startReview(workOrderId, reviewer) {
        return updateStatus(workOrderId, STATUS.IN_REVIEW, {reviewer});
    }

    /**
     * 获取工单列表
     */
    function getWorkOrders(filter = {}) {
        let orders = loadWorkOrders();

        if (filter.status) {
            orders = orders.filter(o => o.status === filter.status);
        }
        if (filter.priority) {
            orders = orders.filter(o => o.priority === filter.priority);
        }
        if (filter.user_id) {
            orders = orders.filter(o => o.user_id === filter.user_id);
        }
        if (filter.source) {
            orders = orders.filter(o => o.source === filter.source);
        }

        // 按优先级和时间排序
        const priorityOrder = {critical: 0, high: 1, medium: 2, low: 3};
        orders.sort((a, b) => {
            if (priorityOrder[a.priority] !== priorityOrder[b.priority]) {
                return priorityOrder[a.priority] - priorityOrder[b.priority];
            }
            return new Date(b.created_at) - new Date(a.created_at);
        });

        return orders;
    }

    /**
     * 获取单个工单
     */
    function getWorkOrder(workOrderId) {
        const orders = loadWorkOrders();
        return orders.find(o => o.work_order_id === workOrderId) || null;
    }

    /**
     * 超时检测与预警
     */
    function checkTimeouts() {
        const orders = loadWorkOrders();
        const now = Date.now();
        const warnings = [];

        for (const order of orders) {
            if (order.status === STATUS.PENDING || order.status === STATUS.IN_REVIEW) {
                const deadline = new Date(order.deadline).getTime();
                if (now > deadline) {
                    warnings.push({
                        work_order_id: order.work_order_id,
                        status: order.status,
                        priority: order.priority,
                        overdue_time: now - deadline,
                        message: `工单 ${order.work_order_id} 已超时`
                    });
                } else if (deadline - now < 60 * 60 * 1000) {
                    // 即将超时（1小时内）
                    warnings.push({
                        work_order_id: order.work_order_id,
                        status: order.status,
                        priority: order.priority,
                        remaining_time: deadline - now,
                        message: `工单 ${order.work_order_id} 即将超时`
                    });
                }
            }
        }

        return warnings;
    }

    /**
     * 获取统计
     */
    function getStats() {
        const orders = loadWorkOrders();
        const warnings = checkTimeouts();

        return {
            total: orders.length,
            pending: orders.filter(o => o.status === STATUS.PENDING).length,
            in_review: orders.filter(o => o.status === STATUS.IN_REVIEW).length,
            approved: orders.filter(o => o.review_history?.some(h => h.to_status === STATUS.APPROVED)).length,
            rejected: orders.filter(o => o.review_history?.some(h => h.to_status === STATUS.REJECTED)).length,
            closed: orders.filter(o => o.status === STATUS.CLOSED).length,
            high_priority: orders.filter(o => o.priority === PRIORITY.HIGH || o.priority === PRIORITY.CRITICAL).length,
            timeout_warnings: warnings.length,
            audit_log_count: auditLogs.length
        };
    }

    /**
     * 导出工单
     */
    function exportWorkOrders(format = 'json') {
        const orders = loadWorkOrders();
        const data = {
            export_time: new Date().toISOString(),
            operator: META,
            stats: getStats(),
            work_orders: orders
        };

        if (format === 'json') {
            const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `gov_review_workorders_${Date.now()}.json`;
            a.click();
            URL.revokeObjectURL(url);
        }

        return data;
    }

    /**
     * 清理已关闭工单（保留最近90天）
     */
    function cleanupClosedOrders(days = 90) {
        const orders = loadWorkOrders();
        const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
        const before = orders.length;
        const cleaned = orders.filter(o =>
            o.status !== STATUS.CLOSED ||
            !o.closed_at ||
            new Date(o.closed_at).getTime() > cutoff
        );
        saveWorkOrders(cleaned);
        return {cleaned: before - cleaned.length, remaining: cleaned.length};
    }

    return {
        META,
        STATUS,
        PRIORITY,
        createWorkOrder,
        updateStatus,
        approve,
        reject,
        requestRegenerate,
        startReview,
        getWorkOrders,
        getWorkOrder,
        checkTimeouts,
        getStats,
        exportWorkOrders,
        cleanupClosedOrders,
        getAuditLogs: () => [...auditLogs]
    };
})();

if (typeof window !== 'undefined') {
    window.GovReview = GovReview;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = GovReview;
}

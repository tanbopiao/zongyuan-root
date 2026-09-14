/**
 * 政务消息通知算子 GOV-OP-014
 * 确权标识：DID-BR-000002
 * 溯源水印：Ω₀⊂⊙∞⊂Ω
 * 版本：V1.0.0
 *
 * 核心功能：
 * 1. 系统公告推送
 * 2. 政策更新提醒
 * 3. 工单状态变更通知
 * 4. 未读消息计数
 *
 * 阴阳具足：
 * - 阳（能力）：多类型通知、实时推送、未读计数、已读标记、消息分类
 * - 阴（约束）：消息持久化、防重复推送、静默时段、用户偏好、审计留痕
 */

const GovNotification = (function() {
    'use strict';

    const META = {
        operator_id: 'GOV-OP-014',
        operator_name: '消息通知算子',
        version: 'V1.0.0',
        did: 'DID-BR-000002',
        trace_mark: 'Ω₀⊂⊙∞⊂Ω',
        created_at: '2026-09-05'
    };

    // 消息类型
    const TYPE = {
        SYSTEM: 'system',           // 系统公告
        POLICY: 'policy',           // 政策更新
        WORKORDER: 'workorder',     // 工单状态
        COMPLIANCE: 'compliance',   // 合规预警
        SESSION: 'session'          // 会话提醒
    };

    // 优先级
    const PRIORITY = {
        LOW: 'low',
        MEDIUM: 'medium',
        HIGH: 'high',
        URGENT: 'urgent'
    };

    // 存储key
    const STORAGE_KEY = 'gov_notifications';
    const PREF_KEY = 'gov_notification_prefs';

    // 审计日志
    let auditLogs = [];

    // 新消息回调
    let onNewMessage = null;

    function generateMessageId() {
        return 'MSG-' + Date.now().toString(36).toUpperCase() + '-' +
            Math.random().toString(36).substr(2, 4).toUpperCase();
    }

    function generateTraceId() {
        return 'NOTIFY-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
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
     * 加载消息
     */
    function loadMessages() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
        } catch (e) {
            return [];
        }
    }

    /**
     * 保存消息
     */
    function saveMessages(messages) {
        // 最多保留500条
        if (messages.length > 500) {
            messages = messages.slice(-500);
        }
        localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    }

    /**
     * 加载用户偏好
     */
    function loadPreferences() {
        try {
            return JSON.parse(localStorage.getItem(PREF_KEY) || '{}');
        } catch (e) {
            return {};
        }
    }

    /**
     * 保存用户偏好
     */
    function savePreferences(prefs) {
        localStorage.setItem(PREF_KEY, JSON.stringify(prefs));
    }

    /**
     * 检查是否在静默时段
     */
    function isQuietHours() {
        const prefs = loadPreferences();
        if (!prefs.quiet_hours_enabled) return false;

        const now = new Date();
        const hour = now.getHours();
        const start = prefs.quiet_hours_start || 22;
        const end = prefs.quiet_hours_end || 8;

        if (start < end) {
            return hour >= start && hour < end;
        } else {
            return hour >= start || hour < end;
        }
    }

    /**
     * 检查用户是否启用该类型通知
     */
    function isTypeEnabled(type) {
        const prefs = loadPreferences();
        if (prefs.disabled_types && prefs.disabled_types.includes(type)) {
            return false;
        }
        return true;
    }

    /**
     * 发送消息
     * @param {Object} params
     * @param {string} params.type - 消息类型
     * @param {string} params.title - 标题
     * @param {string} params.content - 内容
     * @param {string} params.priority - 优先级
     * @param {Object} params.data - 附加数据
     * @param {string} params.user_id - 目标用户
     * @returns {Object} 消息
     */
    function send(params) {
        const traceId = generateTraceId();

        try {
            if (!params.title || !params.content) {
                return {success: false, error: '标题和内容不能为空', trace_id: traceId};
            }

            const type = params.type || TYPE.SYSTEM;
            const priority = params.priority || PRIORITY.MEDIUM;

            // 检查用户偏好
            if (!isTypeEnabled(type)) {
                addAuditLog('send_blocked', params, {reason: 'type_disabled'});
                return {success: false, error: '该类型通知已被用户禁用', trace_id: traceId};
            }

            // 静默时段检查（紧急消息除外）
            if (isQuietHours() && priority !== PRIORITY.URGENT) {
                addAuditLog('send_queued', params, {reason: 'quiet_hours'});
                // 静默时段存入待发送队列
                const queued = JSON.parse(localStorage.getItem('gov_notification_queue') || '[]');
                queued.push({...params, queued_at: new Date().toISOString()});
                localStorage.setItem('gov_notification_queue', JSON.stringify(queued));
                return {success: true, queued: true, trace_id: traceId, message: '静默时段，已存入待发送队列'};
            }

            // 防重复：5分钟内相同标题+内容不重复发送
            const messages = loadMessages();
            const fiveMinutesAgo = Date.now() - 5 * 60 * 1000;
            const duplicate = messages.find(m =>
                m.title === params.title &&
                m.content === params.content &&
                new Date(m.created_at).getTime() > fiveMinutesAgo
            );

            if (duplicate) {
                addAuditLog('send_duplicate', params, {duplicate_id: duplicate.message_id});
                return {success: false, duplicate: true, trace_id: traceId, message: '5分钟内已发送过相同消息'};
            }

            const message = {
                message_id: generateMessageId(),
                trace_id: traceId,
                type,
                title: params.title,
                content: params.content,
                priority,
                data: params.data || {},
                user_id: params.user_id || 'all',
                read: false,
                read_at: null,
                created_at: new Date().toISOString(),
                did: META.did
            };

            messages.unshift(message);
            saveMessages(messages);

            // 触发新消息回调
            if (onNewMessage) {
                try {
                    onNewMessage(message);
                } catch (e) {
                    console.error('新消息回调异常:', e);
                }
            }

            addAuditLog('send', params, message);

            return {
                success: true,
                trace_id: traceId,
                message: message,
                unread_count: getUnreadCount()
            };

        } catch (error) {
            return {success: false, error: error.message, trace_id: traceId};
        }
    }

    /**
     * 系统公告
     */
    function sendSystemAnnouncement(title, content, priority = PRIORITY.HIGH) {
        return send({
            type: TYPE.SYSTEM,
            title,
            content,
            priority
        });
    }

    /**
     * 政策更新提醒
     */
    function sendPolicyUpdate(policyTitle, changeType, policyId) {
        return send({
            type: TYPE.POLICY,
            title: `政策更新：${policyTitle}`,
            content: `政策「${policyTitle}」已${changeType}，请及时查看。`,
            priority: PRIORITY.MEDIUM,
            data: {policy_id: policyId, change_type: changeType}
        });
    }

    /**
     * 工单状态变更通知
     */
    function sendWorkOrderUpdate(workOrderId, status, title) {
        const statusText = {
            pending: '待审核',
            in_review: '审核中',
            approved: '审核通过',
            rejected: '已驳回',
            closed: '已关闭'
        };
        return send({
            type: TYPE.WORKORDER,
            title: `工单状态变更：${statusText[status] || status}`,
            content: `您的工单「${title}」状态已变更为「${statusText[status] || status}」。`,
            priority: status === 'rejected' ? PRIORITY.HIGH : PRIORITY.MEDIUM,
            data: {work_order_id: workOrderId, status}
        });
    }

    /**
     * 合规预警
     */
    function sendComplianceAlert(level, description) {
        return send({
            type: TYPE.COMPLIANCE,
            title: `合规预警（${level}）`,
            content: description,
            priority: level === 'critical' ? PRIORITY.URGENT : PRIORITY.HIGH
        });
    }

    /**
     * 标记已读
     */
    function markAsRead(messageId) {
        const traceId = generateTraceId();
        const messages = loadMessages();
        const msg = messages.find(m => m.message_id === messageId);

        if (!msg) {
            return {success: false, error: '消息不存在', trace_id: traceId};
        }

        msg.read = true;
        msg.read_at = new Date().toISOString();
        saveMessages(messages);

        addAuditLog('mark_read', {messageId}, msg);
        return {success: true, trace_id: traceId, unread_count: getUnreadCount()};
    }

    /**
     * 全部标记已读
     */
    function markAllAsRead() {
        const traceId = generateTraceId();
        const messages = loadMessages();
        const now = new Date().toISOString();
        let count = 0;

        for (const msg of messages) {
            if (!msg.read) {
                msg.read = true;
                msg.read_at = now;
                count++;
            }
        }

        saveMessages(messages);
        addAuditLog('mark_all_read', {}, {count});

        return {success: true, trace_id: traceId, marked_count: count};
    }

    /**
     * 获取未读数量
     */
    function getUnreadCount() {
        const messages = loadMessages();
        return messages.filter(m => !m.read).length;
    }

    /**
     * 获取消息列表
     */
    function getMessages(filter = {}) {
        let messages = loadMessages();

        if (filter.type) {
            messages = messages.filter(m => m.type === filter.type);
        }
        if (filter.read !== undefined) {
            messages = messages.filter(m => m.read === filter.read);
        }
        if (filter.priority) {
            messages = messages.filter(m => m.priority === filter.priority);
        }

        // 按时间倒序
        messages.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

        return messages;
    }

    /**
     * 删除消息
     */
    function deleteMessage(messageId) {
        const traceId = generateTraceId();
        let messages = loadMessages();
        const before = messages.length;
        messages = messages.filter(m => m.message_id !== messageId);
        saveMessages(messages);

        addAuditLog('delete', {messageId}, {deleted: before - messages.length});
        return {success: true, trace_id: traceId, deleted: before - messages.length};
    }

    /**
     * 清空已读消息
     */
    function clearRead() {
        const traceId = generateTraceId();
        let messages = loadMessages();
        const before = messages.length;
        messages = messages.filter(m => !m.read);
        saveMessages(messages);

        addAuditLog('clear_read', {}, {cleared: before - messages.length});
        return {success: true, trace_id: traceId, cleared: before - messages.length};
    }

    /**
     * 处理静默时段队列
     */
    function processQueuedMessages() {
        if (isQuietHours()) return {processed: 0, reason: 'still_quiet_hours'};

        const queued = JSON.parse(localStorage.getItem('gov_notification_queue') || '[]');
        let processed = 0;

        for (const msg of queued) {
            send(msg);
            processed++;
        }

        localStorage.setItem('gov_notification_queue', '[]');
        addAuditLog('process_queue', {}, {processed});

        return {success: true, processed};
    }

    /**
     * 设置新消息回调
     */
    function setOnNewMessage(callback) {
        onNewMessage = callback;
    }

    /**
     * 更新用户偏好
     */
    function updatePreferences(prefs) {
        const current = loadPreferences();
        const updated = {...current, ...prefs};
        savePreferences(updated);
        addAuditLog('update_prefs', prefs, updated);
        return updated;
    }

    /**
     * 获取统计
     */
    function getStats() {
        const messages = loadMessages();
        return {
            total: messages.length,
            unread: getUnreadCount(),
            read: messages.filter(m => m.read).length,
            by_type: {
                system: messages.filter(m => m.type === TYPE.SYSTEM).length,
                policy: messages.filter(m => m.type === TYPE.POLICY).length,
                workorder: messages.filter(m => m.type === TYPE.WORKORDER).length,
                compliance: messages.filter(m => m.type === TYPE.COMPLIANCE).length,
                session: messages.filter(m => m.type === TYPE.SESSION).length
            },
            by_priority: {
                urgent: messages.filter(m => m.priority === PRIORITY.URGENT).length,
                high: messages.filter(m => m.priority === PRIORITY.HIGH).length,
                medium: messages.filter(m => m.priority === PRIORITY.MEDIUM).length,
                low: messages.filter(m => m.priority === PRIORITY.LOW).length
            },
            queued: JSON.parse(localStorage.getItem('gov_notification_queue') || '[]').length,
            audit_log_count: auditLogs.length
        };
    }

    return {
        META,
        TYPE,
        PRIORITY,
        send,
        sendSystemAnnouncement,
        sendPolicyUpdate,
        sendWorkOrderUpdate,
        sendComplianceAlert,
        markAsRead,
        markAllAsRead,
        getUnreadCount,
        getMessages,
        deleteMessage,
        clearRead,
        processQueuedMessages,
        setOnNewMessage,
        updatePreferences,
        getStats,
        getAuditLogs: () => [...auditLogs]
    };
})();

if (typeof window !== 'undefined') {
    window.GovNotification = GovNotification;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = GovNotification;
}

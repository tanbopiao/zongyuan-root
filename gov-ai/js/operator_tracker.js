/**
 * 政务中台算子调用上报器
 * 自动追踪页面功能使用情况，上报到算子统计API
 * DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
 */
(function() {
  'use strict';

  const API_BASE = '/gov-api/api/gov/operators/call';
  const TRACKED_EVENTS = [];
  let sessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);

  // 算子ID映射表
  const OP_IDS = {
    'chat': 'GOV-OP-006',
    'policy_search': 'GOV-OP-007',
    'doc_generate': 'GOV-OP-008',
    'guide_query': 'GOV-OP-009',
    'compliance_check': 'GOV-OP-010',
    'verification': 'GOV-OP-011',
    'review': 'GOV-OP-015',
    'session_timeout': 'GOV-OP-012',
    'policy_lifecycle': 'GOV-OP-016',
    'export': 'GOV-OP-013',
    'notification': 'GOV-OP-014',
    'analytics': 'GOV-OP-017',
    'api_call': 'GOV-OP-001',
    'user_action': 'GOV-OP-002',
    'modal': 'GOV-OP-003',
    'loading': 'GOV-OP-004',
    'audit': 'GOV-OP-005'
  };

  // 上报函数
  function reportOperatorCall(opType, success, latencyMs, details) {
    const opId = OP_IDS[opType] || opType;
    const payload = {
      op_id: opId,
      success: success !== false,
      latency_ms: latencyMs || 0,
      details: Object.assign({
        session_id: sessionId,
        page: window.location.pathname,
        user_agent: navigator.userAgent.substring(0, 100)
      }, details || {})
    };

    // 异步上报，不阻塞页面
    if (navigator.sendBeacon) {
      const blob = new Blob([JSON.stringify(payload)], {type: 'application/json'});
      navigator.sendBeacon(API_BASE, blob);
    } else {
      fetch(API_BASE, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
        keepalive: true
      }).catch(() => {});
    }

    TRACKED_EVENTS.push({
      op_id: opId,
      success: payload.success,
      latency_ms: payload.latency_ms,
      timestamp: new Date().toISOString()
    });
  }

  // 自动追踪页面加载
  function trackPageLoad() {
    const startTime = performance.now();
    window.addEventListener('load', function() {
      const loadTime = Math.round(performance.now() - startTime);
      reportOperatorCall('loading', true, loadTime, {event: 'page_load'});
    });
  }

  // 自动追踪API调用（包装fetch）
  function trackApiCalls() {
    const originalFetch = window.fetch;
    if (originalFetch) {
      window.fetch = function(...args) {
        const startTime = performance.now();
        const url = typeof args[0] === 'string' ? args[0] : args[0].url;
        return originalFetch.apply(this, args).then(function(response) {
          const latency = Math.round(performance.now() - startTime);
          if (url.includes('/gov-api/')) {
            reportOperatorCall('api_call', response.ok, latency, {url: url.substring(0, 100)});
          }
          return response;
        }).catch(function(error) {
          const latency = Math.round(performance.now() - startTime);
          reportOperatorCall('api_call', false, latency, {url: url.substring(0, 100), error: error.message});
          throw error;
        });
      };
    }
  }

  // 自动追踪按钮点击
  function trackButtonClicks() {
    document.addEventListener('click', function(e) {
      const target = e.target.closest('button, .quick-item, .tab-item, .list-item, .hot-item');
      if (!target) return;

      const text = target.textContent.trim().substring(0, 50);
      let opType = 'user_action';

      // 根据文本内容判断算子类型
      if (text.includes('问答') || text.includes('提问') || text.includes('发送')) opType = 'chat';
      else if (text.includes('政策') || text.includes('搜索')) opType = 'policy_search';
      else if (text.includes('公文') || text.includes('生成')) opType = 'doc_generate';
      else if (text.includes('办事') || text.includes('指南')) opType = 'guide_query';
      else if (text.includes('合规') || text.includes('审查')) opType = 'compliance_check';
      else if (text.includes('导出') || text.includes('下载')) opType = 'export';
      else if (text.includes('通知') || text.includes('消息')) opType = 'notification';

      reportOperatorCall(opType, true, 0, {action: 'click', text: text});
    }, true);
  }

  // 自动追踪表单提交
  function trackFormSubmits() {
    document.addEventListener('submit', function(e) {
      const form = e.target;
      reportOperatorCall('user_action', true, 0, {action: 'form_submit', form_id: form.id || 'unknown'});
    }, true);
  }

  // 会话超时追踪
  function trackSessionTimeout() {
    let lastActivity = Date.now();
    const TIMEOUT_MS = 30 * 60 * 1000; // 30分钟

    ['click', 'keypress', 'scroll', 'mousemove'].forEach(function(evt) {
      document.addEventListener(evt, function() {
        lastActivity = Date.now();
      }, true);
    });

    setInterval(function() {
      const idleTime = Date.now() - lastActivity;
      if (idleTime > TIMEOUT_MS) {
        reportOperatorCall('session_timeout', true, idleTime, {event: 'session_timeout'});
        lastActivity = Date.now(); // 重置，避免重复上报
      }
    }, 60000);
  }

  // 页面离开时上报会话统计
  function trackSessionEnd() {
    window.addEventListener('beforeunload', function() {
      reportOperatorCall('analytics', true, 0, {
        event: 'session_end',
        duration: Math.round((Date.now() - parseInt(sessionId.split('_')[1])) / 1000),
        events_tracked: TRACKED_EVENTS.length
      });
    });
  }

  // 初始化
  function init() {
    trackPageLoad();
    trackApiCalls();
    trackButtonClicks();
    trackFormSubmits();
    trackSessionTimeout();
    trackSessionEnd();
    console.log('✅ 算子调用上报器已启动，会话ID:', sessionId);
  }

  // 暴露全局API
  window.OperatorTracker = {
    report: reportOperatorCall,
    getSessionId: function() { return sessionId; },
    getTrackedEvents: function() { return TRACKED_EVENTS; }
  };

  // 自动初始化
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

/**
 * 政务操作审计算子 - GOV-OP-005
 * 操作日志审计：记录、上报、导出、统计
 * 功能: 记录用户所有操作，支持合规审计
 */
class GovAuditOperator {
  constructor(options = {}) {
    this.maxLogs = options.maxLogs || 500;
    this.autoSave = options.autoSave !== false;
    this.logs = this._load();
    this.sessionId = this._generateSessionId();
    this.startTime = new Date().toISOString();
  }

  _generateSessionId() {
    return 'sess_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 6);
  }

  _load() {
    try {
      return JSON.parse(localStorage.getItem('gov_audit_logs') || '[]');
    } catch (e) { return []; }
  }

  _save() {
    if (this.autoSave) {
      localStorage.setItem('gov_audit_logs', JSON.stringify(this.logs.slice(-this.maxLogs)));
    }
  }

  /**
   * 记录操作
   * @param {string} action - 操作类型（如: chat, search, generate, export）
   * @param {Object} data - 操作数据
   * @param {string} result - 结果（success/failure）
   */
  log(action, data = {}, result = 'success') {
    const entry = {
      id: 'log_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 4),
      sessionId: this.sessionId,
      timestamp: new Date().toISOString(),
      action,
      data,
      result,
      userAgent: navigator.userAgent.substring(0, 80),
      url: window.location.pathname
    };
    this.logs.push(entry);
    if (this.logs.length > this.maxLogs) {
      this.logs = this.logs.slice(-this.maxLogs);
    }
    this._save();
    return entry.id;
  }

  // 便捷方法
  logChat(message, responseLength) {
    return this.log('chat', { messageLength: message.length, responseLength }, 'success');
  }

  logSearch(keyword, resultsCount) {
    return this.log('search', { keyword, resultsCount }, 'success');
  }

  logGenerate(docType, length) {
    return this.log('generate', { docType, length }, 'success');
  }

  logExport(type, size) {
    return this.log('export', { type, size }, 'success');
  }

  logError(action, error) {
    return this.log(action, { error: error.message || String(error) }, 'failure');
  }

  logPageView(page) {
    return this.log('page_view', { page }, 'success');
  }

  /**
   * 查询日志
   */
  query(filters = {}) {
    let result = [...this.logs];
    if (filters.action) result = result.filter(l => l.action === filters.action);
    if (filters.result) result = result.filter(l => l.result === filters.result);
    if (filters.sessionId) result = result.filter(l => l.sessionId === filters.sessionId);
    if (filters.startTime) result = result.filter(l => l.timestamp >= filters.startTime);
    if (filters.endTime) result = result.filter(l => l.timestamp <= filters.endTime);
    if (filters.limit) result = result.slice(-filters.limit);
    return result;
  }

  /**
   * 统计
   */
  getStats() {
    const stats = {
      total: this.logs.length,
      sessionId: this.sessionId,
      sessionStart: this.startTime,
      byAction: {},
      byResult: { success: 0, failure: 0 },
      byPage: {}
    };
    this.logs.forEach(log => {
      stats.byAction[log.action] = (stats.byAction[log.action] || 0) + 1;
      stats.byResult[log.result] = (stats.byResult[log.result] || 0) + 1;
      stats.byPage[log.url] = (stats.byPage[log.url] || 0) + 1;
    });
    return stats;
  }

  /**
   * 导出日志
   */
  export(format = 'json') {
    if (format === 'json') {
      return JSON.stringify({
        sessionId: this.sessionId,
        exportedAt: new Date().toISOString(),
        total: this.logs.length,
        logs: this.logs
      }, null, 2);
    }
    if (format === 'csv') {
      const headers = ['id', 'timestamp', 'action', 'result', 'url', 'data'];
      const rows = this.logs.map(l => [
        l.id, l.timestamp, l.action, l.result, l.url,
        JSON.stringify(l.data).replace(/"/g, '""')
      ]);
      return [headers.join(','), ...rows.map(r => r.map(c => `"${c}"`).join(','))].join('\n');
    }
    return null;
  }

  /**
   * 下载日志文件
   */
  download(format = 'json', filename) {
    const content = this.export(format);
    const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || `gov_audit_${new Date().toISOString().slice(0, 10)}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  /**
   * 清空日志
   */
  clear() {
    this.logs = [];
    this._save();
  }

  /**
   * 获取当前会话日志
   */
  getSessionLogs() {
    return this.logs.filter(l => l.sessionId === this.sessionId);
  }
}

if (typeof window !== 'undefined') window.GovAuditOperator = GovAuditOperator;

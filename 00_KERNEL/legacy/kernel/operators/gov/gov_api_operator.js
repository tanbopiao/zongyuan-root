/**
 * 政务API调用算子 - GOV-OP-001
 * 统一所有政务中台页面的API调用
 * 功能: fetch封装、重试、缓存、错误处理、审计日志
 */
class GovAPIOperator {
  constructor(baseUrl = '/gov-api', options = {}) {
    this.baseUrl = baseUrl;
    this.timeout = options.timeout || 30000;
    this.retryCount = options.retryCount || 2;
    this.retryDelay = options.retryDelay || 1000;
    this.cache = new Map();
    this.cacheTTL = options.cacheTTL || 60000;
    this.auditLog = [];
  }

  async get(endpoint, options = {}) {
    return this._request('GET', endpoint, null, options);
  }

  async post(endpoint, data, options = {}) {
    return this._request('POST', endpoint, data, options);
  }

  async _request(method, endpoint, data = null, options = {}) {
    const url = this.baseUrl + endpoint;
    const cacheKey = method + ':' + url + ':' + JSON.stringify(data || {});

    if (method === 'GET' && !options.noCache) {
      const cached = this._getCache(cacheKey);
      if (cached) return cached;
    }

    let lastError = null;
    for (let attempt = 0; attempt <= this.retryCount; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);
        const fetchOptions = {
          method: method,
          headers: { 'Content-Type': 'application/json' },
          signal: controller.signal
        };
        if (data) fetchOptions.body = JSON.stringify(data);

        const response = await fetch(url, fetchOptions);
        clearTimeout(timeoutId);
        const result = await response.json();
        this._logAudit(method, endpoint, response.status, attempt);

        if (method === 'GET' && response.ok && !options.noCache) {
          this._setCache(cacheKey, result);
        }
        if (!response.ok) throw new Error('API错误 ' + response.status);
        return result;
      } catch (error) {
        lastError = error;
        if (attempt < this.retryCount && !options.noRetry) {
          await this._sleep(this.retryDelay * (attempt + 1));
          continue;
        }
      }
    }
    this._logAudit(method, endpoint, 'FAILED', this.retryCount);
    return { error: lastError.message, success: false };
  }

  _getCache(key) {
    const entry = this.cache.get(key);
    if (entry && Date.now() - entry.time < this.cacheTTL) return entry.data;
    this.cache.delete(key);
    return null;
  }

  _setCache(key, data) {
    this.cache.set(key, { data, time: Date.now() });
    if (this.cache.size > 100) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
  }

  clearCache() { this.cache.clear(); }

  _logAudit(method, endpoint, status, attempt) {
    this.auditLog.push({ time: new Date().toISOString(), method, endpoint, status, attempt });
    if (this.auditLog.length > 200) this.auditLog = this.auditLog.slice(-100);
  }

  getAuditLog() { return [...this.auditLog]; }

  _sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }
}

if (typeof window !== 'undefined') window.GovAPIOperator = GovAPIOperator;

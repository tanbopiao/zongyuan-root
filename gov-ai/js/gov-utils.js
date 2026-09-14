// ========== 政务中台统一工具库 V1.0 ==========
// 统一错误处理 | API调用封装 | 重试机制 | 用户友好提示
// P1优化：统一错误处理

const GovUtils = (function() {
    'use strict';

    // 配置
    const CONFIG = {
        maxRetries: 2,           // 最大重试次数
        retryDelay: 1000,        // 重试延迟(ms)
        timeout: 30000,          // 超时时间(ms)
        showErrorToast: true,    // 是否显示错误提示
        logErrors: true          // 是否记录错误日志
    };

    // 错误码映射
    const ERROR_MESSAGES = {
        400: '请求参数错误，请检查输入',
        401: '登录已过期，请重新登录',
        403: '没有权限执行此操作',
        404: '请求的资源不存在',
        408: '请求超时，请稍后重试',
        429: '请求过于频繁，请稍后再试',
        500: '服务器内部错误，请稍后重试',
        502: '网关错误，服务暂时不可用',
        503: '服务维护中，请稍后再试',
        504: '网关超时，请稍后重试'
    };

    // 显示Toast提示
    function showToast(message, type = 'info', duration = 3000) {
        // 检查是否已有toast容器
        let container = document.getElementById('gov-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'gov-toast-container';
            container.style.cssText = 'position:fixed;top:20px;right:20px;z-index:99999;display:flex;flex-direction:column;gap:8px;pointer-events:none;';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        const colors = {
            success: 'background:linear-gradient(135deg,#1b5e20,#2e7d32);border-color:#4caf50;',
            error: 'background:linear-gradient(135deg,#b71c1c,#c62828);border-color:#f44336;',
            warning: 'background:linear-gradient(135deg,#e65100,#ef6c00);border-color:#ff9800;',
            info: 'background:linear-gradient(135deg,#0d47a1,#1565c0);border-color:#2196f3;'
        };
        const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };

        toast.style.cssText = `
            ${colors[type] || colors.info}
            color:#fff;padding:12px 20px;border-radius:8px;border:1px solid;
            box-shadow:0 4px 12px rgba(0,0,0,0.3);font-size:14px;
            display:flex;align-items:center;gap:8px;max-width:360px;
            animation:govToastIn .3s ease-out;pointer-events:auto;
        `;
        toast.innerHTML = `<span style="font-size:16px">${icons[type] || icons.info}</span><span>${message}</span>`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'govToastOut .3s ease-in forwards';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    // 记录错误日志
    function logError(context, error, extra = {}) {
        if (!CONFIG.logErrors) return;
        const errorLog = {
            time: new Date().toISOString(),
            context: context,
            message: error.message || String(error),
            stack: error.stack || null,
            extra: extra,
            url: window.location.href,
            userAgent: navigator.userAgent
        };
        console.error('[GovUtils Error]', errorLog);

        // 尝试上报到后端（如果有错误收集API）
        try {
            if (window._govErrorLogs === undefined) window._govErrorLogs = [];
            window._govErrorLogs.push(errorLog);
            // 最多保留100条
            if (window._govErrorLogs.length > 100) window._govErrorLogs.shift();
        } catch (e) {}
    }

    // 带超时的fetch
    function fetchWithTimeout(url, options = {}, timeout = CONFIG.timeout) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);
        return fetch(url, { ...options, signal: controller.signal })
            .finally(() => clearTimeout(timeoutId));
    }

    // 延迟
    function delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // 统一API调用（带重试+错误处理）
    async function govFetch(url, options = {}) {
        const {
            method = 'GET',
            body = null,
            headers = {},
            retries = CONFIG.maxRetries,
            showError = CONFIG.showErrorToast,
            loadingEl = null,
            ...rest
        } = options;

        let lastError = null;

        for (let attempt = 0; attempt <= retries; attempt++) {
            try {
                // 显示加载状态
                if (loadingEl) loadingEl.style.display = 'block';

                const fetchOptions = {
                    method,
                    headers: {
                        'Content-Type': 'application/json',
                        ...headers
                    },
                    ...rest
                };
                if (body && method !== 'GET') {
                    fetchOptions.body = typeof body === 'string' ? body : JSON.stringify(body);
                }

                const response = await fetchWithTimeout(url, fetchOptions);

                // 处理HTTP错误
                if (!response.ok) {
                    const errorText = await response.text().catch(() => '');
                    let errorData = {};
                    try { errorData = JSON.parse(errorText); } catch (e) {}

                    const errorMessage = errorData.error || errorData.message ||
                        ERROR_MESSAGES[response.status] || `请求失败 (${response.status})`;

                    // 401/403不重试
                    if (response.status === 401 || response.status === 403) {
                        if (showError) showToast(errorMessage, 'error');
                        logError('govFetch', new Error(errorMessage), { url, status: response.status, attempt });
                        throw new Error(errorMessage);
                    }

                    // 429/5xx可重试
                    if ((response.status === 429 || response.status >= 500) && attempt < retries) {
                        lastError = new Error(errorMessage);
                        await delay(CONFIG.retryDelay * (attempt + 1));
                        continue;
                    }

                    if (showError) showToast(errorMessage, 'error');
                    logError('govFetch', new Error(errorMessage), { url, status: response.status, attempt });
                    throw new Error(errorMessage);
                }

                // 解析响应
                const contentType = response.headers.get('content-type') || '';
                let data;
                if (contentType.includes('application/json')) {
                    data = await response.json();
                } else {
                    data = await response.text();
                }

                // 检查业务错误（API返回{error: "..."}）
                if (data && typeof data === 'object' && data.error && !data.result) {
                    const errorMessage = data.error || '业务处理失败';
                    if (showError) showToast(errorMessage, 'warning');
                    logError('govFetch business', new Error(errorMessage), { url, data });
                }

                return data;

            } catch (error) {
                lastError = error;

                // 超时/网络错误可重试
                if ((error.name === 'AbortError' || error.name === 'TypeError' || !error.message.startsWith('请求失败')) && attempt < retries) {
                    await delay(CONFIG.retryDelay * (attempt + 1));
                    continue;
                }

                // 最终失败
                if (showError && error.message !== '请求失败 (401)' && error.message !== '请求失败 (403)') {
                    const userMessage = error.name === 'AbortError' ?
                        '请求超时，请检查网络后重试' :
                        (error.message || '网络请求失败');
                    showToast(userMessage, 'error');
                }
                logError('govFetch final', error, { url, attempt });
                throw error;

            } finally {
                if (loadingEl) loadingEl.style.display = 'none';
            }
        }

        throw lastError || new Error('请求失败');
    }

    // 便捷方法
    const api = {
        get: (url, options) => govFetch(url, { ...options, method: 'GET' }),
        post: (url, body, options) => govFetch(url, { ...options, method: 'POST', body }),
        put: (url, body, options) => govFetch(url, { ...options, method: 'PUT', body }),
        del: (url, options) => govFetch(url, { ...options, method: 'DELETE' })
    };

    // 全局错误监听
    function initGlobalErrorHandling() {
        // 未捕获的Promise错误
        window.addEventListener('unhandledrejection', function(event) {
            logError('unhandledrejection', event.reason || new Error('Unhandled Promise rejection'));
        });

        // 全局JS错误
        window.addEventListener('error', function(event) {
            if (event.message && !event.message.includes('ResizeObserver')) {
                logError('global error', new Error(event.message), {
                    filename: event.filename,
                    lineno: event.lineno,
                    colno: event.colno
                });
            }
        });

        // 添加Toast动画样式
        const style = document.createElement('style');
        style.textContent = `
            @keyframes govToastIn { from { opacity:0; transform:translateX(100px); } to { opacity:1; transform:translateX(0); } }
            @keyframes govToastOut { from { opacity:1; transform:translateX(0); } to { opacity:0; transform:translateX(100px); } }
        `;
        document.head.appendChild(style);

        console.log('[GovUtils] 全局错误处理已初始化');
    }

    // 自动初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initGlobalErrorHandling);
    } else {
        initGlobalErrorHandling();
    }

    // 暴露API
    return {
        fetch: govFetch,
        api: api,
        showToast: showToast,
        logError: logError,
        config: CONFIG,
        getErrorLogs: () => window._govErrorLogs || [],
        clearErrorLogs: () => { if (window._govErrorLogs) window._govErrorLogs = []; }
    };
})();

// 兼容旧代码：暴露到全局
window.govFetch = GovUtils.fetch;
window.govApi = GovUtils.api;
window.govToast = GovUtils.showToast;

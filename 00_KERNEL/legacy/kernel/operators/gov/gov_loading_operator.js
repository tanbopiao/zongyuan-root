/**
 * 政务加载状态算子 - GOV-OP-004
 * 统一加载状态管理：loading、error、empty、骨架屏
 * 功能: 替代不统一的加载提示
 */
class GovLoadingOperator {
  constructor(options = {}) {
    this.spinnerColor = options.spinnerColor || '#1a73e8';
    this.textColor = options.textColor || '#5f6368';
    this._initStyles();
  }

  _initStyles() {
    if (document.getElementById('gov-loading-styles')) return;
    const style = document.createElement('style');
    style.id = 'gov-loading-styles';
    style.textContent = `
      .gov-loading-container {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; padding: 40px 20px; min-height: 200px;
      }
      .gov-spinner {
        width: 36px; height: 36px; border: 3px solid #e8f0fe;
        border-top-color: #1a73e8; border-radius: 50%;
        animation: govSpin 0.8s linear infinite;
      }
      .gov-loading-text {
        margin-top: 12px; font-size: 14px; color: #5f6368;
      }
      .gov-error-container {
        display: flex; flex-direction: column; align-items: center;
        padding: 40px 20px; text-align: center;
      }
      .gov-error-icon { font-size: 40px; margin-bottom: 12px; }
      .gov-error-text { font-size: 14px; color: #d93025; margin-bottom: 8px; }
      .gov-error-retry {
        margin-top: 12px; padding: 8px 20px; background: #1a73e8;
        color: #fff; border: none; border-radius: 8px; cursor: pointer;
        font-size: 14px;
      }
      .gov-empty-container {
        display: flex; flex-direction: column; align-items: center;
        padding: 40px 20px; text-align: center;
      }
      .gov-empty-icon { font-size: 48px; margin-bottom: 12px; opacity: 0.5; }
      .gov-empty-text { font-size: 14px; color: #9aa0a6; }
      .gov-skeleton {
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 200% 100%;
        animation: govSkeleton 1.5s ease-in-out infinite;
        border-radius: 4px;
      }
      @keyframes govSpin { to { transform: rotate(360deg); } }
      @keyframes govSkeleton {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
      }
    `;
    document.head.appendChild(style);
  }

  showLoading(container, text = '加载中...') {
    if (typeof container === 'string') {
      container = document.querySelector(container);
    }
    if (!container) return;
    container.innerHTML = `
      <div class="gov-loading-container">
        <div class="gov-spinner"></div>
        <div class="gov-loading-text">${text}</div>
      </div>
    `;
  }

  showError(container, message, onRetry) {
    if (typeof container === 'string') {
      container = document.querySelector(container);
    }
    if (!container) return;
    container.innerHTML = `
      <div class="gov-error-container">
        <div class="gov-error-icon">⚠️</div>
        <div class="gov-error-text">${message}</div>
        ${onRetry ? '<button class="gov-error-retry">重试</button>' : ''}
      </div>
    `;
    if (onRetry) {
      container.querySelector('.gov-error-retry').addEventListener('click', onRetry);
    }
  }

  showEmpty(container, text = '暂无数据', icon = '📭') {
    if (typeof container === 'string') {
      container = document.querySelector(container);
    }
    if (!container) return;
    container.innerHTML = `
      <div class="gov-empty-container">
        <div class="gov-empty-icon">${icon}</div>
        <div class="gov-empty-text">${text}</div>
      </div>
    `;
  }

  showSkeleton(container, lines = 5) {
    if (typeof container === 'string') {
      container = document.querySelector(container);
    }
    if (!container) return;
    let html = '<div style="padding: 16px;">';
    for (let i = 0; i < lines; i++) {
      const width = 60 + Math.random() * 40;
      const height = i === 0 ? 20 : 14;
      html += `<div class="gov-skeleton" style="width:${width}%;height:${height}px;margin-bottom:${8 + Math.random() * 8}px;"></div>`;
    }
    html += '</div>';
    container.innerHTML = html;
  }

  showContent(container, content) {
    if (typeof container === 'string') {
      container = document.querySelector(container);
    }
    if (!container) return;
    if (typeof content === 'string') {
      container.innerHTML = content;
    } else if (content instanceof HTMLElement) {
      container.innerHTML = '';
      container.appendChild(content);
    }
  }

  /**
   * 自动管理异步加载状态
   * @param {string|HTMLElement} container - 容器
   * @param {Function} asyncFn - 异步函数
   * @param {Object} options - {loadingText, errorText, emptyText, emptyCheck}
   */
  async autoManage(container, asyncFn, options = {}) {
    this.showLoading(container, options.loadingText || '加载中...');
    try {
      const result = await asyncFn();
      if (options.emptyCheck && options.emptyCheck(result)) {
        this.showEmpty(container, options.emptyText || '暂无数据');
      } else {
        return result;
      }
    } catch (error) {
      this.showError(container, options.errorText || error.message, () => {
        this.autoManage(container, asyncFn, options);
      });
      throw error;
    }
  }
}

if (typeof window !== 'undefined') window.GovLoadingOperator = GovLoadingOperator;

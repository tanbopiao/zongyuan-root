/**
 * 火斗云智AIOS 转化数据埋点脚本
 * DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω
 *
 * 跟踪事件：
 * - 页面访问（page_view）
 * - 按钮点击（button_click）
 * - 卡片点击（card_click）
 * - 下载链接点击（download_click）
 * - 试用申请提交（trial_submit）
 * - Demo交互（demo_interact）
 */

class HuodouaiTracker {
  constructor(options = {}) {
    this.endpoint = options.endpoint || '/api/track'
    this.sessionId = this._getOrCreateSessionId()
    this.events = []
    this.startTime = Date.now()

    // 自动记录页面访问
    this.track('page_view', {
      page: location.pathname,
      referrer: document.referrer,
      title: document.title
    })

    // 页面卸载时上报
    window.addEventListener('beforeunload', () => {
      this.flush()
    })
  }

  _getOrCreateSessionId() {
    let sid = sessionStorage.getItem('huodouai_sid')
    if (!sid) {
      sid = 'sid-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9)
      sessionStorage.setItem('huodouai_sid', sid)
    }
    return sid
  }

  track(eventName, properties = {}) {
    const event = {
      event: eventName,
      timestamp: Date.now(),
      session_id: this.sessionId,
      page: location.pathname,
      properties: properties
    }
    this.events.push(event)

    // 控制台输出（开发模式）
    if (location.hostname === 'localhost') {
      console.log('[Tracker]', eventName, properties)
    }
  }

  flush() {
    if (this.events.length === 0) return

    const payload = {
      events: this.events,
      session_id: this.sessionId,
      duration: Date.now() - this.startTime
    }

    // 使用sendBeacon确保页面卸载时也能发送
    if (navigator.sendBeacon) {
      navigator.sendBeacon(this.endpoint, JSON.stringify(payload))
    } else {
      fetch(this.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        keepalive: true
      })
    }

    this.events = []
  }
}

// 自动绑定常见元素点击
function bindAutoTracking(tracker) {
  // 跟踪所有产品卡片点击
  document.querySelectorAll('.product-card').forEach(card => {
    card.addEventListener('click', () => {
      const title = card.querySelector('.product-title')?.textContent || 'unknown'
      const href = card.getAttribute('href') || ''
      tracker.track('card_click', {
        card_name: title,
        href: href
      })
    })
  })

  // 跟踪所有按钮点击
  document.querySelectorAll('button, .btn').forEach(btn => {
    btn.addEventListener('click', () => {
      tracker.track('button_click', {
        text: btn.textContent?.trim() || '',
        page: location.pathname
      })
    })
  })

  // 跟踪下载链接点击
  document.querySelectorAll('a[href$=".zip"], a[href*="download"]').forEach(link => {
    link.addEventListener('click', () => {
      tracker.track('download_click', {
        href: link.getAttribute('href'),
        page: location.pathname
      })
    })
  })
}

// 自动初始化
if (typeof window !== 'undefined') {
  window.huodouaiTracker = new HuodouaiTracker()

  // DOM加载完成后绑定自动跟踪
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      bindAutoTracking(window.huodouaiTracker)
    })
  } else {
    bindAutoTracking(window.huodouaiTracker)
  }
}

// 导出供其他脚本使用
if (typeof module !== 'undefined') {
  module.exports = HuodouaiTracker
}

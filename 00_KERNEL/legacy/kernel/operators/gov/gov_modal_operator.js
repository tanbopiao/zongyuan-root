/**
 * 政务弹窗算子 - GOV-OP-003
 * 统一弹窗组件：创建、显示、关闭、动画、事件
 * 功能: 替代每个页面自己写的modal
 */
class GovModalOperator {
  constructor(options = {}) {
    this.zIndex = options.zIndex || 1000;
    this.animationDuration = options.animationDuration || 200;
    this.modals = new Map();
    this._initStyles();
  }

  _initStyles() {
    if (document.getElementById('gov-modal-styles')) return;
    const style = document.createElement('style');
    style.id = 'gov-modal-styles';
    style.textContent = `
      .gov-modal-overlay {
        display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.5); z-index: 1000;
        align-items: center; justify-content: center; padding: 20px;
        animation: govFadeIn 0.2s ease;
      }
      .gov-modal-overlay.active { display: flex; }
      .gov-modal-card {
        background: #fff; border-radius: 16px; max-width: 600px; width: 100%;
        max-height: 80vh; overflow: hidden; display: flex; flex-direction: column;
        animation: govSlideUp 0.25s ease;
      }
      .gov-modal-header {
        padding: 16px 20px; border-bottom: 1px solid #e0e0e0;
        display: flex; justify-content: space-between; align-items: center;
        font-size: 16px; font-weight: 600;
      }
      .gov-modal-close {
        font-size: 24px; cursor: pointer; color: #9aa0a6;
        background: none; border: none; line-height: 1;
      }
      .gov-modal-body { padding: 20px; overflow-y: auto; flex: 1; }
      .gov-modal-footer {
        padding: 12px 20px; border-top: 1px solid #e0e0e0;
        display: flex; gap: 8px; justify-content: flex-end;
      }
      .gov-modal-btn {
        padding: 8px 16px; border-radius: 8px; font-size: 14px;
        cursor: pointer; border: none; font-weight: 500;
      }
      .gov-modal-btn.primary { background: #1a73e8; color: #fff; }
      .gov-modal-btn.secondary { background: #e8f0fe; color: #1a73e8; }
      @keyframes govFadeIn { from { opacity: 0; } to { opacity: 1; } }
      @keyframes govSlideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
    `;
    document.head.appendChild(style);
  }

  create(id, options = {}) {
    const overlay = document.createElement('div');
    overlay.className = 'gov-modal-overlay';
    overlay.id = 'gov-modal-' + id;
    overlay.innerHTML = `
      <div class="gov-modal-card">
        <div class="gov-modal-header">
          <span>${options.title || '提示'}</span>
          <button class="gov-modal-close">&times;</button>
        </div>
        <div class="gov-modal-body">${options.content || ''}</div>
        ${options.footer ? `<div class="gov-modal-footer">${options.footer}</div>` : ''}
      </div>
    `;
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay || e.target.classList.contains('gov-modal-close')) {
        this.close(id);
      }
    });
    document.body.appendChild(overlay);
    this.modals.set(id, overlay);
    return overlay;
  }

  show(id, content) {
    let modal = this.modals.get(id);
    if (!modal) {
      modal = this.create(id, { title: id });
    }
    if (content) {
      modal.querySelector('.gov-modal-body').innerHTML = content;
    }
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  close(id) {
    const modal = this.modals.get(id);
    if (modal) {
      modal.classList.remove('active');
      document.body.style.overflow = '';
    }
  }

  closeAll() {
    this.modals.forEach((modal) => modal.classList.remove('active'));
    document.body.style.overflow = '';
  }

  setContent(id, content) {
    const modal = this.modals.get(id);
    if (modal) {
      modal.querySelector('.gov-modal-body').innerHTML = content;
    }
  }

  setTitle(id, title) {
    const modal = this.modals.get(id);
    if (modal) {
      modal.querySelector('.gov-modal-header span').textContent = title;
    }
  }

  destroy(id) {
    const modal = this.modals.get(id);
    if (modal) {
      modal.remove();
      this.modals.delete(id);
    }
  }

  alert(message, title = '提示') {
    return new Promise((resolve) => {
      const id = 'alert-' + Date.now();
      this.create(id, {
        title,
        content: `<div style="font-size:14px;line-height:1.7">${message}</div>`,
        footer: `<button class="gov-modal-btn primary" data-action="ok">确定</button>`
      });
      const modal = this.modals.get(id);
      modal.querySelector('[data-action="ok"]').addEventListener('click', () => {
        this.close(id);
        setTimeout(() => { this.destroy(id); resolve(); }, 200);
      });
      this.show(id);
    });
  }

  confirm(message, title = '确认') {
    return new Promise((resolve) => {
      const id = 'confirm-' + Date.now();
      this.create(id, {
        title,
        content: `<div style="font-size:14px;line-height:1.7">${message}</div>`,
        footer: `
          <button class="gov-modal-btn secondary" data-action="cancel">取消</button>
          <button class="gov-modal-btn primary" data-action="ok">确定</button>
        `
      });
      const modal = this.modals.get(id);
      modal.querySelector('[data-action="ok"]').addEventListener('click', () => {
        this.close(id);
        setTimeout(() => { this.destroy(id); resolve(true); }, 200);
      });
      modal.querySelector('[data-action="cancel"]').addEventListener('click', () => {
        this.close(id);
        setTimeout(() => { this.destroy(id); resolve(false); }, 200);
      });
      this.show(id);
    });
  }
}

if (typeof window !== 'undefined') window.GovModalOperator = GovModalOperator;

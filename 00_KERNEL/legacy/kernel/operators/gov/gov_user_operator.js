/**
 * 政务用户体系算子 - GOV-OP-002
 * 统一用户数据管理：历史记录、收藏、草稿、偏好
 * 功能: localStorage封装、数据持久化、容量管理
 */
class GovUserOperator {
  constructor(options = {}) {
    this.prefix = options.prefix || 'gov_';
    this.maxHistory = options.maxHistory || 50;
    this.maxDrafts = options.maxDrafts || 20;
    this.maxFavorites = options.maxFavorites || 100;
  }

  // ===== 咨询历史 =====
  getHistory() {
    try {
      return JSON.parse(localStorage.getItem(this.prefix + 'chat_history') || '[]');
    } catch (e) { return []; }
  }

  addHistory(message) {
    const history = this.getHistory();
    history.push({ ...message, time: new Date().toISOString() });
    localStorage.setItem(this.prefix + 'chat_history', JSON.stringify(history.slice(-this.maxHistory)));
    return history.length;
  }

  clearHistory() {
    localStorage.removeItem(this.prefix + 'chat_history');
  }

  // ===== 收藏政策 =====
  getFavorites() {
    try {
      return JSON.parse(localStorage.getItem(this.prefix + 'favorites') || '[]');
    } catch (e) { return []; }
  }

  addFavorite(item) {
    const favorites = this.getFavorites();
    if (!favorites.find(f => f.id === item.id)) {
      favorites.push(item);
      localStorage.setItem(this.prefix + 'favorites', JSON.stringify(favorites.slice(-this.maxFavorites)));
      return true;
    }
    return false;
  }

  removeFavorite(id) {
    const favorites = this.getFavorites().filter(f => f.id !== id);
    localStorage.setItem(this.prefix + 'favorites', JSON.stringify(favorites));
  }

  isFavorite(id) {
    return this.getFavorites().some(f => f.id === id);
  }

  toggleFavorite(item) {
    if (this.isFavorite(item.id)) {
      this.removeFavorite(item.id);
      return false;
    }
    this.addFavorite(item);
    return true;
  }

  // ===== 公文草稿 =====
  getDrafts() {
    try {
      return JSON.parse(localStorage.getItem(this.prefix + 'doc_drafts') || '[]');
    } catch (e) { return []; }
  }

  saveDraft(title, content) {
    const drafts = this.getDrafts();
    drafts.push({ title, content, time: new Date().toISOString() });
    localStorage.setItem(this.prefix + 'doc_drafts', JSON.stringify(drafts.slice(-this.maxDrafts)));
    return drafts.length;
  }

  deleteDraft(index) {
    const drafts = this.getDrafts();
    drafts.splice(index, 1);
    localStorage.setItem(this.prefix + 'doc_drafts', JSON.stringify(drafts));
  }

  // ===== 用户偏好 =====
  getPreferences() {
    try {
      return JSON.parse(localStorage.getItem(this.prefix + 'preferences') || '{}');
    } catch (e) { return {}; }
  }

  setPreference(key, value) {
    const prefs = this.getPreferences();
    prefs[key] = value;
    localStorage.setItem(this.prefix + 'preferences', JSON.stringify(prefs));
  }

  // ===== 统计 =====
  getStats() {
    return {
      historyCount: this.getHistory().length,
      favoritesCount: this.getFavorites().length,
      draftsCount: this.getDrafts().length,
      storageUsed: this._getStorageSize()
    };
  }

  _getStorageSize() {
    let total = 0;
    for (let key in localStorage) {
      if (key.startsWith(this.prefix)) {
        total += localStorage.getItem(key).length;
      }
    }
    return (total / 1024).toFixed(2) + ' KB';
  }

  // ===== 导出/导入 =====
  exportAll() {
    return {
      history: this.getHistory(),
      favorites: this.getFavorites(),
      drafts: this.getDrafts(),
      preferences: this.getPreferences(),
      exportedAt: new Date().toISOString()
    };
  }

  importAll(data) {
    if (data.history) localStorage.setItem(this.prefix + 'chat_history', JSON.stringify(data.history));
    if (data.favorites) localStorage.setItem(this.prefix + 'favorites', JSON.stringify(data.favorites));
    if (data.drafts) localStorage.setItem(this.prefix + 'doc_drafts', JSON.stringify(data.drafts));
    if (data.preferences) localStorage.setItem(this.prefix + 'preferences', JSON.stringify(data.preferences));
    return true;
  }
}

if (typeof window !== 'undefined') window.GovUserOperator = GovUserOperator;

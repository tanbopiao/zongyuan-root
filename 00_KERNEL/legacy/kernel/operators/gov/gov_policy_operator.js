/**
 * 政务政策查询算子 - GOV-OP-007
 * 封装政策检索、分类、详情、配图核心逻辑
 * 依赖: gov_api_operator
 * 功能: 搜索、分类筛选、详情、收藏、配图
 */
class GovPolicyOperator {
  constructor(options = {}) {
    this.api = options.api; // GovAPIOperator实例
    this.user = options.user; // GovUserOperator实例
    this.cache = new Map();
    this.cacheTTL = 5 * 60 * 1000; // 5分钟缓存
  }

  /**
   * 搜索政策
   */
  async search(keyword, options = {}) {
    const cacheKey = 'search:' + keyword + ':' + JSON.stringify(options);
    const cached = this._getCache(cacheKey);
    if (cached) return cached;

    const params = new URLSearchParams({ q: keyword });
    if (options.category) params.append('category', options.category);
    if (options.page) params.append('page', options.page);
    if (options.limit) params.append('limit', options.limit);

    const result = await this.api.get('/api/gov/policy/search?' + params.toString());
    if (result.error) return { error: result.error, success: false };

    const policies = result.policies || result.data || result.results || [];
    this._setCache(cacheKey, { policies, success: true });
    return { policies, success: true, total: result.total || policies.length };
  }

  /**
   * 获取政策分类
   */
  async getCategories() {
    const cached = this._getCache('categories');
    if (cached) return cached;

    const result = await this.api.get('/api/gov/policy/categories');
    if (result.error) return { error: result.error, success: false };

    const categories = result.categories || result.data || [];
    this._setCache('categories', { categories, success: true });
    return { categories, success: true };
  }

  /**
   * 获取政策详情
   */
  async getDetail(policyId) {
    const cacheKey = 'detail:' + policyId;
    const cached = this._getCache(cacheKey);
    if (cached) return cached;

    const result = await this.api.get('/api/gov/policy/detail?id=' + policyId);
    if (result.error) return { error: result.error, success: false };

    this._setCache(cacheKey, { policy: result, success: true });
    return { policy: result, success: true };
  }

  /**
   * 获取政策配图
   */
  async getImages(policyId) {
    const result = await this.api.get('/api/policy-images?id=' + policyId);
    if (result.error) return { error: result.error, success: false };
    const images = result.images || result.data || [];
    return { images, success: true };
  }

  /**
   * 收藏/取消收藏政策
   */
  toggleFavorite(policy) {
    if (!this.user) return false;
    return this.user.toggleFavorite({
      id: policy.id || policy.policy_id,
      title: policy.title || policy.name,
      category: policy.category,
      type: 'policy'
    });
  }

  /**
   * 检查是否已收藏
   */
  isFavorite(policyId) {
    if (!this.user) return false;
    return this.user.isFavorite(policyId);
  }

  /**
   * 获取热门政策
   */
  async getHot(limit = 10) {
    const result = await this.api.get('/api/hot?limit=' + limit);
    if (result.error) return { error: result.error, success: false };
    const hot = result.hot || result.data || [];
    return { hot, success: true };
  }

  /**
   * 渲染政策卡片HTML
   */
  renderPolicyCard(policy, options = {}) {
    const isFav = this.isFavorite(policy.id || policy.policy_id);
    return `
      <div class="policy-card" data-id="${policy.id || policy.policy_id}" style="padding:16px;border:1px solid #e0e0e0;border-radius:12px;margin-bottom:12px;cursor:pointer;">
        <div style="display:flex;justify-content:space-between;align-items:start;">
          <div style="flex:1;">
            <div style="font-size:15px;font-weight:600;color:#202124;margin-bottom:6px;">${policy.title || policy.name || '未命名政策'}</div>
            ${policy.category ? `<span style="display:inline-block;padding:2px 8px;background:#e8f0fe;color:#1a73e8;border-radius:4px;font-size:12px;margin-bottom:6px;">${policy.category}</span>` : ''}
            ${policy.summary ? `<div style="font-size:13px;color:#5f6368;line-height:1.6;">${policy.summary.substring(0, 80)}...</div>` : ''}
          </div>
          <span style="font-size:18px;margin-left:8px;cursor:pointer;" class="fav-btn">${isFav ? '⭐' : '☆'}</span>
        </div>
        ${policy.date ? `<div style="font-size:12px;color:#9aa0a6;margin-top:8px;">${policy.date}</div>` : ''}
      </div>
    `;
  }

  /**
   * 批量渲染政策列表
   */
  renderPolicyList(policies, options = {}) {
    if (!policies || policies.length === 0) {
      return '<div style="text-align:center;padding:40px;color:#9aa0a6;">暂无相关政策</div>';
    }
    return policies.map(p => this.renderPolicyCard(p, options)).join('');
  }

  // 缓存管理
  _getCache(key) {
    const entry = this.cache.get(key);
    if (entry && Date.now() - entry.time < this.cacheTTL) return entry.data;
    this.cache.delete(key);
    return null;
  }

  _setCache(key, data) {
    this.cache.set(key, { data, time: Date.now() });
    if (this.cache.size > 50) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
  }

  clearCache() { this.cache.clear(); }
}

if (typeof window !== 'undefined') window.GovPolicyOperator = GovPolicyOperator;

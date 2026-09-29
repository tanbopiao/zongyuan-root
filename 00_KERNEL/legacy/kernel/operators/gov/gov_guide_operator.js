/**
 * 政务办事指南算子 - GOV-OP-009
 * 封装办事指南查询、详情、流程、预约核心逻辑
 * 依赖: gov_api_operator
 * 功能: 列表、分类、详情、流程步骤、材料清单、预约
 */
class GovGuideOperator {
  constructor(options = {}) {
    this.api = options.api;
    this.cache = new Map();
    this.cacheTTL = 10 * 60 * 1000; // 10分钟缓存
  }

  /**
   * 获取办事指南列表
   */
  async getList(options = {}) {
    const cacheKey = 'list:' + JSON.stringify(options);
    const cached = this._getCache(cacheKey);
    if (cached) return cached;

    const params = new URLSearchParams();
    if (options.category) params.append('category', options.category);
    if (options.page) params.append('page', options.page);
    if (options.limit) params.append('limit', options.limit);
    if (options.keyword) params.append('q', options.keyword);

    const result = await this.api.get('/api/gov/guide/list?' + params.toString());
    if (result.error) return { error: result.error, success: false };

    const guides = result.guides || result.data || result.results || [];
    this._setCache(cacheKey, { guides, success: true });
    return { guides, success: true, total: result.total || guides.length };
  }

  /**
   * 获取办事指南详情
   */
  async getDetail(guideId) {
    const cacheKey = 'detail:' + guideId;
    const cached = this._getCache(cacheKey);
    if (cached) return cached;

    const result = await this.api.get('/api/gov/guide/detail?id=' + guideId);
    if (result.error) return { error: result.error, success: false };

    this._setCache(cacheKey, { guide: result, success: true });
    return { guide: result, success: true };
  }

  /**
   * 获取分类列表
   */
  async getCategories() {
    const cached = this._getCache('categories');
    if (cached) return cached;

    const result = await this.api.get('/api/gov/guide/categories');
    if (result.error) {
      // fallback: 内置分类
      return { categories: this._getFallbackCategories(), success: true, fallback: true };
    }

    const categories = result.categories || result.data || this._getFallbackCategories();
    this._setCache('categories', { categories, success: true });
    return { categories, success: true };
  }

  _getFallbackCategories() {
    return [
      { id: 'social', name: '社会保障', icon: '🛡️', count: 0 },
      { id: 'business', name: '企业服务', icon: '🏢', count: 0 },
      { id: 'household', name: '户籍人口', icon: '👥', count: 0 },
      { id: 'housing', name: '住房保障', icon: '🏠', count: 0 },
      { id: 'education', name: '教育培训', icon: '📚', count: 0 },
      { id: 'medical', name: '医疗卫生', icon: '🏥', count: 0 },
      { id: 'employment', name: '就业创业', icon: '💼', count: 0 },
      { id: 'tax', name: '税务服务', icon: '💰', count: 0 },
      { id: 'legal', name: '法律服务', icon: '⚖️', count: 0 },
      { id: 'other', name: '其他事项', icon: '📋', count: 0 }
    ];
  }

  /**
   * 渲染办事指南卡片
   */
  renderGuideCard(guide) {
    return `
      <div class="guide-card" data-id="${guide.id || guide.guide_id}" style="padding:16px;border:1px solid #e0e0e0;border-radius:12px;margin-bottom:12px;cursor:pointer;background:#fff;">
        <div style="display:flex;align-items:start;gap:12px;">
          <div style="font-size:28px;">${guide.icon || '📋'}</div>
          <div style="flex:1;">
            <div style="font-size:15px;font-weight:600;color:#202124;margin-bottom:4px;">${guide.title || guide.name || '办事指南'}</div>
            ${guide.category ? `<span style="display:inline-block;padding:2px 8px;background:#e6f4ea;color:#137333;border-radius:4px;font-size:12px;margin-bottom:6px;">${guide.category}</span>` : ''}
            ${guide.desc ? `<div style="font-size:13px;color:#5f6368;line-height:1.6;">${guide.desc.substring(0, 60)}...</div>` : ''}
            <div style="display:flex;gap:12px;margin-top:8px;font-size:12px;color:#9aa0a6;">
              ${guide.time_limit ? `<span>⏱️ ${guide.time_limit}</span>` : ''}
              ${guide.cost ? `<span>💰 ${guide.cost}</span>` : ''}
              ${guide.online ? `<span style="color:#137333;">✅ 可在线办理</span>` : ''}
            </div>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * 渲染办事流程步骤
   */
  renderSteps(steps) {
    if (!steps || steps.length === 0) return '<div style="color:#9aa0a6;">暂无流程信息</div>';
    return `
      <div style="position:relative;padding-left:24px;">
        ${steps.map((step, i) => `
          <div style="position:relative;padding-bottom:20px;">
            <div style="position:absolute;left:-24px;top:0;width:20px;height:20px;border-radius:50%;background:#1a73e8;color:#fff;font-size:12px;display:flex;align-items:center;justify-content:center;">${i + 1}</div>
            ${i < steps.length - 1 ? '<div style="position:absolute;left:-15px;top:20px;width:2px;height:calc(100% - 10px);background:#e0e0e0;"></div>' : ''}
            <div style="font-size:14px;font-weight:600;color:#202124;margin-bottom:4px;">${step.title || step.name || '步骤' + (i + 1)}</div>
            ${step.desc ? `<div style="font-size:13px;color:#5f6368;line-height:1.6;">${step.desc}</div>` : ''}
          </div>
        `).join('')}
      </div>
    `;
  }

  /**
   * 渲染材料清单
   */
  renderMaterials(materials) {
    if (!materials || materials.length === 0) return '<div style="color:#9aa0a6;">暂无材料要求</div>';
    return `
      <div style="background:#f8f9fa;border-radius:8px;padding:12px;">
        <div style="font-size:14px;font-weight:600;margin-bottom:8px;color:#202124;">📎 所需材料</div>
        ${materials.map((m, i) => `
          <div style="display:flex;align-items:center;gap:8px;padding:6px 0;font-size:13px;color:#5f6368;">
            <input type="checkbox" id="mat_${i}" style="accent-color:#1a73e8;">
            <label for="mat_${i}">${m.name || m}${m.required ? ' <span style="color:#d93025;">*</span>' : ''}</label>
          </div>
        `).join('')}
      </div>
    `;
  }

  /**
   * 搜索办事指南
   */
  async search(keyword, options = {}) {
    return this.getList({ ...options, keyword });
  }

  /**
   * 预约办事（模拟）
   */
  async book(guideId, date, time) {
    // 实际项目中调用预约API
    return {
      success: true,
      bookingId: 'BK' + Date.now(),
      guideId,
      date,
      time,
      message: '预约成功，请按时前往办理'
    };
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

if (typeof window !== 'undefined') window.GovGuideOperator = GovGuideOperator;

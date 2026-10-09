/**
 * 政务公文生成算子 - GOV-OP-008
 * 封装公文生成、润色、模板、草稿核心逻辑
 * 依赖: gov_api_operator, gov_user_operator
 * 功能: 生成、润色、模板选择、草稿管理、导出
 */
class GovDocOperator {
  constructor(options = {}) {
    this.api = options.api;
    this.user = options.user;
    this.templates = this._getTemplates();
  }

  /**
   * 内置公文模板
   */
  _getTemplates() {
    return [
      { id: 'notice', name: '通知', icon: '📢', desc: '发布事项、传达要求' },
      { id: 'report', name: '报告', icon: '📊', desc: '汇报工作、反映情况' },
      { id: 'request', name: '请示', icon: '🙏', desc: '向上级请求指示批准' },
      { id: 'reply', name: '批复', icon: '✅', desc: '答复下级请示事项' },
      { id: 'summary', name: '总结', icon: '📝', desc: '回顾工作、总结经验' },
      { id: 'plan', name: '计划', icon: '📋', desc: '安排工作、制定目标' },
      { id: 'letter', name: '函', icon: '✉️', desc: '不相隶属机关间商洽' },
      { id: 'meeting', name: '会议纪要', icon: '🗓️', desc: '记录会议要点决议' }
    ];
  }

  getTemplates() {
    return [...this.templates];
  }

  /**
   * 生成公文
   */
  async generate(templateId, title, content, options = {}) {
    const template = this.templates.find(t => t.id === templateId);
    if (!template) {
      return { error: '未知模板类型: ' + templateId, success: false };
    }

    const result = await this.api.post('/api/gov/doc/generate', {
      template: templateId,
      template_name: template.name,
      title,
      content,
      options: {
        tone: options.tone || 'formal',
        length: options.length || 'medium',
        department: options.department,
        date: options.date
      }
    });

    if (result.error) return { error: result.error, success: false };

    const doc = {
      template: templateId,
      template_name: template.name,
      title: result.title || title,
      content: result.content || result.generated || result,
      generated_at: new Date().toISOString()
    };

    // 自动保存草稿
    if (this.user) {
      this.user.saveDraft(doc.title, doc.content);
    }

    return { doc, success: true };
  }

  /**
   * 润色公文
   */
  async polish(content, options = {}) {
    const result = await this.api.post('/api/gov/doc/polish', {
      content,
      options: {
        style: options.style || 'official',
        level: options.level || 'standard',
        preserve_structure: options.preserveStructure !== false
      }
    });

    if (result.error) return { error: result.error, success: false };

    return {
      original: content,
      polished: result.polished || result.content || result,
      changes: result.changes || [],
      success: true
    };
  }

  /**
   * 获取草稿列表
   */
  getDrafts() {
    if (!this.user) return [];
    return this.user.getDrafts();
  }

  /**
   * 保存草稿
   */
  saveDraft(title, content) {
    if (!this.user) return false;
    return this.user.saveDraft(title, content);
  }

  /**
   * 删除草稿
   */
  deleteDraft(index) {
    if (!this.user) return false;
    this.user.deleteDraft(index);
    return true;
  }

  /**
   * 导出公文
   */
  exportDoc(doc, format = 'txt') {
    const content = `【${doc.template_name || '公文'}】\n\n${doc.title || ''}\n\n${doc.content || ''}\n\n---\n生成时间: ${new Date().toLocaleString()}\nΩ₀⊂⊙∞⊂Ω DID-BR-000002`;

    if (format === 'txt') {
      this._download(content, doc.title || '公文', 'text/plain', '.txt');
    } else if (format === 'html') {
      const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${doc.title}</title>
        <style>body{font-family:"SimSun",serif;max-width:800px;margin:40px auto;padding:0 20px;line-height:1.8;}
        h1{text-align:center;font-size:22px;}p{text-indent:2em;margin:12px 0;}</style></head>
        <body><h1>${doc.title}</h1><div>${(doc.content || '').replace(/\n/g, '<br>')}</div></body></html>`;
      this._download(html, doc.title || '公文', 'text/html', '.html');
    }
    return true;
  }

  /**
   * 复制到剪贴板
   */
  async copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (e) {
      // fallback
      const textarea = document.createElement('textarea');
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      return true;
    }
  }

  /**
   * 渲染模板选择器
   */
  renderTemplateSelector(onSelect) {
    const html = `
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;">
        ${this.templates.map(t => `
          <div class="doc-template" data-id="${t.id}" style="padding:16px;border:1px solid #e0e0e0;border-radius:12px;cursor:pointer;text-align:center;transition:all 0.2s;" onmouseover="this.style.borderColor='#1a73e8'" onmouseout="this.style.borderColor='#e0e0e0'">
            <div style="font-size:28px;margin-bottom:8px;">${t.icon}</div>
            <div style="font-size:14px;font-weight:600;color:#202124;">${t.name}</div>
            <div style="font-size:11px;color:#9aa0a6;margin-top:4px;">${t.desc}</div>
          </div>
        `).join('')}
      </div>
    `;
    return html;
  }

  /**
   * 字数统计
   */
  countWords(text) {
    const chinese = (text.match(/[\u4e00-\u9fa5]/g) || []).length;
    const english = (text.match(/[a-zA-Z]+/g) || []).length;
    const total = text.length;
    return { chinese, english, total, estimatedReadTime: Math.ceil(total / 300) };
  }

  _download(content, filename, mimeType, extension) {
    const blob = new Blob([content], { type: mimeType + ';charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename + extension;
    a.click();
    URL.revokeObjectURL(url);
  }
}

if (typeof window !== 'undefined') window.GovDocOperator = GovDocOperator;

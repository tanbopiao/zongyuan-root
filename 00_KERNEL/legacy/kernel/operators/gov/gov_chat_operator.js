/**
 * 政务智能问答算子 - GOV-OP-006
 * 封装政务AI问答核心逻辑
 * 依赖: gov_api_operator
 * 功能: 对话管理、历史记录、快捷提问、流式输出
 */
class GovChatOperator {
  constructor(options = {}) {
    this.api = options.api; // GovAPIOperator实例
    this.user = options.user; // GovUserOperator实例
    this.maxHistory = options.maxHistory || 20;
    this.conversation = [];
    this.isLoading = false;
  }

  /**
   * 发送消息并获取回复
   */
  async send(message, options = {}) {
    if (this.isLoading) {
      return { error: '正在处理中，请稍候', success: false };
    }
    this.isLoading = true;

    try {
      // 记录用户消息
      this.conversation.push({ role: 'user', content: message, time: new Date().toISOString() });

      // 调用API
      const result = await this.api.post('/api/gov/chat', {
        message,
        history: options.includeHistory ? this.conversation.slice(-this.maxHistory) : undefined,
        context: options.context
      });

      if (result.error) {
        this.conversation.push({ role: 'assistant', content: '抱歉，服务暂时不可用，请稍后重试。', error: true });
        return { error: result.error, success: false };
      }

      // 记录助手回复
      const reply = result.reply || result.answer || result.response || JSON.stringify(result);
      this.conversation.push({ role: 'assistant', content: reply, time: new Date().toISOString() });

      // 保存到用户历史
      if (this.user) {
        this.user.addHistory({ role: 'user', content: message });
      }

      this.isLoading = false;
      return { reply, success: true, raw: result };
    } catch (error) {
      this.isLoading = false;
      this.conversation.push({ role: 'assistant', content: '发生错误：' + error.message, error: true });
      return { error: error.message, success: false };
    }
  }

  /**
   * 获取当前对话历史
   */
  getConversation() {
    return [...this.conversation];
  }

  /**
   * 清空当前对话
   */
  clearConversation() {
    this.conversation = [];
  }

  /**
   * 获取快捷提问建议
   */
  getQuickQuestions(category = 'general') {
    const questions = {
      general: [
        '社保怎么交？',
        '营业执照怎么办？',
        '公积金提取流程',
        '居住证办理指南',
        '医保报销比例'
      ],
      policy: [
        '最新社保政策',
        '小微企业扶持政策',
        '人才引进政策',
        '税收优惠政策'
      ],
      business: [
        '公司注册流程',
        '资质办理要求',
        '年报怎么报',
        '变更登记流程'
      ]
    };
    return questions[category] || questions.general;
  }

  /**
   * 格式化回复（简单的markdown转HTML）
   */
  formatReply(text) {
    if (!text) return '';
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>')
      .replace(/^\d+\.\s/gm, (m) => '<br>' + m);
  }

  /**
   * 获取对话统计
   */
  getStats() {
    const userMsgs = this.conversation.filter(m => m.role === 'user').length;
    const assistantMsgs = this.conversation.filter(m => m.role === 'assistant').length;
    const errors = this.conversation.filter(m => m.error).length;
    return {
      totalMessages: this.conversation.length,
      userMessages: userMsgs,
      assistantMessages: assistantMsgs,
      errors,
      isLoading: this.isLoading
    };
  }
}

if (typeof window !== 'undefined') window.GovChatOperator = GovChatOperator;

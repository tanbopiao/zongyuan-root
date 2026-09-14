/**
 * 政务中台算子库 - 统一入口
 * 版本: 3.2.0
 * 包含: 5个基础设施算子 + 4个核心功能算子 + 3个合规治理算子 + 2个业务闭环算子 + 3个运营完善算子 = 17个算子
 * P3全部8个算子开发完成
 *
 * 用法:
 *   const ops = GovOperators.init({ apiBase: '/gov-api' });
 *   const reply = await ops.chat.send('社保怎么交');
 *   const policies = await ops.policy.search('社保');
 *   const verify = await ops.verification.verify({ai_text: '...', policy_reference: [...]});
 *   const comply = ops.compliance.review({content: '...'});
 *   const wo = ops.review.createWorkOrder({content: '...', risk_info: {...}});
 */
const GovOperators = {
  version: '3.2.0',
  // 基础设施算子 (5)
  API: typeof GovAPIOperator !== 'undefined' ? GovAPIOperator : null,
  User: typeof GovUserOperator !== 'undefined' ? GovUserOperator : null,
  Modal: typeof GovModalOperator !== 'undefined' ? GovModalOperator : null,
  Loading: typeof GovLoadingOperator !== 'undefined' ? GovLoadingOperator : null,
  Audit: typeof GovAuditOperator !== 'undefined' ? GovAuditOperator : null,
  // 核心功能算子 (4)
  Chat: typeof GovChatOperator !== 'undefined' ? GovChatOperator : null,
  Policy: typeof GovPolicyOperator !== 'undefined' ? GovPolicyOperator : null,
  Doc: typeof GovDocOperator !== 'undefined' ? GovDocOperator : null,
  Guide: typeof GovGuideOperator !== 'undefined' ? GovGuideOperator : null,
  // 合规治理算子 (3) - P3第一批
  Verification: typeof GovVerification !== 'undefined' ? GovVerification : null,
  Compliance: typeof GovCompliance !== 'undefined' ? GovCompliance : null,
  Review: typeof GovReview !== 'undefined' ? GovReview : null,
  // 业务闭环算子 (2) - P3第二批
  PolicyLifecycle: typeof GovPolicyLifecycle !== 'undefined' ? GovPolicyLifecycle : null,
  SessionTimeout: typeof GovSessionTimeout !== 'undefined' ? GovSessionTimeout : null,
  // 运营完善算子 (3) - P3第三批
  Export: typeof GovExport !== 'undefined' ? GovExport : null,
  Notification: typeof GovNotification !== 'undefined' ? GovNotification : null,
  Analytics: typeof GovAnalytics !== 'undefined' ? GovAnalytics : null,

  /**
   * 一键初始化所有算子
   */
  init(options = {}) {
    const api = new this.API(options.apiBase || '/gov-api', options.api);
    const user = new this.User(options.user);
    return {
      // 基础设施
      api,
      user,
      modal: new this.Modal(options.modal),
      loading: new this.Loading(options.loading),
      audit: new this.Audit(options.audit),
      // 核心功能
      chat: new this.Chat({ api, user }),
      policy: new this.Policy({ api, user }),
      doc: new this.Doc({ api, user }),
      guide: new this.Guide({ api }),
      // 合规治理（单例模式，无需new）
      verification: this.Verification,
      compliance: this.Compliance,
      review: this.Review,
      // 业务闭环（单例模式）
      policyLifecycle: this.PolicyLifecycle,
      sessionTimeout: this.SessionTimeout,
      // 运营完善（单例模式）
      export: this.Export,
      notification: this.Notification,
      analytics: this.Analytics
    };
  },

  /**
   * 获取算子库信息
   */
  getInfo() {
    return {
      version: this.version,
      infrastructure: ['API', 'User', 'Modal', 'Loading', 'Audit'],
      core: ['Chat', 'Policy', 'Doc', 'Guide'],
      governance: ['Verification', 'Compliance', 'Review'],
      business: ['PolicyLifecycle', 'SessionTimeout'],
      operations: ['Export', 'Notification', 'Analytics'],
      total: 17,
      new_in_v3_2: ['Export(批量导出)', 'Notification(消息通知)', 'Analytics(运营统计)'],
      p3_complete: true,
      description: '政务中台算子库V3.2，5基础设施+4核心功能+3合规治理+2业务闭环+3运营完善=17算子，P3全部8个算子开发完成，阴阳具足全域闭环'
    };
  }
};
if (typeof window !== 'undefined') {
  window.GovOperators = GovOperators;
}

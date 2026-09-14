Page({
  data: {},
  login() { wx.showToast({title:'登录功能开发中', icon:'none'}); },
  goFavorites() { wx.showToast({title:'我的收藏', icon:'none'}); },
  goAppointments() { wx.showToast({title:'我的预约', icon:'none'}); },
  goHistory() { wx.showToast({title:'浏览历史', icon:'none'}); },
  goFeedback() { wx.showToast({title:'意见反馈', icon:'none'}); },
  goSetting() { wx.showToast({title:'通用设置', icon:'none'}); },
  goAbout() { wx.showModal({title:'关于我们', content:'政务AI助手 v1.0.0\n基于大语言模型的智能政务服务平台\nΩ₀⊂⊙∞⊂Ω | DID-BR-000002', showCancel:false}); },
  clearCache() {
    wx.showModal({title:'确认清除', content:'确定要清除缓存吗？', success: (res) => {
      if (res.confirm) { wx.showToast({title:'缓存已清除', icon:'success'}); }
    }});
  }
});

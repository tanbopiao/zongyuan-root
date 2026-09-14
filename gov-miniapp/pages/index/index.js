const api = require('../../utils/api.js');
Page({
  data: {
    hotPolicies: [],
    hotGuides: []
  },
  onLoad() {
    this.loadHotData();
  },
  async loadHotData() {
    try {
      const policies = await api.searchPolicy('社保');
      this.setData({
        hotPolicies: (policies.policies || policies.results || []).slice(0, 3).map(p => ({
          id: p.id || p._id,
          title: p.title,
          category: p.category || '政策',
          date: p.date || p.publish_date || '2024-01-01'
        }))
      });
    } catch(e) {
      this.setData({
        hotPolicies: [
          {id:1, title:'4050社保补贴政策', category:'社保', date:'2024-01-15'},
          {id:2, title:'灵活就业人员参保指南', category:'社保', date:'2024-02-01'},
          {id:3, title:'医保异地就医备案', category:'医保', date:'2024-03-10'}
        ]
      });
    }
    this.setData({
      hotGuides: [
        {id:1, title:'身份证办理'},
        {id:2, title:'营业执照注册'},
        {id:3, title:'社保参保登记'},
        {id:4, title:'居住证办理'}
      ]
    });
  },
  goChat() { wx.showToast({title:'智能问答', icon:'none'}); },
  goPolicy() { wx.switchTab({url:'/pages/policy/policy'}); },
  goGuide() { wx.switchTab({url:'/pages/guide/guide'}); },
  goDoc() { wx.navigateTo({url:'/pages/doc/doc'}); },
  viewPolicy(e) { wx.showToast({title:'查看政策', icon:'none'}); },
  viewGuide(e) { wx.showToast({title:'查看指南', icon:'none'}); }
});

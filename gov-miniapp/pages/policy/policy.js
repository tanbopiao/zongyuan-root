const api = require('../../utils/api.js');
Page({
  data: {
    keyword: '',
    categories: ['全部', '社保', '医保', '户籍', '教育', '就业', '住房', '税务', '婚姻', '生育'],
    currentCategory: '全部',
    policies: []
  },
  onLoad() { this.loadPolicies(); },
  onInput(e) { this.setData({keyword: e.detail.value}); },
  onSearch() { this.loadPolicies(); },
  selectCategory(e) {
    this.setData({currentCategory: e.currentTarget.dataset.cat});
    this.loadPolicies();
  },
  async loadPolicies() {
    try {
      const kw = this.data.keyword || this.data.currentCategory;
      const result = await api.searchPolicy(kw);
      const list = (result.policies || result.results || []).slice(0, 20);
      this.setData({policies: list});
    } catch(e) {
      this.setData({
        policies: [
          {id:1, title:'4050社保补贴政策', summary:'就业困难人员灵活就业社保补贴', category:'社保', date:'2024-01-15'},
          {id:2, title:'城乡居民基本医疗保险', summary:'居民医保参保缴费指南', category:'医保', date:'2024-02-01'},
          {id:3, title:'居住证办理新规', summary:'流动人口居住证办理条件', category:'户籍', date:'2024-03-10'}
        ]
      });
    }
  },
  viewDetail(e) {
    wx.showToast({title:'查看政策详情', icon:'none'});
  }
});

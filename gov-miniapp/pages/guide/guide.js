const api = require('../../utils/api.js');
Page({
  data: {
    tabs: ['全部', '证件办理', '社保医保', '工商税务', '婚姻生育', '户籍人口'],
    currentTab: 0,
    guides: []
  },
  onLoad() { this.loadGuides(); },
  switchTab(e) {
    this.setData({currentTab: e.currentTarget.dataset.index});
    this.loadGuides();
  },
  async loadGuides() {
    try {
      const result = await api.getGuideList();
      const list = (result.guides || result.results || []).slice(0, 15);
      this.setData({guides: list});
    } catch(e) {
      this.setData({
        guides: [
          {id:1, title:'身份证办理', category:'证件办理', conditions:'年满16周岁公民', location:'户籍地派出所', phone:'12345'},
          {id:2, title:'营业执照注册', category:'工商税务', conditions:'具备完全民事行为能力', location:'政务服务中心', phone:'12315'},
          {id:3, title:'社保参保登记', category:'社保医保', conditions:'本市户籍或居住证', location:'社保经办机构', phone:'12333'}
        ]
      });
    }
  },
  viewDetail(e) { wx.showToast({title:'查看办事详情', icon:'none'}); },
  bookAppointment(e) { wx.showToast({title:'预约功能开发中', icon:'none'}); }
});

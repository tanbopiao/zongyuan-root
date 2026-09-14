Page({
  data: {
    docTypes: ['通知', '报告', '请示', '函', '纪要', '决定', '意见', '通报'],
    typeIndex: 0,
    title: '',
    content: '',
    result: '',
    loading: false,
    history: []
  },
  onTypeChange(e) { this.setData({typeIndex: e.detail.value}); },
  onTitleInput(e) { this.setData({title: e.detail.value}); },
  onContentInput(e) { this.setData({content: e.detail.value}); },
  async generateDoc() {
    if (!this.data.title) { wx.showToast({title:'请输入标题', icon:'none'}); return; }
    this.setData({loading: true, result: ''});
    setTimeout(() => {
      const type = this.data.docTypes[this.data.typeIndex];
      const result = ;
      this.setData({loading: false, result});
      wx.showToast({title:'生成成功', icon:'success'});
    }, 1500);
  },
  copyResult() {
    wx.setClipboardData({data: this.data.result, success: () => wx.showToast({title:'已复制', icon:'success'})});
  },
  saveResult() {
    const history = [{title: this.data.title, type: this.data.docTypes[this.data.typeIndex], time: new Date().toLocaleString()}, ...this.data.history].slice(0, 10);
    this.setData({history});
    wx.showToast({title:'已保存', icon:'success'});
  }
});

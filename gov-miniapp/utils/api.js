const API_BASE = 'https://huodouai.com/gov-api/api/gov/';
function request(url, method = 'GET', data = {}) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: API_BASE + url,
      method,
      data,
      header: {'Content-Type': 'application/json'},
      success: res => resolve(res.data),
      fail: reject
    });
  });
}
module.exports = {
  searchPolicy: keyword => request('policy/search?keyword=' + encodeURIComponent(keyword)),
  getGuideList: () => request('guide/list'),
  getHealth: () => request('health')
};

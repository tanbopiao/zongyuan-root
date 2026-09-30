/* ============================================================================
 * ZONGYUAN-ROOT 真值根握手模块 v1.0
 * DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 昆仑洞天自治体系
 *
 * 功能：
 *  1. 全握手 rootHandshake()  —— 客户端与根API握手，获取内核真值快照
 *  2. 轻握手 lightHandshake() —— 收到变更事件后校验根哈希，增量对齐
 *  3. 多窗口广播 BroadcastChannel + storage 兜底（同源多标签实时同步）
 *  4. 版本锁冲突处理         —— 本地摘要比对，真值变更自动广播通知
 *  5. 自动保活               —— 每60秒轻握手一次，变更即广播
 *
 * 设计原则：
 *  - 窗口之间只传递"变更通知"，不传递完整真值；
 *  - 完整真值一律从根API读取，根是唯一权威信源；
 *  - 断线自动重连，重连后自动全握手补齐。
 * ==========================================================================*/
(function () {
  'use strict';

  var ROOT = {
    apiBase: '/admin/api',        // nginx 代理到 8100 产线内核
    did: 'DID-BR-000002',
    kernel: 'ZONGYUAN-ROOT',
    node: '',
    truthVersion: 0,
    merkleRoot: '',
    localDigest: '',
    lastDigest: '',
    lastSync: 0
  };

  /* ---------- 轻量哈希（djb2）· 本地快照摘要 ---------- */
  function hashStr(s) {
    var h = 5381;
    for (var i = 0; i < s.length; i++) {
      h = ((h << 5) + h + s.charCodeAt(i)) >>> 0;
    }
    return h.toString(16).padStart(8, '0');
  }

  /* ---------- 计算本地真值摘要（works + tasks 状态） ---------- */
  function computeLocalDigest() {
    return Promise.all([
      fetch(ROOT.apiBase + '/works').then(function (r) { return r.json(); }).catch(function () { return null; }),
      fetch(ROOT.apiBase + '/task/list').then(function (r) { return r.json(); }).catch(function () { return null; })
    ]).then(function (res) {
      var w = res[0] ? JSON.stringify(res[0].stats || res[0]) : 'null';
      var t = res[1] ? JSON.stringify(res[1].count || res[1]) : 'null';
      return hashStr(w + t);
    }).catch(function () {
      return hashStr('local');
    });
  }

  /* ---------- 全握手 ---------- */
  function rootHandshake() {
    return fetch(ROOT.apiBase + '/system/status')
      .then(function (r) { return r.json(); })
      .then(function (sys) {
        return computeLocalDigest().then(function (digest) {
          ROOT.kernel = sys.kernel || ROOT.kernel;
          ROOT.node = sys.node || 'ZR-ROOT';
          ROOT.truthVersion = (sys.timestamp ? Date.parse(sys.timestamp) : Date.now());
          ROOT.merkleRoot = hashStr(ROOT.kernel + ':' + ROOT.node + ':' + ROOT.truthVersion);
          ROOT.localDigest = digest;
          ROOT.lastSync = Date.now();
          console.log('[ROOT-HS] 全握手成功 | 内核:', ROOT.kernel, '| 节点:', ROOT.node, '| 摘要:', digest);
          return true;
        });
      })
      .catch(function (e) {
        console.warn('[ROOT-HS] 全握手失败，降级本地模式', e);
        return false;
      });
  }

  /* ---------- 轻握手：比对根哈希 + 本地摘要，变化即广播 ---------- */
  function lightHandshake() {
    return rootHandshake().then(function (ok) {
      if (!ok) return false;
      // 本地真值变化检测：上一轮摘要 != 当前摘要 → 广播变更通知
      if (ROOT.lastDigest !== '' && ROOT.lastDigest !== ROOT.localDigest) {
        broadcast('truth-changed', { merkle: ROOT.merkleRoot, from: ROOT.localDigest, to: ROOT.lastDigest });
      }
      ROOT.lastDigest = ROOT.localDigest;
      return true;
    });
  }

  /* ---------- 多窗口广播通道 ---------- */
  var bc = null;
  try { bc = new BroadcastChannel('zongyuan-root'); } catch (e) { bc = null; }

  function broadcast(type, payload) {
    var msg = { type: type, payload: payload, ts: Date.now(), did: ROOT.did };
    if (bc) { try { bc.postMessage(msg); } catch (e) {} }
    // storage 事件兜底（BroadcastChannel 失效时）
    try { localStorage.setItem('zr-sync', JSON.stringify(msg)); } catch (e) {}
  }

  if (bc) {
    bc.onmessage = function (ev) {
      var d = ev.data;
      if (d && d.did === ROOT.did && d.type === 'truth-changed') {
        console.log('[ROOT-HS] 收到其他窗口真值变更通知，轻握手对齐');
        lightHandshake();
      }
    };
  }

  // storage 兜底监听（同源其他标签页写入时触发）
  window.addEventListener('storage', function (ev) {
    if (ev.key === 'zr-sync') {
      lightHandshake();
    }
  });

  /* ---------- 对外接口 ---------- */
  window.RootTruth = {
    handshake: rootHandshake,
    light: lightHandshake,
    notifyChange: function () { broadcast('truth-changed', { merkle: ROOT.merkleRoot }); },
    status: function () {
      return {
        did: ROOT.did,
        kernel: ROOT.kernel,
        node: ROOT.node,
        merkle: ROOT.merkleRoot,
        digest: ROOT.localDigest,
        lastSync: ROOT.lastSync
      };
    }
  };

  /* ---------- 启动自动握手 + 60秒保活 ---------- */
  rootHandshake();
  setInterval(lightHandshake, 60000);
})();

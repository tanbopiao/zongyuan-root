/* 火斗云智AIOS · ZR Console — 零依赖原生 JS
 * API 契约 Base: /api/v1  端口 8920
 */
(function(){
  'use strict';

  // ---------- 配置 ----------
  var LS_BASE = 'zr_api_base';
  var LS_KEY  = 'zr_api_key';

  var $ = function(id){ return document.getElementById(id); };
  var apiBaseEl = $('apiBase');
  var apiKeyEl  = $('apiKey');

  function getBase(){
    // 默认空串 = 同源相对路径（页面由后端 / 提供，直接打 /api/v1，免 CORS）。
    // 用户可在右上角覆盖为 http://other-host:8920。
    var v = (apiBaseEl.value || '').trim().replace(/\/+$/,'');
    return v;
  }
  function getKey(){ return (apiKeyEl.value || '').trim(); }

  apiBaseEl.value = localStorage.getItem(LS_BASE) || '';
  apiKeyEl .value  = localStorage.getItem(LS_KEY)  || '';
  apiBaseEl.addEventListener('change', function(){ localStorage.setItem(LS_BASE, getBase()); boot(); });
  apiKeyEl .addEventListener('change', function(){ localStorage.setItem(LS_KEY,  getKey());  });

  // ---------- fetch 封装 ----------
  function api(method, path, body){
    var headers = { 'Accept': 'application/json' };
    var key = getKey();
    if (key) headers['X-API-Key'] = key;
    var opts = { method: method, headers: headers };
    if (body !== undefined && body !== null){
      headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    var url = getBase() + '/api/v1' + path;
    return Promise.race([
      fetch(url, opts).then(function(r){
        return r.text().then(function(txt){
          var data;
          try { data = txt ? JSON.parse(txt) : {}; }
          catch(e){ data = { _raw: txt, _status: r.status }; }
          if (!r.ok){
            var err = new Error('HTTP ' + r.status + ' ' + (data.error || data.detail || r.statusText));
            err.status = r.status; err.data = data;
            throw err;
          }
          return data;
        });
      }),
      new Promise(function(_, reject){
        setTimeout(function(){ reject(new Error('请求超时（>6s）')); }, 6000);
      })
    ]);
  }

  function toast(msg, isErr){
    var t = $('toast');
    t.textContent = msg;
    t.style.borderColor = isErr ? 'var(--err)' : 'var(--gold)';
    t.style.color = isErr ? '#E8B4A8' : 'var(--gold-bright)';
    t.classList.remove('hidden');
    clearTimeout(toast._t);
    toast._t = setTimeout(function(){ t.classList.add('hidden'); }, 2600);
  }

  function showOffline(on){
    $('offline').classList.toggle('hidden', !on);
    document.body.classList.toggle('offline-mode', on);
    if (on){ $('offlineUrl').textContent = getBase() + '/api/v1/health'; }
  }

  // ---------- 视图切换 ----------
  var tabs = document.querySelectorAll('#tabs button');
  tabs.forEach(function(btn){
    btn.addEventListener('click', function(){
      tabs.forEach(function(b){ b.classList.remove('active'); });
      btn.classList.add('active');
      var v = btn.getAttribute('data-view');
      document.querySelectorAll('.view').forEach(function(s){ s.classList.remove('active'); });
      $('view-' + v).classList.add('active');
      loadView(v);
    });
  });
  function loadView(v){
    if (v === 'overview')   loadOverview();
    else if (v === 'truth') loadTruthList();
    else if (v === 'task')  loadTaskList();
    else if (v === 'operators') loadOperators();
    else if (v === 'provenance') loadChain();
    else if (v === 'gateway') loadChannels();
  }

  // ---------- 1. 概览 ----------
  function loadOverview(){
    Promise.all([
      api('GET','/health').catch(function(e){ return { _err: e.message }; }),
      api('GET','/task').catch(function(){ return null; }),
      api('GET','/operators').catch(function(){ return null; })
    ]).then(function(rs){
      var health = rs[0];
      $('ovHealth').textContent = JSON.stringify(health, null, 2);
      if (health && !health._err){
        showOffline(false);
        var up = health.uptime_secs || health.uptime || health.started_at || 0;
        $('ovUptime').textContent = fmtUptime(up);
        // D5b 修复：真值总数直接取 health.truth_count（后端已聚合），不再用 /truth?limit=1 采样
        $('ovTruthCount').textContent = (health.truth_count != null) ? health.truth_count : '--';
      } else {
        showOffline(true);
        $('ovUptime').textContent = '--';
        $('ovTruthCount').textContent = '--';
      }
      // task count
      if (rs[1] && !rs[1]._err){
        var tarr = Array.isArray(rs[1]) ? rs[1] : (rs[1].items || rs[1].tasks || rs[1].data || []);
        $('ovTaskCount').textContent = tarr.length;
      } else { $('ovTaskCount').textContent = '--'; }
      // operators
      if (rs[2] && !rs[2]._err){
        var oarr = Array.isArray(rs[2]) ? rs[2] : (rs[2].items || rs[2].operators || rs[2].data || []);
        $('ovOpCount').textContent = oarr.length || OPERATORS.length;
      } else { $('ovOpCount').textContent = OPERATORS.length; }

      // modules
      var mods = health && health.modules ? health.modules : defaultModules(health);
      // health.modules 形如 {memory:"up", provenance:"up", ...}，转成 [{name,status}]
      if (health && health.modules && !Array.isArray(mods)){
        mods = Object.keys(health.modules).map(function(k){
          var st = health.modules[k];
          return { name: k, status: (st === 'up' || st === 'ok') ? 'ok' : (st === 'down' ? 'err' : 'warn') };
        });
      }
      renderMods(mods);
    });
  }
  function defaultModules(h){
    var up = !(h && h._err);
    return [
      { name: 'truth_store',    status: up ? 'ok' : 'err' },
      { name: 'scheduler',      status: up ? 'ok' : 'err' },
      { name: 'provenance',     status: up ? 'ok' : 'err' },
      { name: 'model_gateway',  status: up ? 'warn' : 'err' },
      { name: 'merkle_dag',     status: up ? 'ok' : 'err' },
      { name: 'efuse_guard',    status: up ? 'ok' : 'err' }
    ];
  }
  function renderMods(mods){
    var box = $('modList'); box.innerHTML = '';
    mods.forEach(function(m){
      var div = document.createElement('div');
      var cls = 'mod ' + (m.status === 'ok' ? 'ok' : m.status === 'warn' ? 'warn' : 'err');
      div.className = cls;
      div.innerHTML = '<div><b></b><span></span></div><div class="dot"></div>';
      div.querySelector('b').textContent = m.name;
      div.querySelector('span').textContent = m.status;
      box.appendChild(div);
    });
  }
  function fmtUptime(s){
    if (typeof s !== 'number' || !isFinite(s)) return '--';
    if (s < 60) return s.toFixed(0) + 's';
    if (s < 3600) return (s/60).toFixed(1) + 'm';
    return (s/3600).toFixed(1) + 'h';
  }

  // ---------- 2. 真值库 ----------
  var TRUTH_TYPES = ['meta_law','rule','config','decision','data','creative','risk','protocol','unknown'];
  function loadTruthList(){
    var type = $('truthType').value;
    var q = ($('truthQ').value || '').trim();
    var limit = $('truthLimit').value || 50;
    var path = '/truth?limit=' + encodeURIComponent(limit);
    if (type) path += '&type=' + encodeURIComponent(type);
    if (q)    path += '&q=' + encodeURIComponent(q);
    api('GET', path).then(function(data){
      var arr = Array.isArray(data) ? data : (data.items || data.truths || data.data || []);
      renderTruthList(arr);
    }).catch(function(e){ toast('真值列表加载失败：' + e.message, true); renderTruthList([]); });
  }
  function renderTruthList(arr){
    var box = $('truthList'); box.innerHTML = '';
    if (!arr.length){ box.innerHTML = '<div class="muted">暂无真值。可在下方表单新增。</div>'; return; }
    arr.forEach(function(t){
      var row = document.createElement('div');
      row.className = 'truth-row';
      row.innerHTML =
        '<div class="tid"></div>' +
        '<div class="ttype"></div>' +
        '<div class="tsource"></div>' +
        '<div><span class="badge">conf </span></div>' +
        '<div><span class="badge">查看</span></div>';
      row.querySelector('.tid').textContent = t.truth_id || t.id || '-';
      row.querySelector('.ttype').textContent = t.truth_type || t.type || '?';
      row.querySelector('.tsource').textContent = t.source || '';
      row.querySelectorAll('.badge')[0].textContent = 'conf ' + (t.confidence != null ? t.confidence : '-');
      row.addEventListener('click', function(){ openTruthDetail(t.truth_id || t.id); });
      box.appendChild(row);
    });
  }
  function openTruthDetail(id){
    api('GET', '/truth/' + encodeURIComponent(id)).then(function(t){
      $('truthDetailCard').classList.remove('hidden');
      $('truthDetail').textContent = JSON.stringify(t, null, 2);
    }).catch(function(e){ toast('详情失败：' + e.message, true); });
  }
  $('truthDetailClose').addEventListener('click', function(){
    $('truthDetailCard').classList.add('hidden');
  });

  $('btnTruthList').addEventListener('click', loadTruthList);
  $('truthForm').addEventListener('submit', function(ev){
    ev.preventDefault();
    var fd = new FormData(ev.target);
    var content;
    try { content = JSON.parse(fd.get('content') || '{}'); }
    catch(e){ toast('content 不是合法 JSON', true); return; }
    var body = {
      truth_type: fd.get('truth_type'),
      source: fd.get('source'),
      confidence: parseFloat(fd.get('confidence') || '0.9'),
      content: content
    };
    api('POST', '/truth', body).then(function(res){
      $('truthFormMsg').textContent = '已提交：' + (res.truth_id || res.id || 'OK');
      toast('真值已写入');
      loadTruthList();
    }).catch(function(e){ toast('提交失败：' + e.message, true); });
  });

  // ---------- 3. 任务调度 ----------
  function loadTaskList(){
    api('GET','/task').then(function(data){
      var arr = Array.isArray(data) ? data : (data.items || data.tasks || data.data || []);
      renderTaskList(arr);
    }).catch(function(e){ toast('任务列表加载失败：' + e.message, true); renderTaskList([]); });
  }
  function renderTaskList(arr){
    var box = $('taskList'); box.innerHTML = '';
    if (!arr.length){ box.innerHTML = '<div class="muted">暂无任务。</div>'; return; }
    arr.forEach(function(t){
      var row = document.createElement('div');
      row.className = 'task-row';
      row.innerHTML =
        '<div class="nm"></div>' +
        '<div class="ttype"></div>' +
        '<div class="sched"></div>' +
        '<div class="st"></div>' +
        '<button class="btn-ghost">run</button>';
      row.querySelector('.nm').textContent = t.name || t.task_id || '-';
      row.querySelector('.ttype').textContent = t.task_type || '';
      row.querySelector('.sched').textContent = (t.schedule||'') + (t.interval_secs ? (' / ' + t.interval_secs + 's') : '');
      var st = row.querySelector('.st');
      st.textContent = t.status || 'idle';
      st.className = 'st ' + (t.status === 'running' ? 'run' : t.status === 'error' ? 'err' : 'idle');
      row.querySelector('button').addEventListener('click', function(){
        manualRun(t.task_id || t.id);
      });
      box.appendChild(row);
    });
  }
  function manualRun(id){
    api('POST', '/agent/run', { task_id: id }).then(function(res){
      toast('已触发 run：' + (res.run_id || res.task_id || 'OK'));
      setTimeout(loadTaskList, 600);
    }).catch(function(e){ toast('run 失败：' + e.message, true); });
  }
  $('btnTaskList').addEventListener('click', loadTaskList);
  $('taskForm').addEventListener('submit', function(ev){
    ev.preventDefault();
    var fd = new FormData(ev.target);
    var params;
    try { params = JSON.parse(fd.get('params') || '{}'); }
    catch(e){ toast('params 不是合法 JSON', true); return; }
    var body = {
      name: fd.get('name'),
      task_type: fd.get('task_type'),
      schedule: fd.get('schedule'),
      interval_secs: parseInt(fd.get('interval_secs') || '0', 10),
      params: params
    };
    api('POST','/task', body).then(function(res){
      $('taskFormMsg').textContent = '已创建：' + (res.task_id || res.id || 'OK');
      toast('任务已创建');
      loadTaskList();
    }).catch(function(e){ toast('创建失败：' + e.message, true); });
  });

  // ---------- 4. 算子拓扑（27 算子十层） ----------
  var OPERATORS = [
    { layer: 1, name: 'P4 真值对账算子', id: 'P4' },
    { layer: 1, name: 'P7 外部锚定算子', id: 'P7' },
    { layer: 1, name: '真值提炼蒸馏算子', id: 'TRUTH-DISTILL' },
    { layer: 2, name: '黎曼流形世界模型度量算子', id: 'RIEM-METRIC' },
    { layer: 2, name: 'SM-BS 双向稳态映射算子', id: 'SM-BS-MAP' },
    { layer: 2, name: '漂移巡检量化算子', id: 'DRIFT-SCAN' },
    { layer: 3, name: '实体关系抽取算子', id: 'KG-EXTRACT' },
    { layer: 3, name: '知识图谱补全算子', id: 'KG-COMPLETE' },
    { layer: 3, name: '跨文档实体链接算子', id: 'KG-LINK' },
    { layer: 4, name: '因果链溯源回溯算子', id: 'CAUSAL-TRACE' },
    { layer: 4, name: '奇点概率预测算子', id: 'SING-PREDICT' },
    { layer: 4, name: '因果干预模拟算子', id: 'CAUSAL-DO' },
    { layer: 5, name: 'CausalToTruth 适配器算子', id: 'C2T' },
    { layer: 5, name: 'TruthToEvolution 适配器算子', id: 'T2E' },
    { layer: 5, name: 'EvolutionToCausal 适配器算子', id: 'E2C' },
    { layer: 6, name: '四层结构化拆分算子', id: 'STRUCT-4L' },
    { layer: 6, name: '九大元类归类算子', id: 'META9-CLASS' },
    { layer: 6, name: 'Merkle-DAG 主链追加校验算子', id: 'MERKLE-APPEND' },
    { layer: 7, name: '飞书资源↔M9 账本双向对账算子', id: 'FS-M9-RECON' },
    { layer: 8, name: 'eFuse 熔断触发算子', id: 'EFUSE-BURN' },
    { layer: 8, name: 'ZKP 零知识隐私校验算子', id: 'ZKP-VERIFY' },
    { layer: 9, name: '方案生成评估算子', id: 'DECIDE-GEN' },
    { layer: 9, name: '风险识别分级算子', id: 'RISK-RANK' },
    { layer: 9, name: '法律意见书生成算子', id: 'LEGAL-MEMO' },
    { layer: 10, name: 'Lv6 多主体文明仿真约束算子', id: 'SIM6-LOCK' },
    { layer: 10, name: '角色元规则隔离校验算子', id: 'ROLE-GUARD' },
    { layer: 10, name: '9:16 电影级国风关键帧一致性算子', id: 'FRAME-916' }
  ];
  var LAYER_NAMES = {
    1: '真值过滤与深度蒸馏',
    2: '流形度量与 SM-BS 稳态映射',
    3: '知识图谱秩序化重建',
    4: '因果级推理',
    5: 'CTE 三位一体适配器流转',
    6: '结构化归档深化',
    7: '资产对账治理',
    8: '安全确权',
    9: '决策与法律护盾',
    10: '业务实体约束'
  };

  function loadOperators(){
    api('GET','/operators').then(function(data){
      var arr = Array.isArray(data) ? data : (data.items || data.operators || data.data || []);
      renderOperators(arr);
    }).catch(function(){
      renderOperators([]); // 用本地拓扑兜底
    });
  }
  function renderOperators(liveOps){
    // 用 liveOps 状态覆盖本地拓扑；若后端未返回，全部 registered
    var liveMap = {};
    liveOps.forEach(function(o){
      var k = o.operator_id || o.id || o.name || o.code;
      liveMap[k] = o;
    });
    $('opCount').textContent = '已注册 ' + OPERATORS.length + ' / 27';
    var box = $('opLayers'); box.innerHTML = '';
    for (var L = 1; L <= 10; L++){
      var layerDiv = document.createElement('div');
      layerDiv.className = 'layer';
      var ops = OPERATORS.filter(function(o){ return o.layer === L; });
      var html = '<div class="layer-head"><b>第 ' + L + ' 层 · ' + LAYER_NAMES[L] + '</b><span>' + ops.length + ' 个算子</span></div><div class="ops">';
      ops.forEach(function(o){
        var live = liveMap[o.id] || liveMap[o.name] || liveMap[o.oid];
        var status = live && live.status ? live.status : 'registered';
        var badgeCls = status === 'active' ? 'active' : 'registered';
        html += '<div class="op"><div><div class="on">' + o.name + '</div><div class="oid">' + o.id + '</div></div><span class="badge ' + badgeCls + '">' + status + '</span></div>';
      });
      html += '</div>';
      layerDiv.innerHTML = html;
      box.appendChild(layerDiv);
    }
  }

  // ---------- 5. 溯源链 ----------
  function loadChain(){
    api('GET','/provenance/chain').then(function(data){
      var root = data.merkle_root || data.root || '-';
      var len  = data.length != null ? data.length : (data.chain ? data.chain.length : '-');
      $('chainRoot').textContent = root;
      $('chainLen').textContent = len;
      $('chainData').textContent = JSON.stringify(data, null, 2);
    }).catch(function(e){
      $('chainRoot').textContent = '--';
      $('chainLen').textContent = '--';
      $('chainData').textContent = '加载失败：' + e.message;
    });
  }
  $('btnChain').addEventListener('click', loadChain);
  $('btnVerify').addEventListener('click', function(){
    $('verifyResult').textContent = '校验中…';
    api('POST','/provenance/verify', {}).then(function(res){
      $('verifyResult').textContent = JSON.stringify(res, null, 2);
      toast(res.ok === false ? '校验未通过' : '校验完成');
    }).catch(function(e){ $('verifyResult').textContent = '校验失败：' + e.message; });
  });

  // ---------- 6. 模型网关 ----------
  function loadChannels(){
    api('GET','/gateway/channels').then(function(data){
      var arr = Array.isArray(data) ? data : (data.channels || data.items || data.data || []);
      renderChannels(arr.length ? arr : defaultChannels());
    }).catch(function(){ renderChannels(defaultChannels()); });
  }
  function defaultChannels(){
    return [
      { channel: 'local',     model: 'ollama',       status: 'unknown', endpoint: '127.0.0.1:11434' },
      { channel: 'licensed',  model: '—',            status: 'unknown', endpoint: 'ZR_LICENSED_BASE_URL' },
      { channel: 'byok',      model: '—',            status: 'unknown', endpoint: 'ZR_BYOK_BASE_URL' }
    ];
  }
  function mask(k){
    if (!k) return '未配置';
    k = String(k);
    if (k.length <= 8) return '****';
    return k.slice(0,4) + '****' + k.slice(-4);
  }
  function renderChannels(arr){
    var box = $('channelCards'); box.innerHTML = '';
    arr.forEach(function(c){
      var div = document.createElement('div');
      div.className = 'ch-card';
      div.innerHTML =
        '<h4>' + c.channel + '</h4>' +
        '<div class="kv"><span>model</span><b></b></div>' +
        '<div class="kv"><span>status</span><b></b></div>' +
        '<div class="kv"><span>endpoint</span><b></b></div>' +
        '<div class="kv"><span>key</span><b></b></div>';
      div.querySelectorAll('b')[0].textContent = c.model || '—';
      div.querySelectorAll('b')[1].textContent = c.status || 'unknown';
      div.querySelectorAll('b')[2].textContent = c.endpoint || c.base_url || '—';
      div.querySelectorAll('b')[3].textContent = mask(c.api_key || c.key);
      box.appendChild(div);
    });
  }
  $('btnChannels').addEventListener('click', loadChannels);

  $('chatForm').addEventListener('submit', function(ev){
    ev.preventDefault();
    var fd = new FormData(ev.target);
    var messages;
    try { messages = JSON.parse(fd.get('messages') || '[]'); }
    catch(e){ toast('messages 不是合法 JSON 数组', true); return; }
    var body = {
      channel: fd.get('channel'),
      model: fd.get('model') || undefined,
      messages: messages
    };
    $('chatResult').textContent = '请求中…';
    $('chatAudit').textContent = '';
    api('POST','/gateway/chat', body).then(function(res){
      $('chatResult').textContent = JSON.stringify(res, null, 2);
      $('chatAudit').textContent = 'audit_id: ' + (res.audit_id || res.request_id || '-');
      $('chatMsg').textContent = 'OK';
    }).catch(function(e){
      $('chatResult').textContent = '失败：' + e.message;
      $('chatMsg').textContent = '';
    });
  });

  // ---------- boot ----------
  $('btnRefresh').addEventListener('click', boot);
  $('btnRetry').addEventListener('click', boot);
  function boot(){
    loadOverview();
  }
  boot();
})();

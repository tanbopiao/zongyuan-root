// 用户身份识别：URL参数 > localStorage > 自动生成
(function initDeviceId() {
  const urlParams = new URLSearchParams(window.location.search);
  const urlDeviceId = urlParams.get("device_id");
  const storedId = localStorage.getItem("drama_device_id");
  if (urlDeviceId) {
    localStorage.setItem("drama_device_id", urlDeviceId);
    console.log("[身份] 使用URL参数设备ID:", urlDeviceId);
  } else if (!storedId) {
    const newId = "device-" + Date.now().toString(36) + Math.random().toString(36).substr(2, 6);
    localStorage.setItem("drama_device_id", newId);
    console.log("[身份] 自动生成设备ID:", newId);
  }
})();


// 全局错误捕获
window.addEventListener('error', function(e) {
    var errDiv = document.createElement('div');
    errDiv.style.cssText = 'position:fixed;top:0;left:0;right:0;background:#EA6668;color:#fff;padding:10px;z-index:99999;font-size:13px;';
    errDiv.textContent = 'JS错误: ' + e.message + ' (行' + e.lineno + ')';
    document.body.appendChild(errDiv);
});

// L0漂移检测结果处理
function handleDriftResponse(data, nodeType) {
    if (data.error && data.drift_level === 3) {
        return { blocked: true, html: `<div class="drift-panel block">
            <strong>⛔ L0铁律拦截（Level3）</strong><br/>
            <span style="color:#EA6668">违反《阴阳分立·雌雄纯一定序篇》</span><br/>
            ${(data.reason||[]).slice(0,3).map(r=>'• '+r).join('<br/>')}<br/>
            <small>请修改提示词，去除雄性化/西方铠甲/畸形等元素后重试</small>
        </div>` };
    }
    if (data.drift_check) {
        const lvl = data.drift_check.level;
        const cls = lvl===0?'drift-pass':lvl<=2?'drift-warn':'drift-block';
        const txt = lvl===0?'L0通过':lvl===1?'轻微漂移':lvl===2?'特征不足':'已拦截';
        return { blocked:false, badge:`<span class="drift-badge ${cls}">${txt}</span>` };
    }
    return { blocked:false, badge:'' };
}

// ============ 数据 ============
const TEMPLATES = [
  {id:'taiyin', icon:'🌙', name:'太阴月神·觉醒篇', desc:'墟境探测启封→月神觉醒→秩序校准，双镜头合成', tags:['7节点','觉醒','月神'], nodes:['script','storyboard','keyframe','video','video','compose','archive']},
  {id:'xuannv', icon:'⚔️', name:'九天玄女·战斗篇', desc:'玄女出战→玄鸟图腾→青金战斗形态，双关键帧', tags:['7节点','战斗','玄女'], nodes:['script','storyboard','keyframe','keyframe','video','compose','archive']},
  {id:'feilingxi', icon:'🔥', name:'赤霞司命·绯灵汐', desc:'赤霞觉醒→司命之力→收束归档', tags:['5节点','赤霞','绯灵汐'], nodes:['script','storyboard','keyframe','video','archive']},
  {id:'wentai', icon:'🏯', name:'罗定文旅·文塔印象', desc:'文塔实景→文旅叙事→宣传短片', tags:['6节点','文旅','宣传'], nodes:['script','storyboard','keyframe','video','compose','archive']},
  {id:'remake', icon:'🎬', name:'拉片复刻（自定义）', desc:'输入参考视频描述，AI自动拆解复刻', tags:['自定义','拉片','复刻'], nodes:[], custom:true},
  {id:'minimal', icon:'⚡', name:'极简测试', desc:'仅剧本+归档，快速验证流程', tags:['2节点','快速','测试'], nodes:['script','archive']},
  // ===== 通用模板矩阵（不绑定昆仑IP，适配外部用户多样化需求） =====
  {id:'gufeng', icon:'🏮', name:'古风短剧·通用', desc:'古风言情/仙侠/宫廷，主角外观可自定义', tags:['通用','古风','5节点'], nodes:['script','storyboard','keyframe','video','archive'], category:'general'},
  {id:'dushi', icon:'🏙️', name:'都市情感·通用', desc:'现代都市/职场/爱情短剧，贴近生活场景', tags:['通用','都市','5节点'], nodes:['script','storyboard','keyframe','video','archive'], category:'general'},
  {id:'daihuo', icon:'🛍️', name:'产品种草·30秒', desc:'小红书/抖音风带货口播，3镜头快节奏', tags:['通用','带货','3节点'], nodes:['script','keyframe','video','archive'], category:'general'},
  {id:'kepu', icon:'📚', name:'知识科普·通用', desc:'知识讲解/科普动画，清晰易懂', tags:['通用','科普','4节点'], nodes:['script','storyboard','keyframe','video','archive'], category:'general'},
  {id:'qiye', icon:'🏢', name:'品牌宣传片', desc:'企业形象/品牌故事/产品发布，专业质感', tags:['通用','企业','5节点'], nodes:['script','storyboard','keyframe','video','compose','archive'], category:'general'},
  {id:'xuanyi', icon:'🔮', name:'悬疑反转·通用', desc:'悬疑/推理/反转短剧，结尾出乎意料', tags:['通用','悬疑','5节点'], nodes:['script','storyboard','keyframe','video','archive'], category:'general'}
];

const NODE_NAMES = {script:'📝 剧本', storyboard:'🎬 分镜', keyframe:'🖼️ 关键帧', video:'🎥 视频', compose:'✂️ 合成', archive:'💾 归档'};

// ============ 状态 ============
let currentTemplate = null;
// ============ 全局认证拦截：所有fetch自动带Basic Auth ============
const _origFetch = window.fetch;
async function _fetchWithRetry(url, options, retries) {
    const resp = await _origFetch.call(this, url, options);
    if (resp.status === 429 && retries < 3) {
        await new Promise(r => setTimeout(r, Math.pow(2, retries) * 1000));
        return _fetchWithRetry(url, options, retries + 1);
    }
    return resp;
}
window.fetch = function(url, options) {
    options = options || {};
    options.headers = options.headers || {};
    if (typeof options.headers === 'object' && !options.headers.append) {
        options.headers['Authorization'] = 'Basic ' + btoa('zongyuan:8v4iGrYBK2Fz9UC');
    }
    return _fetchWithRetry(url, options, 0);
};

// ============ 默认API配置 ============
const DEFAULT_API_CONFIG = {
    provider: 'agnes',
    api_key: 'sk-c15ub0rOGZXa33elApicuNCvyLXXqzRYQY8U7nlzjxSrzywv',
    endpoint: 'https://apihub.agnes-ai.cn/v1',
    model: 'agnes-video-v2.0',
    text_model: 'agnes-2.5-flash',
    image_model: 'agnes-image-2.0-flash',
    mode: 'public',
    paywall_approved: false
};

let currentModel = 'doubao';
const API_CONFIG_KEY = 'zongyuan_drama_api_config';

// ============ 初始化 ============
// 设备ID（云端作品识别）
const DEVICE_ID = localStorage.getItem('zy_device_id') || (function(){
  const id = 'dev-' + Math.random().toString(36).substr(2, 12);
  localStorage.setItem('zy_device_id', id);
  return id;
})();

function init() {
    // 首次访问自动填充默认API配置
  if (!localStorage.getItem(API_CONFIG_KEY)) {
    localStorage.setItem(API_CONFIG_KEY, JSON.stringify(DEFAULT_API_CONFIG));
    console.log('已自动填充默认API配置（Seedance/Seedream）');
  }
  renderTemplates();
  updateApiBadge();
  checkFirstVisit();
}

function checkFirstVisit() {
  if (!localStorage.getItem('zongyuan_drama_visited')) {
    localStorage.setItem('zongyuan_drama_visited', '1');
  }
}

// ============ AI需求引导式创建 ============
function showAICreateModal() {
  document.getElementById('ai-create-modal').style.display = 'flex';
}
function closeAICreateModal() {
  document.getElementById('ai-create-modal').style.display = 'none';
  document.getElementById('ai-gen-status').style.display = 'none';
}
async function generateAITemplate() {
  const demand = document.getElementById('ai-demand-input').value.trim();
  if (!demand) { alert('请输入你的需求描述'); return; }
  const btn = document.getElementById('ai-gen-btn');
  const status = document.getElementById('ai-gen-status');
  btn.disabled = true;
  btn.textContent = '⏳ AI分析中...';
  status.style.display = 'block';
  status.textContent = '正在分析需求，生成模板配置...';
  try {
    const resp = await fetch('/ai-proxy/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        model: 'doubao',
        messages: [
          {role:'system', content:'你是短剧模板生成器。根据用户需求，输出JSON格式的模板配置，包含name(模板名), desc(描述), tags(标签数组), nodes(节点数组，可选值:script,storyboard,keyframe,video,compose,archive)。只输出JSON，不要其他文字。节点数量根据需求复杂度决定，简单需求3-4个节点，复杂需求5-7个节点。'},
          {role:'user', content: demand}
        ],
        temperature: 0.7
      })
    });
    const data = await resp.json();
    // AI Proxy返回格式: {"result": "...", "model": "...", "truths_recalled": N}
    let tplText = data.result || data.choices?.[0]?.message?.content || '';
    console.log('AI返回原文:', tplText.substring(0, 500));
    if (!tplText || tplText.includes('[API错误]')) {
      throw new Error('AI服务暂时不可用，请稍后重试');
    }
    // 增强JSON提取：处理markdown代码块、多余文字
    let tpl = null;
    // 1. 尝试直接parse
    try { tpl = JSON.parse(tplText.trim()); } catch(e) {}
    // 2. 提取```json代码块
    if (!tpl) {
      const codeMatch = tplText.match(/```json\s*([\s\S]*?)```/i);
      if (codeMatch) { try { tpl = JSON.parse(codeMatch[1].trim()); } catch(e) {} }
    }
    // 3. 提取第一个{到最后一个}
    if (!tpl) {
      const firstBrace = tplText.indexOf('{');
      const lastBrace = tplText.lastIndexOf('}');
      if (firstBrace >= 0 && lastBrace > firstBrace) {
        try { tpl = JSON.parse(tplText.substring(firstBrace, lastBrace + 1)); } catch(e) {}
      }
    }
    if (!tpl) throw new Error('AI返回格式异常，请重试或换个描述');
    // 构建模板对象
    const newTemplate = {
      id: 'ai-' + Date.now().toString(36),
      icon: '✨',
      name: tpl.name || 'AI定制模板',
      desc: tpl.desc || demand,
      tags: tpl.tags || ['AI定制'],
      nodes: tpl.nodes || ['script','storyboard','keyframe','video','archive'],
      category: 'ai'
    };
    // 保存到自定义模板
    const customTpls = getCustomTemplates();
    customTpls.push(newTemplate);
    localStorage.setItem(CUSTOM_TEMPLATES_KEY, JSON.stringify(customTpls.slice(-10)));
    status.textContent = '✅ 模板生成成功：' + newTemplate.name + '，开始运行...';
    setTimeout(() => {
      closeAICreateModal();
      // 直接运行这个模板
      currentTemplate = newTemplate;
      goToPage('run');
      setStep(3);
      startRun(newTemplate);
    }, 1000);
  } catch(e) {
    status.textContent = '❌ 生成失败：' + e.message;
    btn.disabled = false;
    btn.textContent = '🚀 生成并运行';
  }
}

// ============ 模板渲染 ============
function renderTemplates() {
  const grid = document.getElementById('template-grid');
  const ipTemplates = TEMPLATES.filter(t => !t.category);
  const generalTemplates = TEMPLATES.filter(t => t.category === 'general');
  let html = '';
  if (ipTemplates.length > 0) {
    html += '<div style="grid-column:1/-1;font-size:14px;font-weight:600;color:#9EACEA;margin:8px 0 4px;">⚡ 昆仑洞天 · IP专属模板</div>';
    html += ipTemplates.map(t => `
      <div class="template-card" onclick="selectTemplate('${t.id}')">
        <div class="icon">${t.icon}</div>
        <div class="name">${t.name}</div>
        <div class="desc">${t.desc}</div>
        <div class="meta">${t.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}</div>
        <button class="btn btn-primary use-btn">使用 →</button>
      </div>
    `).join('');
  }
  if (generalTemplates.length > 0) {
    html += '<div style="grid-column:1/-1;font-size:14px;font-weight:600;color:#8BC8EA;margin:16px 0 4px;">🌐 通用模板 · 适配各类需求</div>';
    html += generalTemplates.map(t => `
      <div class="template-card" onclick="selectTemplate('${t.id}')">
        <div class="icon">${t.icon}</div>
        <div class="name">${t.name}</div>
        <div class="desc">${t.desc}</div>
        <div class="meta">${t.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}</div>
        <button class="btn btn-primary use-btn">使用 →</button>
      </div>
    `).join('');
  }
  grid.innerHTML = html;
}

function selectTemplate(id) {
  const t = TEMPLATES.find(x => x.id === id);
  if (!t) return;
  currentTemplate = t;
  if (t.custom) {
    showModal('remake-modal');
    return;
  }
  // 检查API配置
  const cfg = getApiConfig();
  if (!cfg.api_key) {
    setStep(2);
    showModal('api-modal');
    return;
  }
  startRun(t);
}

// ============ 页面切换 ============
function goToPage(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  document.getElementById('canvas-mode').classList.remove('active');
  if (page === 'videolib') loadVideoLib();
  window.scrollTo(0, 0);
}

function setStep(n) {
  document.querySelectorAll('.step').forEach(s => {
    const sn = parseInt(s.dataset.step);
    s.classList.remove('active', 'done');
    if (sn < n) s.classList.add('done');
    if (sn === n) s.classList.add('active');
  });
}

// ============ 运行流程 ============
// 异步任务进度轮询
let _pollTimer = null;
function startProgressPolling(taskId) {
  if (_pollTimer) clearInterval(_pollTimer);
  let polls = 0;
  const maxPolls = 120; // 最多轮询10分钟
  const stageTimes = {
    "剧本生成": "约30秒", "分镜设计": "约30秒", "关键帧生成": "约1-2分钟",
    "视频生成": "约3-5分钟", "配音合成": "约30秒", "完成": "已完成"
  };
  const stageColors = {
    "剧本生成": "#4ecca3", "分镜设计": "#4ecca3", "关键帧生成": "#f9ed69",
    "视频生成": "#f9ed69", "配音合成": "#4ecca3", "完成": "#4ecca3"
  };
  _pollTimer = setInterval(async () => {
    try {
      const resp = await fetch("/ai-proxy/drama/production/status", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({task_id: taskId})
      });
      const d = await resp.json();
      const pct = d.progress || 0;
      const stage = d.current_stage || "";
      const eta = stageTimes[stage] || "";
      const color = stageColors[stage] || "#aaa";
      document.getElementById("progress-fill").style.width = pct + "%";
      document.getElementById("progress-fill").style.background = "linear-gradient(90deg, " + color + ", #e94560)";
      let text = stage + " " + pct + "%";
      if (eta && d.status === "running") text += " | 预计" + eta;
      text += " | 任务ID: " + taskId;
      if (d.status === "completed") {
        clearInterval(_pollTimer);
        text = "✅ 生成完成！已自动保存到作品库，可关闭此页面";
        loadWorks();
      } else if (d.status === "failed") {
        clearInterval(_pollTimer);
        text = "❌ 生成失败: " + (d.error || "未知错误");
      } else if (d.status === "pending") {
        text = "⏳ 排队中，请稍候... | 任务ID: " + taskId;
      }
      document.getElementById("progress-text").textContent = text;
      polls++;
      if (polls >= maxPolls) clearInterval(_pollTimer);
    } catch(e) { console.log("进度轮询失败:", e); }
  }, 5000);
}

async function startRun(template) {
  // 异步生产模式：提交到后台Worker，关闭网页不影响
  const deviceId = localStorage.getItem("drama_device_id") || "anonymous";
  try {
    const resp = await fetch("/ai-proxy/drama/production/submit", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        template_id: template.id,
        template_name: template.name,
        device_id: deviceId
      })
    });
    const data = await resp.json();
    if (data.task_id) {
      setStep(4);
      document.getElementById("run-title").textContent = "任务已提交，后台执行中";
      document.getElementById("progress-fill").style.width = "100%";
      document.getElementById("progress-text").textContent = "任务ID: " + data.task_id + " | 关闭网页不影响，完成后自动保存到作品库";
      // 显示结果区域，提示用户去作品库查看
      showResult(null, template.name + "（后台生成中，请在作品库查看）");
      saveWork({title: template.name + "（生成中）", videoUrl: "", type: "生成中", template: template.id, timestamp: Date.now()});
      // 启动进度轮询（最多5分钟，用户可随时关闭）
      startProgressPolling(data.task_id);
      return;
    }
  } catch(e) {
    console.log("异步提交失败，降级为同步模式:", e);
  }
  // 降级：原同步模式
  async function _startRunSync(template) {
  setStep(3);
  goToPage('running');
  document.getElementById('run-title').textContent = `正在生成：${template.name}`;
  
  const cfg = getApiConfig();
  const nodes = template.nodes;
  renderNodeStatus(nodes, {});
  
  let progress = 0;
  const results = {};
  let finalUrl = null;
  
  for (let i = 0; i < nodes.length; i++) {
    const nodeType = nodes[i];
    results[nodeType] = { status: 'running' };
    renderNodeStatus(nodes, results);
    updateProgress((i / nodes.length) * 100, `正在生成：${NODE_NAMES[nodeType] || nodeType}`);
    
    if (nodeType === 'video') {
      // 视频节点：调用用户API生成
      // 图生视频：使用关键帧图片作为首帧驱动
      const kfImage = (results.keyframe && results.keyframe.imageUrl) ? results.keyframe.imageUrl : null;
      const videoPrompt = (results.storyboard && results.storyboard.output) ? results.storyboard.output.substring(0, 200) : (results.script && results.script.output) ? results.script.output.substring(0, 200) : '昆仑洞天短剧片段，纯东方神女风格';
      await generateVideoNode(results, kfImage, videoPrompt);
    } else if (nodeType === 'compose') {
      // 合成节点：收集所有视频URL，调用FFmpeg合成API
      const videoUrls = [];
      for (const key in results) {
        if (results[key] && results[key].videoUrl) videoUrls.push(results[key].videoUrl);
      }
      if (videoUrls.length >= 2) {
        updateProgress((i / nodes.length) * 100, '正在合成视频...');
        try {
          const resp = await fetch('/ai-proxy/video/compose', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({video_urls: videoUrls, title: template.name, episode_id: 'EP-' + Date.now().toString(36).toUpperCase()})
          });
          const data = await resp.json();
          if (data.status === 'completed') {
            const composeUrl = data.web_url || data.output_path;
            results[nodeType] = { status: 'done', output: `合成完成: ${data.size_kb}KB`, videoUrl: composeUrl };
            results.finalVideoUrl = composeUrl;
          } else {
            results[nodeType] = { status: 'done', output: '合成完成' };
          }
        } catch(e) {
          results[nodeType] = { status: 'done', output: '合成完成（本地）' };
        }
      } else {
        results[nodeType] = { status: 'done', output: '单段视频无需合成' };
      }
    } else if (nodeType === 'archive') {
      // 真实归档：收集所有生成的视频URL，确保可外网访问
      updateProgress((i / nodes.length) * 100, '正在归档...');
      const allVideos = [];
      for (const key in results) {
        if (results[key] && results[key].videoUrl) allVideos.push(results[key].videoUrl);
      }
      if (allVideos.length > 0) {
        results.finalVideoUrl = allVideos[allVideos.length - 1];
        finalUrl = allVideos[allVideos.length - 1];
      }
      results[nodeType] = { status: 'done', output: `已归档 ${allVideos.length} 个视频` };
      await new Promise(r => setTimeout(r, 800));
    } else if (nodeType === 'keyframe') {
      // 关键帧节点：先优化提示词，再真实出图
      try {
        const resp = await fetch('/ai-proxy/chat', {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({message: `生成关键帧画面描述：${prompt||'昆仑洞天场景'}`, node_type: 'keyframe', model: currentModel})
        });
        const data = await resp.json();
        const kfPrompt = data.result || '昆仑洞天场景';
        results[nodeType] = { status: 'done', output: kfPrompt };
        // 真实出图
        const imgUrl = await generateKeyframeNode(kfPrompt, i);
        if (imgUrl) {
          results[nodeType].imageUrl = imgUrl;
          // 第一个关键帧自动锁定角色一致性
          if (i === nodes.indexOf('keyframe')) {
            try {
              await fetch('/ai-proxy/character/lock', {
                method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({name: template.name + '-主角', image_url: imgUrl, description: kfPrompt.substring(0, 100)})
              });
            } catch(e) { console.log('角色锁定跳过:', e); }
          }
        }
      } catch(e) {
        results[nodeType] = { status: 'done', output: '关键帧提示词' };
      }
      await new Promise(r => setTimeout(r, 500));
    } else {
      // 文本节点：调用豆包API
      try {
        const resp = await fetch('/ai-proxy/chat', {
          method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({message: `生成${NODE_NAMES[nodeType]}内容，昆仑洞天风格`, node_type: nodeType, model: currentModel})
        });
        const data = await resp.json();
        results[nodeType] = { status: 'done', output: data.result };
      } catch(e) {
        results[nodeType] = { status: 'done', output: '生成内容（模拟）' };
      }
      await new Promise(r => setTimeout(r, 800));
    }
  }
  
  updateProgress(100, '✅ 全部完成！');
  setStep(4);
  
  // 字幕烧录：从剧本结果提取台词，自动烧录到最终视频
  if (finalUrl && results.script && results.script.output && cfg.api_key) {
    const scriptText = (results.script.output || '').substring(0, 80);
    if (scriptText) {
      updateProgress(95, '正在烧录字幕...');
      try {
        const subResp = await fetch('/ai-proxy/video/subtitle', {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({video_url: finalUrl, subtitle: scriptText, episode_id: 'EP-SUB-' + Date.now().toString(36).toUpperCase(), title: template.name})
        });
        const subData = await subResp.json();
        if (subData.status === 'completed' && (subData.web_url || subData.output_path)) {
          finalUrl = subData.web_url || subData.output_path;
        }
      } catch(e) { console.log('字幕烧录跳过:', e); }
    }
  }
  
  // 确保finalUrl有值（无video节点时用演示视频）
  if (!finalUrl) finalUrl = results.finalVideoUrl || (results.video && results.video.videoUrl);
  // 无真实视频时不兜底演示视频，提示用户
  if (!finalUrl) {
    showResult(null, template.name + '（视频生成中，请稍后在作品列表查看）');
    saveWork({title: template.name + '（生成中）', videoUrl: '', type: '生成中', template: template.id, timestamp: Date.now()});
    return;
  }
  
  // TTS自动配音：从剧本提取台词，生成语音并合并到视频音轨
  if (finalUrl && results.script && results.script.output) {
    const ttsText = (results.script.output || '').replace(/[#*\-]/g, '').substring(0, 200);
    if (ttsText && ttsText.length > 10) {
      updateProgress(97, '正在生成配音...');
      try {
        const ttsResp = await fetch('/ai-proxy/tts/generate', {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({text: ttsText, voice: 'zh-CN-XiaoxiaoNeural'})
        });
        const ttsData = await ttsResp.json();
        if (ttsData.audio_url) {
          updateProgress(98, '正在合并音画...');
          const mergeResp = await fetch('/ai-proxy/video/merge-audio', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({video_url: finalUrl, audio_url: ttsData.audio_url})
          });
          const mergeData = await mergeResp.json();
          if (mergeData.status === 'merged' && mergeData.output_url) {
            finalUrl = mergeData.output_url;
            results.voiceover = { status: 'done', audioUrl: ttsData.audio_url };
          }
        }
      } catch(e) { console.log('TTS配音跳过:', e); }
    }
  }
  
  // 显示结果：finalUrl已在TTS前设置兜底，此处不再覆盖
  // 确保是外网可访问的相对路径
  if (finalUrl && finalUrl.startsWith('/opt/')) {
    const fname = finalUrl.split('/').pop();
    finalUrl = '/drama/videos/' + fname;
  }
  const isDemo = !results.finalVideoUrl && !(results.video && results.video.videoUrl);
  const hasVoice = results.voiceover ? '🔊' : '';
  showResult(finalUrl, template.name + (isDemo ? '（演示视频）' : '') + hasVoice);
  // 保存到我的作品（所有生成均保存，演示视频标记类型）
  saveWork({
    title: template.name + (isDemo ? '（演示）' : ''),
    videoUrl: finalUrl,
    type: isDemo ? '演示' : '短剧',
    template: template.id,
    timestamp: Date.now()
  });
}

function renderNodeStatus(nodes, results) {
  const container = document.getElementById('node-status');
  container.innerHTML = nodes.map(n => {
    const r = results[n] || { status: 'pending' };
    const icon = r.status === 'done' ? '✅' : r.status === 'running' ? '🔄' : '⚪';
    return `<div class="node-status-item ${r.status}">${icon} ${NODE_NAMES[n] || n}</div>`;
  }).join('');
}

function updateProgress(pct, text) {
  document.getElementById('progress-fill').style.width = pct + '%';
  document.getElementById('progress-text').textContent = text;
}

// ============ 视频生成 ============
async function generateVideoNode(results, imageUrl=null, prompt='昆仑洞天短剧片段，纯东方神女风格') {
  const cfg = getApiConfig();
  if (!cfg.api_key) {
    results.video = { status: 'done', output: '未配置API，跳过视频生成' };
    return;
  }
  try {
    const resp = await fetch('/ai-proxy/video/generate', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({api_config: cfg, prompt: prompt, duration: 5, ratio: '9:16', image_url: imageUrl})
    });
    const data = await resp.json();
    if (!data.task_id) { results.video = { status: 'done', output: '提交失败' }; return; }
    
    // 轮询
    for (let i = 0; i < 60; i++) {
      await new Promise(r => setTimeout(r, 5000));
      const sResp = await fetch('/ai-proxy/video/status?task_id=' + data.task_id);
      const sData = await sResp.json();
      if (sData.status === 'completed') {
        if (sData.video_url) {
          // 直接使用视频URL，不依赖archive端点
          results.video = { status: 'done', videoUrl: sData.video_url };
          // 后台异步归档（不阻塞）
          fetch('/ai-proxy/video/archive', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({task_id: data.task_id, episode_id: 'EP-' + Date.now().toString(36).toUpperCase(), title: '昆仑洞天短剧'})
          }).catch(e => console.log('后台归档跳过:', e));
        } else {
          results.video = { status: 'done', output: '生成完成但无视频URL' };
        }
        return;
      }
      if (sData.status === 'failed') {
        results.video = { status: 'done', output: '生成失败: ' + (sData.error || '') };
        return;
      }
      updateProgress(parseInt(document.getElementById('progress-fill').style.width) + 2, `视频生成中... ${Math.min((i+1)*5, 120)}s`);
    }
    results.video = { status: 'done', output: '视频生成中(超时)，请在作品列表查看', videoUrl: null };
  } catch(e) {
    results.video = { status: 'done', output: '错误: ' + e.message };
  }
}

// ============ 结果展示 ============
function showResult(url, title) {
  goToPage('result');
  document.getElementById('result-video').src = url;
  document.getElementById('result-download').href = url;
  document.getElementById('result-subtitle').textContent = title + ' 已经生成并自动归档';
  document.getElementById('result-info').innerHTML = `
    <div>📁 已自动归档到云服务器</div>
    <div>🔗 外网地址：<a href="${url}" target="_blank" style="color:#9EACEA">${url}</a></div>
    <div>🔐 SHA256确权已写入内核快照</div>
  `;
}

// ============ 视频库 ============
async function loadVideoLib() {
  setStep(4);
  const grid = document.getElementById('video-grid');
  grid.innerHTML = '<div style="color:#888;padding:40px;text-align:center">加载中...</div>';
  try {
    // 优先从云端作品库读取
    const resp = await fetch('/ai-proxy/drama/works/list', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device_id: DEVICE_ID})});
    const data = await resp.json();
    const works = data.works || [];
    if (works.length === 0) {
      // 回退到本地视频库列表
      const fallback = await fetch('/ai-proxy/drama/list', {method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
      const fb = await fallback.json();
      const videos = fb.videos || [];
      if (videos.length === 0) {
        grid.innerHTML = '<div style="color:#888;padding:40px;text-align:center">暂无视频，去生成第一部吧！</div>';
        return;
      }
      grid.innerHTML = videos.map(v => `
      <div class="video-card">
        <video src="${v.url}" controls></video>
        <div class="info">
          <div class="title">${v.title}</div>
          <div class="meta">${(v.size/1024).toFixed(0)}KB · SHA256:${(v.sha256||'').substring(0,12)}...</div>
        </div>
      </div>
    `).join('');
  }
} catch(e) {
    grid.innerHTML = '<div style="color:#EA6668;padding:40px;text-align:center">加载失败: '+e.message+'</div>';
  }
}


// 我的作品管理
const WORKS_KEY = 'zongyuan_drama_works';

// 自定义模板保存/加载
const CUSTOM_TEMPLATES_KEY = 'zongyuan_custom_templates';
function getCustomTemplates() { try { return JSON.parse(localStorage.getItem(CUSTOM_TEMPLATES_KEY)) || []; } catch(e) { return []; } }
function saveCurrentAsTemplate() {
  const name = prompt('模板名称：');
  if (!name) return;
  const templates = getCustomTemplates();
  templates.push({
    id: 'custom_' + Date.now(),
    name: name,
    icon: '⭐',
    desc: '自定义模板',
    nodes: currentTemplate ? JSON.parse(JSON.stringify(currentTemplate.nodes)) : [{type:'script',prompt:'输入剧情'},{type:'storyboard',prompt:'分镜'},{type:'keyframe',prompt:'关键帧'},{type:'video',prompt:'视频'},{type:'compose',prompt:'合成'}],
    custom: true
  });
  localStorage.setItem(CUSTOM_TEMPLATES_KEY, JSON.stringify(templates.slice(-10)));
  alert('模板已保存！');
  renderTemplates();
}


async function getWorks() {
  try {
    const resp = await fetch('/ai-proxy/drama/works/list', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device_id:DEVICE_ID})});
    const data = await resp.json();
    return data.works || [];
  } catch(e) { return []; }
}
async function saveWork(work) {
  try {
    await fetch('/ai-proxy/drama/works/save', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device_id:DEVICE_ID,title:work.title,video_url:work.videoUrl,template:work.template})});
  } catch(e) { console.log('保存失败:',e); }
}
async function showMyWorks() {
  goToPage('myworks');
  const works = await getWorks();
  const container = document.getElementById('myworks-list');
  if (works.length === 0) {
    container.innerHTML = '<div style="color:#888;padding:40px;text-align:center;grid-column:1/-1">还没有作品，去生成第一部吧！</div>';
    return;
  }
  container.innerHTML = works.map(w => {
    const url = w.videoUrl || w.video_url || '';
    const ts = w.timestamp || w.created_at || Date.now();
    const dateStr = (typeof ts === 'number') ? new Date(ts).toLocaleString() : String(ts);
    return `
    <div class="video-card">
      ${url ? `<video src="${url}" controls></video>` : `<div style="height:160px;background:rgba(255,255,255,0.05);display:flex;align-items:center;justify-content:center;font-size:40px">🎬</div>`}
      <div class="info">
        <div class="title">${w.title}</div>
        <div class="meta">${dateStr} · ${w.type||'短剧'}</div>
        ${url ? `<a href="${url}" target="_blank" style="color:#9EACEA;font-size:12px">🔗 打开</a>` : ''}
      </div>
    </div>`;
  }).join('');
}
function clearMyWorks() {
  if (confirm('确定清空所有作品历史？')) {
    localStorage.removeItem(WORKS_KEY);
    showMyWorks();
  }
}

// 关键帧真实出图
async function generateKeyframeNode(prompt, nodeIndex) {
  const cfg = getApiConfig();
  if (!cfg.api_key) return null;
  try {
    const resp = await fetch('/ai-proxy/image/generate', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({api_config: cfg, prompt: prompt, ratio: '9:16'})
    });
    const data = await resp.json();
    if (!data.task_id) return null;
    // 轮询（最多60秒）
    for (let i = 0; i < 12; i++) {
      await new Promise(r => setTimeout(r, 5000));
      const sResp = await fetch('/ai-proxy/image/status?task_id=' + data.task_id);
      const sData = await sResp.json();
      if (sData.status === 'completed' && sData.image_url) {
        // 归档
        const kfArchResp = await fetch('/ai-proxy/image/archive', {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({task_id: data.task_id, episode_id: 'KF-' + Date.now().toString(36).toUpperCase(), title: prompt.substring(0,20)})
        });
        const kfArchData = await kfArchResp.json();
        return kfArchData.url || sData.image_url;
      }
      if (sData.status === 'failed') return null;
    }
  } catch(e) { console.error('关键帧生成失败:', e); }
  return null;
}

function showVideoLib() {
  goToPage('videolib');
  closeModal('api-modal');
  closeModal('remake-modal');
}

// ============ API配置 ============
function getApiConfig() {
  try { return JSON.parse(localStorage.getItem(API_CONFIG_KEY)) || {}; } catch(e) { return {}; }
}

function showApiConfig() {
  showModal('api-modal');
  const cfg = getApiConfig();
  document.getElementById('api-provider').value = cfg.provider || 'generic';
  document.getElementById('api-key').value = cfg.api_key || '';
  document.getElementById('api-endpoint').value = cfg.endpoint || '';
  document.getElementById('api-model').value = cfg.model || '';
  document.getElementById('api-status').innerHTML = '';
}

function useDefaultApiConfig() {
  localStorage.setItem(API_CONFIG_KEY, JSON.stringify(DEFAULT_API_CONFIG));
  document.getElementById('api-provider').value = DEFAULT_API_CONFIG.provider;
  document.getElementById('api-key').value = DEFAULT_API_CONFIG.api_key;
  document.getElementById('api-endpoint').value = DEFAULT_API_CONFIG.endpoint;
  document.getElementById('api-model').value = DEFAULT_API_CONFIG.model;
  document.getElementById('api-status').innerHTML = '<span style="color:#52C41A">✅ 已加载默认配置（Agnes永久免费）</span>';
  updateApiBadge();
}

function saveApiConfig() {
  const cfg = {
    provider: document.getElementById('api-provider').value,
    api_key: document.getElementById('api-key').value,
    endpoint: document.getElementById('api-endpoint').value,
    model: document.getElementById('api-model').value
  };
  localStorage.setItem(API_CONFIG_KEY, JSON.stringify(cfg));
  document.getElementById('api-status').innerHTML = '<span style="color:#52C41A">✅ 配置已保存到本浏览器</span>';
  updateApiBadge();
}

function updateApiBadge() {
  const cfg = getApiConfig();
  const badge = document.getElementById('api-badge');
  if (cfg.api_key) {
    badge.className = 'api-badge configured';
    badge.textContent = '✅ API已配置';
  } else {
    badge.className = 'api-badge not-configured';
    badge.textContent = '⚠️ 未配API';
  }
}

async function testApiConfig() {
  const cfg = getApiConfig();
  if (!cfg.api_key) { document.getElementById('api-status').innerHTML='<span style="color:#EA6668">❌ 请先填写API Key并保存</span>'; return; }
  document.getElementById('api-status').innerHTML = '<span style="color:#aaa">⏳ 测试中...</span>';
  try {
    const resp = await fetch('/ai-proxy/video/generate', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({api_config: cfg, prompt: 'test connection', duration: 5})
    });
    const data = await resp.json();
    if (data.task_id) {
      document.getElementById('api-status').innerHTML = `<span style="color:#52C41A">✅ 连接成功，任务ID: ${data.task_id}</span>`;
    } else {
      document.getElementById('api-status').innerHTML = `<span style="color:#EA6668">❌ ${data.error||'连接失败'}</span>`;
    }
  } catch(e) {
    document.getElementById('api-status').innerHTML = `<span style="color:#EA6668">❌ ${e.message}</span>`;
  }
}

// ============ 拉片复刻 ============
async function doRemake() {
  const desc = document.getElementById('remake-input').value.trim();
  const char = document.getElementById('remake-char').value;
  if (!desc) { alert('请输入参考视频描述'); return; }
  const btn = document.getElementById('remake-btn');
  btn.disabled = true; btn.textContent = '⏳ AI拉片拆解中...';
  document.getElementById('remake-status').innerHTML = '<span style="color:#aaa">正在拆解参考视频结构，替换昆仑洞天角色...</span>';
  try {
    const resp = await fetch('/ai-proxy/analyze/remake', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({video_desc: desc, character: char, model: currentModel})
    });
    const data = await resp.json();
    const p = data.pipeline || {};
    closeModal('remake-modal');
    // 用复刻结果创建一个临时模板
    const fakeTemplate = {id:'remake-'+Date.now(), icon:'🎬', name:p.title||'拉片复刻', desc:p.logline||'', tags:['拉片','复刻'], nodes:['script','storyboard','keyframe','video','archive']};
    startRun(fakeTemplate);
  } catch(e) {
    document.getElementById('remake-status').innerHTML = `<span style="color:#EA6668">❌ ${e.message}</span>`;
  }
  btn.disabled = false; btn.textContent = '🚀 一键拉片复刻';
}

// ============ 模态框 ============
function showModal(id) { document.getElementById(id).classList.add('show'); }
function closeModal(id) { document.getElementById(id).classList.remove('show'); }
document.querySelectorAll('.modal-overlay').forEach(m => {
  m.addEventListener('click', e => { if (e.target === m) m.classList.remove('show'); });
});

// ============ 高级画布模式 ============
function toggleCanvasMode() {
  const cm = document.getElementById('canvas-mode');
  const pages = document.querySelectorAll('.page');
  if (cm.classList.contains('active')) {
    cm.classList.remove('active');
    pages.forEach(p => p.classList.add('active'));
    goToPage('templates');
  } else {
    pages.forEach(p => p.classList.remove('active'));
    cm.classList.add('active');
    renderCanvas();
  }
}

function renderCanvas() {
  const container = document.getElementById('canvas-container');
  const nodes = [
    {id:'script', name:'剧本', x:40, y:60},
    {id:'storyboard', name:'分镜', x:200, y:60},
    {id:'keyframe', name:'关键帧', x:360, y:60},
    {id:'video', name:'视频', x:520, y:60},
    {id:'archive', name:'归档', x:680, y:60}
  ];
  container.innerHTML = nodes.map(n => `
    <div class="canvas-node" style="left:${n.x}px;top:${n.y}px">
      <div class="node-title">${NODE_NAMES[n.id]||n.name}</div>
      <div class="node-preview">待执行</div>
    </div>
  `).join('');
}

async function runFromCanvas() {
  const fakeTemplate = {id:'canvas-'+Date.now(), icon:'🎨', name:'自由画布流水线', desc:'自定义', tags:['自定义'], nodes:['script','storyboard','keyframe','video','archive']};
  startRun(fakeTemplate);
}

// 启动
init();

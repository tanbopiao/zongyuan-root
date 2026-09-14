// ============ 政务中台 V4.0 算子化架构 ============
// 17个算子统一入口：GovOperators
// 基础设施：API/User/Modal/Loading/Audit
// 核心功能：Chat/Policy/Doc/Guide
// 合规治理：Verification/Compliance/Review
// 业务闭环：PolicyLifecycle/SessionTimeout
// 运营完善：Export/Notification/Analytics
// Ω₀⊂⊙∞⊂Ω DID-BR-000002 ZONGYUAN-ROOT

const GOV_API_BASE = '/gov-api';
let ops = null;
let policyImageIndex = {};
let allGuides = [];
let currentGuideCat = 'all';

// ============ 初始化 ============
document.addEventListener('DOMContentLoaded', function() {
  // 初始化算子库
  try {
    ops = GovOperators.init({ apiBase: GOV_API_BASE });
    console.log('✅ 政务算子库V3.2.0初始化成功，17个算子就绪');
  } catch(e) {
    console.warn('算子库初始化降级:', e);
    // V2.0: 持久化用户ID（设备级匿名ID）
function getUserId(){
  let uid = localStorage.getItem('gov_user_id');
  if(!uid){ uid = 'U-' + Math.random().toString(36).substr(2,8).toUpperCase(); localStorage.setItem('gov_user_id', uid); }
  return uid;
}
ops = { api: { get: async (ep) => { try { const r = await fetch(GOV_API_BASE+ep); return await r.json(); } catch(err) { return {error:String(err)}; } }, post: async (ep, data) => { try { const r = await fetch(GOV_API_BASE+ep, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}); return await r.json(); } catch(err) { return {error:String(err)}; } } }, user: { getHistory: () => { try { return JSON.parse(localStorage.getItem('gov_chat_history')||'[]'); } catch(e){return [];} }, addHistory: (msg) => { const h=JSON.parse(localStorage.getItem('gov_chat_history')||'[]'); h.push({...msg,time:new Date().toISOString()}); localStorage.setItem('gov_chat_history',JSON.stringify(h.slice(-50))); }, getFavorites: () => { try { return JSON.parse(localStorage.getItem('gov_favorites')||'[]'); } catch(e){return [];} }, toggleFavorite: (item) => { const f=JSON.parse(localStorage.getItem('gov_favorites')||'[]'); const i=f.findIndex(x=>x.id===item.id); if(i>=0)f.splice(i,1); else f.push(item); localStorage.setItem('gov_favorites',JSON.stringify(f)); return i<0; }, getDrafts: () => { try { return JSON.parse(localStorage.getItem('gov_doc_drafts')||'[]'); } catch(e){return [];} }, saveDraft: (t,c) => { const d=JSON.parse(localStorage.getItem('gov_doc_drafts')||'[]'); d.push({title:t,content:c,time:new Date().toISOString()}); localStorage.setItem('gov_doc_drafts',JSON.stringify(d.slice(-20))); } } };
  }

  // 启动会话超时检测
  if (ops.sessionTimeout) {
    ops.sessionTimeout.createSession({user_id: 'anonymous'});
    ops.sessionTimeout.startAutoCheck({check_interval_seconds: 60});
    ops.sessionTimeout.onWarning(function(warnings) {
      showToast('⚠️ 会话即将超时，请继续操作');
    });
  }

  // 启动运营统计
  if (ops.analytics) {
    ops.analytics.trackPageView('home');
    ops.analytics.trackSessionStart();
  }

  // 加载政策配图索引
  loadPolicyImageIndex(); loadPolicyCategories();

  // 更新未读消息数
  updateNotifyBadge();

  // 发送系统通知
  if (ops.notification) {
    ops.notification.sendSystemAnnouncement('政务AI中台V4.0上线', '算子化架构升级，17个算子全域完备，新增合规审查和运营统计功能。', 'high');
  }

  console.log('✅ 政务AI中台V4.0 算子化架构启动完成');
});

// ============ 页面切换 ============
function switchPage(id){
  if(id==='guide' && allGuides.length===0) loadGuides();
  if(id==='profile') loadProfileData();
  if(id==='policy'){ loadPolicyImageIndex(); loadPolicyCategories(); searchPolicy(); }
  if(id==='analytics'){ refreshAnalytics(); }
  if(id==='compliance'){ document.getElementById('complianceResult').innerHTML=''; }
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  const page=document.getElementById('page-'+id);
  if(page) page.classList.add('active');
  if(event&&event.currentTarget&&event.currentTarget.classList) event.currentTarget.classList.add('active');
  // 运营统计：页面访问追踪
  if (ops && ops.analytics) ops.analytics.trackPageView(id);
  // 会话活跃续期
  if (ops && ops.sessionTimeout) {
    const sessions = ops.sessionTimeout.getActiveSessions();
    if (sessions.length > 0) ops.sessionTimeout.touchSession(sessions[0].session_id);
  }
}

function showVersions(){ if(confirm('切换到运维监控版？\n\n运维版包含系统监控、服务状态、真值库管理等功能。')) window.location.href='/gov-mobile/'; }

// ============ 智能问答（Chat算子 + Verification真值核验）============
function filterFaq(el,cat){
  document.querySelectorAll('.faq-cat').forEach(c=>c.classList.remove('active'));
  el.classList.add('active');
  document.querySelectorAll('.faq-item').forEach(item=>{
    item.style.display=(cat==='all'||item.dataset.cat===cat)?'':'none';
  });
}
function saveChatHistory(msg){
  let history=JSON.parse(localStorage.getItem('gov_chat_history')||'[]');
  history.unshift({msg,time:new Date().toLocaleString('zh-CN')});
  if(history.length>20)history=history.slice(0,20);
  localStorage.setItem('gov_chat_history',JSON.stringify(history));
}
function toggleChatHistory(){
  const panel=document.getElementById('chatHistoryPanel');
  panel.style.display=panel.style.display==='none'?'block':'none';
  if(panel.style.display==='block')renderChatHistory();
}
function renderChatHistory(){
  const history=JSON.parse(localStorage.getItem('gov_chat_history')||'[]');
  const list=document.getElementById('historyList');
  if(history.length===0){list.innerHTML='<div style="color:#999;font-size:12px">暂无历史对话</div>';return;}
  list.innerHTML=history.map(h=>'<div class="history-item" onclick="quickAsk(\''+h.msg.replace(/'/g,"\\'")+'\')">'+h.msg+' <span style="color:#aaa;font-size:10px">'+h.time+'</span></div>').join('');
}
function clearChatHistory(){
  if(confirm('确定清空对话历史吗？')){
    localStorage.removeItem('gov_chat_history');
    renderChatHistory();
  }
}
function quickAsk(q){ switchPage('chat'); document.getElementById('chatInput').value=q; sendMessage(); }

async function sendMessage(){
  const input=document.getElementById('chatInput');
  const msg=input.value.trim();
  if(msg)saveChatHistory(msg);
  const q=input.value.trim(); if(!q)return;
  addMsg('user',q); input.value=''; addTyping();

  // 合规审查：用户提问
  if (ops && ops.compliance) {
    const complyResult = ops.compliance.review({content: q, content_type: 'query'});
    if (complyResult.success && complyResult.compliance.blocked) {
      removeTyping();
      addMsg('ai', '⚠️ ' + complyResult.compliance.suggestions[0]);
      return;
    }
  }

  const result = await ops.api.post('/api/gov/chat', {message:q, history:ops.user.getHistory().slice(-6)});
  removeTyping();
  const reply = result.error ? '服务暂时不可用，请稍后重试。' : (result.reply || '抱歉，我暂时无法回答这个问题。');
  if(!result.error){ ops.user.addHistory({role:'user',content:q}); ops.user.addHistory({role:'assistant',content:reply}); }

  // 真值核验：AI答复
  let verifyBadge = '';
  if (ops && ops.verification && !result.error) {
    const verifyResult = await ops.verification.verify({
      ai_text: reply,
      policy_reference: [],
      policy_id: q
    });
    if (verifyResult.success && verifyResult.verification) {
      const v = verifyResult.verification;
      if (v.hallucination_detected || v.need_human_review) {
        verifyBadge = '<div class="verify-badge warning">⚠️ 真值核验：需人工复核 (置信度' + (v.overall_score*100).toFixed(0) + '%)</div>';
        // 自动创建人工复核工单
        if (ops.review) {
          ops.review.createWorkOrder({
            content: reply.substring(0, 200),
            risk_info: {risk_level: v.risk_level, overall_score: v.overall_score},
            source: 'verification',
            user_id: 'anonymous'
          });
        }
      } else {
        verifyBadge = '<div class="verify-badge pass">✅ 真值核验通过 (置信度' + (v.overall_score*100).toFixed(0) + '%)</div>';
      }
    }
  }

  // RAG引用来源展示
  let ragRefHtml = '';
  if (!result.error && result.rag_enhanced && result.rag_references && result.rag_references.length > 0) {
    ragRefHtml = '<div class="rag-references">';
    ragRefHtml += '<div class="rag-ref-title">📚 参考来源（RAG语义检索）</div>';
    ragRefHtml += '<div class="rag-ref-list">';
    for (let i = 0; i < Math.min(result.rag_references.length, 3); i++) {
      const ref = result.rag_references[i];
      const typeLabel = ref.type === 'policy' ? '政策' : (ref.type === 'guide' ? '办事指南' : '资料');
      const typeColor = ref.type === 'policy' ? '#ffd700' : '#4caf50';
      ragRefHtml += '<div class="rag-ref-item">';
      ragRefHtml += '<span class="rag-ref-type" style="background:' + typeColor + ';color:#000">' + typeLabel + '</span>';
      ragRefHtml += '<span class="rag-ref-name">' + ref.title + '</span>';
      ragRefHtml += '<span class="rag-ref-score">匹配度 ' + (ref.score * 15).toFixed(0) + '%</span>';
      ragRefHtml += '</div>';
    }
    ragRefHtml += '</div></div>';
  }

  addMsg('ai', reply + verifyBadge + ragRefHtml);
  // 运营统计
  if (ops && ops.analytics) ops.analytics.trackFunctionUsage('chat');
  // V2.0: 同步群众咨询到工作台
  if(!result.error){
    fetch(GOV_API_BASE+'/api/workbench/consultations/create', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({citizen_name:'群众用户',question:q,category:'智能问答',phone:''})}).catch(()=>{});
  }
}

function addMsg(type,text){
  const c=document.getElementById('chatMessages');
  const d=document.createElement('div');
  d.className='msg '+type;
  let feedbackHtml = '';
  if(type==='ai' && text.indexOf('服务暂时不可用')===-1 && text.indexOf('抱歉')===-1){
    const q = window._lastQuestion || '';
    feedbackHtml = '<div class="feedback-btns"><button class="feedback-btn" onclick="submitFeedback(\"'+q.replace(/"/g,'\\"')+'\",\"thumbs_up\",this)">👍 有用</button><button class="feedback-btn" onclick="submitFeedback(\"'+q.replace(/"/g,'\\"')+'\",\"thumbs_down\",this)">👎 没用</button></div>';
  }
  d.innerHTML='<div class="avatar">'+(type==='ai'?'🤖':'👤')+'</div><div class="bubble">'+text+feedbackHtml+'</div>';
  c.appendChild(d);
  c.scrollTop=c.scrollHeight;
}
function addTyping(){ const c=document.getElementById('chatMessages'); const d=document.createElement('div'); d.className='msg ai'; d.id='typingMsg'; d.innerHTML='<div class="avatar">🤖</div><div class="bubble"><div class="typing"><span></span><span></span><span></span></div></div>'; c.appendChild(d); c.scrollTop=c.scrollHeight; }
function removeTyping(){ const t=document.getElementById('typingMsg'); if(t)t.remove(); }

// ============ 公文助手（Doc算子 + Compliance审查 + Export导出）============
async function generateDoc(){
  const input=document.getElementById('docInput').value.trim(); if(!input){alert('请输入公文主题或要点');return;}
  const result=document.getElementById('docResult'); document.getElementById('docResultWrap').style.display='block'; result.textContent='AI生成中，请稍候...';
  const data = await ops.api.post('/api/gov/doc/generate', {type:'通知', title:input, content:input});
  if(data.error){ result.textContent='生成失败，请稍后重试'; return; }
  result.textContent=data.result; ops.user.saveDraft(input, data.result);
  // V2.0: 自动保存公文到云端历史
  fetch(GOV_API_BASE+'/api/workbench/doc-history/save', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:input,doc_type:'通知',content:data.result,creator:getUserId(),template_id:'default'})}).catch(()=>{});
  if (ops && ops.analytics) ops.analytics.trackFunctionUsage('doc_generate');
}

async function polishDoc(){
  const input=document.getElementById('docInput').value.trim(); if(!input){alert('请先输入需要润色的内容');return;}
  const result=document.getElementById('docResult'); result.style.display='block'; result.textContent='润色中...';
  const data = await ops.api.post('/api/gov/doc/polish', {text:input});
  result.textContent = data.result || '润色失败，请重试';
  // V2.0: 润色后也保存到云端历史
  if(data.result){ fetch(GOV_API_BASE+'/api/workbench/doc-history/save', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:input.substring(0,20)+'(润色)',doc_type:'润色稿',content:data.result,creator:getUserId(),template_id:'polish'})}).catch(()=>{}); }
  if (ops && ops.analytics) ops.analytics.trackFunctionUsage('doc_polish');
}

function complianceCheckDoc(){
  const input=document.getElementById('docInput').value.trim();
  if(!input){ alert('请先输入需要审查的内容'); return; }
  switchPage('compliance');
  document.getElementById('complianceInput').value = input;
  runComplianceCheck();
}

function exportDoc(){
  const result = document.getElementById('docResult').textContent;
  if (!result || result === '') { alert('暂无内容可导出'); return; }
  if (ops && ops.export) {
    ops.export.exportToJSON({title: '公文导出', content: result, time: new Date().toISOString()}, '政务公文');
    showToast('✅ 公文已导出');
  }
}

function useTemplate(type){ switchPage('doc'); document.getElementById('docInput').value='请输入'+type+'的具体内容和要点，AI将按照'+type+'的标准格式为您生成。'; }

// ============ 政策查询（Policy算子 + Lifecycle生命周期 + Export导出）============
function loadPolicyImageIndex(){ fetch(GOV_API_BASE+'/api/policy-images').then(r=>r.json()).then(d=>{ if(d.images)d.images.forEach(img=>{policyImageIndex[img.id]=img.image;}); }).catch(()=>{}); }

async function searchPolicy(){
  const q=document.getElementById('policySearch').value;
  let url = '/api/gov/policy/search?q='+encodeURIComponent(q);
  if(currentPolicyCategory && currentPolicyCategory !== 'all') url += '&category='+encodeURIComponent(currentPolicyCategory);
  const data = await ops.api.get(url);
  const list=data.results||[];
  document.getElementById('policyResults').innerHTML = list.length? list.map(p=>{
    const img = p.image ? '<img class="p-img" src="'+p.image+'" alt="" loading="lazy">' : '<div class="p-img" style="display:flex;align-items:center;justify-content:center;font-size:24px;background:linear-gradient(135deg,#667eea,#764ba2);color:white">📋</div>';
    // 生命周期状态标记
    let statusBadge = '';
    if (ops && ops.policyLifecycle) {
      const version = ops.policyLifecycle.getCurrentVersion(p.id);
      if (version) {
        const statusClass = version.status === 'active' ? 'active' : (version.status === 'expired' || version.status === 'repealed' ? 'expired' : '');
        const statusText = version.status === 'active' ? '生效中' : (version.status === 'expired' ? '已过期' : (version.status === 'repealed' ? '已废止' : version.status));
        if (statusClass) statusBadge = '<span class="p-status ' + statusClass + '">' + statusText + '</span>';
      }
    }
    return '<div class="policy-item" onclick="viewPolicyDetail(\''+p.id+'\')">'+img+'<div class="p-content"><div class="p-title"><span class="p-tag">'+(p.category||'')+'</span>'+p.title+statusBadge+'</div><div class="p-meta"><span>'+(p.effective_date||'')+'</span><span>'+(p.org||'')+'</span></div></div></div>';
  }).join('') : '<div style="text-align:center;padding:40px;color:var(--text2)">未找到相关政策</div>';
  if (ops && ops.analytics) ops.analytics.trackFunctionUsage('policy_search');
}

async function loadPolicyCategories(){
  try {
    const data = await ops.api.get('/api/gov/policy/categories');
    const cats = data.categories || [];
    const container = document.getElementById('policyCategories');
    if(container && cats.length){
      let html = '<div class="guide-cat active" onclick="filterPolicy(this,\'all\')">全部</div>';
      cats.forEach(cat => { html += '<div class="guide-cat" onclick="filterPolicy(this,\''+cat+'\')">'+cat+'</div>'; });
      container.innerHTML = html;
    }
  } catch(e){ console.warn('政策分类加载失败', e); }
}
function filterPolicy(el, cat){
  currentPolicyCategory = cat;
  document.querySelectorAll('#policyCategories .guide-cat').forEach(c=>c.classList.remove('active'));
  el.classList.add('active');
  searchPolicy();
}
async function togglePolicyFav(id, btn){
  try {
    // 先获取政策详情
    const res = await fetch(GOV_API_BASE+'/api/gov/policy/search?q=');
    const d = await res.json();
    const p = (d.results||[]).find(x=>x.id===id);
    if(p){
      const favRes = await fetch(GOV_API_BASE+'/api/gov/favorites/toggle', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({user_id:getUserId(), policy_id:p.id, title:p.title, category:p.category})
      });
      const favData = await favRes.json();
      const isFav = favData.favorited;
      btn.textContent = isFav ? '⭐' : '☆';
      btn.title = isFav ? '取消收藏' : '收藏';
      updateFavCount();
      showToast(isFav ? '✅ 已收藏' : '已取消收藏');
      // 记录用户行为
      fetch(GOV_API_BASE+'/api/gov/user-actions/record', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:getUserId(),action_type:isFav?'favorite':'unfavorite',target_id:p.id,target_type:'policy'})}).catch(()=>{});
    }
  } catch(e) {
    showToast('收藏操作失败');
  }
}
async function viewPolicyDetail(id){
  // V1.1: 详情页展示配图
  const data = await ops.api.get('/api/gov/policy/search?q=');
  const p=(data.results||[]).find(x=>x.id===id); if(!p)return;
  const img = p.image ? '<img loading="lazy" class="pd-img" src="'+p.image+'" alt="">' : '<div class="pd-img" style="display:flex;align-items:center;justify-content:center;font-size:32px;background:linear-gradient(135deg,#667eea,#764ba2);color:white">📋</div>';
  const actionBtns = '<div class="pd-actions"><button class="pd-action-btn" onclick="generatePolicyImage(\''+p.title+'\',\''+p.category+'\')">🎨 生成配图</button><button class="pd-action-btn pd-voice" onclick="readPolicyAloud(\''+p.title+'。'+(p.summary||p.content||'').substring(0,200)+'\')">🔊 朗读政策</button></div>';
  document.getElementById('policyDetailContent').innerHTML='<div class="pd-header">'+img+'<div><div class="pd-title">'+p.title+'</div><div class="pd-meta"><span class="p-tag">'+(p.category||'')+'</span> '+(p.effective_date||'')+' '+(p.org||'')+'</div><div class="pd-meta" style="margin-top:4px">文号：'+(p.doc_no||'')+'</div></div></div>'+actionBtns+'<div class="pd-body">'+(p.summary||p.content||'暂无详细内容')+'</div><div id="policyImageResult"></div><div id="policyAudioResult"></div>'+(p.image?'<div style="margin-top:16px;text-align:center"><a href="'+p.image+'" download style="display:inline-block;padding:10px 24px;background:var(--primary);color:#fff;border-radius:8px;text-decoration:none;font-size:14px">📥 下载配图</a></div>':'');
  document.getElementById('policyDetailModal').classList.add('active');
}
function closePolicyDetail(){ document.getElementById('policyDetailModal').classList.remove('active'); }
// ============ 政策配图生成（AI Proxy）============
async function generatePolicyImage(title, category){
  const resultDiv = document.getElementById('policyImageResult');
  if(!resultDiv) return;
  const btn = event.target;
  btn.disabled = true;
  btn.textContent = '🎨 生成中...';
  resultDiv.innerHTML = '<div class="policy-image-loading">⏳ AI正在生成配图，请稍候...</div>';
  try{
    const prompt = '政务政策宣传图，主题：' + title + '，分类：' + (category||'政务') + '，黑金风格，正式庄重，政府办公，高清';
    const resp = await fetch(GOV_API + '/api/gov/image/generate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({prompt: prompt, size: '1024x1024'})
    });
    const data = await resp.json();
    if(data.success && data.task_id){
      // 轮询状态
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        if(attempts > 30){ clearInterval(poll); resultDiv.innerHTML = '<div style="color:#f44;text-align:center;padding:10px">⏰ 生成超时，请稍后重试</div>'; btn.disabled=false; btn.textContent='🎨 生成配图'; return; }
        try{
          const statusResp = await fetch(GOV_API + '/api/gov/image/status', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({task_id: data.task_id})
          });
          const statusData = await statusResp.json();
          if(statusData.status === 'completed' && statusData.image_url){
            clearInterval(poll);
            resultDiv.innerHTML = '<div class="policy-image-result"><img src="' + statusData.image_url + '" alt="政策配图"><div style="margin-top:8px;color:#666;font-size:12px">✅ AI生成配图</div></div>';
            btn.disabled = false;
            btn.textContent = '🎨 重新生成';
          } else if(statusData.status === 'failed'){
            clearInterval(poll);
            resultDiv.innerHTML = '<div style="color:#f44;text-align:center;padding:10px">❌ 生成失败</div>';
            btn.disabled = false;
            btn.textContent = '🎨 生成配图';
          }
        }catch(e){}
      }, 2000);
    } else {
      resultDiv.innerHTML = '<div style="color:#f44;text-align:center;padding:10px">❌ ' + (data.error||'生成失败') + '</div>';
      btn.disabled = false;
      btn.textContent = '🎨 生成配图';
    }
  }catch(e){
    resultDiv.innerHTML = '<div style="color:#f44;text-align:center;padding:10px">❌ 网络错误</div>';
    btn.disabled = false;
    btn.textContent = '🎨 生成配图';
  }
}

// ============ 政策语音朗读（edge-tts免费）============
async function readPolicyAloud(text){
  const audioDiv = document.getElementById('policyAudioResult');
  if(!audioDiv) return;
  const btn = event.target;
  btn.disabled = true;
  btn.textContent = '🔊 合成中...';
  audioDiv.innerHTML = '<div class="policy-image-loading">⏳ 正在合成语音...</div>';
  try{
    const resp = await fetch(GOV_API + '/api/gov/tts/generate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text: text, voice: 'zh-CN-XiaoxiaoNeural'})
    });
    const data = await resp.json();
    if(data.status === 'generated' && data.audio_url){
      const audioUrl = data.audio_url.startsWith('http') ? data.audio_url : ('https://huodouai.com' + data.audio_url);
      audioDiv.innerHTML = '<div class="policy-audio-player"><audio controls autoplay src="' + audioUrl + '"></audio><div style="margin-top:8px;color:#666;font-size:12px">✅ 微软神经网络语音合成 | 时长' + (data.duration||'?') + '秒</div></div>';
    } else {
      audioDiv.innerHTML = '<div style="color:#f44;text-align:center;padding:10px">❌ 语音合成失败</div>';
    }
  }catch(e){
    audioDiv.innerHTML = '<div style="color:#f44;text-align:center;padding:10px">❌ 网络错误</div>';
  }
  btn.disabled = false;
  btn.textContent = '🔊 朗读政策';
}


function exportPolicies(){
  if (ops && ops.export) {
    ops.api.get('/api/gov/policy/search?q=').then(data => {
      const list = data.results || [];
      ops.export.exportPolicies(list, 'json');
      showToast('✅ 政策库已导出（' + list.length + '条）');
    });
  }
}

// ============ 办事指南（Guide算子）============
async function loadGuides(){
  try { const data = await ops.api.get('/api/gov/guide/list'); allGuides = data.results||data.guides||[]; renderGuideCategories(); renderGuideList(); }
  catch(e){ document.getElementById('guideList').innerHTML='<div style="text-align:center;padding:40px;color:var(--text2)">加载失败，请稍后重试</div>'; }
}
function renderGuideCategories(){
  const cats=[...new Set(allGuides.map(g=>g.category))];
  const container=document.getElementById('guideCategories');
  let html='<div class="guide-cat active" onclick="filterGuide(this,\'all\')">全部</div>';
  cats.forEach(cat=>{ html+='<div class="guide-cat" onclick="filterGuide(this,\''+cat+'\')">'+cat+'</div>'; });
  container.innerHTML=html;
}
function filterGuide(el,cat){ document.querySelectorAll('.guide-cat').forEach(c=>c.classList.remove('active')); el.classList.add('active'); currentGuideCat=cat; renderGuideList(); }
function renderGuideList(){
  const list=currentGuideCat==='all'?allGuides:allGuides.filter(g=>g.category===currentGuideCat);
  const container=document.getElementById('guideList');
  if(list.length===0){ container.innerHTML='<div style="text-align:center;padding:40px;color:var(--text2)">暂无指南</div>'; return; }
  let html='';
  list.forEach((g,i)=>{
    html+='<div class="guide-step" onclick="showGuideDetail(\''+g.id+'\')" style="cursor:pointer"><div class="step-title"><span class="step-num">'+(i+1)+'</span>'+g.title+'</div><div class="step-content">'+(g.conditions||'')+'</div><div class="step-material">'+(g.materials||[]).slice(0,3).map(m=>'<span>'+m+'</span>').join('')+'</div><div style="margin-top:8px;font-size:12px;color:var(--primary)">点击查看详情 ›</div></div>';
  });
  container.innerHTML=html;
}
function showGuideDetail(id){
  const g=allGuides.find(x=>x.id===id); if(!g)return;
  document.getElementById('guideDetailTitle').textContent=g.title;
  let html='<div style="margin-bottom:16px"><span style="display:inline-block;padding:4px 12px;background:var(--primary);color:#fff;border-radius:12px;font-size:12px">'+g.category+'</span></div>';
  html+='<div style="margin-bottom:12px"><strong>办理条件：</strong>'+(g.conditions||'无')+'</div>';
  html+='<div style="margin-bottom:12px"><strong>所需材料：</strong><ul style="margin:8px 0;padding-left:20px">'+(g.materials||[]).map(m=>'<li>'+m+'</li>').join('')+'</ul></div>';
  html+='<div style="margin-bottom:12px"><strong>办理流程：</strong><ol style="margin:8px 0;padding-left:20px">'+(g.steps||[]).map(s=>'<li>'+s+'</li>').join('')+'</ol></div>';
  html+='<div style="margin-bottom:12px"><strong>办理地点：</strong>'+(g.location||'详见当地政务服务中心')+'</div>';
  html+='<div style="margin-bottom:12px"><strong>联系电话：</strong>'+(g.phone||'12345')+'</div>';
  html+='<div style="margin-bottom:12px"><strong>办理时间：</strong>'+(g.time||'工作日 9:00-17:00')+'</div>';
  html+='<div style="margin-top:20px;padding-top:16px;border-top:1px solid var(--border);display:flex;gap:12px"><button onclick="openAppointmentForm(\''+g.id+'\',\''+g.title.replace(/'/g,"")+'\')" style="flex:1;padding:12px;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:14px;cursor:pointer">📅 立即预约</button><button onclick="closeGuideDetail()" style="padding:12px 24px;background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:8px;font-size:14px;cursor:pointer">关闭</button></div>';
  document.getElementById('guideDetailContent').innerHTML=html;
  document.getElementById('guideDetailModal').classList.add('active');
  if (ops && ops.analytics) ops.analytics.trackFunctionUsage('guide_query');
}
function closeGuideDetail(){ document.getElementById('guideDetailModal').classList.remove('active'); }
// ============ 办事指南多模态 ============
async function generateGuideImage(title, category){
  const resultDiv = document.getElementById('guideImageResult');
  if(!resultDiv) return;
  const btn = event.target;
  btn.disabled = true; btn.textContent = '🎨 生成中...';
  resultDiv.innerHTML = '<div style="text-align:center;padding:16px;color:#666">⏳ AI正在生成配图...</div>';
  try{
    const prompt = '政务办事指南宣传图，事项：' + title + '，分类：' + (category||'政务服务') + '，黑金风格，正式庄重，政务大厅';
    const resp = await fetch(GOV_API + '/api/gov/image/generate', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:prompt,size:'1024x1024'})});
    const data = await resp.json();
    if(data.success && data.task_id){
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        if(attempts > 30){ clearInterval(poll); resultDiv.innerHTML='<div style="color:#f44;text-align:center;padding:10px">⏰ 超时</div>'; btn.disabled=false; btn.textContent='🎨 生成配图'; return; }
        try{
          const sResp = await fetch(GOV_API + '/api/gov/image/status', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task_id:data.task_id})});
          const sData = await sResp.json();
          if(sData.status === 'completed' && sData.image_url){
            clearInterval(poll);
            resultDiv.innerHTML = '<div style="text-align:center;margin-top:12px"><img src="'+sData.image_url+'" style="max-width:100%;border-radius:12px"></div>';
            btn.disabled=false; btn.textContent='🎨 重新生成';
          } else if(sData.status === 'failed'){ clearInterval(poll); resultDiv.innerHTML='<div style="color:#f44;text-align:center;padding:10px">❌ 失败</div>'; btn.disabled=false; btn.textContent='🎨 生成配图'; }
        }catch(e){}
      }, 2000);
    }
  }catch(e){ resultDiv.innerHTML='<div style="color:#f44;text-align:center;padding:10px">❌ 网络错误</div>'; btn.disabled=false; btn.textContent='🎨 生成配图'; }
}
async function readGuideAloud(text){
  const audioDiv = document.getElementById('guideAudioResult');
  if(!audioDiv) return;
  const btn = event.target;
  btn.disabled = true; btn.textContent = '🔊 合成中...';
  audioDiv.innerHTML = '<div style="text-align:center;padding:16px;color:#666">⏳ 正在合成语音...</div>';
  try{
    const resp = await fetch(GOV_API + '/api/gov/tts/generate', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:text.substring(0,500),voice:'zh-CN-XiaoxiaoNeural'})});
    const data = await resp.json();
    if(data.status === 'generated' && data.audio_url){
      const url = data.audio_url.startsWith('http') ? data.audio_url : ('https://huodouai.com' + data.audio_url);
      audioDiv.innerHTML = '<div style="margin-top:12px;padding:12px;background:#f8f9fa;border-radius:10px"><audio controls autoplay src="'+url+'" style="width:100%"></audio></div>';
    } else { audioDiv.innerHTML='<div style="color:#f44;text-align:center;padding:10px">❌ 合成失败</div>'; }
  }catch(e){ audioDiv.innerHTML='<div style="color:#f44;text-align:center;padding:10px">❌ 网络错误</div>'; }
  btn.disabled=false; btn.textContent='🔊 朗读指南';
}


// ============ 办事预约功能 ============
function openAppointmentForm(guideId, guideTitle){
  closeGuideDetail();
  const today = new Date().toISOString().split('T')[0];
  const html = '<div style="margin-bottom:16px"><div style="font-weight:600;margin-bottom:8px">预约事项</div><div style="padding:10px;background:var(--card);border-radius:8px;font-size:14px">'+guideTitle+'</div></div>'+
    '<div style="margin-bottom:16px"><label style="display:block;margin-bottom:6px;font-size:13px">预约人姓名</label><input type="text" id="apptName" placeholder="请输入姓名" style="width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;font-size:14px"></div>'+
    '<div style="margin-bottom:16px"><label style="display:block;margin-bottom:6px;font-size:13px">联系电话</label><input type="tel" id="apptPhone" placeholder="请输入手机号" style="width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;font-size:14px"></div>'+
    '<div style="margin-bottom:16px"><label style="display:block;margin-bottom:6px;font-size:13px">预约日期</label><input type="date" id="apptDate" min="'+today+'" value="'+today+'" style="width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;font-size:14px"></div>'+
    '<div style="margin-bottom:16px"><label style="display:block;margin-bottom:6px;font-size:13px">预约时段</label><select id="apptTime" style="width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;font-size:14px"><option value="09:00-10:00">09:00-10:00</option><option value="10:00-11:00">10:00-11:00</option><option value="11:00-12:00">11:00-12:00</option><option value="14:00-15:00">14:00-15:00</option><option value="15:00-16:00">15:00-16:00</option><option value="16:00-17:00">16:00-17:00</option></select></div>'+
    '<div style="margin-bottom:16px"><label style="display:block;margin-bottom:6px;font-size:13px">备注（选填）</label><textarea id="apptRemark" rows="2" placeholder="特殊需求说明" style="width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;font-size:14px;resize:none"></textarea></div>'+
    '<div style="display:flex;gap:12px"><button onclick="submitAppointment(\''+guideId+'\',\''+guideTitle.replace(/'/g,"")+'\')" style="flex:1;padding:12px;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:14px;cursor:pointer">确认预约</button><button onclick="closeAppointmentForm()" style="padding:12px 24px;background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:8px;font-size:14px;cursor:pointer">取消</button></div>';
  document.getElementById('appointmentFormContent').innerHTML = html;
  document.getElementById('appointmentModal').classList.add('active');
}
function closeAppointmentForm(){ document.getElementById('appointmentModal').classList.remove('active'); }
async function submitAppointment(guideId, guideTitle){
  const name = document.getElementById('apptName').value.trim();
  const phone = document.getElementById('apptPhone').value.trim();
  const date = document.getElementById('apptDate').value;
  const time = document.getElementById('apptTime').value;
  const remark = document.getElementById('apptRemark').value.trim();
  if(!name){ alert('请输入预约人姓名'); return; }
  if(!phone || !/^1[3-9]\d{9}$/.test(phone)){ alert('请输入正确的手机号'); return; }
  try {
    const res = await fetch(GOV_API_BASE+'/api/gov/appointments/create', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({user_id:getUserId(), guide_id:guideId, guide_title:guideTitle, name, phone, date, time_slot:time, remark})
    });
    const data = await res.json();
    if(data.ok){
      closeAppointmentForm();
      showToast('✅ 预约成功！预约号：'+data.appointment.id);
      updateAppointmentCount();
      // 记录用户行为
      fetch(GOV_API_BASE+'/api/gov/user-actions/record', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:getUserId(),action_type:'appointment',target_id:guideId,target_type:'guide'})}).catch(()=>{});
    } else {
      alert('预约失败，请重试');
    }
  } catch(e) {
    alert('网络错误，预约失败');
  }
}
async function getAppointments(){
  try {
    const res = await fetch(GOV_API_BASE+'/api/gov/appointments?user_id='+getUserId());
    const data = await res.json();
    return data.appointments || [];
  } catch(e){ return []; }
}
async function updateAppointmentCount(){
  const list = await getAppointments();
  const el = document.getElementById('apptCount');
  if(el) el.textContent = list.length+'条预约';
}
async function showAppointmentList(){
  const list = await getAppointments();
  const html = list.length===0 ? '<div style="text-align:center;padding:40px;color:var(--text2)">暂无预约记录</div>' :
    list.map(a=>'<div style="padding:12px;border-bottom:1px solid var(--border)"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px"><span style="font-weight:600;font-size:14px">'+(a.guide_title||a.guideTitle)+'</span><span style="font-size:11px;padding:2px 8px;background:#e6f4ea;color:#52c41a;border-radius:10px">'+(a.status==='pending'?'待确认':a.status)+'</span></div><div style="font-size:12px;color:var(--text2)">预约人：'+a.name+' | '+a.phone+'</div><div style="font-size:12px;color:var(--text2);margin-top:4px">时间：'+a.date+' '+(a.time_slot||a.time)+'</div><div style="font-size:10px;color:#999;margin-top:4px">预约号：'+a.id+'</div></div>').join('');
  document.getElementById('favListContent').innerHTML = html;
  document.getElementById('favModal').querySelector('.modal-header span').textContent = '我的预约';
  document.getElementById('favModal').classList.add('active');
}

// ============ 合规审查（Compliance算子）============
function runComplianceCheck(){
  const input = document.getElementById('complianceInput').value.trim();
  if (!input) { alert('请输入需要审查的内容'); return; }
  const resultDiv = document.getElementById('complianceResult');

  if (ops && ops.compliance) {
    const result = ops.compliance.review({content: input, content_type: 'text'});
    if (result.success) {
      const c = result.compliance;
      let html = '<div class="compliance-result ' + (c.blocked ? 'block' : (c.risk_level === 'low' || c.risk_level === 'pass' ? 'pass' : 'warning')) + '">';
      html += '<strong>审查结果：</strong>' + (c.passed ? '✅ 通过' : (c.blocked ? '❌ 已拦截' : '⚠️ 有风险')) + '<br>';
      html += '<strong>风险等级：</strong>' + c.risk_level + '<br>';
      html += '<strong>风险评分：</strong>' + (c.risk_score * 100).toFixed(0) + '%<br>';
      html += '<strong>问题数量：</strong>' + c.total_issues + '个<br>';
      if (c.sensitive_words && (c.sensitive_words.high.length + c.sensitive_words.medium.length + c.sensitive_words.low.length > 0)) {
        html += '<strong>敏感词：</strong>高:' + c.sensitive_words.high.length + ' 中:' + c.sensitive_words.medium.length + ' 低:' + c.sensitive_words.low.length + '<br>';
      }
      if (c.classified_content && c.classified_content.length > 0) {
        html += '<strong>涉密内容：</strong>' + c.classified_content.length + '项<br>';
      }
      if (c.language_issues && c.language_issues.length > 0) {
        html += '<strong>用语问题：</strong>' + c.language_issues.length + '项<br>';
        c.language_issues.forEach(issue => {
          html += '  • ' + issue.message + '<br>';
        });
      }
      if (c.suggestions && c.suggestions.length > 0) {
        html += '<strong>建议：</strong><br>';
        c.suggestions.forEach(s => { html += '  • ' + s + '<br>'; });
      }
      html += '</div>';
      resultDiv.innerHTML = html;

      // 高风险自动创建复核工单
      if (c.blocked && ops.review) {
        ops.review.createWorkOrder({
          content: input.substring(0, 200),
          risk_info: {risk_level: c.risk_level},
          source: 'compliance',
          user_id: 'anonymous'
        });
      }
    }
  }
  if (ops && ops.analytics) ops.analytics.trackFunctionUsage('compliance_check');
}

// ============ 运营统计（Analytics算子）============
function refreshAnalytics(){
  if (ops && ops.analytics) {
    const overview = ops.analytics.getOverview();
    document.getElementById('statPV').textContent = overview.total_pv;
    document.getElementById('statUV').textContent = overview.total_uv;
    document.getElementById('statChat').textContent = overview.total_sessions;
    document.getElementById('statSession').textContent = overview.total_sessions;

    const funcRanking = ops.analytics.getFunctionRanking();
    const container = document.getElementById('functionRanking');
    if (funcRanking.length > 0) {
      container.innerHTML = funcRanking.map((f, i) =>
        '<div class="quick-item"><div class="q-icon">' + (i+1) + '</div><div class="q-info"><div class="q-title">' + f.function + '</div><div class="q-desc">使用' + f.count + '次</div></div></div>'
      ).join('');
    } else {
      container.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text2)">暂无数据</div>';
    }
  }
}

function exportAnalyticsReport(){
  if (ops && ops.export && ops.analytics) {
    const report = ops.analytics.generateReport();
    ops.export.exportToJSON(report, '政务运营报表');
    showToast('✅ 运营报表已导出');
  }
}

// ============ 个人中心（User算子 + Notification消息）============
function loadProfileData(){
  document.getElementById('histCount').textContent=ops.user.getHistory().length+'条记录';
  document.getElementById('draftCount').textContent=ops.user.getDrafts().length+'篇草稿';
  updateFavCount(); updateAppointmentCount();
  fetch(GOV_API_BASE+'/api/notifications/unread-count?user_id='+getUserId()).then(r=>r.json()).then(d=>{
    document.getElementById('notifyCount').textContent = (d.unread_count||0) + '条未读';
  }).catch(()=>{});
}

function showHistoryList(){
  const hist=ops.user.getHistory().slice().reverse(); const container=document.getElementById('historyListContent');
  container.innerHTML = hist.length===0 ? '<div style="text-align:center;padding:40px;color:var(--text2)">暂无咨询记录</div>' :
    hist.map(msg=>{ const isUser=msg.role==='user'; const time=new Date(msg.time||Date.now()).toLocaleString('zh-CN'); return '<div style="padding:12px;border-bottom:1px solid #eee"><div style="font-size:12px;color:var(--text2);margin-bottom:4px">'+(isUser?'👤 我':'🤖 AI')+' · '+time+'</div><div style="font-size:14px;color:var(--text1)">'+(msg.content||'').substring(0,100)+((msg.content||'').length>100?'...':'')+'</div></div>'; }).join('');
  document.getElementById('historyModal').classList.add('active');
}

function showDraftList(){
  const drafts=ops.user.getDrafts().slice().reverse(); const container=document.getElementById('draftListContent');
  container.innerHTML = drafts.length===0 ? '<div style="text-align:center;padding:40px;color:var(--text2)">暂无公文草稿</div>' :
    drafts.map((d,i)=>{ const time=new Date(d.time||Date.now()).toLocaleString('zh-CN'); return '<div style="padding:12px;border-bottom:1px solid #eee;cursor:pointer" onclick="viewDraft('+i+')"><div style="font-size:14px;font-weight:600;margin-bottom:4px">'+(d.title||'未命名公文')+'</div><div style="font-size:12px;color:var(--text2)">'+time+'</div><div style="font-size:12px;color:var(--text2);margin-top:4px">'+(d.content||'').substring(0,80)+'...</div></div>'; }).join('');
  document.getElementById('draftModal').classList.add('active');
}

function viewDraft(index){
  const drafts = ops.user.getDrafts().slice().reverse();
  const d = drafts[index];
  if (d) {
    document.getElementById('draftModal').classList.remove('active');
    switchPage('doc');
    document.getElementById('docInput').value = d.title;
    document.getElementById('docResult').style.display = 'block';
    document.getElementById('docResult').textContent = d.content;
  }
}

async function showFavList(){
  try {
    const res = await fetch(GOV_API_BASE+'/api/gov/favorites?user_id='+getUserId());
    const data = await res.json();
    const favs = data.favorites || [];
    const container=document.getElementById('favListContent');
    container.innerHTML = favs.length===0 ? '<div style="text-align:center;padding:40px;color:var(--text2)">暂无收藏</div>' :
      favs.map(f=>'<div style="padding:12px;border-bottom:1px solid #eee;cursor:pointer" onclick="viewPolicyDetail(\''+(f.policy_id||f.id)+'\')"><div style="font-size:14px;font-weight:600">'+(f.title||f.policy_id)+'</div><div style="font-size:11px;color:var(--text2);margin-top:2px"><span class="p-tag">'+(f.category||'')+'</span></div></div>').join('');
    document.getElementById('favModal').classList.add('active');
  } catch(e) {
    document.getElementById('favListContent').innerHTML = '<div style="text-align:center;padding:40px;color:var(--text2)">加载失败</div>';
    document.getElementById('favModal').classList.add('active');
  }
}

async function showNotifications(){
  try {
    const res = await fetch(GOV_API_BASE+'/api/notifications/list?user_id='+getUserId()+'&limit=20');
    const data = await res.json();
    const messages = data.notifications || [];
    const container = document.getElementById('notifyListContent');
    const header = '<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 12px;border-bottom:1px solid #eee;background:#f9fafb"><span style="font-size:13px;color:#666">共'+messages.length+'条</span><button onclick="markAllNotifyRead()" style="background:none;border:none;color:#3b82f6;font-size:12px;cursor:pointer">全部已读</button></div>';
    container.innerHTML = header + (messages.length === 0 ? '<div style="text-align:center;padding:40px;color:var(--text2)">暂无消息</div>' :
      messages.map(m => '<div style="padding:12px;border-bottom:1px solid #eee;cursor:pointer" onclick="markNotifyRead(\'' + m.id + '\')"><div style="font-size:14px;font-weight:600;margin-bottom:4px">'+m.icon+' ' + m.title + (m.read ? '' : ' <span style="color:var(--danger);font-size:10px">未读</span>') + '</div><div style="font-size:12px;color:var(--text2)">' + m.content + '</div><div style="font-size:10px;color:var(--text3);margin-top:4px">' + new Date(m.created_at).toLocaleString('zh-CN') + '</div></div>').join(''));
    document.getElementById('notifyModal').classList.add('active');
  } catch(e) {
    document.getElementById('notifyListContent').innerHTML = '<div style="text-align:center;padding:40px;color:var(--text2)">加载失败</div>';
    document.getElementById('notifyModal').classList.add('active');
  }
}

async function markNotifyRead(messageId){
  try {
    await fetch(GOV_API_BASE+'/api/notifications/read', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:messageId,user_id:getUserId()})});
  } catch(e){}
  updateNotifyBadge();
  showNotifications();
}

async function markAllNotifyRead(){
  try {
    await fetch(GOV_API_BASE+'/api/notifications/read-all', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:getUserId()})});
  } catch(e){}
  updateNotifyBadge();
  showNotifications();
}

async function updateNotifyBadge(){
  try {
    const res = await fetch(GOV_API_BASE+'/api/notifications/unread-count?user_id='+getUserId());
    const data = await res.json();
    const count = data.unread_count || 0;
    const badge = document.getElementById('notifyBadge');
    if (count > 0) {
      badge.style.display = 'flex';
      badge.textContent = count > 99 ? '99+' : count;
    } else {
      badge.style.display = 'none';
    }
  } catch(e) {}
}

function showOperatorInfo(){
  if (ops) {
    const info = GovOperators.getInfo();
    alert('政务中台算子库信息\n\n版本：' + info.version + '\n算子总数：' + info.total + '个\n\n基础设施：' + info.infrastructure.join('、') + '\n核心功能：' + info.core.join('、') + '\n合规治理：' + info.governance.join('、') + '\n业务闭环：' + info.business.join('、') + '\n运营完善：' + info.operations.join('、') + '\n\nP3补齐算子：全部完成 ✅');
  }
}

// ============ 工具函数 ============
function showToast(msg){
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2000);
}

// 页面卸载时记录会话结束
window.addEventListener('beforeunload', function() {
  if (ops && ops.analytics) ops.analytics.trackSessionEnd();
});

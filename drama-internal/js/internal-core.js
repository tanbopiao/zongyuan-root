// 昆仑洞天短剧生产内部控制台 - 核心逻辑
// 全免费模式：zhipu + agnes + siliconflow + ollama
// 付费模型一律禁用

const API_BASE = '/ai-proxy';  // 通过Nginx反代到8021
const FREE_MODELS = ['zhipu','agnes','siliconflow','ollama-local'];
const PAID_MODELS_DISABLED = ['doubao','kimi','hunyuan','aliyun','seedance','seedream','wanxiang'];

// 通用API调用（强制免费模式）
async function apiCall(endpoint, data={}, method='POST'){
  try{
    const opts = {
      method: method,
      headers: {'Content-Type':'application/json'}
    };
    if(method==='POST') opts.body = JSON.stringify({...data, mode:'public', paywall_approved:false});
    const resp = await fetch(`${API_BASE}${endpoint}`, opts);
    return await resp.json();
  }catch(e){
    return {error: e.message};
  }
}

// 文本生成（免费优先）
async function generateText(prompt, maxTokens=800){
  return await apiCall('/chat', {
    message: prompt,
    model: 'auto',  // auto走智能路由，优先免费
    mode: 'public',
    max_tokens: maxTokens
  });
}

// 图片生成（Agnes免费）
async function generateImage(prompt, ratio='9:16'){
  return await apiCall('/image/generate', {
    prompt: prompt,
    ratio: ratio,
    mode: 'public',
    provider: 'agnes'  // 强制Agnes免费
  });
}

// 视频生成（Agnes免费）
async function generateVideo(prompt, duration=10, ratio='9:16'){
  return await apiCall('/video/generate', {
    prompt: prompt,
    duration: duration,
    ratio: ratio,
    mode: 'public',
    provider: 'agnes'  // 强制Agnes免费
  });
}

// TTS配音（edge-tts免费）
async function generateTTS(text, voice='zh-CN-XiaoxiaoNeural'){
  return await apiCall('/tts/generate', {
    text: text,
    voice: voice
  });
}

// 批量提交
async function submitBatch(prompts, template='gufeng'){
  return await apiCall('/batch/submit', {
    prompts: prompts,
    template: template
  });
}

// 轮询任务状态
async function pollTask(taskId, type='image', interval=3000, timeout=300000){
  const endpoint = type==='image' ? '/image/status' : '/video/status';
  const start = Date.now();
  return new Promise((resolve)=>{
    const check = async ()=>{
      const result = await apiCall(`${endpoint}?task_id=${taskId}`, {}, 'GET');
      if(result.status==='completed' || result.status==='failed'){
        resolve(result);
        return;
      }
      if(Date.now()-start > timeout){
        resolve({status:'timeout', task_id:taskId});
        return;
      }
      setTimeout(check, interval);
    };
    check();
  });
}

// 工具函数
function formatTime(ts){
  return new Date(ts*1000).toLocaleString();
}

function downloadFile(url, filename){
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
}

console.log('[内部控制台] core.js 已加载，全免费模式');

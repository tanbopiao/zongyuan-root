#!/usr/bin/env python3
"""修改轻量化战略V2网页：对话面板接入真实API"""
import re

html_path = "/home/user/Doubao/chats/38437458338949122/lightweight-strategy-v2.html"

with open(html_path, encoding="utf-8") as f:
    content = f.read()

# 替换sendMessage函数
old_send = """// 发送消息
function sendMessage(){
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if(!text) return;
  addMessage(text,'user');
  input.value = '';
  setTimeout(()=>{
    let reply = agentKnowledge['default'];
    for(const key in agentKnowledge){
      if(key !== 'default' && text.includes(key.replace(/？/g,''))){
        reply = agentKnowledge[key];
        break;
      }
    }
    addMessage(reply,'agent');
  },800);
}"""

new_send = """// 发送消息（接入真实AI API）
async function sendMessage(){
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if(!text) return;
  addMessage(text,'user');
  input.value = '';
  
  // 显示思考中状态
  const thinkingId = 'thinking-' + Date.now();
  addMessage('智能体正在思考...','agent');
  const thinkingEl = document.getElementById('chatMessages').lastElementChild;
  thinkingEl.id = thinkingId;
  thinkingEl.style.opacity = '0.6';
  
  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text, model: 'doubao'})
    });
    const data = await resp.json();
    thinkingEl.remove();
    if(data.result){
      addMessage(data.result, 'agent');
    } else {
      fallbackReply(text);
    }
  } catch(e) {
    thinkingEl.remove();
    fallbackReply(text);
  }
}

// API不可用时的知识库fallback
function fallbackReply(text){
  let reply = agentKnowledge['default'];
  for(const key in agentKnowledge){
    if(key !== 'default' && text.includes(key.replace(/？/g,''))){
      reply = agentKnowledge[key];
      break;
    }
  }
  addMessage(reply,'agent');
}"""

content = content.replace(old_send, new_send)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 对话面板已接入真实API")
print("  - API端点: /api/chat (Nginx反代到8021 ai_proxy)")
print("  - 智能路由: 豆包/智谱/硅基流动/阿里云/Kimi等8个免费API")
print("  - Fallback: API不可用时使用预设知识库")
print("  - 思考中状态: 显示加载提示")

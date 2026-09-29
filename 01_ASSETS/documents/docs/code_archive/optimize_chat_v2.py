#!/usr/bin/env python3
"""修改网页：注入体系约束system prompt + 前端缓存 + 效率优化"""

html_path = "/home/user/Doubao/chats/38437458338949122/lightweight-strategy-v2.html"

with open(html_path, encoding="utf-8") as f:
    content = f.read()

# 1. 在agentKnowledge之后添加体系约束常量和缓存
old_knowledge_end = """  'default': '感谢您的提问！我是元极恒一智能体，正在持续学习和进化中。您可以点击下方快捷问题了解更多，或者访问火斗云智AIOS官网获取完整信息。Ω₀⊂⊙∞⊂Ω'
};"""

new_knowledge_end = """  'default': '感谢您的提问！我是火斗云智AIOS智能体，正在持续学习和进化中。您可以点击下方快捷问题了解更多，或者访问官网获取完整信息。Ω₀⊂⊙∞⊂Ω'
};

// 体系前置约束（注入所有AI调用，禁止通用大模型自由发挥）
const SYSTEM_CONSTRAINT = `你是火斗云智AIOS官方智能体，必须严格遵守以下约束：
1. 对外品牌统一使用"火斗云智AIOS"或"火斗云智系统"，内部体系为ZONGYUAN-ROOT元极恒一自治体系
2. 核心理念：轻量化优先（单HTML≤50KB即开即用）、网页即智能体身体（Webpage-as-Agent-Body）
3. 确权标识：DID-BR-000002，溯源标识：Ω₀⊂⊙∞⊂Ω
4. 回答简洁专业，结构化输出，不超过200字，禁止冗余客套
5. 禁止提及昆仑洞天、短剧创作、东方神女等无关内容（除非用户主动询问）
6. 零成本运行，所有能力基于免费API和本地算力
7. 高阶智能态：以最优稳态为决策准则，主动给出建设性建议`;

// 前端缓存（常见问题5分钟缓存，减少重复API调用）
const chatCache = new Map();
const CACHE_TTL = 5 * 60 * 1000;`;

content = content.replace(old_knowledge_end, new_knowledge_end)

# 2. 修改sendMessage函数，添加system约束+force_model+缓存
old_send = """// 发送消息（接入真实AI API）
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
}"""

new_send = """// 发送消息（真实AI + 体系约束 + 前端缓存 + 效率优化）
async function sendMessage(){
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if(!text) return;
  addMessage(text,'user');
  input.value = '';
  
  // 检查缓存
  const cacheKey = text.toLowerCase().trim();
  const cached = chatCache.get(cacheKey);
  if(cached && Date.now() - cached.time < CACHE_TTL){
    setTimeout(()=>addMessage(cached.reply, 'agent'), 300);
    return;
  }
  
  // 显示思考中状态
  addMessage('智能体正在思考...','agent');
  const thinkingEl = document.getElementById('chatMessages').lastElementChild;
  thinkingEl.style.opacity = '0.6';
  
  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        message: text,
        system: SYSTEM_CONSTRAINT,
        force_model: 'zhipu',
        max_tokens: 300
      })
    });
    const data = await resp.json();
    thinkingEl.remove();
    if(data.result){
      addMessage(data.result, 'agent');
      // 写入缓存
      chatCache.set(cacheKey, {reply: data.result, time: Date.now()});
      // 缓存上限50条
      if(chatCache.size > 50){
        const firstKey = chatCache.keys().next().value;
        chatCache.delete(firstKey);
      }
    } else {
      fallbackReply(text);
    }
  } catch(e) {
    thinkingEl.remove();
    fallbackReply(text);
  }
}"""

content = content.replace(old_send, new_send)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 网页端已优化")
print("  1. 注入体系前置约束SYSTEM_CONSTRAINT（7条铁律）")
print("  2. force_model: zhipu（glm-4-flash，响应最快的免费模型）")
print("  3. max_tokens: 300（简洁输出，减少延迟）")
print("  4. 前端缓存：常见问题5分钟缓存，上限50条")
print("  5. 缓存命中300ms快速回复")

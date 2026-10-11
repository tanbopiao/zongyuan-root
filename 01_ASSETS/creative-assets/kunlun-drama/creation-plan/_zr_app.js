// AI体验工作台 - 主逻辑
// 直连AI Proxy，支持真实多模型切换+通用prompt

const API_BASE = '/ai-proxy';
const STORAGE_KEY = 'experience_chat_data';
const MAX_HISTORY = 50;

// 状态
let state = {
  chats: [],
  currentChatId: null,
  currentModel: 'zhipu',
  isSending: false
};

// 模型信息（仅保留已验证可用的免费/免费额度模型）
const MODELS = {
  zhipu: { name: '智谱GLM-4-Flash', type: '完全免费' },
  kimi: { name: 'Kimi K2.6', type: '免费额度' },
  doubao: { name: '豆包Seed-1.6', type: '免费额度' },
  agnes: { name: 'Agnes 2.5-Flash', type: '完全免费' },
  siliconflow: { name: 'Qwen2.5-7B', type: '免费额度' }
};

// 初始化
document.addEventListener('DOMContentLoaded', function() {
  loadState();
  renderChatList();
  setupInput();
  if (state.chats.length === 0) {
    showWelcome();
  } else {
    switchChat(state.chats[0].id);
  }
});

// 加载状态
function loadState() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const data = JSON.parse(saved);
      state.chats = data.chats || [];
      state.currentModel = data.currentModel || 'zhipu';
      document.getElementById('modelSelect').value = state.currentModel;
      updateModelTip();
    }
  } catch(e) {
    console.warn('加载状态失败:', e);
  }
}

// 保存状态
function saveState() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      chats: state.chats,
      currentModel: state.currentModel
    }));
  } catch(e) {
    console.warn('保存状态失败:', e);
  }
}

// 新建对话
function newChat() {
  const chat = {
    id: 'chat_' + Date.now(),
    title: '新对话',
    messages: [],
    createdAt: Date.now(),
    model: state.currentModel
  };
  state.chats.unshift(chat);
  state.currentChatId = chat.id;
  saveState();
  renderChatList();
  showWelcome();
  closeSidebar();
}

// 切换对话
function switchChat(chatId) {
  state.currentChatId = chatId;
  const chat = getCurrentChat();
  if (chat) {
    document.getElementById('currentChatTitle').textContent = chat.title;
    renderMessages();
    hideWelcome();
  }
  renderChatList();
  closeSidebar();
}

// 删除对话
function deleteChat(chatId, event) {
  event.stopPropagation();
  state.chats = state.chats.filter(c => c.id !== chatId);
  if (state.currentChatId === chatId) {
    if (state.chats.length > 0) {
      switchChat(state.chats[0].id);
    } else {
      state.currentChatId = null;
      showWelcome();
    }
  }
  saveState();
  renderChatList();
}

// 获取当前对话
function getCurrentChat() {
  return state.chats.find(c => c.id === state.currentChatId);
}

// 渲染对话列表
function renderChatList() {
  const container = document.getElementById('chatListItems');
  if (state.chats.length === 0) {
    container.innerHTML = '<div style="padding:12px;color:var(--text-muted);font-size:12px;text-align:center;">暂无历史对话</div>';
    return;
  }
  container.innerHTML = state.chats.map(chat => `
    <div class="chat-item ${chat.id === state.currentChatId ? 'active' : ''}" onclick="switchChat('${chat.id}')">
      <span style="font-size:14px;">💬</span>
      <span class="chat-item-title">${escapeHtml(chat.title)}</span>
      <span class="chat-item-delete" onclick="deleteChat('${chat.id}', event)">×</span>
    </div>
  `).join('');
}

// 渲染消息
function renderMessages() {
  const chat = getCurrentChat();
  const container = document.getElementById('messages');
  if (!chat || chat.messages.length === 0) {
    container.innerHTML = '';
    return;
  }
  container.innerHTML = chat.messages.map(msg => renderMessage(msg)).join('');
  scrollToBottom();
}

// 渲染单条消息
function renderMessage(msg) {
  const isUser = msg.role === 'user';
  const avatar = isUser ? '👤' : '🤖';
  let content = msg.content;
  // 简单的代码块格式化
  content = content.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
  content = content.replace(/`([^`]+)`/g, '<code>$1</code>');
  content = content.replace(/\n/g, '<br>');
  return `
    <div class="message ${isUser ? 'user' : 'ai'}">
      <div class="message-avatar">${avatar}</div>
      <div class="message-bubble">${content}</div>
    </div>
  `;
}

// 发送消息
async function sendMessage() {
  if (state.isSending) return;
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if (!text) return;

  // 如果没有当前对话，先创建
  if (!state.currentChatId) {
    newChat();
  }

  const chat = getCurrentChat();
  
  // 添加用户消息
  chat.messages.push({ role: 'user', content: text, timestamp: Date.now() });
  
  // 更新标题（第一条消息）
  if (chat.messages.length === 1) {
    chat.title = text.length > 20 ? text.substring(0, 20) + '...' : text;
    document.getElementById('currentChatTitle').textContent = chat.title;
  }

  input.value = '';
  adjustInputHeight();
  hideWelcome();
  renderMessages();
  renderChatList();
  saveState();

  // 显示打字指示器
  showTypingIndicator();
  state.isSending = true;
  updateSendButton();

  try {
    // 调用AI Proxy chat端点（通用prompt+真实多模型）
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        message: text,
        model: state.currentModel,
        prompt_type: 'general'
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    const reply = data.reply || data.result || '抱歉，我暂时无法回答这个问题。';

    // 添加AI回复
    chat.messages.push({ role: 'assistant', content: reply, timestamp: Date.now() });
    saveState();

  } catch(error) {
    console.error('发送失败:', error);
    chat.messages.push({ 
      role: 'assistant', 
      content: `⚠️ 抱歉，服务暂时不可用。错误信息：${error.message}`, 
      timestamp: Date.now() 
    });
  } finally {
    hideTypingIndicator();
    state.isSending = false;
    updateSendButton();
    renderMessages();
  }
}

// 快捷提问
function sendQuickPrompt(text) {
  document.getElementById('chatInput').value = text;
  sendMessage();
}

// 显示打字指示器
function showTypingIndicator() {
  const container = document.getElementById('messages');
  const indicator = document.createElement('div');
  indicator.id = 'typingIndicator';
  indicator.className = 'message ai';
  indicator.innerHTML = `
    <div class="message-avatar">🤖</div>
    <div class="message-bubble">
      <div class="typing-indicator">
        <span></span><span></span><span></span>
      </div>
    </div>
  `;
  container.appendChild(indicator);
  scrollToBottom();
}

// 隐藏打字指示器
function hideTypingIndicator() {
  const indicator = document.getElementById('typingIndicator');
  if (indicator) indicator.remove();
}

// 切换模型
function switchModel(model) {
  state.currentModel = model;
  saveState();
  updateModelTip();
  // 显示提示
  const modelInfo = MODELS[model];
  showToast(`已切换到 ${modelInfo.name}（${modelInfo.type}）`);
}

// 更新模型提示
function updateModelTip() {
  const modelInfo = MODELS[state.currentModel];
  document.getElementById('modelTip').textContent = `当前模型：${modelInfo.name}`;
}

// 清空当前对话
function clearCurrentChat() {
  const chat = getCurrentChat();
  if (!chat) return;
  if (!confirm('确定要清空当前对话吗？')) return;
  chat.messages = [];
  chat.title = '新对话';
  document.getElementById('currentChatTitle').textContent = '新对话';
  saveState();
  renderMessages();
  renderChatList();
  showWelcome();
}

// 导出对话
function exportChat() {
  const chat = getCurrentChat();
  if (!chat || chat.messages.length === 0) {
    showToast('没有可导出的对话');
    return;
  }
  let text = `AI体验工作台 - 对话导出\n`;
  text += `对话标题：${chat.title}\n`;
  text += `导出时间：${new Date().toLocaleString()}\n`;
  text += `模型：${MODELS[chat.model || state.currentModel].name}\n`;
  text += `${'='.repeat(50)}\n\n`;
  chat.messages.forEach(msg => {
    const role = msg.role === 'user' ? '🧑 用户' : '🤖 AI助手';
    text += `${role}\n${msg.content}\n\n`;
  });
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `对话_${chat.title}_${new Date().toISOString().slice(0,10)}.txt`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('对话已导出');
}

// 显示欢迎页
function showWelcome() {
  document.getElementById('welcomePage').style.display = 'flex';
  document.getElementById('chatArea').style.display = 'none';
}

// 隐藏欢迎页
function hideWelcome() {
  document.getElementById('welcomePage').style.display = 'none';
  document.getElementById('chatArea').style.display = 'block';
}

// 设置输入框
function setupInput() {
  const input = document.getElementById('chatInput');
  input.addEventListener('input', adjustInputHeight);
}

// 调整输入框高度
function adjustInputHeight() {
  const input = document.getElementById('chatInput');
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 200) + 'px';
  updateSendButton();
}

// 处理键盘事件
function handleKeyDown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

// 更新发送按钮状态
function updateSendButton() {
  const input = document.getElementById('chatInput');
  const btn = document.getElementById('sendBtn');
  btn.disabled = !input.value.trim() || state.isSending;
}

// 切换侧边栏（移动端）
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('overlay');
  sidebar.classList.toggle('open');
  overlay.classList.toggle('show');
}

// 关闭侧边栏
function closeSidebar() {
  if (window.innerWidth <= 768) {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('overlay').classList.remove('show');
  }
}

// 滚动到底部
function scrollToBottom() {
  const chatArea = document.getElementById('chatArea');
  setTimeout(() => {
    chatArea.scrollTop = chatArea.scrollHeight;
  }, 100);
}

// 显示提示
function showToast(message) {
  const toast = document.createElement('div');
  toast.style.cssText = `
    position: fixed;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: var(--bg-tertiary);
    color: var(--text-primary);
    padding: 12px 24px;
    border-radius: 8px;
    border: 1px solid var(--accent);
    z-index: 1000;
    font-size: 14px;
    animation: fadeIn 0.3s;
  `;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2500);
}

// HTML转义
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// 添加CSS动画
const style = document.createElement('style');
style.textContent = `
  @keyframes fadeIn {
    from { opacity: 0; transform: translateX(-50%) translateY(-10px); }
    to { opacity: 1; transform: translateX(-50%) translateY(0); }
  }
`;
document.head.appendChild(style);

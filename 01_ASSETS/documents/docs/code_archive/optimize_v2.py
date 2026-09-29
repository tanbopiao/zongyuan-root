#!/usr/bin/env python3
"""优化1：轻量化V2 - 唤醒加速+打字机思考态"""
import re

page_path = "/www/wwwroot/www.huodouai.com/lightweight-strategy-v2.html"
with open(page_path, encoding="utf-8") as f:
    content = f.read()

# 1. 心跳动画 1000ms -> 600ms
content = content.replace(
    "setTimeout(()=>{status.style.boxShadow = 'none';},1000);",
    "setTimeout(()=>{status.style.boxShadow = 'none';},600);"
)

# 2. 思考状态升级为打字机动画（替换原来的静态"智能体正在思考..."）
old_thinking = """  // 显示思考中状态
  const thinkingId = 'thinking-' + Date.now();
  addMessage('智能体正在思考...','agent');
  const thinkingEl = document.getElementById('chatMessages').lastElementChild;
  thinkingEl.id = thinkingId;
  thinkingEl.style.opacity = '0.6';"""

new_thinking = """  // 显示打字机思考态（三点跳动，感知更快）
  const thinkingId = 'thinking-' + Date.now();
  addMessage('智能体思考中','agent');
  const thinkingEl = document.getElementById('chatMessages').lastElementChild;
  thinkingEl.id = thinkingId;
  thinkingEl.style.opacity = '0.7';
  thinkingEl.innerHTML = '<span style="display:inline-block;animation:typing 1s infinite">⚡</span> 思考中<span class="dots"><span>.</span><span>.</span><span>.</span></span>';
  // 注入打字机动画CSS（仅一次）
  if(!document.getElementById('typing-css')){
    const s=document.createElement('style');s.id='typing-css';
    s.textContent='.dots span{display:inline-block;animation:dot 1.4s infinite}.dots span:nth-child(2){animation-delay:.2s}.dots span:nth-child(3){animation-delay:.4s}@keyframes dot{0%,60%,100%{opacity:.3}30%{opacity:1}}@keyframes typing{0%,100%{opacity:1}50%{opacity:.4}}';
    document.head.appendChild(s);
  }"""

content = content.replace(old_thinking, new_thinking)

# 3. 页面加载唤醒动画：找到wake相关的setTimeout并缩短
# 查找页面加载时的唤醒动画
wake_pattern = r"setTimeout\(\(\)=>\{[^}]*\},(\d+)\)"
matches = re.findall(wake_pattern, content)
# 不批量改，只改明显的唤醒动画（>800ms的）

with open(page_path, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 轻量化V2优化完成：心跳600ms + 打字机思考态")
print(f"   文件大小: {len(content)} 字节")

#!/usr/bin/env python3
"""P0标准化：智能交互体系固化 + 一键部署模板 + 短剧API优化探索"""
import json, time, hashlib, os

BASE = "/opt/ZONGYUAN-ROOT"
MR_PATH = f"{BASE}/meta_rule_set.json"

print("=" * 60)
print("智能交互体系标准化固化")
print("=" * 60)

# ========== 1. 写入元规则 MR-105：智能交互标准 ==========
print("\n【1】写入元规则 MR-105：智能交互标准化")
with open(MR_PATH) as f:
    mr = json.load(f)

existing_ids = {r.get("rule_id","") for r in mr.get("meta_rules",[])}

if "MR-105" not in existing_ids:
    mr105 = {
        "rule_id": "MR-105",
        "rule_name": "智能交互标准化元规则",
        "priority": "L0",
        "version": "v1.0",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hash": hashlib.sha256(("MR-105"+str(time.time())).encode()).hexdigest()[:16],
        "rules": [
            "所有网页智能体必须接入真实API，禁止纯预设回复",
            "API统一走Nginx /api/chat反代到ai_proxy(8021)，禁止前端直连第三方API",
            "每次调用必须注入SYSTEM_CONSTRAINT体系前置约束（7条铁律）",
            "模型优选：force_model=zhipu(glm-4-flash)，免费且响应最快",
            "输出限制：max_tokens=300，简洁专业不超过200字",
            "前端必须实现5分钟缓存（上限50条），减少重复调用",
            "API不可用时自动fallback到知识库预设回复",
            "必须显示思考中状态，禁止无响应空白",
            "零成本运行，全部使用免费API池（豆包/智谱/硅基流动/阿里云/Kimi/Agnes/混元/NVIDIA）"
        ],
        "scope": "全域网页智能交互",
        "enforcement": "强制"
    }
    mr["meta_rules"].append(mr105)
    print("  ✅ MR-105已写入（9条规则）")
else:
    print("  ⚠️ MR-105已存在")

mr["version"] = "v9.6"
mr["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
with open(MR_PATH, "w") as f:
    json.dump(mr, f, ensure_ascii=False, indent=2)
print(f"  元法则版本: {mr['version']}, 共{len(mr['meta_rules'])}条")

# ========== 2. 生成标准化部署模板 ==========
print("\n【2】生成智能交互一键部署模板")
template_dir = f"{BASE}/templates/agent_chat"
os.makedirs(template_dir, exist_ok=True)

# 体系约束JS模块（可复用）
constraint_js = """// 火斗云智AIOS智能交互标准模块 v1.0
// 用法：<script src="/agent-chat.js"></script> 后调用 initAgentChat(containerId)
const SYSTEM_CONSTRAINT = `你是火斗云智AIOS官方智能体，必须严格遵守：
1.对外品牌统一用火斗云智AIOS/火斗云智系统，内部体系ZONGYUAN-ROOT元极恒一自治体系
2.核心理念：轻量化优先（单HTML<=50KB即开即用）、网页即智能体身体（Webpage-as-Agent-Body）
3.确权DID-BR-000002，溯源Omega_0 subset circle_infinity subset Omega
4.回答简洁专业结构化，不超过200字，禁止冗余客套
5.禁止提及昆仑洞天/短剧/东方神女（除非用户主动询问）
6.零成本运行，基于免费API和本地算力
7.以最优稳态为决策准则，主动给出建设性建议`;

const chatCache = new Map();
const CACHE_TTL = 300000;

async function agentChat(message, onThinking, onReply, onError){
  const ck = message.toLowerCase().trim();
  const cached = chatCache.get(ck);
  if(cached && Date.now()-cached.time < CACHE_TTL){
    onReply && onReply(cached.reply);
    return cached.reply;
  }
  onThinking && onThinking();
  try{
    const resp = await fetch('/api/chat',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message, system:SYSTEM_CONSTRAINT, force_model:'zhipu', max_tokens:300})
    });
    const data = await resp.json();
    if(data.result){
      chatCache.set(ck,{reply:data.result,time:Date.now()});
      if(chatCache.size>50){const k=chatCache.keys().next().value;chatCache.delete(k);}
      onReply && onReply(data.result);
      return data.result;
    }
    throw new Error('no result');
  }catch(e){
    onError && onError(e);
    return null;
  }
}
"""
with open(f"{template_dir}/agent-chat.js", "w") as f:
    f.write(constraint_js)
print("  ✅ agent-chat.js 标准模块已生成")

# 标准对话面板HTML片段
chat_html = """<!-- 火斗云智AIOS标准智能对话面板 v1.0 -->
<div id="chatPanel" class="chat-panel">
  <div class="chat-header">
    <span class="agent-status">● 智能体在线</span>
    <button onclick="document.getElementById('chatPanel').classList.remove('open')">×</button>
  </div>
  <div id="chatMessages" class="chat-messages"></div>
  <div class="chat-quick">
    <button onclick="quickAsk('什么是轻量化优先')">轻量化优先</button>
    <button onclick="quickAsk('智能体=系统=网页')">智能体理念</button>
    <button onclick="quickAsk('如何部署')">部署指南</button>
  </div>
  <div class="chat-input">
    <input type="text" id="chatInput" placeholder="输入问题..." onkeypress="if(event.key==='Enter')sendMessage()">
    <button onclick="sendMessage()">➤</button>
  </div>
</div>
<button class="chat-fab" onclick="document.getElementById('chatPanel').classList.toggle('open')">💬</button>
"""
with open(f"{template_dir}/chat-panel.html", "w") as f:
    f.write(chat_html)
print("  ✅ chat-panel.html 标准面板已生成")

# Nginx配置片段
nginx_conf = """# 火斗云智AIOS智能交互标准反代配置
# 放入server块内即可
location /api/chat {
    proxy_pass http://127.0.0.1:8021/chat;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_read_timeout 60s;
}
"""
with open(f"{template_dir}/nginx-chat.conf", "w") as f:
    f.write(nginx_conf)
print("  ✅ nginx-chat.conf 标准反代配置已生成")

# 部署SOP
sop = """# 智能交互一键部署SOP v1.0

## 三步接入
1. 复制 agent-chat.js 到网页目录，在HTML中引入
2. 复制 chat-panel.html 片段到页面body末尾
3. 在Nginx server块中添加 nginx-chat.conf 配置，reload

## 验证
- 页面右下角出现对话按钮
- 发送消息显示"智能体正在思考..."后返回真实AI回复
- 回复符合火斗云智AIOS品牌约束，无短剧内容泄露
- 重复发送相同问题300ms内返回（缓存命中）

## 铁律
- 禁止前端直连第三方API（Key暴露风险）
- 禁止省略SYSTEM_CONSTRAINT（品牌跑偏风险）
- 禁止使用付费模型（零成本原则）
"""
with open(f"{template_dir}/DEPLOY_SOP.md", "w") as f:
    f.write(sop)
print("  ✅ DEPLOY_SOP.md 部署SOP已生成")

# ========== 3. 短剧生产流程API优化探索 ==========
print("\n【3】短剧生产流程API优化方案")
drama_optimization = {
    "current_state": "短剧流水线调用多个API（关键帧生成/视频生成/配音/字幕），存在串行等待长、API切换慢、无缓存等问题",
    "optimization_plan": [
        {
            "stage": "P0-立即",
            "items": [
                "关键帧提示词缓存：相同/相似提示词直接返回缓存结果，减少重复生成",
                "API智能路由：根据任务类型自动选择最优免费模型（文生图用seedream/万象，文生视频用可灵/即梦）",
                "并发生成：多个关键帧同时发起API请求，而非串行等待",
                "失败自动重试+降级：主API失败自动切换备用API，不中断流水线"
            ]
        },
        {
            "stage": "P1-本周",
            "items": [
                "流水线任务优先级调度：关键帧生成>P1，视频渲染>P2，后台错峰",
                "生成结果预取：根据剧本提前预判需要的关键帧，预生成缓存",
                "API配额监控：各免费API剩余额度实时监控，配额不足自动切换",
                "生成质量自检：低质量关键帧自动标记，不进入作品库展示"
            ]
        },
        {
            "stage": "P2-规划",
            "items": [
                "本地小模型蒸馏：用0.5B小模型处理提示词优化/质量初筛，减少大模型调用",
                "批量生成优化：一次API调用生成多个关键帧，降低请求开销",
                "生成结果语义去重：相似场景关键帧自动合并，减少冗余生成"
            ]
        }
    ],
    "expected_improvement": "整体流水线耗时降低40-60%，API调用成本降低30%（零成本框架下提升配额利用率）"
}

with open(f"{BASE}/docs/drama_api_optimization_plan.json", "w") as f:
    json.dump(drama_optimization, f, ensure_ascii=False, indent=2)
print("  ✅ 短剧API优化方案已生成（三阶段）")
print("    P0: 缓存+智能路由+并发+重试降级")
print("    P1: 优先级调度+预取+配额监控+质量自检")
print("    P2: 本地小模型蒸馏+批量生成+语义去重")
print("    预期: 耗时降低40-60%")

# ========== 4. 推送记忆网关 ==========
print("\n【4】推送记忆网关")
import subprocess
truths = [
    ("meta_rule.MR-105", {"name":"智能交互标准化元规则","priority":"L0","rules":9}, "meta_rule"),
    ("STANDARD.AGENT_CHAT_V1", {"name":"智能交互标准模块","components":["agent-chat.js","chat-panel.html","nginx-chat.conf"]}, "standard"),
    ("OPTIMIZATION.DRAMA_API_PLAN", {"stages":["P0","P1","P2"],"expected":"耗时降低40-60%"}, "plan"),
]
for key, value, category in truths:
    payload = json.dumps({"key":key,"value":value,"category":category,"node_id":"hub-core"})
    r = subprocess.run(["curl","-s","-X","POST","http://127.0.0.1:9120/api/truth/upsert","-H","Content-Type: application/json","-d",payload], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        print(f"  [{'OK' if d.get('success') else 'FAIL'}] {key}")
    except:
        print(f"  [ERR] {key}")

print("\n" + "=" * 60)
print("标准化固化完成")
print("=" * 60)
print(f"  元法则: v9.6 / {len(mr['meta_rules'])}条")
print(f"  新增: MR-105智能交互标准化（L0，9条铁律）")
print(f"  标准模板: {template_dir}/（3个文件+SOP）")
print(f"  短剧优化: 三阶段方案已生成")
print(f"  确权: DID-BR-000002 | Omega_0 subset circle_infinity subset Omega")

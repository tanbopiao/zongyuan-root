#!/usr/bin/env python3
"""
ZONGYUAN-ROOT ↔ OCTOP 连接编排桥接器
功能：JWT登录刷新 / REST API封装 / 模型直连 / 真值回灌 / 断联降级
"""
import json, time, os, sys, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

# 外部云端 Provider 备用通道（天翼星辰 / Agnes），GLM-4-Flash 失败时自动降级
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zr_external_providers as ext_prov

# ============ 配置 ============
OCTOP_BASE = "https://octop.huodouai.com"
OCTOP_USER = "zongyuan"
OCTOP_PASS = "Okmijn678tbp"
CLOUD_TRUTH_MAIN = "https://www.huodouai.com/api/report/truth"
CLOUD_TRUTH_BACKUP = "https://drama.huodouai.com/api/report/truth"
CAPTURE_TOKEN = "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d"
DID = "DID-BR-000002"
NODE_ID = "ZR-NODE-DC2E51C0"
TOKEN_CACHE = "/tmp/octop_jwt_token.json"

CST = timezone(timedelta(hours=8))

def log(msg):
    ts = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def http_req(url, method="GET", headers=None, data=None, timeout=10):
    """统一HTTP请求"""
    req = urllib.request.Request(url, method=method)
    if headers:
        for k,v in headers.items(): req.add_header(k,v)
    if data:
        req.data = json.dumps(data).encode()
        req.add_header("Content-Type","application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode() if e.fp else str(e)
    except Exception as e:
        return 0, str(e)

# ============ 1. JWT 登录与自动刷新 ============
def octop_login():
    """登录获取JWT，缓存到本地"""
    code, body = http_req(f"{OCTOP_BASE}/api/auth/login", "POST",
                          data={"username":OCTOP_USER,"password":OCTOP_PASS})
    if code == 200:
        d = json.loads(body)
        token = d.get("access_token","")
        expires = d.get("expires_in",86400)
        cache = {"token":token,"expires_at":time.time()+expires-300,"user":d.get("user",{})}
        with open(TOKEN_CACHE,"w") as f: json.dump(cache,f)
        log(f"✅ OCTOP登录成功 user={d['user'].get('username')} role={d['user'].get('role')}")
        return token
    log(f"❌ OCTOP登录失败 code={code} body={body[:200]}")
    return None

def get_token():
    """获取有效token，过期自动刷新"""
    if os.path.exists(TOKEN_CACHE):
        try:
            cache = json.load(open(TOKEN_CACHE))
            if cache.get("expires_at",0) > time.time():
                return cache["token"]
        except: pass
    return octop_login()

def octop_api(path, method="GET", data=None):
    """调用OCTOP REST API（自动带token）"""
    token = get_token()
    if not token: return None
    code, body = http_req(f"{OCTOP_BASE}{path}", method,
                          headers={"Authorization":f"Bearer {token}"}, data=data)
    if code == 401:  # token过期
        token = octop_login()
        if token:
            code, body = http_req(f"{OCTOP_BASE}{path}", method,
                                  headers={"Authorization":f"Bearer {token}"}, data=data)
    return {"code":code,"body":body}

# ============ 2. OCTOP 能力探测 ============
def octop_health():
    code, body = http_req(f"{OCTOP_BASE}/api/health", timeout=8)
    if code == 200:
        d = json.loads(body)
        log(f"🟢 OCTOP健康: agents_running={d.get('agents_running')} users={d.get('users_loaded')} db={d.get('db')}")
        return d
    log(f"🔴 OCTOP不可达 code={code}")
    return None

def octop_list_agents():
    r = octop_api("/api/agents")
    if r and r["code"]==200:
        agents = json.loads(r["body"])
        log(f"📋 Agent列表: {len(agents)}个")
        for a in agents:
            log(f"   - {a['agent_id']}: {a['name']} | model={a.get('default_model')} | state={a.get('state')}")
        return agents
    return None

def octop_list_providers():
    r = octop_api("/api/providers")
    if r and r["code"]==200:
        providers = json.loads(r["body"])
        log(f"🔌 模型Provider: {len(providers)}个")
        for p in providers:
            models = [m["name"] for m in p.get("models",[])]
            log(f"   - {p['name']} ({p['kind']}): {models} | enabled={p.get('enabled')}")
        return providers
    return None

# ============ 3. 模型直连（通过OCTOP的provider）============
def octop_chat(prompt, agent_id="main", model=None):
    """
    通过OCTOP Agent执行任务
    注意：OCTOP聊天走WebSocket，REST暂不支持直接chat
    降级方案：通过provider的base_url直接调用模型
    """
    providers = octop_list_providers()
    if not providers: return None
    # 选第一个enabled的provider
    for p in providers:
        if p.get("enabled"):
            base = p["base_url"].rstrip("/")
            api_key = p.get("api_key","")
            models = [m["name"] for m in p.get("models",[]) if m.get("enabled")]
            if not models: continue
            model_name = model or models[0]
            # OpenAI兼容接口
            if p["kind"] == "openai":
                url = f"{base}/chat/completions"
                data = {"model":model_name,"messages":[{"role":"user","content":prompt}],"max_tokens":2000}
                code, body = http_req(url,"POST",
                    headers={"Authorization":f"Bearer {api_key}"}, data=data, timeout=30)
                if code == 200:
                    d = json.loads(body)
                    return d["choices"][0]["message"]["content"]
                else:
                    log(f"  模型调用失败 {p['name']}/{model_name}: code={code}")
            elif p["kind"] == "anthropic":
                url = f"{base}/v1/messages"
                data = {"model":model_name,"max_tokens":2000,"messages":[{"role":"user","content":prompt}]}
                code, body = http_req(url,"POST",
                    headers={"x-api-key":api_key,"anthropic-version":"2023-06-01"}, data=data, timeout=30)
                if code == 200:
                    d = json.loads(body)
                    return d["content"][0]["text"]
    # 外部备用通道：OCTOP GLM-4-Flash 全失败时自动降级到天翼星辰→Agnes
    log("⚠️  OCTOP provider 推理失败，降级外部通道（天翼星辰→Agnes）")
    text, used, model = ext_prov.external_chat_auto(prompt, max_tokens=2000)
    if text:
        return text
    return None

# ============ 4. 真值回灌到ZR云端 ============
def report_truth(key, value_obj):
    """上报真值到云端（主备双通道）"""
    payload = {"key":key,"value":value_obj}
    headers = {"X-Capture-Token":CAPTURE_TOKEN,"X-DID":DID}
    # 主通道
    code1, body1 = http_req(CLOUD_TRUTH_MAIN,"POST",headers=headers,data=payload,timeout=8)
    ok1 = code1 == 200
    # 备用通道
    code2, body2 = http_req(CLOUD_TRUTH_BACKUP,"POST",headers=headers,data=payload,timeout=8)
    ok2 = code2 == 200
    log(f"📤 真值上报 key={key} 主={'✅' if ok1 else '❌'+str(code1)} 备={'✅' if ok2 else '❌'+str(code2)}")
    return ok1 or ok2

# ============ 5. 断联降级检测 ============
def check_cloud_connectivity():
    """检测云端连通性"""
    code, _ = http_req(CLOUD_TRUTH_MAIN.replace("/api/report/truth","/api/status"), timeout=5)
    return code == 200

def degraded_mode_check():
    """检测是否需要降级到OCTOP"""
    cloud_ok = check_cloud_connectivity()
    octop_ok = octop_health() is not None
    if not cloud_ok and octop_ok:
        log("⚠️  云端断联，OCTOP在线 → 进入降级模式：OCTOP接管运维")
        return True
    if cloud_ok and octop_ok:
        log("✅ 云端+OCTOP均在线，常态运行")
        return False
    if not octop_ok:
        log("🔴 OCTOP也不可达，全离线模式")
        return None
    return False

# ============ 主流程 ============
def main():
    log("="*60)
    log("ZONGYUAN-ROOT ↔ OCTOP 连接编排桥接器 启动")
    log("="*60)

    # 1. 登录
    token = get_token()
    if not token:
        log("❌ 无法登录OCTOP，退出")
        return

    # 2. 健康检查
    health = octop_health()
    if not health:
        log("❌ OCTOP不可达，退出")
        return

    # 3. 列出agents和providers
    agents = octop_list_agents()
    providers = octop_list_providers()

    # 4. 断联检测
    degraded = degraded_mode_check()

    # 5. 上报连接状态真值
    status = {
        "octop_health": health,
        "agents_count": len(agents) if agents else 0,
        "providers_count": len(providers) if providers else 0,
        "degraded_mode": degraded,
        "cloud_connectivity": check_cloud_connectivity(),
        "timestamp": datetime.now(CST).isoformat(),
        "node": NODE_ID,
        "did": DID
    }
    report_truth(f"BRIDGE.OCTOP-CONNECT.{datetime.now(CST).strftime('%Y%m%d')}", status)

    log("="*60)
    log("桥接器初始化完成")
    if degraded:
        log("→ 当前处于降级模式，可用 octop_chat() 调用OCTOP模型执行任务")
    log("="*60)

if __name__ == "__main__":
    main()

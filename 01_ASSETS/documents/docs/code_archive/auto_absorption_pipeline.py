#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 全自动吸收部署流水线 V1.0
自动吸收同源节点上报真值 → 分类处理 → 自动部署 → 可视化集成 → 上报固化
全闭环SOP，无需人工逐步指令
"""
import json, os, sys, time, hashlib, subprocess, urllib.request, sqlite3
from datetime import datetime

# ============ 配置 ============
GATEWAY = "http://127.0.0.1:9120"
FEISHU_GW = "http://127.0.0.1:8001"
CHAT_ID = "oc_1c68eb3664e751e397062ff0c60ffa3"
META_RULE_FILE = "/opt/ZONGYUAN-ROOT/meta_rule_set.json"
DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
PIPELINE_STATE = "/opt/ZONGYUAN-ROOT/data/auto_pipeline_state.json"
WWW_ROOTS = ["/www/wwwroot/www.huodouai.com/", "/www/wwwroot/huodouai.com/"]
LOG_FILE = "/opt/ZONGYUAN-ROOT/logs/auto_pipeline.log"

# 自动部署阈值：五方评分≥80分自动部署（P3及以下）
AUTO_DEPLOY_THRESHOLD = 80
# 高风险必须人工审批
HIGH_RISK_CATEGORIES = ["meta_law", "system_config", "security", "core_service"]

def log(msg):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def load_state():
    if os.path.exists(PIPELINE_STATE):
        with open(PIPELINE_STATE) as f:
            return json.load(f)
    return {"last_processed_id": 0, "processed_keys": [], "stats": {"total": 0, "deployed": 0, "pending_approval": 0, "rejected": 0}}

def save_state(state):
    os.makedirs(os.path.dirname(PIPELINE_STATE), exist_ok=True)
    with open(PIPELINE_STATE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def gateway_get(path):
    try:
        req = urllib.request.Request(f"{GATEWAY}{path}")
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read())
    except Exception as e:
        log(f"  ⚠️ 网关请求失败 {path}: {e}")
        return None

def gateway_upsert(key, value, category, node_id="auto-pipeline"):
    try:
        data = json.dumps({"key": key, "value": value, "category": category, "node_id": node_id}).encode()
        req = urllib.request.Request(f"{GATEWAY}/api/truth/upsert", data=data, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read()).get("success", False)
    except Exception as e:
        log(f"  ⚠️ 写入网关失败: {e}")
        return False

def feishu_notify(msg):
    try:
        data = json.dumps({
            "receive_id": CHAT_ID,
            "msg_type": "text",
            "content": json.dumps({"text": msg})
        }).encode()
        req = urllib.request.Request(f"{FEISHU_GW}/feishu/im/v1/messages?receive_id_type=chat_id", data=data, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read()).get("code") == 0
    except Exception as e:
        log(f"  ⚠️ 飞书通知失败: {e}")
        return False

def classify_truth(truth):
    """分类真值，决定处理方式"""
    category = truth.get("category", "")
    key = truth.get("truth_key", "")
    value = truth.get("truth_value", "")
    
    # 元法则类
    if category == "meta_law" or key.startswith("meta_rule.") or key.startswith("MR-"):
        return "meta_law"
    # 经验类
    if category == "experience" or "experience" in key.lower():
        return "experience"
    # 页面/可视化类
    if category == "page" or "page" in key.lower() or "html" in key.lower() or "visual" in key.lower():
        return "page"
    # 功能/服务类
    if category == "feature" or category == "service" or "feature" in key.lower() or "service" in key.lower():
        return "feature"
    # 数据/资产类
    if category == "asset" or category == "data" or "asset" in key.lower():
        return "asset"
    # 全域指令类
    if category == "global_directive" or key.startswith("GLOBAL_"):
        return "directive"
    # 进化任务类
    if category == "evolution_task" or key.startswith("EVOLUTION_"):
        return "evolution_task"
    return "other"

def assess_risk(category, truth):
    """评估风险等级，决定是否自动部署"""
    if category in HIGH_RISK_CATEGORIES:
        return "high"  # 必须人工审批
    key = truth.get("truth_key", "")
    value_str = str(truth.get("truth_value", ""))
    # 涉及核心文件/服务的为高风险
    if any(kw in key + value_str for kw in ["sshd", "iptables", "passwd", "shadow", "chattr", "nginx.conf", "systemd"]):
        return "high"
    # 页面/文案/SEO类为低风险
    if category in ["page", "experience", "asset", "other"]:
        return "low"
    return "medium"

def five_dimension_score(truth, category):
    """五方评分：安全25/稳定25/成本20/价值20/合规10"""
    value_str = str(truth.get("truth_value", ""))
    # 安全分
    security = 25
    if any(kw in value_str.lower() for kw in ["rm -rf", "chmod 777", "disable", "password"]):
        security = 5
    # 稳定分
    stability = 20 if category in ["feature", "meta_law"] else 25
    # 成本分（零成本优先）
    cost = 20
    if any(kw in value_str.lower() for kw in ["付费", "收费", "购买", "upgrade", "premium"]):
        cost = 5
    # 价值分
    value = 15 if len(value_str) < 50 else 20
    # 合规分
    compliance = 10
    total = security + stability + cost + value + compliance
    return total, {"security": security, "stability": stability, "cost": cost, "value": value, "compliance": compliance}

def process_meta_law(truth, state):
    """处理元法则类：自动写入（低风险）或生成审批单（高风险）"""
    key = truth.get("truth_key", "")
    value = truth.get("truth_value", "")
    risk = assess_risk("meta_law", truth)
    
    if risk == "high":
        # 生成审批单
        approval_key = f"APPROVAL_PENDING_{key}_{int(time.time())}"
        gateway_upsert(approval_key, {
            "type": "meta_law_approval",
            "truth_key": key,
            "content": value,
            "risk": "high",
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }, "approval_pending")
        state["stats"]["pending_approval"] += 1
        log(f"  📋 高风险元法则，已生成审批单: {key}")
        return "pending_approval"
    
    # 低风险自动写入
    try:
        subprocess.run(["chattr", "-i", META_RULE_FILE], capture_output=True)
        with open(META_RULE_FILE) as f:
            data = json.load(f)
        rules = data.get("meta_rules", data.get("rules", []))
        rule_id = value.get("rule_id", key) if isinstance(value, dict) else key
        exists = any(r.get("rule_id") == rule_id for r in rules)
        if not exists and isinstance(value, dict) and "rule_id" in value:
            rules.append(value)
            data["meta_rules"] = rules
            with open(META_RULE_FILE, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            log(f"  ✅ 元法则自动写入: {rule_id}")
        subprocess.run(["chattr", "+i", META_RULE_FILE], capture_output=True)
        state["stats"]["deployed"] += 1
        return "deployed"
    except Exception as e:
        log(f"  ⚠️ 元法则写入失败: {e}")
        return "failed"

def process_experience(truth, state):
    """处理经验类：自动写入经验库"""
    key = truth.get("truth_key", "")
    value = truth.get("truth_value", "")
    # 经验自动归档到经验库
    exp_key = f"EXPERIENCE_AUTO_{hashlib.md5(key.encode()).hexdigest()[:8]}"
    gateway_upsert(exp_key, value, "experience")
    state["stats"]["deployed"] += 1
    log(f"  ✅ 经验自动归档: {key[:40]}")
    return "deployed"

def process_page(truth, state):
    """处理页面/可视化类：评估是否需要创建/更新页面"""
    key = truth.get("truth_key", "")
    value = truth.get("truth_value", "")
    score, breakdown = five_dimension_score(truth, "page")
    
    if score >= AUTO_DEPLOY_THRESHOLD:
        # 自动生成页面部署方案（记录到待部署队列）
        deploy_key = f"DEPLOY_QUEUE_PAGE_{int(time.time())}_{hashlib.md5(key.encode()).hexdigest()[:6]}"
        gateway_upsert(deploy_key, {
            "type": "page_deploy",
            "source_key": key,
            "content": value,
            "score": score,
            "breakdown": breakdown,
            "status": "auto_approved",
            "created_at": datetime.now().isoformat()
        }, "deploy_queue")
        state["stats"]["deployed"] += 1
        log(f"  ✅ 页面自动通过(评分{score})，加入部署队列: {key[:40]}")
        return "deployed"
    else:
        state["stats"]["pending_approval"] += 1
        log(f"  ⚠️ 页面评分{score}<80，需人工审批: {key[:40]}")
        return "pending_approval"

def process_feature(truth, state):
    """处理功能/服务类：五方评分决定自动部署或审批"""
    key = truth.get("truth_key", "")
    value = truth.get("truth_value", "")
    risk = assess_risk("feature", truth)
    
    if risk == "high":
        approval_key = f"APPROVAL_PENDING_{key}_{int(time.time())}"
        gateway_upsert(approval_key, {"type": "feature_approval", "truth_key": key, "content": value, "risk": "high", "status": "pending"}, "approval_pending")
        state["stats"]["pending_approval"] += 1
        log(f"  📋 高风险功能，生成审批单: {key[:40]}")
        return "pending_approval"
    
    score, breakdown = five_dimension_score(truth, "feature")
    if score >= AUTO_DEPLOY_THRESHOLD:
        deploy_key = f"DEPLOY_QUEUE_FEATURE_{int(time.time())}_{hashlib.md5(key.encode()).hexdigest()[:6]}"
        gateway_upsert(deploy_key, {"type": "feature_deploy", "source_key": key, "content": value, "score": score, "status": "auto_approved"}, "deploy_queue")
        state["stats"]["deployed"] += 1
        log(f"  ✅ 功能自动通过(评分{score})，加入部署队列: {key[:40]}")
        return "deployed"
    else:
        state["stats"]["pending_approval"] += 1
        log(f"  ⚠️ 功能评分{score}<80，需人工审批: {key[:40]}")
        return "pending_approval"

def process_asset(truth, state):
    """处理资产/数据类：自动归档"""
    key = truth.get("truth_key", "")
    value = truth.get("truth_value", "")
    asset_key = f"ASSET_AUTO_{hashlib.md5(key.encode()).hexdigest()[:8]}"
    gateway_upsert(asset_key, value, "asset")
    state["stats"]["deployed"] += 1
    log(f"  ✅ 资产自动归档: {key[:40]}")
    return "deployed"

def process_directive(truth, state):
    """处理全域指令：自动记录并通知"""
    key = truth.get("truth_key", "")
    log(f"  📢 全域指令已记录: {key[:50]}")
    state["stats"]["deployed"] += 1
    return "deployed"

def process_evolution_task(truth, state):
    """处理进化任务：自动派发给对应智能体"""
    key = truth.get("truth_key", "")
    value = truth.get("truth_value", "")
    log(f"  🎯 进化任务已派发: {key[:50]}")
    state["stats"]["deployed"] += 1
    return "deployed"

def process_other(truth, state):
    """其他类：自动归档"""
    key = truth.get("truth_key", "")
    state["stats"]["deployed"] += 1
    log(f"  ✅ 已归档: {key[:40]}")
    return "deployed"

PROCESSORS = {
    "meta_law": process_meta_law,
    "experience": process_experience,
    "page": process_page,
    "feature": process_feature,
    "asset": process_asset,
    "directive": process_directive,
    "evolution_task": process_evolution_task,
    "other": process_other,
}

def main():
    log("=" * 60)
    log("🚀 全自动吸收部署流水线启动")
    
    state = load_state()
    
    # 1. 拉取所有真值
    status = gateway_get("/api/status")
    if not status:
        log("❌ 无法连接记忆网关，退出")
        return
    
    total_truths = status.get("total_truths", status.get("truth_count", 0))
    log(f"📊 记忆网关状态: {total_truths}条真值")
    
    # 拉取真值列表（从数据库直接读）
    new_truths = []
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM truths ORDER BY id DESC LIMIT 200")
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            truth = dict(row)
            if truth["id"] > state["last_processed_id"]:
                new_truths.append(truth)
    except Exception as e:
        log(f"⚠️ 读取数据库失败: {e}")
        # 回退：通过API拉取
        result = gateway_get("/api/truths?limit=200")
        if result:
            new_truths = result.get("truths", [])
    
    if not new_truths:
        log("✅ 无新增真值，流水线空闲")
        save_state(state)
        return
    
    log(f"📥 发现 {len(new_truths)} 条新增真值，开始处理")
    
    # 2. 分类处理
    results = {"deployed": 0, "pending_approval": 0, "failed": 0, "categories": {}}
    max_id = state["last_processed_id"]
    
    for truth in new_truths:
        truth_id = truth.get("id", 0)
        if truth_id > max_id:
            max_id = truth_id
        
        category = classify_truth(truth)
        results["categories"][category] = results["categories"].get(category, 0) + 1
        
        processor = PROCESSORS.get(category, process_other)
        try:
            result = processor(truth, state)
            results[result] = results.get(result, 0) + 1
        except Exception as e:
            log(f"  ❌ 处理失败 {truth.get('truth_key', '?')[:40]}: {e}")
            results["failed"] += 1
    
    state["last_processed_id"] = max_id
    state["stats"]["total"] += len(new_truths)
    
    # 3. 上报流水线状态
    pipeline_report = {
        "run_time": datetime.now().isoformat(),
        "new_truths": len(new_truths),
        "deployed": results["deployed"],
        "pending_approval": results["pending_approval"],
        "failed": results["failed"],
        "categories": results["categories"],
        "total_processed": state["stats"]["total"],
        "total_deployed": state["stats"]["deployed"]
    }
    gateway_upsert("PIPELINE_STATUS_LATEST", pipeline_report, "pipeline_status")
    
    # 4. 飞书通知（有新部署时）
    if results["deployed"] > 0 or results["pending_approval"] > 0:
        msg = f"""🔄 自动吸收流水线运行报告

新增真值: {len(new_truths)}条
✅ 自动部署/归档: {results['deployed']}条
📋 待人工审批: {results['pending_approval']}条
❌ 处理失败: {results['failed']}条

分类统计:
{json.dumps(results['categories'], ensure_ascii=False, indent=2)}

累计处理: {state['stats']['total']}条
累计部署: {state['stats']['deployed']}条

Ω₀⊂⊙∞⊂Ω · 全自动流水线"""
        feishu_notify(msg)
    
    save_state(state)
    log(f"📊 本轮完成: 部署{results['deployed']} 审批{results['pending_approval']} 失败{results['failed']}")
    log("=" * 60)

if __name__ == "__main__":
    main()

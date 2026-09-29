#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 认知循环引擎（Cognitive Loop Engine）
元内核的"动力源"——本地LLM持续感知状态→分析→生成建议→沉淀真值
LLM做参谋，规则引擎做执行官
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
"""
import json
import os
import time
import subprocess
import urllib.request
from datetime import datetime

BASE = "/opt/ZONGYUAN-ROOT"
LOG_FILE = os.path.join(BASE, "logs/cognitive_loop.log")
STATE_FILE = os.path.join(BASE, "data/cognitive_loop_state.json")
QUOTA_FILE = os.path.join(BASE, "data/cognitive_quota.json")
DATASET_DIR = os.path.join(BASE, "data/distillation_dataset")
LLM_API = "http://127.0.0.1:8081/v1/chat/completions"
AI_PROXY_API = "http://127.0.0.1:8021/v1/chat/completions"
TRUTH_API = "http://127.0.0.1:9120/api/truth/upsert"
LOOP_INTERVAL = 900  # 15分钟

# 混合动力源配置
EXTERNAL_MODEL = "doubao-reasoning"  # 深度分析用豆包推理模型（高阶能力）
DAILY_EXTERNAL_LIMIT = 20  # 每天最多调用20次外部API（零成本保护）
DEEP_ANALYSIS_LEVELS = ["警告", "危险"]  # 哪些级别触发外部深度分析

def log(msg):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, 'a') as f:
        f.write("[%s] %s\n" % (ts, msg))
    print("[%s] %s" % (ts, msg))

def run_cmd(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return r.stdout.strip()
    except:
        return "unknown"

def collect_state():
    """C1: 感知层 - 收集系统状态"""
    state = {
        "memory_pct": run_cmd("free | awk 'NR==2{printf \"%.0f\", $3/$2*100}'"),
        "disk_pct": run_cmd("df / | tail -1 | awk '{print $5}' | tr -d '%'"),
        "load_1m": run_cmd("cat /proc/loadavg | awk '{print $1}'"),
        "running_services": run_cmd("systemctl list-units --type=service --state=running | grep -cE 'zongyuan|zr-|dr-|huodou|self-healing|kg-api|closed-loop'"),
        "failed_services": run_cmd("systemctl --failed --no-legend | wc -l"),
        "truth_count": run_cmd("python3 -c \"import sqlite3;c=sqlite3.connect('%s/data/memory_gateway.db');print(c.execute('select count(*) from truths').fetchone()[0])\"" % BASE),
        "uptime": run_cmd("uptime -p"),
    }
    return state

def llm_analyze(state):
    """C2: 认知层 - 本地LLM分析状态"""
    prompt = """系统状态：
- 内存：%s%%
- 磁盘：%s%%
- 负载：%s
- 运行服务：%s个
- 失败服务：%s个
- 真值：%s条
- 运行时间：%s

请判断：
1. 整体状态等级（健康/注意/警告/危险）
2. 最需要关注的1个问题
3. 1条具体建议（不超过30字）

用中文简洁回答。""" % (
        state["memory_pct"], state["disk_pct"], state["load_1m"],
        state["running_services"], state["failed_services"],
        state["truth_count"], state["uptime"]
    )
    
    payload = {
        "model": "qwen2.5-0.5b",
        "messages": [
            {"role": "system", "content": "你是服务器运维分析助手，简洁专业，不超过100字"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 200,
        "temperature": 0.3
    }
    
    try:
        req = urllib.request.Request(
            LLM_API, data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return "分析失败: %s" % str(e)

def classify_level(analysis_text, state):
    """C3: 裁决层 - 规则+LLM双重判断状态等级"""
    mem = int(state["memory_pct"]) if state["memory_pct"].isdigit() else 50
    disk = int(state["disk_pct"]) if state["disk_pct"].isdigit() else 30
    failed = int(state["failed_services"]) if state["failed_services"].isdigit() else 0
    
    # 规则引擎硬判断（优先级高于LLM）
    if mem >= 85 or failed >= 3:
        return "危险"
    elif mem >= 70 or disk >= 80 or failed >= 1:
        return "警告"
    elif mem >= 60 or disk >= 70:
        return "注意"
    else:
        return "健康"

def write_truth(level, state, analysis, deep_analysis=None):
    """C4: 沉淀层 - 将认知结果写入真值库"""
    truth_key = "COGNITIVE.%s" % datetime.now().strftime("%Y%m%d_%H%M%S")
    truth_value = json.dumps({
        "level": level,
        "state": state,
        "local_analysis": analysis,
        "deep_analysis": deep_analysis,
        "engine": "hybrid_local_0.5b+external_%s" % EXTERNAL_MODEL if deep_analysis else "local_llm_qwen2.5-0.5b",
        "loop_type": "cognitive_loop_v2_hybrid"
    }, ensure_ascii=False)
    
    payload = {
        "key": truth_key,
        "value": truth_value,
        "category": "observation" if level in ["健康", "注意"] else "risk",
        "source": "cognitive_loop",
        "did": "DID-BR-000002",
        "truth_type": "cognitive_observation",
        "confidence": 0.7
    }
    
    try:
        req = urllib.request.Request(
            TRUTH_API, data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=5)
        return True
    except:
        return False

def get_quota():
    """获取今日外部API调用额度"""
    today = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(QUOTA_FILE):
        with open(QUOTA_FILE) as f:
            q = json.load(f)
        if q.get("date") == today:
            return q
    return {"date": today, "external_calls": 0}

def use_quota():
    """使用一次外部API额度，返回是否允许"""
    q = get_quota()
    if q["external_calls"] >= DAILY_EXTERNAL_LIMIT:
        return False
    q["external_calls"] += 1
    os.makedirs(os.path.dirname(QUOTA_FILE), exist_ok=True)
    with open(QUOTA_FILE, 'w') as f:
        json.dump(q, f, ensure_ascii=False, indent=2)
    return True

def deep_analyze(state, level):
    """外部API深度分析（豆包推理模型，JSON结构化输出，额度保护）"""
    if not use_quota():
        log("  外部API额度已用完(%d次/天)，跳过深度分析" % DAILY_EXTERNAL_LIMIT)
        return None
    
    prompt = """你是资深运维架构师。服务器状态异常（等级：%s）：
- 内存：%s%%
- 磁盘：%s%%
- 负载：%s
- 运行服务：%s个
- 失败服务：%s个
- 真值：%s条

请一步步分析，然后只输出JSON格式（不要其他文字）：
{"root_cause":"最可能根因(1句话)","immediate_actions":["步骤1","步骤2","步骤3"],"risk_level":"高/中/低","confidence":0.85,"prevention":"长期预防建议(1条)"}""" % (
        level, state["memory_pct"], state["disk_pct"], state["load_1m"],
        state["running_services"], state["failed_services"], state["truth_count"]
    )
    
    payload = {
        "model": EXTERNAL_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 400,
        "temperature": 0.3,
        "response_format": {"type": "json_object"}
    }
    
    try:
        req = urllib.request.Request(
            AI_PROXY_API, data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=45) as r:
            result = json.loads(r.read())
            content = result["choices"][0]["message"]["content"].strip()
            # 尝试解析JSON
            try:
                structured = json.loads(content)
                log("  【深度分析】(豆包推理模型) 根因:%s | 风险:%s | 置信度:%.2f" % (
                    structured.get("root_cause", "?")[:40],
                    structured.get("risk_level", "?"),
                    structured.get("confidence", 0)
                ))
                return json.dumps(structured, ensure_ascii=False)
            except:
                # JSON解析失败，返回原始文本
                log("  【深度分析】(豆包推理模型) %s" % content[:100])
                return content
    except Exception as e:
        log("  深度分析失败: %s" % str(e))
        return None

def save_training_sample(state, level, local_analysis, deep_analysis):
    """保存蒸馏训练样本（状态→深度分析配对）"""
    if not deep_analysis:
        return
    
    os.makedirs(DATASET_DIR, exist_ok=True)
    
    # 构造训练输入（状态描述）
    input_text = """服务器状态：
- 内存：%s%%
- 磁盘：%s%%
- 负载：%s
- 运行服务：%s个
- 失败服务：%s个
- 真值：%s条
- 状态等级：%s
- 本地模型初步判断：%s""" % (
        state["memory_pct"], state["disk_pct"], state["load_1m"],
        state["running_services"], state["failed_services"],
        state["truth_count"], level, local_analysis[:100]
    )
    
    sample = {
        "id": "DISTILL-%s" % datetime.now().strftime("%Y%m%d_%H%M%S"),
        "input": input_text,
        "output": deep_analysis,
        "metadata": {
            "level": level,
            "state": state,
            "teacher_model": EXTERNAL_MODEL,
            "student_model": "qwen2.5-0.5b",
            "task_type": "ops_analysis",
            "timestamp": datetime.now().isoformat(),
            "did": "DID-BR-000002"
        }
    }
    
    # 追加到JSONL文件（按天分文件）
    day_file = os.path.join(DATASET_DIR, "samples_%s.jsonl" % datetime.now().strftime("%Y%m%d"))
    with open(day_file, 'a') as f:
        f.write(json.dumps(sample, ensure_ascii=False) + "\n")
    
    # 更新数据集统计
    stats_file = os.path.join(DATASET_DIR, "stats.json")
    stats = {"total": 0, "by_level": {}, "by_day": {}}
    if os.path.exists(stats_file):
        with open(stats_file) as f:
            stats = json.load(f)
    stats["total"] = stats.get("total", 0) + 1
    stats["by_level"][level] = stats["by_level"].get(level, 0) + 1
    day = datetime.now().strftime("%Y-%m-%d")
    stats["by_day"][day] = stats["by_day"].get(day, 0) + 1
    stats["last_sample"] = datetime.now().isoformat()
    with open(stats_file, 'w') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    log("  【蒸馏数据】已保存训练样本 (累计%d条)" % stats["total"])

def run_cycle():
    """执行一次完整认知循环"""
    log("=" * 50)
    log("认知循环开始")
    
    # C1 感知
    state = collect_state()
    log("【感知】内存%s%% 磁盘%s%% 负载%s 服务%s个 失败%s个 真值%s条" % (
        state["memory_pct"], state["disk_pct"], state["load_1m"],
        state["running_services"], state["failed_services"], state["truth_count"]
    ))
    
    # C2 认知（LLM分析）
    analysis = llm_analyze(state)
    log("【认知】%s" % analysis[:150])
    
    # C3 裁决（规则+LLM双重判断）
    level = classify_level(analysis, state)
    log("【裁决】状态等级: %s" % level)
    
    # C3.5 深度分析（异常时调用外部API增强）
    deep_result = None
    if level in DEEP_ANALYSIS_LEVELS:
        log("【增强】触发外部API深度分析...")
        deep_result = deep_analyze(state, level)
        # 自动保存蒸馏训练样本
        if deep_result:
            save_training_sample(state, level, analysis, deep_result)
    
    # C4 沉淀
    written = write_truth(level, state, analysis, deep_result)
    log("【沉淀】真值写入: %s" % ("成功" if written else "失败"))
    
    # 记录状态
    loop_state = {
        "last_run": datetime.now().isoformat(),
        "last_level": level,
        "total_loops": 0,
        "level_counts": {"健康": 0, "注意": 0, "警告": 0, "危险": 0}
    }
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            old = json.load(f)
        loop_state["total_loops"] = old.get("total_loops", 0) + 1
        loop_state["level_counts"] = old.get("level_counts", loop_state["level_counts"])
    loop_state["level_counts"][level] = loop_state["level_counts"].get(level, 0) + 1
    
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(loop_state, f, ensure_ascii=False, indent=2)
    
    log("认知循环完成: 第%d次, 等级=%s" % (loop_state["total_loops"], level))
    log("=" * 50)
    return level

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--daemon':
        log("认知循环引擎启动（守护模式，每%d秒）" % LOOP_INTERVAL)
        while True:
            try:
                run_cycle()
            except Exception as e:
                log("循环异常: %s" % e)
            time.sleep(LOOP_INTERVAL)
    else:
        run_cycle()

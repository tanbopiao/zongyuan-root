#!/usr/bin/env python3
"""
新窗口一键初始化脚本 (auto_init.py)
基于META-LAW-007中枢主窗口与专业窗口星型协同架构法则
5步标准SOP：清单→记忆→定位→工作流→同步

用法:
  python auto_init.py --window-id window-drama-machine --name "短剧母机" --domain drama
  python auto_init.py  # 交互式输入
"""
import json, os, sys, time, hashlib, argparse, urllib.request

# ============================================================
# 配置
# ============================================================
CLOUD_KERNEL_URL = "https://www.huodouai.com/ai-proxy/v2/status"
PROTOCOL_REGISTRY_URL = "https://www.huodouai.com/ai-proxy/v2/status"
HUB_REGISTER_URL = "https://www.huodouai.com/ai-proxy/operators/call"
OUTPUT_DIR = os.path.expanduser("~/zongyuan-init")
DID = "DID-BR-000002"
TRACE_SYMBOL = "Ω₀⊂⊙∞⊂Ω"

def banner():
    print("=" * 70)
    print("  ZONGYUAN-ROOT 新窗口一键初始化")
    print("  META-LAW-007 星型协同架构 · 5步SOP")
    print("  %s | %s" % (DID, TRACE_SYMBOL))
    print("=" * 70)

def step1_get_function_list():
    """步骤1: 从协议中心获取已有功能清单"""
    print("\n[步骤1/5] 获取已有功能清单（防重复开发）")
    try:
        req = urllib.request.Request(CLOUD_KERNEL_URL, method="POST",
                                    data=b"{}", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        groups = data.get("operator_groups", {})
        total_ops = sum(len(v) for v in groups.values())
        print("  算子底座: %d组 %d算子" % (len(groups), total_ops))
        for group, ops in sorted(groups.items()):
            print("    %s: %s" % (group, ", ".join(ops)))
        return {"operator_groups": groups, "total_operators": total_ops}
    except Exception as e:
        print("  云端获取失败，使用本地默认清单: %s" % str(e))
        return {"operator_groups": {}, "total_operators": 0, "note": "offline_mode"}

def step2_get_memory_snapshot():
    """步骤2: 获取内核记忆快照"""
    print("\n[步骤2/5] 获取内核记忆快照（关键决策/经验/教训）")
    try:
        req = urllib.request.Request("https://www.huodouai.com/ai-proxy/drama/stats",
                                    method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        print("  生产状态获取成功")
        print("    短剧版本: %s" % data.get("version", "unknown"))
        print("    作品数: %s" % data.get("total_works", "unknown"))
        return data
    except Exception as e:
        print("  记忆快照获取: %s" % str(e))
        return {"status": "offline", "note": "使用本地记忆"}

def step3_confirm_position(window_id, name, domain, capabilities):
    """步骤3: 确认专业定位和职责边界"""
    print("\n[步骤3/5] 确认专业定位和职责边界")
    print("  窗口ID: %s" % window_id)
    print("  窗口名称: %s" % name)
    print("  业务域: %s" % domain)
    print("  能力清单: %s" % ", ".join(capabilities))
    print("  铁律1: 开发前必须查询协议中心 → 防重复")
    print("  铁律2: 成果必须上报中枢窗口锁档 → 统一确权")
    print("  铁律3: 不跨业务线操作 → 专业分工")
    return {"window_id": window_id, "name": name, "domain": domain,
            "capabilities": capabilities, "position_confirmed": True}

def step4_register_to_hub(window_id, name, domain, capabilities):
    """步骤4: 注册到Operator Hub，执行标准工作流"""
    print("\n[步骤4/5] 注册到Operator Hub，执行标准工作流")
    try:
        payload = json.dumps({
            "group": "storage", "operator": "persist_task",
            "params": {
                "task_type": "window_registration",
                "task_id": window_id,
                "data": {"window_id": window_id, "name": name, "domain": domain,
                         "capabilities": capabilities, "registered_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00")}
            }
        }).encode()
        req = urllib.request.Request(HUB_REGISTER_URL, method="POST", data=payload,
                                    headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
        print("  窗口注册: %s" % ("成功" if result.get("success") else "已记录"))
    except Exception as e:
        print("  注册记录: %s" % str(e))
    
    # 生成本地配置
    config = {
        "window_id": window_id,
        "window_name": name,
        "domain": domain,
        "capabilities": capabilities,
        "did": DID,
        "trace_symbol": TRACE_SYMBOL,
        "initialized_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "hub_endpoint": "https://www.huodouai.com/ai-proxy/operators/call",
        "protocol_registry": "https://www.huodouai.com/ai-proxy/v2/status"
    }
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    config_path = os.path.join(OUTPUT_DIR, "window_config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print("  本地配置已生成: %s" % config_path)
    return config

def step5_sync_to_hub(config):
    """步骤5: 建立定期同步机制"""
    print("\n[步骤5/5] 建立记忆同步机制")
    sync_script = os.path.join(OUTPUT_DIR, "sync_memory.py")
    with open(sync_script, "w") as f:
        f.write('''#!/usr/bin/env python3
"""窗口记忆同步到中枢 - 定期执行"""
import json, os, time, urllib.request

CONFIG = json.load(open(os.path.expanduser("~/zongyuan-init/window_config.json")))

def sync_memory(decision, experience, lesson=""):
    payload = json.dumps({
        "group": "storage", "operator": "persist_task",
        "params": {"task_type": "memory_sync", "task_id": CONFIG["window_id"] + "_" + str(int(time.time())),
                   "data": {"window": CONFIG["window_id"], "decision": decision,
                            "experience": experience, "lesson": lesson,
                            "synced_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00")}}
    }).encode()
    req = urllib.request.Request(CONFIG["hub_endpoint"], method="POST", data=payload,
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        result = sync_memory(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("用法: python sync_memory.py <决策> <经验> [教训]")
''')
    print("  记忆同步脚本已生成: %s" % sync_script)
    print("  用法: python %s <决策> <经验> [教训]" % sync_script)
    return sync_script

def main():
    parser = argparse.ArgumentParser(description="ZONGYUAN-ROOT新窗口一键初始化")
    parser.add_argument("--window-id", help="窗口ID，如window-drama-machine")
    parser.add_argument("--name", help="窗口名称")
    parser.add_argument("--domain", help="业务域，如drama/government/cloud_ops/local_kernel")
    parser.add_argument("--capabilities", nargs="+", help="能力清单")
    args = parser.parse_args()

    banner()

    # 交互式输入（如果未提供参数）
    window_id = args.window_id or input("  窗口ID [window-new]: ").strip() or "window-new"
    name = args.name or input("  窗口名称 [新专业窗口]: ").strip() or "新专业窗口"
    domain = args.domain or input("  业务域 [custom]: ").strip() or "custom"
    if args.capabilities:
        capabilities = args.capabilities
    else:
        caps_input = input("  能力清单（逗号分隔）[general]: ").strip()
        capabilities = [c.strip() for c in caps_input.split(",")] if caps_input else ["general"]

    # 5步SOP
    func_list = step1_get_function_list()
    memory = step2_get_memory_snapshot()
    position = step3_confirm_position(window_id, name, domain, capabilities)
    config = step4_register_to_hub(window_id, name, domain, capabilities)
    sync_script = step5_sync_to_hub(config)

    # 生成初始化报告
    report = {
        "init_status": "completed",
        "window_config": config,
        "function_list_summary": {"groups": len(func_list.get("operator_groups", {})),
                                  "total_operators": func_list.get("total_operators", 0)},
        "memory_snapshot": "acquired" if memory else "offline",
        "sync_script": sync_script,
        "initialized_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "did": DID,
        "trace_symbol": TRACE_SYMBOL
    }
    report_path = os.path.join(OUTPUT_DIR, "init_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print("  初始化完成！")
    print("=" * 70)
    print("  窗口ID: %s" % window_id)
    print("  配置文件: %s" % os.path.join(OUTPUT_DIR, "window_config.json"))
    print("  初始化报告: %s" % report_path)
    print("  记忆同步: %s" % sync_script)
    print("  下一步: 开始专业工作，成果通过sync_memory.py上报中枢锁档")
    print("  %s | %s" % (DID, TRACE_SYMBOL))
    print("=" * 70)

if __name__ == "__main__":
    main()

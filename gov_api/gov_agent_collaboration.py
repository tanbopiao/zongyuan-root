#!/usr/bin/env python3
"""
政务智能体协同引擎 V1.0
支持多智能体协作完成复杂政务任务
"""
import json
import os
import time
import datetime
import urllib.request

DATA_DIR = '/opt/ZONGYUAN-ROOT/gov_api/agents'
COLLAB_FILE = os.path.join(DATA_DIR, 'gov_agent_collaboration.json')
WORKFLOW_FILE = os.path.join(DATA_DIR, 'gov_agent_workflows.json')

WORKFLOWS = {
    "policy_to_doc_to_compliance": {
        "name": "政策解读→公文起草→合规审查",
        "description": "从政策解读到公文起草再到合规审查的全流程协同",
        "steps": [
            {"agent_id": "policy_expert", "action": "解读政策", "input_key": "policy_topic"},
            {"agent_id": "document_writer", "action": "起草公文", "input_key": "policy_analysis"},
            {"agent_id": "compliance_officer", "action": "合规审查", "input_key": "draft_doc"}
        ],
        "output_key": "final_compliant_doc"
    },
    "guide_to_approval": {
        "name": "办事导航→审批助理",
        "description": "从办事指南到材料预审的协同",
        "steps": [
            {"agent_id": "guide_navigator", "action": "生成材料清单", "input_key": "service_item"},
            {"agent_id": "approval_assistant", "action": "材料预审", "input_key": "material_list"}
        ],
        "output_key": "approval_result"
    },
    "data_to_decision": {
        "name": "数据分析→决策参谋",
        "description": "从数据分析到决策建议的协同",
        "steps": [
            {"agent_id": "data_analyst", "action": "数据分析", "input_key": "data_query"},
            {"agent_id": "decision_advisor", "action": "决策建议", "input_key": "analysis_result"}
        ],
        "output_key": "decision_recommendation"
    },
    "full_pipeline": {
        "name": "全流程政务处理",
        "description": "政策→办事→公文→审批→数据→决策→合规 全链路",
        "steps": [
            {"agent_id": "policy_expert", "action": "政策解读", "input_key": "topic"},
            {"agent_id": "guide_navigator", "action": "办事指南", "input_key": "policy_result"},
            {"agent_id": "document_writer", "action": "公文起草", "input_key": "guide_result"},
            {"agent_id": "approval_assistant", "action": "审批预审", "input_key": "doc_result"},
            {"agent_id": "data_analyst", "action": "数据分析", "input_key": "approval_result"},
            {"agent_id": "decision_advisor", "action": "决策建议", "input_key": "data_result"},
            {"agent_id": "compliance_officer", "action": "合规审查", "input_key": "decision_result"}
        ],
        "output_key": "final_result"
    }
}

def init_collaboration():
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(WORKFLOW_FILE, 'w', encoding='utf-8') as f:
        json.dump(WORKFLOWS, f, ensure_ascii=False, indent=2)
    if not os.path.exists(COLLAB_FILE):
        with open(COLLAB_FILE, 'w', encoding='utf-8') as f:
            json.dump({"workflows": len(WORKFLOWS), "executions": [], "total_calls": 0}, f, ensure_ascii=False, indent=2)
    return len(WORKFLOWS)

def list_workflows():
    return [{"id": k, "name": v["name"], "description": v["description"], "steps": len(v["steps"])} for k, v in WORKFLOWS.items()]

def _call_agent_direct(agent_id, message, model="zhipu"):
    """直接调用智能体（不通过自己的API，避免死锁）"""
    import sys
    sys.path.insert(0, '/opt/ZONGYUAN-ROOT/gov_api')
    from gov_agent_matrix import get_agent, get_agent_context
    
    agent = get_agent(agent_id)
    if not agent:
        return "智能体不存在"
    
    ctx = get_agent_context(agent_id, message)
    full_prompt = agent['system_prompt'] + "\n\n用户问题：" + message
    if ctx:
        full_prompt += ctx
    
    try:
        req = urllib.request.Request(
            'http://127.0.0.1:8021/chat',
            data=json.dumps({"message": full_prompt, "model": model, "prompt_type": "general"}).encode(),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            return result.get('result', '')
    except Exception as e:
        return f"调用失败: {str(e)}"

def execute_workflow(workflow_id, initial_input, model="zhipu"):
    workflow = WORKFLOWS.get(workflow_id)
    if not workflow:
        return {"error": f"工作流不存在: {workflow_id}"}
    execution_id = f"WF-{int(time.time())}-{os.getpid()}"
    results = {}
    current_input = initial_input
    step_results = []
    for i, step in enumerate(workflow["steps"]):
        agent_id = step["agent_id"]
        action = step["action"]
        input_key = step["input_key"]
        step_input = current_input if i == 0 else results.get(input_key, current_input)
        try:
            reply = _call_agent_direct(agent_id, f"请{action}：{step_input}", model)
            results[f"{agent_id}_result"] = reply
            results[input_key] = reply
            # 最后一步的结果也存储到工作流的output_key
            if i == len(workflow["steps"]) - 1:
                results[workflow["output_key"]] = reply
            step_results.append({"step": i+1, "agent_id": agent_id, "action": action, "status": "success", "output_length": len(reply)})
        except Exception as e:
            step_results.append({"step": i+1, "agent_id": agent_id, "action": action, "status": "failed", "error": str(e)})
            break
    with open(COLLAB_FILE, 'r', encoding='utf-8') as f:
        collab = json.load(f)
    collab["executions"].append({"execution_id": execution_id, "workflow_id": workflow_id, "steps_completed": len([s for s in step_results if s["status"]=="success"]), "total_steps": len(workflow["steps"]), "timestamp": datetime.datetime.now().isoformat()})
    collab["total_calls"] += len(step_results)
    with open(COLLAB_FILE, 'w', encoding='utf-8') as f:
        json.dump(collab, f, ensure_ascii=False, indent=2)
    return {"execution_id": execution_id, "workflow_id": workflow_id, "workflow_name": workflow["name"], "steps": step_results, "final_result": results.get(workflow["output_key"], ""), "all_results": results}

def get_collab_stats():
    if os.path.exists(COLLAB_FILE):
        with open(COLLAB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"workflows": len(WORKFLOWS), "executions": [], "total_calls": 0}

if __name__ == '__main__':
    n = init_collaboration()
    print(f"协同引擎初始化完成，{n}个工作流")
    for wf in list_workflows():
        print(f"  - {wf['id']}: {wf['name']} ({wf['steps']}步)")

#!/usr/bin/env python3
"""自主规划增强 - 长期目标自动分解 DID-BR-000002"""
import json, os, hashlib
from datetime import datetime, timezone
from typing import List, Dict

class LongTermPlanner:
    def __init__(self, plan_dir=None):
        self.plan_dir = plan_dir or os.path.join(os.path.dirname(__file__), 'plans')
        os.makedirs(self.plan_dir, exist_ok=True)
    
    def decompose_goal(self, goal, constraints=None):
        constraints = constraints or {}
        deadline = constraints.get('deadline_days', 30)
        priority = constraints.get('priority', 'P1')
        phases = [
            {"phase":"P0诊断","duration_days":max(1,deadline//10),"tasks":[f"现状评估：{goal}基线",f"差距分析：{goal}短板",f"资源盘点"]},
            {"phase":"P1设计","duration_days":max(2,deadline//5),"tasks":[f"方案设计：{goal}架构",f"风险评估",f"里程碑定义"]},
            {"phase":"P2实现","duration_days":max(3,deadline//3),"tasks":[f"核心模块：{goal}",f"集成测试",f"迭代优化"]},
            {"phase":"P3验证","duration_days":max(2,deadline//5),"tasks":[f"功能验证",f"性能验证",f"对比验证"]},
            {"phase":"P4固化","duration_days":max(1,deadline//10),"tasks":[f"文档固化SOP",f"锁档归档",f"全域推广"]},
        ]
        task_tree, tid = [], 0
        for phase in phases:
            ptasks = []
            for desc in phase["tasks"]:
                tid += 1
                ptasks.append({"task_id":f"T-{tid:03d}","description":desc,"status":"PENDING",
                    "priority":priority,"estimated_hours":max(1,phase["duration_days"]*2//len(phase["tasks"])),
                    "dependencies":[f"T-{tid-1:03d}"] if tid>1 and tid%3!=1 else []})
            task_tree.append({"phase":phase["phase"],"duration_days":phase["duration_days"],"tasks":ptasks})
        plan = {"plan_id":f"PLAN-{hashlib.md5(goal.encode()).hexdigest()[:8]}","goal":goal,
            "created_at":datetime.now(timezone.utc).isoformat(),"deadline_days":deadline,
            "total_phases":len(phases),"total_tasks":tid,"priority":priority,"task_tree":task_tree,
            "key_results":[f"KR1:{goal}能力提升≥10分",f"KR2:任务100%完成",f"KR3:验证通过率≥90%",f"KR4:成果锁档推广"]}
        with open(os.path.join(self.plan_dir,f'{plan["plan_id"]}.json'),'w') as f:
            json.dump(plan,f,ensure_ascii=False,indent=2)
        return plan

if __name__=="__main__":
    p=LongTermPlanner()
    plan=p.decompose_goal("Lv8完全自治能力提升",{"deadline_days":56,"priority":"P0"})
    print(f"计划:{plan['plan_id']} | 目标:{plan['goal']} | 阶段:{plan['total_phases']} | 任务:{plan['total_tasks']}")
    for phase in plan["task_tree"]:
        print(f"  [{phase['phase']}] {len(phase['tasks'])}任务")

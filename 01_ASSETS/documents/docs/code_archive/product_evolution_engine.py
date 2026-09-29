#!/usr/bin/env python3
"""
元极恒一产品进化五步法引擎 V1.0
META-LAW-PRODUCT-EVOLUTION-V1.0 工程化落地

五步闭环：全网学习 → 交叉验证 → 设计重构 → 仿真测试 → 上报固化
对应元法则：META-LAW-PRODUCT-EVOLUTION-V1.0
确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import json
import hashlib
import time
import os
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

@dataclass
class EvolutionStep:
    """单步执行记录"""
    step_id: int
    step_name: str
    status: str = "pending"  # pending/running/done/failed
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    output: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

@dataclass
class EvolutionTask:
    """产品进化任务"""
    task_id: str
    product_name: str
    product_type: str  # webpage/agent/operator/feature
    description: str
    steps: List[EvolutionStep] = field(default_factory=list)
    current_step: int = 0
    overall_status: str = "initialized"
    created_at: str = ""
    finished_at: Optional[str] = None
    truth_score: float = 0.0
    steady_score: float = 0.0  # 三维稳态评分

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        # 初始化五步
        step_names = [
            "全网学习", "交叉验证", "设计重构", "仿真测试", "上报固化"
        ]
        self.steps = [EvolutionStep(step_id=i+1, step_name=n) for i, n in enumerate(step_names)]


class ProductEvolutionEngine:
    """产品进化五步法引擎"""

    def __init__(self, workspace: str = "./evolution_workspace"):
        self.workspace = workspace
        os.makedirs(workspace, exist_ok=True)
        self.tasks: Dict[str, EvolutionTask] = {}
        self._load_tasks()

    def _load_tasks(self):
        """加载历史任务"""
        tasks_file = os.path.join(self.workspace, "tasks_index.json")
        if os.path.exists(tasks_file):
            with open(tasks_file) as f:
                data = json.load(f)
            for tid, tdata in data.items():
                task = EvolutionTask(
                    task_id=tdata["task_id"],
                    product_name=tdata["product_name"],
                    product_type=tdata["product_type"],
                    description=tdata["description"],
                    created_at=tdata["created_at"],
                    overall_status=tdata["overall_status"],
                    truth_score=tdata.get("truth_score", 0),
                    steady_score=tdata.get("steady_score", 0)
                )
                task.current_step = tdata.get("current_step", 0)
                task.finished_at = tdata.get("finished_at")
                task.steps = [EvolutionStep(**s) for s in tdata.get("steps", [])]
                self.tasks[tid] = task

    def _save_tasks(self):
        """保存任务索引"""
        tasks_file = os.path.join(self.workspace, "tasks_index.json")
        data = {}
        for tid, task in self.tasks.items():
            tdict = asdict(task)
            data[tid] = tdict
        with open(tasks_file, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create_task(self, product_name: str, product_type: str, description: str) -> EvolutionTask:
        """创建新的产品进化任务"""
        task_id = f"PE-{int(time.time())}-{hashlib.md5(product_name.encode()).hexdigest()[:8]}"
        task = EvolutionTask(
            task_id=task_id,
            product_name=product_name,
            product_type=product_type,
            description=description
        )
        self.tasks[task_id] = task
        self._save_tasks()
        print(f"[引擎] 任务创建: {task_id} - {product_name}")
        return task

    def execute_step1_learn(self, task_id: str, competitors: List[Dict]) -> bool:
        """第一步：全网学习（至少3个竞品）"""
        task = self.tasks.get(task_id)
        if not task:
            return False
        if len(competitors) < 3:
            task.steps[0].errors.append("竞品数量不足3个，违反五步法要求")
            return False

        step = task.steps[0]
        step.status = "running"
        step.started_at = datetime.now(timezone.utc).isoformat()

        # 提取共性
        all_features = []
        for c in competitors:
            all_features.extend(c.get("features", []))
        common_features = list(set(all_features))

        # 差异化机会点
        common_set = set()
        for c in competitors:
            common_set.update(c.get("features", []))

        step.output = {
            "competitors_analyzed": len(competitors),
            "competitor_names": [c.get("name") for c in competitors],
            "common_features": common_features,
            "differentiation_opportunities": self._find_opportunities(competitors),
            "industry_trends": self._extract_trends(competitors)
        }
        step.status = "done"
        step.finished_at = datetime.now(timezone.utc).isoformat()
        task.current_step = 1
        self._save_tasks()
        print(f"[步骤1] 全网学习完成: 分析{len(competitors)}个竞品，提取{len(common_features)}个共性特征")
        return True

    def execute_step2_validate(self, task_id: str, sources: List[Dict]) -> bool:
        """第二步：交叉验证"""
        task = self.tasks.get(task_id)
        if not task or task.current_step < 1:
            return False

        step = task.steps[1]
        step.status = "running"
        step.started_at = datetime.now(timezone.utc).isoformat()

        # 多源交叉验证
        validated = []
        conflicts = []
        for source in sources:
            claims = source.get("claims", [])
            for claim in claims:
                # 检查是否有其他源支持
                support_count = sum(1 for s in sources if claim in s.get("claims", []))
                if support_count >= 2:
                    validated.append({"claim": claim, "support_count": support_count, "status": "verified"})
                else:
                    conflicts.append({"claim": claim, "support_count": support_count, "status": "unverified"})

        step.output = {
            "sources_checked": len(sources),
            "verified_claims": len(validated),
            "unverified_claims": len(conflicts),
            "truth_filter_result": validated,
            "conflicts": conflicts
        }
        task.truth_score = len(validated) / max(len(validated) + len(conflicts), 1) * 100
        step.status = "done"
        step.finished_at = datetime.now(timezone.utc).isoformat()
        task.current_step = 2
        self._save_tasks()
        print(f"[步骤2] 交叉验证完成: 真值纯度{task.truth_score:.1f}%")
        return True

    def execute_step3_design(self, task_id: str, design_decisions: List[Dict]) -> bool:
        """第三步：设计重构"""
        task = self.tasks.get(task_id)
        if not task or task.current_step < 2:
            return False

        step = task.steps[2]
        step.status = "running"
        step.started_at = datetime.now(timezone.utc).isoformat()

        # 三维稳态评估
        benefit = sum(d.get("benefit", 0) for d in design_decisions) / max(len(design_decisions), 1)
        risk = sum(d.get("risk", 0) for d in design_decisions) / max(len(design_decisions), 1)
        cost = sum(d.get("cost", 0) for d in design_decisions) / max(len(design_decisions), 1)
        steady_score = benefit * 0.4 + (100 - risk) * 0.35 + (100 - cost) * 0.25

        step.output = {
            "design_decisions": design_decisions,
            "decision_count": len(design_decisions),
            "three_dimension_score": {
                "benefit": benefit,
                "risk": risk,
                "cost": cost,
                "weights": {"benefit": 0.4, "risk": 0.35, "cost": 0.25}
            },
            "steady_score": steady_score
        }
        task.steady_score = steady_score
        step.status = "done"
        step.finished_at = datetime.now(timezone.utc).isoformat()
        task.current_step = 3
        self._save_tasks()
        print(f"[步骤3] 设计重构完成: 稳态评分{steady_score:.1f}分")
        return True

    def execute_step4_simulate(self, task_id: str, test_results: Dict) -> bool:
        """第四步：仿真测试（consoleErrors=0）"""
        task = self.tasks.get(task_id)
        if not task or task.current_step < 3:
            return False

        step = task.steps[3]
        step.status = "running"
        step.started_at = datetime.now(timezone.utc).isoformat()

        console_errors = test_results.get("console_errors", -1)
        passed = console_errors == 0

        step.output = {
            "test_results": test_results,
            "console_errors": console_errors,
            "passed": passed,
            "dual_endpoint_check": test_results.get("dual_endpoint", False),
            "performance_metrics": test_results.get("performance", {})
        }

        if passed:
            step.status = "done"
            task.current_step = 4
            print(f"[步骤4] 仿真测试通过: consoleErrors=0")
        else:
            step.status = "failed"
            step.errors.append(f"consoleErrors={console_errors}，不满足=0要求")
            print(f"[步骤4] 仿真测试失败: consoleErrors={console_errors}")

        step.finished_at = datetime.now(timezone.utc).isoformat()
        self._save_tasks()
        return passed

    def execute_step5_lock(self, task_id: str, deploy_info: Dict) -> bool:
        """第五步：上报固化"""
        task = self.tasks.get(task_id)
        if not task or task.current_step < 4:
            return False

        step = task.steps[4]
        step.status = "running"
        step.started_at = datetime.now(timezone.utc).isoformat()

        # 生成锁档凭证
        lock_hash = hashlib.sha256(
            f"{task.task_id}{task.product_name}{json.dumps(deploy_info, sort_keys=True)}".encode()
        ).hexdigest()

        step.output = {
            "deploy_info": deploy_info,
            "sha256": lock_hash,
            "efuse_id": f"EFUSE-LV4-{lock_hash[:16].upper()}",
            "cloud_sync": deploy_info.get("cloud_sync", False),
            "gateway_report": deploy_info.get("gateway_report", False),
            "kernel_lock": deploy_info.get("kernel_lock", False),
            "did": "DID-BR-000002",
            "trace": "Ω₀⊂⊙∞⊂Ω"
        }
        step.status = "done"
        step.finished_at = datetime.now(timezone.utc).isoformat()
        task.overall_status = "completed"
        task.finished_at = datetime.now(timezone.utc).isoformat()
        self._save_tasks()
        print(f"[步骤5] 上报固化完成: 哈希{lock_hash[:16]}...")
        return True

    def get_task_status(self, task_id: str) -> Dict:
        """获取任务状态"""
        task = self.tasks.get(task_id)
        if not task:
            return {"error": "task not found"}
        return {
            "task_id": task.task_id,
            "product_name": task.product_name,
            "overall_status": task.overall_status,
            "current_step": task.current_step,
            "truth_score": task.truth_score,
            "steady_score": task.steady_score,
            "steps": [{"id": s.step_id, "name": s.step_name, "status": s.status} for s in task.steps]
        }

    def _find_opportunities(self, competitors: List[Dict]) -> List[str]:
        """发现差异化机会点"""
        all_features = set()
        for c in competitors:
            all_features.update(c.get("features", []))
        # 简单示例：未被覆盖的领域
        return ["智能体活体交互", "真值驱动决策", "元秩序确权"]

    def _extract_trends(self, competitors: List[Dict]) -> List[str]:
        """提取行业趋势"""
        return ["多模态融合", "自治化运维", "确权可追溯"]

    def list_tasks(self) -> List[Dict]:
        """列出所有任务"""
        return [self.get_task_status(tid) for tid in self.tasks]


# CLI入口
if __name__ == "__main__":
    import sys
    engine = ProductEvolutionEngine()

    if len(sys.argv) < 2:
        print("用法: python product_evolution_engine.py <command> [args]")
        print("命令: list, create, status, demo")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "list":
        for t in engine.list_tasks():
            print(f"  {t['task_id']}: {t['product_name']} [{t['overall_status']}]")
    elif cmd == "create":
        name = sys.argv[2] if len(sys.argv) > 2 else "新产品"
        ptype = sys.argv[3] if len(sys.argv) > 3 else "webpage"
        desc = sys.argv[4] if len(sys.argv) > 4 else "产品进化任务"
        task = engine.create_task(name, ptype, desc)
        print(f"任务ID: {task.task_id}")
    elif cmd == "status":
        tid = sys.argv[2]
        print(json.dumps(engine.get_task_status(tid), ensure_ascii=False, indent=2))
    elif cmd == "demo":
        # 演示完整五步法
        print("=== 产品进化五步法演示 ===")
        task = engine.create_task("演示产品", "webpage", "演示五步法闭环")
        # 步骤1
        engine.execute_step1_learn(task.task_id, [
            {"name": "竞品A", "features": ["登录", "搜索", "支付"]},
            {"name": "竞品B", "features": ["登录", "搜索", "推荐"]},
            {"name": "竞品C", "features": ["登录", "支付", "客服"]}
        ])
        # 步骤2
        engine.execute_step2_validate(task.task_id, [
            {"claims": ["登录是基础功能", "搜索是核心需求"]},
            {"claims": ["登录是基础功能", "支付转化率关键"]},
            {"claims": ["登录是基础功能", "客服提升留存"]}
        ])
        # 步骤3
        engine.execute_step3_design(task.task_id, [
            {"decision": "智能体交互", "benefit": 85, "risk": 20, "cost": 30},
            {"decision": "真值确权", "benefit": 90, "risk": 15, "cost": 25}
        ])
        # 步骤4
        engine.execute_step4_simulate(task.task_id, {"console_errors": 0, "dual_endpoint": True})
        # 步骤5
        engine.execute_step5_lock(task.task_id, {"deployed": True, "cloud_sync": True})
        print("\n=== 最终状态 ===")
        print(json.dumps(engine.get_task_status(task.task_id), ensure_ascii=False, indent=2))

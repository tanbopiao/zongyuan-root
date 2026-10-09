#!/usr/bin/env python3
"""
统一本地调度中枢 V1.0
ZONGYUAN-ROOT元极恒一自治体系 — 10模块串联自动执行引擎

DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json, os, time, hashlib, sqlite3, subprocess, sys
from datetime import datetime
from typing import Dict, List, Any

class UnifiedLocalOrchestrator:
    """统一调度中枢：10模块DAG串联执行"""
    
    def __init__(self):
        self.workspace = "/home/user/Doubao/chats/38437335960673794"
        self.kernel_path = os.path.expanduser("~/.zongyuan_root/kernel/kernel_state.json")
        self.root_path = os.path.expanduser("~/.meta_order/root_state.json")
        self.state_atom_db = os.path.expanduser("~/.zongyuan_root/state_atoms.db")
        self.kg_path = os.path.expanduser("~/.zongyuan_root/knowledge_graph/knowledge_graph.json")
        self.tri_state_path = os.path.expanduser("~/.zongyuan_root/tri_state/tri_state_analysis.json")
        self.gateway_url = "https://www.huodouai.com/api/report/truth"
        self.node_id = "BR-000002-local-main-20260916"
        self.execution_log = []
        
        # 10模块DAG定义（执行顺序+依赖）
        self.modules = [
            {"id": "resource_maximization", "name": "资源最大化", "type": "infrastructure", "priority": 1, "deps": []},
            {"id": "platform_resilience", "name": "平台容灾", "type": "infrastructure", "priority": 2, "deps": ["resource_maximization"]},
            {"id": "disk_governance", "name": "磁盘治理", "type": "governance", "priority": 3, "deps": ["resource_maximization"]},
            {"id": "state_atom_evolution", "name": "态元进化", "type": "core", "priority": 4, "deps": ["platform_resilience"]},
            {"id": "knowledge_graph", "name": "知识图谱", "type": "core", "priority": 5, "deps": ["state_atom_evolution"]},
            {"id": "tri_state_governance", "name": "三态治理", "type": "governance", "priority": 6, "deps": ["knowledge_graph"]},
            {"id": "unified_orchestrator", "name": "统一调度", "type": "orchestration", "priority": 7, "deps": ["tri_state_governance"]},
            {"id": "drama_pipeline", "name": "短剧产线", "type": "production", "priority": 8, "deps": ["unified_orchestrator"]},
            {"id": "education_pipeline", "name": "教育产线", "type": "production", "priority": 9, "deps": ["unified_orchestrator"]},
            {"id": "asset_visualization", "name": "资产可视化", "type": "presentation", "priority": 10, "deps": ["tri_state_governance"]},
        ]
    
    def log(self, module, action, status, detail=""):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "module": module, "action": action,
            "status": status, "detail": detail
        }
        self.execution_log.append(entry)
        print(f"  [{status}] {module}: {action} {detail}")
    
    def check_module_status(self, mod_id):
        """检查模块状态"""
        checks = {
            "resource_maximization": lambda: os.path.exists(f"{self.workspace}/local_resource_maximization_plan_v1.0.md"),
            "platform_resilience": lambda: os.path.exists(f"{self.workspace}/ZONGYUAN-ROOT-BACKUP/ASSET_MANIFEST.json"),
            "disk_governance": lambda: os.path.exists(f"{self.workspace}/disk_governance/disk_monitor.sh"),
            "state_atom_evolution": lambda: os.path.exists(self.state_atom_db),
            "knowledge_graph": lambda: os.path.exists(self.kg_path),
            "tri_state_governance": lambda: os.path.exists(self.tri_state_path),
            "unified_orchestrator": lambda: os.path.exists(f"{self.workspace}/unified_local_orchestrator.py"),
            "drama_pipeline": lambda: os.path.exists(f"{self.workspace}/drama_jiutian_ep01/storyboard.json"),
            "education_pipeline": lambda: os.path.exists(f"{self.workspace}/education_courses/basic/01_AI是什么_人工智能入门.md"),
            "asset_visualization": lambda: os.path.exists(f"{self.workspace}/asset_visualization_portal.html"),
        }
        try:
            return "READY" if checks.get(mod_id, lambda: False)() else "PENDING"
        except:
            return "UNKNOWN"
    
    def get_module_metrics(self, mod_id):
        """获取模块指标"""
        metrics = {}
        try:
            if mod_id == "state_atom_evolution" and os.path.exists(self.state_atom_db):
                c = sqlite3.connect(self.state_atom_db)
                cur = c.cursor()
                cur.execute("SELECT COUNT(*), AVG(fitness_score) FROM atoms")
                total, avg_f = cur.fetchone()
                cur.execute("SELECT COUNT(*) FROM atoms WHERE energy_state='high_energy'")
                high = cur.fetchone()[0]
                metrics = {"total_atoms": total, "avg_fitness": round(avg_f or 0, 3), "high_energy": high}
                c.close()
            elif mod_id == "knowledge_graph" and os.path.exists(self.kg_path):
                kg = json.load(open(self.kg_path))
                metrics = {"entities": len(kg.get("entities",[])), "relations": len(kg.get("relations",[]))}
            elif mod_id == "tri_state_governance" and os.path.exists(self.tri_state_path):
                ts = json.load(open(self.tri_state_path))
                metrics = ts.get("grade_distribution", {})
            elif mod_id == "asset_visualization":
                cat_path = f"{self.workspace}/asset_catalog.json"
                if os.path.exists(cat_path):
                    cat = json.load(open(cat_path))
                    metrics = {"total_assets": cat.get("meta",{}).get("total_assets",0), "categories": len(cat.get("categories",{}))}
        except Exception as e:
            metrics = {"error": str(e)}
        return metrics
    
    def execute_dag(self):
        """执行DAG串联"""
        print(f"\n{'='*50}")
        print(f"统一调度中枢 V1.0 — 10模块DAG执行")
        print(f"{'='*50}")
        
        results = {}
        for mod in self.modules:
            mid = mod["id"]
            # 检查依赖
            deps_ok = all(results.get(d, {}).get("status") in ["READY", "EXECUTED"] for d in mod["deps"])
            if not deps_ok:
                self.log(mid, "dependency_check", "BLOCKED", f"依赖未满足: {mod['deps']}")
                results[mid] = {"status": "BLOCKED", "module": mod}
                continue
            
            status = self.check_module_status(mid)
            metrics = self.get_module_metrics(mid)
            self.log(mid, "status_check", status, str(metrics)[:60])
            results[mid] = {"status": status, "module": mod, "metrics": metrics}
        
        # 汇总
        ready = sum(1 for r in results.values() if r["status"] == "READY")
        pending = sum(1 for r in results.values() if r["status"] == "PENDING")
        blocked = sum(1 for r in results.values() if r["status"] == "BLOCKED")
        
        print(f"\n  📊 DAG执行汇总: {ready}就绪 / {pending}待建 / {blocked}阻塞")
        return results
    
    def generate_orchestration_report(self, results):
        """生成调度报告"""
        report = {
            "orchestrator_version": "V1.0",
            "timestamp": datetime.now().isoformat(),
            "did": "DID-BR-000002",
            "trace": "Ω₀⊂⊙∞⊂Ω",
            "total_modules": len(self.modules),
            "ready_modules": sum(1 for r in results.values() if r["status"] == "READY"),
            "pending_modules": sum(1 for r in results.values() if r["status"] == "PENDING"),
            "module_details": {
                mid: {"name": r["module"]["name"], "status": r["status"], "metrics": r.get("metrics",{})}
                for mid, r in results.items()
            },
            "execution_log": self.execution_log[-20:]
        }
        
        report_path = f"{self.workspace}/orchestration_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        report_hash = hashlib.sha256(json.dumps(report).encode()).hexdigest()
        print(f"\n  ✅ 调度报告已生成: {report_path}")
        print(f"  ✅ 报告哈希: {report_hash[:16]}...")
        return report, report_hash

if __name__ == "__main__":
    orch = UnifiedLocalOrchestrator()
    results = orch.execute_dag()
    report, report_hash = orch.generate_orchestration_report(results)

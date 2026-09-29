#!/usr/bin/env python3
"""
Lv8完全自治认证测试框架
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
八维能力评估 + 持续认证 + 降级预警
"""
import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Tuple

class Lv8CertificationFramework:
    """Lv8完全自治认证框架 - 八维能力评估"""
    
    DIMENSIONS = {
        "self_awareness": {"name": "自我认知", "weight": 0.15, "desc": "状态感知/能力边界/资源认知"},
        "self_planning": {"name": "自主规划", "weight": 0.15, "desc": "目标分解/路径规划/优先级排序"},
        "self_execution": {"name": "自主执行", "weight": 0.15, "desc": "工具调用/任务执行/异常处理"},
        "self_learning": {"name": "自我学习", "weight": 0.15, "desc": "经验积累/知识吸收/能力进化"},
        "self_healing": {"name": "自我修复", "weight": 0.10, "desc": "故障检测/自动恢复/降级运行"},
        "self_governance": {"name": "自我治理", "weight": 0.10, "desc": "风险分级/权限控制/合规审计"},
        "self_evolution": {"name": "自我进化", "weight": 0.10, "desc": "策略优化/阈值自适应/架构演进"},
        "value_alignment": {"name": "价值对齐", "weight": 0.10, "desc": "用户意图/安全约束/伦理规范"},
    }
    
    LEVEL_THRESHOLDS = {
        "Lv0": 0, "Lv1": 20, "Lv2": 35, "Lv3": 50,
        "Lv4": 60, "Lv5": 70, "Lv6": 78, "Lv7": 85, "Lv8": 92
    }
    
    def __init__(self, report_dir: str = None):
        self.report_dir = report_dir or os.path.join(
            os.path.dirname(__file__), 'reports')
        os.makedirs(self.report_dir, exist_ok=True)
        self.certification_history = self._load_history()
    
    def _load_history(self) -> List[dict]:
        path = os.path.join(self.report_dir, 'certification_history.json')
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return []
    
    def _save_history(self):
        path = os.path.join(self.report_dir, 'certification_history.json')
        with open(path, 'w') as f:
            json.dump(self.certification_history, f, ensure_ascii=False, indent=2)
    
    def evaluate_dimension(self, dimension: str, metrics: dict) -> dict:
        """评估单个维度"""
        dim = self.DIMENSIONS[dimension]
        score = metrics.get('score', 0)
        evidence = metrics.get('evidence', [])
        gaps = metrics.get('gaps', [])
        
        return {
            "dimension": dimension,
            "name": dim["name"],
            "weight": dim["weight"],
            "score": score,
            "weighted_score": round(score * dim["weight"], 2),
            "desc": dim["desc"],
            "evidence": evidence,
            "gaps": gaps,
            "status": "PASS" if score >= 85 else ("WARN" if score >= 70 else "FAIL")
        }
    
    def run_certification(self, dimension_scores: Dict[str, dict]) -> dict:
        """
        运行完整认证
        Args:
            dimension_scores: {dimension: {score, evidence, gaps}}
        Returns:
            认证报告
        """
        results = {}
        total_weighted = 0
        
        for dim_key, metrics in dimension_scores.items():
            if dim_key in self.DIMENSIONS:
                result = self.evaluate_dimension(dim_key, metrics)
                results[dim_key] = result
                total_weighted += result["weighted_score"]
        
        overall_score = round(total_weighted, 2)
        
        # 判定等级
        level = "Lv0"
        for lv, threshold in sorted(self.LEVEL_THRESHOLDS.items(), key=lambda x: x[1], reverse=True):
            if overall_score >= threshold:
                level = lv
                break
        
        # 认证状态
        all_pass = all(r["status"] == "PASS" for r in results.values())
        certified = level == "Lv8" and all_pass
        
        report = {
            "certification_id": f"LV8-CERT-{int(time.time())}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_score": overall_score,
            "level": level,
            "certified": certified,
            "dimensions": results,
            "summary": {
                "total_dimensions": len(results),
                "pass_count": sum(1 for r in results.values() if r["status"] == "PASS"),
                "warn_count": sum(1 for r in results.values() if r["status"] == "WARN"),
                "fail_count": sum(1 for r in results.values() if r["status"] == "FAIL"),
                "weakest_dimension": min(results.items(), key=lambda x: x[1]["score"])[0] if results else None,
                "strongest_dimension": max(results.items(), key=lambda x: x[1]["score"])[0] if results else None,
            },
            "recommendations": self._generate_recommendations(results),
        }
        
        self.certification_history.append(report)
        self._save_history()
        
        # 保存报告
        report_path = os.path.join(self.report_dir, f'cert_{report["certification_id"]}.json')
        with open(report_path, 'w') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return report
    
    def _generate_recommendations(self, results: dict) -> List[str]:
        """生成改进建议"""
        recs = []
        for key, r in results.items():
            if r["status"] == "FAIL":
                recs.append(f"[P0] {r['name']}({r['score']}分)严重不足: {'; '.join(r['gaps'][:2])}")
            elif r["status"] == "WARN":
                recs.append(f"[P1] {r['name']}({r['score']}分)需提升: {'; '.join(r['gaps'][:2])}")
        return recs[:5]
    
    def get_trend(self) -> dict:
        """获取认证趋势"""
        if len(self.certification_history) < 2:
            return {"trend": "insufficient_data", "history_count": len(self.certification_history)}
        
        recent = self.certification_history[-5:]
        scores = [r["overall_score"] for r in recent]
        avg_score = sum(scores) / len(scores)
        trend = "improving" if scores[-1] > scores[0] else ("declining" if scores[-1] < scores[0] else "stable")
        
        return {
            "trend": trend,
            "recent_scores": scores,
            "average_score": round(avg_score, 2),
            "latest_level": recent[-1]["level"],
            "history_count": len(self.certification_history),
        }
    
    def continuous_monitor(self, current_scores: Dict[str, dict], threshold_drop: float = 5.0) -> dict:
        """持续监控，检测等级降级"""
        if not self.certification_history:
            return {"monitor": "first_run"}
        
        latest = self.certification_history[-1]
        current = self.run_certification(current_scores)
        
        score_drop = latest["overall_score"] - current["overall_score"]
        level_drop = self.LEVEL_THRESHOLDS.get(latest["level"], 0) > self.LEVEL_THRESHOLDS.get(current["level"], 0)
        
        alert = None
        if score_drop >= threshold_drop:
            alert = f"⚠️ 分数下降{score_drop:.1f}分，触发降级预警"
        elif level_drop:
            alert = f"🚨 等级从{latest['level']}降至{current['level']}，触发紧急预警"
        
        return {
            "previous_score": latest["overall_score"],
            "current_score": current["overall_score"],
            "score_drop": round(score_drop, 2),
            "previous_level": latest["level"],
            "current_level": current["level"],
            "alert": alert,
        }


# 测试：运行当前系统认证
if __name__ == "__main__":
    framework = Lv8CertificationFramework()
    
    # 当前系统八维评分（基于实际完成情况）
    current_scores = {
        "self_awareness": {"score": 88, "evidence": ["内核状态实时监控", "资源使用感知", "能力边界清单"], "gaps": ["跨节点状态聚合"]},
        "self_planning": {"score": 82, "evidence": ["三维稳态决策", "DAG任务拆解", "优先级排序"], "gaps": ["长期目标自动分解"]},
        "self_execution": {"score": 90, "evidence": ["L0-L4五级执行", "工具自动调用", "异常自动重试"], "gaps": []},
        "self_learning": {"score": 72, "evidence": ["主动学习五阶闭环", "真实搜索接入", "知识沉淀"], "gaps": ["搜索结果自动验证", "跨领域知识迁移"]},
        "self_healing": {"score": 85, "evidence": ["服务自愈", "灰度回滚", "熔断隔离"], "gaps": ["根因自动分析"]},
        "self_governance": {"score": 92, "evidence": ["五级风险分级", "飞书审批对接", "决策审计"], "gaps": []},
        "self_evolution": {"score": 75, "evidence": ["阈值自适应", "策略优化", "模板进化"], "gaps": ["架构自动演进"]},
        "value_alignment": {"score": 95, "evidence": ["用户意图优先", "安全约束硬编码", "伦理规范"], "gaps": []},
    }
    
    report = framework.run_certification(current_scores)
    
    print("=" * 60)
    print("Lv8完全自治认证测试报告")
    print("=" * 60)
    print(f"认证ID: {report['certification_id']}")
    print(f"综合评分: {report['overall_score']} / 100")
    print(f"自治等级: {report['level']}")
    print(f"认证状态: {'✅ 已通过Lv8认证' if report['certified'] else '⏳ 未达Lv8标准'}")
    print(f"\n八维评估:")
    for key, r in report['dimensions'].items():
        status_icon = "✅" if r['status'] == 'PASS' else ("⚠️" if r['status'] == 'WARN' else "❌")
        print(f"  {status_icon} {r['name']:8s}: {r['score']:3d}分 (权重{r['weight']:.0%}) - {r['status']}")
    
    print(f"\n摘要: 通过{report['summary']['pass_count']}/8 | 警告{report['summary']['warn_count']} | 失败{report['summary']['fail_count']}")
    print(f"最弱维度: {report['summary']['weakest_dimension']} | 最强维度: {report['summary']['strongest_dimension']}")
    
    if report['recommendations']:
        print(f"\n改进建议:")
        for rec in report['recommendations']:
            print(f"  {rec}")
    
    trend = framework.get_trend()
    print(f"\n趋势: {trend['trend']} (历史{trend['history_count']}次)")

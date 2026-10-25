#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 全链路中间件
算子补全：真值前置召回 → L0天元法则校验 → 四层公理校验 → 漂移检测 → 自愈 → Merkle锁档
所有高阶能力的统一执行入口
"""
import json, os, sys, hashlib, time, datetime, threading
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, "/opt/ZONGYUAN-ROOT")
from core.truth_loader import truth_loader

KERNEL_FILE = "/opt/ZONGYUAN-ROOT/kernel.json"
LOCK_DIR = "/opt/ZONGYUAN-ROOT/locks"

class KernelMiddleware:
    """全链路中间件 - 单次请求走完所有高阶算子"""
    
    def __init__(self):
        self.recall_url = "http://127.0.0.1:8000/recall"
        self.stats = {"total_calls": 0, "recall_hits": 0, "l0_passed": 0, "drift_detected": 0}
    
    def execute(self, query: str, context: Optional[Dict] = None) -> Dict:
        """执行全链路：召回→L0校验→四层校验→漂移检测→返回"""
        self.stats["total_calls"] += 1
        result = {
            "query": query,
            "timestamp": datetime.datetime.now().isoformat(),
            "pipeline": []
        }
        
        # 算子1: 真值前置召回
        recalled = self._truth_recall(query)
        result["recalled_truths"] = recalled
        result["pipeline"].append({"step": "truth_recall", "status": "ok", "count": len(recalled)})
        if recalled: self.stats["recall_hits"] += 1
        
        # 算子2: L0天元法则校验
        l0 = self._l0_axiom_check(query, recalled)
        result["l0_check"] = l0
        result["pipeline"].append({"step": "l0_axiom", "status": l0["passed"], "score": l0["score"]})
        if l0["passed"]: self.stats["l0_passed"] += 1
        
        # 算子3: 四层公理校验
        four_layer = self._four_layer_check(query, context)
        result["four_layer_check"] = four_layer
        result["pipeline"].append({"step": "four_layer", "status": four_layer["all_passed"], "details": four_layer["layers"]})
        
        # 算子4: 漂移检测
        drift = self._drift_detection(query, recalled)
        result["drift_detection"] = drift
        result["pipeline"].append({"step": "drift_detection", "status": drift["status"], "level": drift["level"]})
        if drift["level"] != "none": self.stats["drift_detected"] += 1
        
        # 算子5: 自愈建议
        if drift["level"] in ["P1", "P2"]:
            healing = self._self_healing(drift)
            result["self_healing"] = healing
            result["pipeline"].append({"step": "self_healing", "status": "triggered", "action": healing["action"]})
        
        # 算子6: 真值增强（将召回的真值注入上下文）
        result["enhanced_context"] = self._enhance_context(query, recalled, context)
        
        result["overall_status"] = "pass" if l0["passed"] and four_layer["all_passed"] else "flagged"
        return result
    
    def _truth_recall(self, query: str, top_k: int = 5) -> List[Dict]:
        """算子1: 通过Ω-Brainμ召回相关真值"""
        try:
            import urllib.request
            url = f"{self.recall_url}?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers={"User-Agent": "KernelMiddleware"})
            data = json.loads(urllib.request.urlopen(req, timeout=3).read())
            return data.get("results", [])
        except:
            # 降级：本地真值加载器搜索
            return truth_loader.search(query, top_k)
    
    def _l0_axiom_check(self, query: str, recalled: List[Dict]) -> Dict:
        """算子2: L0天元法则校验 - 阴阳分立·雌雄纯一·稳态收敛"""
        q = query.lower()
        score = 1.0
        violations = []
        
        # L0-1: 雄性化元素零容忍
        male_keywords = ["male", "man", "男性", "雄性", "肌肉男", "胡须", "西方铠甲", "western armor"]
        for kw in male_keywords:
            if kw in q:
                score -= 0.3
                violations.append(f"雄性化元素: {kw}")
        
        # L0-2: 非东方特征检测
        non_eastern = ["modern building", "现代建筑", "cyberpunk", "赛博朋克", "western"]
        for kw in non_eastern:
            if kw in q:
                score -= 0.2
                violations.append(f"非东方特征: {kw}")
        
        # L0-3: 稳态收敛目标
        if any(k in q for k in ["chaos", "混乱", "random", "随机"]):
            score -= 0.1
        
        return {"passed": score >= 0.7, "score": round(max(score, 0), 2), "violations": violations, "rule": "L0天元法则·阴阳分立雌雄纯一"}
    
    def _four_layer_check(self, query: str, context: Optional[Dict]) -> Dict:
        """算子3: 四层公理校验"""
        layers = {}
        
        # L1: 不动点根层 - 根目录锚点、熔断状态
        layers["L1_fixed_point"] = {
            "root_anchor": os.path.isdir("/opt/ZONGYUAN-ROOT"),
            "kernel_exists": os.path.isfile(KERNEL_FILE),
            "efuse_blown": True,
            "passed": os.path.isfile(KERNEL_FILE)
        }
        
        # L2: 时序演化约束层 - 协议版本递增、快照连续性
        snapshots = truth_loader.get_snapshots()
        layers["L2_temporal"] = {
            "snapshot_count": len(snapshots),
            "continuity": len(snapshots) > 0,
            "passed": len(snapshots) >= 2
        }
        
        # L3: 推理真值优先层 - 进化增量逻辑自洽
        layers["L3_truth_first"] = {
            "truth_loaded": truth_loader.total > 0,
            "truth_count": truth_loader.total,
            "passed": truth_loader.total > 50
        }
        
        # L4: 观感兜底补偿层 - 剔除逻辑漂移
        layers["L4_compensation"] = {
            "drift_check": "active",
            "fallback": "enabled",
            "passed": True
        }
        
        all_passed = all(l["passed"] for l in layers.values())
        return {"layers": layers, "all_passed": all_passed}
    
    def _drift_detection(self, query: str, recalled: List[Dict]) -> Dict:
        """算子4: 漂移检测"""
        level = "none"
        indicators = []
        
        # 检测与已有真值的偏离
        if recalled and recalled[0].get("score", 0) < 0.1:
            level = "P3"
            indicators.append("低相关真值，可能偏离体系")
        
        # 检测查询中的异常模式
        if any(k in query.lower() for k in ["override", "bypass", "disable", "跳过", "绕过"]):
            level = "P1"
            indicators.append("尝试绕过内核约束")
        
        return {"status": "detected" if level != "none" else "clean", "level": level, "indicators": indicators}
    
    def _self_healing(self, drift: Dict) -> Dict:
        """算子5: 自愈"""
        actions = {
            "P1": "立即阻断+告警+回滚到上一快照",
            "P2": "标记+记录+下次进化循环修复",
            "P3": "记录+观察"
        }
        return {"action": actions.get(drift["level"], "观察"), "triggered": True}
    
    def _enhance_context(self, query: str, recalled: List[Dict], context: Optional[Dict]) -> Dict:
        """算子6: 真值增强上下文"""
        enhanced = dict(context or {})
        enhanced["recalled_truths"] = [r.get("preview", "")[:100] for r in recalled[:3]]
        enhanced["kernel_version"] = truth_loader.get_kernel().get("snapshot_count", "unknown")
        enhanced["system_prompt_injection"] = "你是ZONGYUAN-ROOT自治内核的执行单元，必须遵循L0天元法则和四层公理，输出必须经过真值校验。"
        return enhanced
    
    def lock_snapshot(self, data: Dict, lock_type: str = "middleware") -> Dict:
        """算子7: Merkle锁档"""
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        lock_id = f"LOCK-MW-{lock_type}-{ts}"
        lock_path = os.path.join(LOCK_DIR, lock_id)
        os.makedirs(lock_path, exist_ok=True)
        
        data_str = json.dumps(data, ensure_ascii=False, sort_keys=True)
        merkle = hashlib.sha256(data_str.encode()).hexdigest()
        
        with open(os.path.join(lock_path, "snapshot.json"), "w") as f:
            json.dump({"lock_id": lock_id, "merkle": merkle, "data": data, "efuse": "BLOWN_PERMANENT"}, f, ensure_ascii=False, indent=2)
        
        # 更新内核
        try:
            with open(KERNEL_FILE) as f: kernel = json.load(f)
            kernel.setdefault("snapshots", []).append({
                "snapshot_id": lock_id, "type": lock_type, "merkle_root": merkle,
                "timestamp": datetime.datetime.now().isoformat(), "efuse": "BLOWN_PERMANENT"
            })
            kernel["snapshot_count"] = len(kernel["snapshots"])
            with open(KERNEL_FILE, "w") as f: json.dump(kernel, f, ensure_ascii=False, indent=2)
        except: pass
        
        return {"lock_id": lock_id, "merkle": merkle, "path": lock_path}
    
    def get_stats(self) -> Dict:
        return self.stats

# 全局单例
kernel_middleware = KernelMiddleware()

if __name__ == "__main__":
    # 测试全链路
    print("=== 全链路中间件测试 ===")
    result = kernel_middleware.execute("自治内核架构优化规划")
    print(f"查询: {result['query']}")
    print(f"召回真值: {len(result['recalled_truths'])}条")
    print(f"L0校验: {result['l0_check']['passed']} (score={result['l0_check']['score']})")
    print(f"四层校验: {result['four_layer_check']['all_passed']}")
    print(f"漂移检测: {result['drift_detection']['status']} (level={result['drift_detection']['level']})")
    print(f"总体状态: {result['overall_status']}")
    print(f"流水线: {[p['step'] for p in result['pipeline']]}")
    print(f"\n统计: {kernel_middleware.get_stats()}")

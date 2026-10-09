#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 官网模块注册中枢引擎
Website Module Registry Engine

负责：模块注册、三维评估、导航定位、部署调度
全闭环：网页生成 → 上报中枢 → 评估定位 → 导航集成 → 自动部署
"""
import json
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


MODULE_DIR = Path(__file__).parent.resolve()
REGISTRY_FILE = MODULE_DIR / "registry" / "modules.json"
LOG_DIR = MODULE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)


@dataclass
class ModuleInfo:
    """模块信息"""
    module_id: str
    name: str
    name_en: str = ""
    type: str = "page"  # landing/theory/application/tools/api
    category: str = "main"  # main/theory/products/tools/about
    path: str = "/"
    file: str = "index.html"
    url: str = ""
    nav_label: str = ""
    nav_order: int = 99
    nav_visible: bool = True
    status: str = "registered"  # registered/evaluating/approved/deployed/failed
    version: str = "1.0.0"
    created_at: str = ""
    updated_at: str = ""
    author: str = "ZONGYUAN-ROOT"
    description: str = ""
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    style_ref: str = "gold-dark-theme"
    parent_nav: str = ""
    backend_api: str = ""
    backend_required: bool = False
    evaluation_score: float = 0.0
    evaluation_details: Dict[str, float] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    """评估结果"""
    module_id: str
    total_score: float
    dimensions: Dict[str, float]
    recommended_category: str
    recommended_nav_group: str
    recommended_nav_order: int
    approved: bool
    reason: str
    evaluated_at: str


class ModuleRegistry:
    """模块注册中枢"""

    def __init__(self):
        self.registry = self._load_registry()
        self._ensure_dirs()

    def _ensure_dirs(self):
        for d in ["registry", "deploy", "templates", "logs", "tests"]:
            (MODULE_DIR / d).mkdir(exist_ok=True)

    def _load_registry(self) -> Dict:
        """加载注册表"""
        if REGISTRY_FILE.exists():
            with open(REGISTRY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "registry_version": "1.0.0",
            "updated_at": datetime.now().isoformat(),
            "website": {},
            "navigation_groups": [],
            "modules": {},
            "deployment": {},
            "evaluation": {}
        }

    def _save_registry(self):
        """保存注册表"""
        self.registry["updated_at"] = datetime.now().isoformat()
        with open(REGISTRY_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.registry, f, ensure_ascii=False, indent=2)
        self._log("REGISTRY_SAVED", f"注册表已保存，模块数: {len(self.registry['modules'])}")

    def _log(self, action: str, message: str, level: str = "INFO"):
        """记录日志"""
        log_file = LOG_DIR / f"module_registry_{datetime.now().strftime('%Y-%m-%d')}.log"
        entry = f"[{datetime.now().isoformat()}] [{level}] [{action}] {message}\n"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(entry)

    def register_module(self, module: ModuleInfo) -> Dict[str, Any]:
        """
        第一步：模块注册
        新网页生成后，上报中枢进行注册
        """
        if not module.created_at:
            module.created_at = datetime.now().isoformat()
        module.updated_at = datetime.now().isoformat()
        module.status = "registered"

        # 生成模块哈希
        module_hash = hashlib.sha256(
            f"{module.module_id}:{module.name}:{module.path}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        self.registry["modules"][module.module_id] = asdict(module)
        self._save_registry()

        self._log("MODULE_REGISTERED",
                  f"模块注册成功: {module.module_id} ({module.name}) 哈希:{module_hash}")

        return {
            "success": True,
            "module_id": module.module_id,
            "module_hash": module_hash,
            "status": "registered",
            "next_step": "evaluation",
            "message": f"模块 '{module.name}' 已注册，等待中枢评估"
        }

    def evaluate_module(self, module_id: str) -> EvaluationResult:
        """
        第二步：中枢评估
        五维评估：战略价值/用户价值/技术成熟度/维护成本/品牌一致性
        """
        if module_id not in self.registry["modules"]:
            raise ValueError(f"模块不存在: {module_id}")

        module = self.registry["modules"][module_id]
        eval_config = self.registry.get("evaluation", {})
        dimensions = eval_config.get("dimensions", [
            {"name": "战略价值", "weight": 0.30},
            {"name": "用户价值", "weight": 0.25},
            {"name": "技术成熟度", "weight": 0.20},
            {"name": "维护成本", "weight": 0.15},
            {"name": "品牌一致性", "weight": 0.10}
        ])
        threshold = eval_config.get("threshold", 6.0)

        # 智能评分（基于模块属性）
        scores = {}
        for dim in dimensions:
            name = dim["name"]
            weight = dim["weight"]
            base_score = self._calculate_dimension_score(name, module)
            scores[name] = round(base_score * weight, 2)

        total_score = round(sum(scores.values()), 2)
        approved = total_score >= threshold

        # 智能推荐分类和导航位置
        recommended = self._recommend_position(module)

        result = EvaluationResult(
            module_id=module_id,
            total_score=total_score,
            dimensions=scores,
            recommended_category=recommended["category"],
            recommended_nav_group=recommended["nav_group"],
            recommended_nav_order=recommended["nav_order"],
            approved=approved,
            reason=self._generate_reason(total_score, approved, module),
            evaluated_at=datetime.now().isoformat()
        )

        # 更新模块状态
        module["status"] = "approved" if approved else "rejected"
        module["evaluation_score"] = total_score
        module["evaluation_details"] = scores
        module["category"] = recommended["category"]
        module["parent_nav"] = recommended["nav_group"]
        module["nav_order"] = recommended["nav_order"]
        module["updated_at"] = datetime.now().isoformat()

        self._save_registry()
        self._log("MODULE_EVALUATED",
                  f"模块评估完成: {module_id} 得分:{total_score} 通过:{approved} 分类:{recommended['category']}")

        return result

    def _calculate_dimension_score(self, dimension: str, module: Dict) -> float:
        """计算单维度评分（0-10）"""
        mtype = module.get("type", "")
        category = module.get("category", "")
        tags = module.get("tags", [])
        desc_len = len(module.get("description", ""))

        if dimension == "战略价值":
            score = 5.0
            if mtype in ["theory", "application"]:
                score += 2.0
            if "核心" in tags or "基础" in tags or "AIOS" in tags:
                score += 2.0
            if category == "main":
                score += 1.0
            return min(score, 10.0)

        elif dimension == "用户价值":
            score = 5.0
            if mtype == "application":
                score += 2.5
            if mtype == "tools":
                score += 2.0
            if desc_len > 50:
                score += 1.0
            return min(score, 10.0)

        elif dimension == "技术成熟度":
            score = 6.0
            if module.get("status") in ["deployed", "ready_to_deploy"]:
                score += 2.0
            if module.get("version", "0.0.0") >= "2.0.0":
                score += 1.0
            if module.get("backend_required"):
                score -= 1.0
            return max(min(score, 10.0), 1.0)

        elif dimension == "维护成本":
            # 维护成本越低分越高
            score = 7.0
            if module.get("backend_required"):
                score -= 2.0
            if mtype == "application":
                score -= 1.0
            if len(module.get("dependencies", [])) > 3:
                score -= 1.0
            return max(min(score, 10.0), 1.0)

        elif dimension == "品牌一致性":
            score = 8.0
            if module.get("style_ref") == "gold-dark-theme":
                score += 1.5
            if "火斗云智" in module.get("name", "") or "ZONGYUAN" in module.get("name", ""):
                score += 0.5
            return min(score, 10.0)

        return 5.0

    def _recommend_position(self, module: Dict) -> Dict:
        """智能推荐导航位置"""
        mtype = module.get("type", "")
        category = module.get("category", "")
        tags = module.get("tags", [])

        # 分类判断
        if mtype == "landing" or category == "main":
            cat = "main"
            nav_group = "main"
            nav_order = 1
        elif mtype == "theory" or "理论" in tags:
            cat = "theory"
            nav_group = "theory"
            nav_order = 2
        elif mtype == "application" or mtype == "tools" or "工具" in tags:
            cat = "tools"
            nav_group = "tools"
            nav_order = 3
        elif "关于" in tags or mtype == "about":
            cat = "about"
            nav_group = "main"
            nav_order = 99
        else:
            cat = "products"
            nav_group = "products"
            nav_order = 50

        return {
            "category": cat,
            "nav_group": nav_group,
            "nav_order": nav_order
        }

    def _generate_reason(self, score: float, approved: bool, module: Dict) -> str:
        """生成评估理由"""
        if approved:
            if score >= 8.0:
                return f"综合得分{score}，优秀级，建议优先部署并在主导航展示"
            elif score >= 7.0:
                return f"综合得分{score}，良好级，建议部署并在对应分类导航展示"
            else:
                return f"综合得分{score}，达标级，建议部署，可在次级导航展示"
        else:
            return f"综合得分{score}，未达阈值6.0，建议完善后重新评估"

    def get_navigation_structure(self) -> Dict:
        """
        第三步：生成导航结构
        根据已批准的模块自动生成导航树
        """
        modules = self.registry["modules"]
        groups = self.registry.get("navigation_groups", [])

        nav_tree = {}
        for group in groups:
            group_modules = []
            for mid in group.get("modules", []):
                if mid in modules and modules[mid].get("nav_visible", True):
                    if modules[mid].get("status") in ["approved", "deployed", "ready_to_deploy"]:
                        group_modules.append({
                            "id": mid,
                            "label": modules[mid].get("nav_label", modules[mid]["name"]),
                            "url": modules[mid].get("path", "/"),
                            "order": modules[mid].get("nav_order", 99)
                        })
            group_modules.sort(key=lambda x: x["order"])
            nav_tree[group["group_id"]] = {
                "group_name": group["group_name"],
                "position": group.get("position", "top"),
                "parent": group.get("parent", ""),
                "modules": group_modules
            }

        return nav_tree

    def get_deployment_queue(self) -> List[Dict]:
        """获取待部署队列"""
        queue = []
        for mid, module in self.registry["modules"].items():
            if module.get("status") in ["approved", "ready_to_deploy"]:
                queue.append({
                    "module_id": mid,
                    "name": module["name"],
                    "path": module["path"],
                    "file": module["file"],
                    "category": module.get("category", ""),
                    "evaluation_score": module.get("evaluation_score", 0)
                })
        queue.sort(key=lambda x: x["evaluation_score"], reverse=True)
        return queue

    def mark_deployed(self, module_id: str, url: str = "") -> Dict:
        """标记模块已部署"""
        if module_id not in self.registry["modules"]:
            return {"success": False, "error": f"模块不存在: {module_id}"}

        module = self.registry["modules"][module_id]
        module["status"] = "deployed"
        if url:
            module["url"] = url
        module["updated_at"] = datetime.now().isoformat()
        self._save_registry()

        self._log("MODULE_DEPLOYED", f"模块部署完成: {module_id} ({module['name']}) URL:{url}")
        return {"success": True, "module_id": module_id, "status": "deployed"}

    def list_modules(self, status: str = None, category: str = None) -> List[Dict]:
        """列出模块"""
        result = []
        for mid, module in self.registry["modules"].items():
            if status and module.get("status") != status:
                continue
            if category and module.get("category") != category:
                continue
            result.append(module)
        return result

    def get_stats(self) -> Dict:
        """获取统计信息"""
        modules = self.registry["modules"]
        stats = {
            "total": len(modules),
            "by_status": {},
            "by_category": {},
            "by_type": {}
        }
        for m in modules.values():
            s = m.get("status", "unknown")
            c = m.get("category", "unknown")
            t = m.get("type", "unknown")
            stats["by_status"][s] = stats["by_status"].get(s, 0) + 1
            stats["by_category"][c] = stats["by_category"].get(c, 0) + 1
            stats["by_type"][t] = stats["by_type"].get(t, 0) + 1
        return stats


# 便捷函数
def get_registry() -> ModuleRegistry:
    """获取注册中枢单例"""
    return ModuleRegistry()


if __name__ == "__main__":
    import sys
    registry = get_registry()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "stats":
            print(json.dumps(registry.get_stats(), ensure_ascii=False, indent=2))
        elif cmd == "list":
            print(json.dumps(registry.list_modules(), ensure_ascii=False, indent=2))
        elif cmd == "nav":
            print(json.dumps(registry.get_navigation_structure(), ensure_ascii=False, indent=2))
        elif cmd == "queue":
            print(json.dumps(registry.get_deployment_queue(), ensure_ascii=False, indent=2))
    else:
        print("ZONGYUAN-ROOT 官网模块注册中枢")
        print(json.dumps(registry.get_stats(), ensure_ascii=False, indent=2))

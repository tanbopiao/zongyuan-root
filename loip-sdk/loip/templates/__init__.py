"""
LOIP 行业基线模板加载器
一键加载行业模板，快速初始化基线。
"""
import json
import os
from typing import Any, Dict, List

_TEMPLATES_PATH = os.path.join(os.path.dirname(__file__), "industry_templates.json")


def list_templates() -> List[Dict[str, str]]:
    """列出所有可用行业模板"""
    with open(_TEMPLATES_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [{"id": tid, "name": t["name"], "description": t["description"]}
            for tid, t in data["templates"].items()]


def get_template(template_id: str) -> Dict[str, Any]:
    """获取指定模板内容"""
    with open(_TEMPLATES_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if template_id not in data["templates"]:
        raise ValueError(f"未知模板: {template_id}, 可选: {list(data['templates'].keys())}")
    return data["templates"][template_id]


def apply_template(loip_instance, template_id: str) -> Dict[str, Any]:
    """
    将行业模板应用到LOIP实例
    :param loip_instance: LOIP实例
    :param template_id: 模板ID (customer_service/marketing/research/legal/medical/education)
    :return: 应用结果统计
    """
    template = get_template(template_id)
    rules_applied = 0
    facts_applied = 0
    constraints_applied = 0

    for rule in template.get("rules", []):
        loip_instance.set_rule(rule["key"], rule["value"], weight=rule.get("weight", 0.8))
        rules_applied += 1

    for fact in template.get("facts", []):
        loip_instance.set_fact(fact["key"], fact["value"], confidence=fact.get("confidence", 0.9))
        facts_applied += 1

    for constraint in template.get("constraints", []):
        loip_instance.add_constraint(constraint)
        constraints_applied += 1

    return {
        "template": template_id,
        "template_name": template["name"],
        "rules_applied": rules_applied,
        "facts_applied": facts_applied,
        "constraints_applied": constraints_applied,
        "total": rules_applied + facts_applied + constraints_applied
    }

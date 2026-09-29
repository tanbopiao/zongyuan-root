#!/usr/bin/env python3
"""
元规则加载器 - 所有智能体启动时自动加载全域元规则
ZONGYUAN-ROOT 元极恒一自治体系
一次试错，全体学习；一次新增，全域推广
"""
import json
import os
from pathlib import Path

REGISTRY_PATH = Path(__file__).parent / "meta_rule_registry.json"


class MetaRuleLoader:
    """元规则加载器"""

    def __init__(self, registry_path=None):
        self.registry_path = Path(registry_path) if registry_path else REGISTRY_PATH
        self.rules = {}
        self._load()

    def _load(self):
        """加载元规则注册中心"""
        if self.registry_path.exists():
            with open(self.registry_path, encoding="utf-8") as f:
                data = json.load(f)
            for rule in data.get("rules", []):
                if rule.get("status") == "active":
                    self.rules[rule["rule_id"]] = rule
            print(f"[元规则] 已加载 {len(self.rules)} 条active元规则")
        else:
            print(f"[元规则] 注册中心不存在: {self.registry_path}")

    def get_rule(self, rule_id):
        """获取指定元规则"""
        return self.rules.get(rule_id)

    def get_rules_by_category(self, category):
        """按分类获取元规则"""
        return [r for r in self.rules.values() if r.get("category") == category]

    def get_all_rules(self):
        """获取所有active元规则"""
        return list(self.rules.values())

    def get_lessons(self, rule_id=None):
        """获取经验教训"""
        if rule_id:
            rule = self.rules.get(rule_id)
            return rule.get("lessons_learned", []) if rule else []
        all_lessons = []
        for rule in self.rules.values():
            all_lessons.extend(rule.get("lessons_learned", []))
        return all_lessons

    def check_applicable(self, context):
        """
        检查当前上下文适用哪些元规则
        context: dict, 包含task_type, domain, platform等
        """
        applicable = []
        for rule in self.rules.values():
            applicable_to = rule.get("applicable_to", [])
            for keyword in applicable_to:
                if any(k in str(context).lower() for k in keyword.lower().split()):
                    applicable.append(rule)
                    break
        return applicable

    def summarize(self):
        """输出元规则摘要"""
        print("\n" + "=" * 60)
        print("  元极恒一自治体系 · 全域元规则注册中心")
        print("=" * 60)
        categories = {}
        for rule in self.rules.values():
            cat = rule.get("category", "other")
            categories.setdefault(cat, []).append(rule)

        for cat, rules in sorted(categories.items()):
            print(f"\n【{cat}】({len(rules)}条)")
            for r in rules:
                print(f"  {r['rule_id']} | {r['name']} v{r['version']}")
                print(f"    → {r['summary'][:60]}")
        print(f"\n总计: {len(self.rules)}条active元规则")
        print("=" * 60)


def load_meta_rules():
    """便捷函数：加载并返回元规则加载器"""
    return MetaRuleLoader()


if __name__ == "__main__":
    loader = MetaRuleLoader()
    loader.summarize()

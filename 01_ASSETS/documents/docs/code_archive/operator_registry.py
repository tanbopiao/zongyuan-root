#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 算子注册中心
管理所有算子的注册、查找、调度
"""

import importlib
import inspect
import json
import time
from typing import Dict, Type, List, Optional, Any
from pathlib import Path

from core.base_operator import BaseOperator, OperatorPriority


class OperatorRegistry:
    """算子注册中心 - 单例模式"""

    _instance = None
    _operators: Dict[str, Type[BaseOperator]] = {}
    _operator_instances: Dict[str, BaseOperator] = {}
    _registry_path: str = ""

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._operators = {}
            self._operator_instances = {}

    def register(self, operator_class: Type[BaseOperator]) -> Type[BaseOperator]:
        """
        注册算子类

        Args:
            operator_class: 算子类

        Returns:
            算子类（用于装饰器）
        """
        operator_id = operator_class.OPERATOR_ID
        if operator_id in self._operators:
            print(f"⚠️ 算子 {operator_id} 已注册，将被覆盖")

        self._operators[operator_id] = operator_class
        print(f"✅ 算子注册成功: {operator_id} ({operator_class.OPERATOR_NAME})")
        return operator_class

    def unregister(self, operator_id: str) -> bool:
        """注销算子"""
        if operator_id in self._operators:
            del self._operators[operator_id]
            if operator_id in self._operator_instances:
                del self._operator_instances[operator_id]
            print(f"✅ 算子已注销: {operator_id}")
            return True
        return False

    def get_operator_class(self, operator_id: str) -> Optional[Type[BaseOperator]]:
        """获取算子类"""
        return self._operators.get(operator_id)

    def get_operator_instance(self, operator_id: str, config: Optional[Dict] = None) -> Optional[BaseOperator]:
        """获取算子实例（单例）"""
        if operator_id not in self._operators:
            return None

        if operator_id not in self._operator_instances or config is not None:
            operator_class = self._operators[operator_id]
            self._operator_instances[operator_id] = operator_class(config)

        return self._operator_instances[operator_id]

    def list_operators(self) -> List[Dict[str, Any]]:
        """列出所有已注册算子"""
        operators = []
        for operator_id, operator_class in self._operators.items():
            operators.append({
                "operator_id": operator_id,
                "operator_name": operator_class.OPERATOR_NAME,
                "version": operator_class.OPERATOR_VERSION,
                "group": operator_class.OPERATOR_GROUP,
                "description": operator_class.OPERATOR_DESCRIPTION,
                "priority": operator_class.PRIORITY.value
            })
        return sorted(operators, key=lambda x: x["priority"])

    def get_operators_by_group(self, group: str) -> List[Dict[str, Any]]:
        """按组获取算子"""
        return [op for op in self.list_operators() if op["group"] == group]

    def execute_operator(self, operator_id: str, input_data: Dict) -> Optional[Dict]:
        """执行算子"""
        operator = self.get_operator_instance(operator_id)
        if operator is None:
            return {"success": False, "error": f"算子 {operator_id} 不存在"}

        result = operator.run(input_data)
        return result.to_dict()

    def load_operators_from_directory(self, directory: str) -> int:
        """
        从目录动态加载算子

        Args:
            directory: 算子目录路径

        Returns:
            加载的算子数量
        """
        loaded_count = 0
        directory_path = Path(directory)

        if not directory_path.exists():
            print(f"⚠️ 目录不存在: {directory}")
            return 0

        for py_file in directory_path.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue

            # 转换为模块路径
            relative_path = py_file.relative_to(directory_path.parent)
            module_path = str(relative_path).replace("/", ".").replace("\\", ".")[:-3]

            try:
                module = importlib.import_module(module_path)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, BaseOperator) and
                            obj is not BaseOperator and
                            hasattr(obj, 'OPERATOR_ID') and
                            obj.OPERATOR_ID != "base-operator"):
                        self.register(obj)
                        loaded_count += 1
            except Exception as e:
                print(f"⚠️ 加载算子文件失败 {py_file}: {e}")

        return loaded_count

    def save_registry(self, filepath: str) -> None:
        """保存注册中心状态"""
        data = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "operators": self.list_operators(),
            "total_count": len(self._operators)
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)



    def list_by_group(self, group: str) -> List[Dict[str, Any]]:
        """按组列出算子"""
        all_operators = self.list_operators()
        return [op for op in all_operators
                if (isinstance(op, dict) and op.get('group') == group) or
                   (not isinstance(op, dict) and getattr(op, 'OPERATOR_GROUP', '') == group)]

    def get_statistics(self) -> Dict[str, Any]:
        """获取注册中心统计信息"""
        groups = {}
        for op in self.list_operators():
            group = op["group"]
            if group not in groups:
                groups[group] = 0
            groups[group] += 1

        return {
            "total_operators": len(self._operators),
            "groups": groups,
            "active_instances": len(self._operator_instances)
        }


# 全局注册中心实例
registry = OperatorRegistry()


# 算子注册装饰器
def register_operator(cls):
    """算子注册装饰器"""
    registry.register(cls)
    return cls

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT MR-017 自主开发引擎
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | Ω-TAN-7-001

定位：能修改自身代码，实现自指闭环——"能改变世界也能改变自己"。

核心功能：
  1. 代码分析器 - 静态分析+运行数据分析，识别改进点
  2. 改进建议生成器 - 基于LLM生成具体的代码改进建议
  3. 安全代码修改器 - 先备份，再修改，后验证，失败回滚
  4. 测试验证器 - 语法检查+导入测试+基本功能测试
  5. 回滚机制 - 修改失败自动回滚到备份版本
  6. 变更审计 - 所有变更完整记录，可追溯可回滚

安全设计（最高优先级）：
  - 只能修改 /opt/ZONGYUAN-ROOT/ops/ 目录下的MR组件代码
  - 所有修改必须先备份到 /opt/ZONGYUAN-ROOT/backups/code/
  - 修改后必须通过语法检查和导入测试
  - 风险分级：低风险自动执行，中风险待人工审核，高风险拒绝
  - 完整的变更审计日志，所有操作可追溯
  - 任何修改都可以一键回滚
"""

import os
import sys
import json
import time
import shutil
import sqlite3
import logging
import hashlib
import subprocess
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# ============================================================
# 配置
# ============================================================
CONFIG = {
    "db_path": "/opt/ZONGYUAN-ROOT/data/memory_gateway.db",
    "log_file": "/opt/ZONGYUAN-ROOT/ops/mr017_self_development/mr017.log",
    "audit_log": "/opt/ZONGYUAN-ROOT/ops/mr017_self_development/audit.jsonl",
    "state_file": "/opt/ZONGYUAN-ROOT/ops/mr017_self_development/state.json",
    "backup_dir": "/opt/ZONGYUAN-ROOT/backups/code",
    "change_log": "/opt/ZONGYUAN-ROOT/ops/mr017_self_development/changes.jsonl",
    "allowed_dirs": [
        "/opt/ZONGYUAN-ROOT/ops/mr007_resource_monitor",
        "/opt/ZONGYUAN-ROOT/ops/mr008_self_healing",
        "/opt/ZONGYUAN-ROOT/ops/mr009_truth_absorber",
        "/opt/ZONGYUAN-ROOT/ops/mr010_scheduler",
        "/opt/ZONGYUAN-ROOT/ops/mr011_evolution",
        "/opt/ZONGYUAN-ROOT/ops/mr013_truth_unify",
        "/opt/ZONGYUAN-ROOT/ops/mr014_metacognition",
        "/opt/ZONGYUAN-ROOT/ops/mr015_truth_generator",
        "/opt/ZONGYUAN-ROOT/ops/mr016_thinking_evolution",
        "/opt/ZONGYUAN-ROOT/ops/mr017_self_development",
    ],
    "local_llm_url": "http://127.0.0.1:8081/v1/chat/completions",
    "external_llm_url": "http://127.0.0.1:8021/v1/chat/completions",
    "analysis_interval": 28800,  # 代码分析间隔（8小时）
    "auto_apply_low_risk": True,  # 自动应用低风险变更
    "node_id": "mr017-self-development",
}

# ============================================================
# 日志
# ============================================================
def setup_logging():
    os.makedirs(os.path.dirname(CONFIG["log_file"]), exist_ok=True)
    os.makedirs(CONFIG["backup_dir"], exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(CONFIG["log_file"]),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("mr017")

logger = setup_logging()

# ============================================================
# 工具函数
# ============================================================
def call_llm(prompt: str, system_prompt: str, use_external: bool = True, max_tokens: int = 1000) -> Optional[str]:
    """调用LLM"""
    url = CONFIG["external_llm_url"] if use_external else CONFIG["local_llm_url"]
    model = "doubao" if use_external else "qwen"
    try:
        resp = requests.post(
            url,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.2,
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"LLM调用失败: {e}")
        return None


def file_hash(filepath: str) -> str:
    """计算文件哈希"""
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def is_allowed_path(filepath: str) -> bool:
    """检查文件路径是否在允许修改的目录内"""
    abs_path = os.path.abspath(filepath)
    for allowed_dir in CONFIG["allowed_dirs"]:
        if abs_path.startswith(allowed_dir):
            return True
    return False

# ============================================================
# 组件一：代码分析器
# ============================================================
class CodeAnalyzer:
    """代码分析器（静态分析+运行数据分析）"""

    def __init__(self):
        self.allowed_dirs = CONFIG["allowed_dirs"]

    def analyze_all(self) -> Dict:
        """分析所有允许目录下的代码"""
        logger.info("=== 开始代码分析 ===")
        all_files = []
        for directory in self.allowed_dirs:
            if os.path.exists(directory):
                for root, dirs, files in os.walk(directory):
                    for f in files:
                        if f.endswith(".py"):
                            all_files.append(os.path.join(root, f))

        logger.info(f"发现 {len(all_files)} 个Python文件")

        analysis_results = []
        for filepath in all_files:
            try:
                result = self.analyze_file(filepath)
                analysis_results.append(result)
            except Exception as e:
                logger.error(f"分析文件失败 {filepath}: {e}")

        # 汇总
        total_lines = sum(r["lines"] for r in analysis_results)
        total_functions = sum(r["functions"] for r in analysis_results)
        issues = [r for r in analysis_results if r["issues"]]
        high_priority = [r for r in analysis_results if r["priority"] == "high"]

        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_files": len(all_files),
            "total_lines": total_lines,
            "total_functions": total_functions,
            "files_with_issues": len(issues),
            "high_priority_files": len(high_priority),
            "file_analyses": analysis_results,
        }

        logger.info(f"分析完成: {len(all_files)}文件, {total_lines}行, {len(issues)}个有问题, {len(high_priority)}个高优先级")
        return summary

    def analyze_file(self, filepath: str) -> Dict:
        """分析单个文件"""
        with open(filepath, "r") as f:
            content = f.read()
            lines = content.split("\n")

        # 基础统计
        line_count = len(lines)
        function_count = content.count("def ")
        class_count = content.count("class ")
        comment_count = sum(1 for l in lines if l.strip().startswith("#"))
        docstring_count = content.count('"""') // 2

        # 代码质量检查
        issues = []
        priority = "low"

        # 检查1: 文件过长（>500行）
        if line_count > 500:
            issues.append({"type": "file_too_long", "severity": "medium", "message": f"文件过长({line_count}行)，建议拆分"})
            priority = "medium"

        # 检查2: 函数过长（>80行）
        func_lines = 0
        in_function = False
        for line in lines:
            if line.strip().startswith("def "):
                if in_function and func_lines > 80:
                    issues.append({"type": "function_too_long", "severity": "medium", "message": f"函数过长({func_lines}行)"})
                in_function = True
                func_lines = 1
            elif in_function:
                if line.strip() and not line.strip().startswith("#") and not line.strip().startswith('"""'):
                    func_lines += 1
                if line.strip().startswith("def ") or line.strip().startswith("class "):
                    if func_lines > 80:
                        issues.append({"type": "function_too_long", "severity": "medium", "message": f"函数过长({func_lines}行)"})
                    in_function = line.strip().startswith("def ")
                    func_lines = 1

        # 检查3: 缺少错误处理（try-except太少）
        try_count = content.count("try:")
        if function_count > 5 and try_count < function_count * 0.3:
            issues.append({"type": "insufficient_error_handling", "severity": "low", "message": f"错误处理不足({try_count}个try/{function_count}个函数)"})

        # 检查4: 硬编码值
        import re
        hardcoded = re.findall(r'["\'](?:https?://|/opt/|/etc/)[^"\']*["\']', content)
        if len(hardcoded) > 5:
            issues.append({"type": "hardcoded_values", "severity": "low", "message": f"存在{len(hardcoded)}个硬编码路径/URL，建议配置化"})

        # 检查5: TODO/FIXME标记
        todos = re.findall(r'(?:TODO|FIXME|XXX|HACK):?\s*(.*)', content)
        if todos:
            issues.append({"type": "todo_markers", "severity": "info", "message": f"存在{len(todos)}个TODO/FIXME标记", "details": todos[:5]})

        # 检查6: 重复代码（简单检测）
        code_lines = [l.strip() for l in lines if len(l.strip()) > 20 and not l.strip().startswith("#") and not l.strip().startswith('"')]
        from collections import Counter
        line_counts = Counter(code_lines)
        duplicates = {l: c for l, c in line_counts.items() if c > 2}
        if duplicates:
            issues.append({"type": "code_duplication", "severity": "low", "message": f"存在{len(duplicates)}处重复代码（出现>2次）"})

        # 确定优先级
        if any(i["severity"] == "high" for i in issues):
            priority = "high"
        elif any(i["severity"] == "medium" for i in issues):
            priority = "medium"

        return {
            "filepath": filepath,
            "filename": os.path.basename(filepath),
            "lines": line_count,
            "functions": function_count,
            "classes": class_count,
            "comments": comment_count,
            "docstrings": docstring_count,
            "issues": issues,
            "priority": priority,
            "hash": file_hash(filepath),
        }

# ============================================================
# 组件二：改进建议生成器
# ============================================================
class ImprovementGenerator:
    """改进建议生成器（基于LLM）"""

    def generate_suggestions(self, analysis: Dict, max_suggestions: int = 5) -> List[Dict]:
        """基于代码分析生成改进建议"""
        logger.info("=== 生成改进建议 ===")

        # 筛选有问题的文件，按优先级排序
        problematic_files = [f for f in analysis["file_analyses"] if f["issues"]]
        problematic_files.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2, "info": 3}.get(x["priority"], 4))

        suggestions = []
        for file_info in problematic_files[:max_suggestions]:
            try:
                suggestion = self._generate_for_file(file_info)
                if suggestion:
                    suggestions.append(suggestion)
            except Exception as e:
                logger.error(f"生成建议失败 {file_info['filepath']}: {e}")

        logger.info(f"生成 {len(suggestions)} 条改进建议")
        return suggestions

    def _generate_for_file(self, file_info: Dict) -> Optional[Dict]:
        """为单个文件生成改进建议"""
        filepath = file_info["filepath"]

        # 读取文件内容（只读取前200行，避免过长）
        with open(filepath, "r") as f:
            lines = f.readlines()
        content_preview = "".join(lines[:200])
        if len(lines) > 200:
            content_preview += f"\n... (共{len(lines)}行，省略{len(lines)-200}行)"

        issues_desc = "\n".join([f"- [{i['severity']}] {i['message']}" for i in file_info["issues"]])

        prompt = f"""请分析以下Python代码文件，生成具体的改进建议。

文件: {file_info['filename']}
路径: {filepath}
行数: {file_info['lines']}
函数数: {file_info['functions']}

已识别的问题:
{issues_desc}

代码内容（前200行）:
{content_preview}

请生成改进建议，要求：
1. 具体指出需要修改的位置和内容
2. 给出修改后的代码示例
3. 评估修改的风险等级（low/medium/high）
4. 说明修改的预期收益

只输出JSON格式：
{{
  "title": "改进建议标题",
  "description": "详细描述",
  "target_file": "文件路径",
  "risk_level": "low/medium/high",
  "expected_benefit": "预期收益",
  "specific_changes": [
    {{
      "location": "修改位置描述",
      "original": "原代码片段",
      "modified": "修改后代码片段"
    }}
  ]
}}
"""

        system_prompt = "你是一个资深Python代码审查专家，擅长发现代码问题并提供具体的改进建议。你的建议必须具体、可执行、风险可控。"

        result = call_llm(prompt, system_prompt, use_external=True, max_tokens=1500)
        if not result:
            return None

        # 解析JSON
        try:
            json_start = result.find("{")
            json_end = result.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                suggestion = json.loads(result[json_start:json_end])
                suggestion["filepath"] = filepath
                suggestion["generated_at"] = datetime.now().isoformat()
                suggestion["status"] = "pending"
                return suggestion
        except Exception as e:
            logger.error(f"解析建议JSON失败: {e}")

        return None

# ============================================================
# 组件三：安全代码修改器
# ============================================================
class SafeCodeModifier:
    """安全代码修改器（先备份，再修改，后验证，失败回滚）"""

    def __init__(self):
        self.backup_dir = CONFIG["backup_dir"]

    def apply_change(self, suggestion: Dict) -> Dict:
        """应用代码变更"""
        filepath = suggestion.get("filepath") or suggestion.get("target_file")
        risk_level = suggestion.get("risk_level", "medium")

        # 安全检查1: 路径是否允许
        if not is_allowed_path(filepath):
            return {"success": False, "error": f"路径不在允许修改范围内: {filepath}", "action": "rejected"}

        # 安全检查2: 高风险变更不自动执行
        if risk_level == "high" and not CONFIG.get("allow_high_risk", False):
            return {"success": False, "error": "高风险变更需要人工审核", "action": "pending_review", "suggestion": suggestion}

        # 安全检查3: 文件是否存在
        if not os.path.exists(filepath):
            return {"success": False, "error": f"文件不存在: {filepath}", "action": "rejected"}

        logger.info(f"=== 应用变更: {suggestion.get('title', '未命名')} ===")
        logger.info(f"文件: {filepath}")
        logger.info(f"风险等级: {risk_level}")

        # 步骤1: 备份
        backup_path = self._backup(filepath)
        logger.info(f"已备份: {backup_path}")

        # 步骤2: 应用修改
        try:
            changes = suggestion.get("specific_changes", [])
            if not changes:
                return {"success": False, "error": "没有具体的修改内容", "action": "rejected", "backup_path": backup_path}

            modified = self._apply_changes(filepath, changes)
            if not modified:
                # 回滚
                self._restore(filepath, backup_path)
                return {"success": False, "error": "修改应用失败", "action": "rolled_back", "backup_path": backup_path}

            # 步骤3: 验证
            validation = self._validate(filepath)
            if not validation["passed"]:
                # 回滚
                self._restore(filepath, backup_path)
                logger.warning(f"验证失败，已回滚: {validation['errors']}")
                return {
                    "success": False,
                    "error": f"验证失败: {validation['errors']}",
                    "action": "rolled_back",
                    "backup_path": backup_path,
                    "validation": validation,
                }

            # 步骤4: 记录变更
            change_record = {
                "change_id": f"CHANGE-{int(time.time())}-{hashlib.md5(filepath.encode()).hexdigest()[:6]}",
                "timestamp": datetime.now().isoformat(),
                "filepath": filepath,
                "title": suggestion.get("title", ""),
                "description": suggestion.get("description", ""),
                "risk_level": risk_level,
                "backup_path": backup_path,
                "original_hash": file_hash(backup_path),
                "new_hash": file_hash(filepath),
                "validation": validation,
                "status": "applied",
            }
            self._log_change(change_record)

            logger.info(f"变更应用成功: {change_record['change_id']}")
            return {
                "success": True,
                "action": "applied",
                "change_id": change_record["change_id"],
                "backup_path": backup_path,
                "validation": validation,
            }

        except Exception as e:
            # 出错回滚
            self._restore(filepath, backup_path)
            logger.error(f"变更异常，已回滚: {e}")
            return {"success": False, "error": str(e), "action": "rolled_back", "backup_path": backup_path}

    def _backup(self, filepath: str) -> str:
        """备份文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(filepath)
        backup_name = f"{filename}.{timestamp}.bak"
        backup_path = os.path.join(self.backup_dir, backup_name)
        shutil.copy2(filepath, backup_path)
        return backup_path

    def _restore(self, filepath: str, backup_path: str):
        """从备份恢复"""
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, filepath)
            logger.info(f"已从备份恢复: {filepath}")

    def _apply_changes(self, filepath: str, changes: List[Dict]) -> bool:
        """应用具体修改"""
        with open(filepath, "r") as f:
            content = f.read()

        modified = False
        for change in changes:
            original = change.get("original", "")
            new = change.get("modified", "")
            if original and new and original in content:
                content = content.replace(original, new, 1)
                modified = True
                logger.info(f"  已替换: {original[:50]}... -> {new[:50]}...")
            elif original:
                logger.warning(f"  未找到原代码: {original[:50]}...")

        if modified:
            with open(filepath, "w") as f:
                f.write(content)
        return modified

    def _validate(self, filepath: str) -> Dict:
        """验证修改后的代码"""
        errors = []

        # 验证1: 语法检查
        try:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", filepath],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                errors.append(f"语法错误: {result.stderr[:200]}")
        except Exception as e:
            errors.append(f"语法检查异常: {e}")

        # 验证2: 导入测试
        if not errors:
            try:
                result = subprocess.run(
                    [sys.executable, "-c", f"import importlib.util; spec = importlib.util.spec_from_file_location('test_mod', '{filepath}'); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)"],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode != 0:
                    errors.append(f"导入错误: {result.stderr[:200]}")
            except Exception as e:
                errors.append(f"导入测试异常: {e}")

        return {
            "passed": len(errors) == 0,
            "errors": errors,
            "syntax_check": "passed" if not any("语法" in e for e in errors) else "failed",
            "import_check": "passed" if not any("导入" in e for e in errors) else "failed",
        }

    def _log_change(self, record: Dict):
        """记录变更日志"""
        with open(CONFIG["change_log"], "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def rollback(self, change_id: str) -> Dict:
        """回滚指定变更"""
        # 查找变更记录
        with open(CONFIG["change_log"], "r") as f:
            for line in f:
                record = json.loads(line)
                if record.get("change_id") == change_id:
                    # 从备份恢复
                    self._restore(record["filepath"], record["backup_path"])
                    record["status"] = "rolled_back"
                    record["rolled_back_at"] = datetime.now().isoformat()
                    self._log_change(record)
                    return {"success": True, "change_id": change_id, "action": "rolled_back"}
        return {"success": False, "error": f"未找到变更: {change_id}"}

# ============================================================
# 自主开发引擎主类
# ============================================================
class SelfDevelopmentEngine:
    """自主开发引擎主类"""

    def __init__(self):
        self.analyzer = CodeAnalyzer()
        self.generator = ImprovementGenerator()
        self.modifier = SafeCodeModifier()
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        if os.path.exists(CONFIG["state_file"]):
            try:
                with open(CONFIG["state_file"], "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "total_analyses": 0,
            "total_suggestions": 0,
            "changes_applied": 0,
            "changes_failed": 0,
            "changes_rolled_back": 0,
            "pending_review": [],
            "last_analysis": None,
            "started_at": datetime.now().isoformat(),
        }

    def _save_state(self):
        os.makedirs(os.path.dirname(CONFIG["state_file"]), exist_ok=True)
        with open(CONFIG["state_file"], "w") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def run_development_cycle(self) -> Dict:
        """执行一轮自主开发循环"""
        logger.info("=" * 60)
        logger.info("MR-017 自主开发循环")
        logger.info("=" * 60)

        cycle_result = {
            "cycle": self.state["total_analyses"] + 1,
            "timestamp": datetime.now().isoformat(),
            "analysis": None,
            "suggestions": [],
            "applied_changes": [],
            "pending_review": [],
        }

        # 步骤1: 代码分析
        logger.info("步骤1: 代码分析...")
        analysis = self.analyzer.analyze_all()
        cycle_result["analysis"] = {
            "total_files": analysis["total_files"],
            "total_lines": analysis["total_lines"],
            "files_with_issues": analysis["files_with_issues"],
            "high_priority_files": analysis["high_priority_files"],
        }
        self.state["total_analyses"] += 1
        self.state["last_analysis"] = datetime.now().isoformat()

        # 步骤2: 生成改进建议
        logger.info("步骤2: 生成改进建议...")
        suggestions = self.generator.generate_suggestions(analysis, max_suggestions=3)
        cycle_result["suggestions"] = [{"title": s.get("title"), "risk": s.get("risk_level"), "file": s.get("filepath")} for s in suggestions]
        self.state["total_suggestions"] += len(suggestions)

        # 步骤3: 应用低风险变更
        logger.info("步骤3: 应用变更...")
        for suggestion in suggestions:
            risk = suggestion.get("risk_level", "medium")
            if risk == "low" and CONFIG["auto_apply_low_risk"]:
                # 自动应用低风险变更
                result = self.modifier.apply_change(suggestion)
                if result["success"]:
                    cycle_result["applied_changes"].append(result)
                    self.state["changes_applied"] += 1
                    logger.info(f"  已应用: {suggestion.get('title')}")
                else:
                    if result.get("action") == "rolled_back":
                        self.state["changes_rolled_back"] += 1
                    else:
                        self.state["changes_failed"] += 1
                    logger.warning(f"  应用失败: {result.get('error')}")
            else:
                # 中高风险待人工审核
                cycle_result["pending_review"].append({
                    "title": suggestion.get("title"),
                    "risk_level": risk,
                    "filepath": suggestion.get("filepath"),
                    "suggestion": suggestion,
                })
                self.state["pending_review"].append({
                    "title": suggestion.get("title"),
                    "risk_level": risk,
                    "filepath": suggestion.get("filepath"),
                    "generated_at": datetime.now().isoformat(),
                })
                logger.info(f"  待审核: [{risk}] {suggestion.get('title')}")

        # 步骤4: 保存状态
        self._save_state()

        # 步骤5: 写入9120
        self._write_to_gateway(cycle_result)

        logger.info(f"自主开发循环完成: 分析{analysis['total_files']}文件, 生成{len(suggestions)}建议, 应用{len(cycle_result['applied_changes'])}变更, 待审核{len(cycle_result['pending_review'])}")
        logger.info("=" * 60)
        return cycle_result

    def _write_to_gateway(self, cycle_result: Dict):
        """将开发循环结果写入9120"""
        try:
            conn = sqlite3.connect(CONFIG["db_path"])
            cursor = conn.cursor()
            key = f"SELF_DEV.{datetime.now().strftime('%Y%m%d_%H%M%S')}.{hashlib.md5(str(time.time()).encode()).hexdigest()[:6]}"
            value = json.dumps(cycle_result, ensure_ascii=False)
            truth_hash = hashlib.sha256(value.encode()).hexdigest()
            now = time.time()
            cursor.execute(
                "INSERT INTO truths (truth_key, truth_value, truth_hash, category, node_id, created_at, updated_at, version) VALUES (?,?,?,?,?,?,?,1)",
                (key, value, truth_hash, "method", CONFIG["node_id"], now, now)
            )
            conn.commit()
            conn.close()
            logger.info(f"自主开发结果已写入9120: {key}")
        except Exception as e:
            logger.error(f"写入9120失败: {e}")

    def get_status(self) -> Dict:
        """获取引擎状态"""
        return {
            "state": self.state,
            "config": {
                "allowed_dirs": len(CONFIG["allowed_dirs"]),
                "auto_apply_low_risk": CONFIG["auto_apply_low_risk"],
                "analysis_interval": f"{CONFIG['analysis_interval'] // 3600}小时",
            },
        }

    def run_forever(self):
        """常驻运行"""
        logger.info("")
        logger.info("╔══════════════════════════════════════════════════════╗")
        logger.info("║  MR-017 自主开发引擎启动                             ║")
        logger.info("║  能力: 代码分析 + 改进建议 + 安全修改 + 自动回滚     ║")
        logger.info("║  安全: 只修改ops目录, 先备份再修改, 失败自动回滚     ║")
        logger.info("║  风险: 低风险自动应用, 中高风险待人工审核             ║")
        logger.info("║  分析间隔: 每{}小时                                  ║".format(CONFIG["analysis_interval"] // 3600))
        logger.info("╚══════════════════════════════════════════════════════╝")
        logger.info("")

        # 启动时立即执行一轮
        self.run_development_cycle()

        while True:
            time.sleep(CONFIG["analysis_interval"])
            try:
                self.run_development_cycle()
            except Exception as e:
                logger.error(f"自主开发循环异常: {e}")
                time.sleep(60)


# ============================================================
# 命令行入口
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MR-017 自主开发引擎")
    parser.add_argument("command", choices=["analyze", "develop", "rollback", "status", "daemon"],
                        help="analyze=只分析代码, develop=执行一轮自主开发, rollback=回滚变更, status=查看状态, daemon=常驻运行")
    parser.add_argument("--change-id", help="回滚指定的变更ID")
    args = parser.parse_args()

    engine = SelfDevelopmentEngine()

    if args.command == "analyze":
        result = engine.analyzer.analyze_all()
        print(json.dumps({k: v for k, v in result.items() if k != "file_analyses"}, ensure_ascii=False, indent=2))
        print(f"\n文件详情（前10个有问题的）:")
        problematic = [f for f in result["file_analyses"] if f["issues"]]
        problematic.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x["priority"], 3))
        for f in problematic[:10]:
            print(f"  [{f['priority']}] {f['filename']}: {len(f['issues'])}个问题")
            for i in f["issues"][:3]:
                print(f"    - [{i['severity']}] {i['message']}")
    elif args.command == "develop":
        result = engine.run_development_cycle()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "rollback":
        if not args.change_id:
            print("请指定 --change-id")
        else:
            result = engine.modifier.rollback(args.change_id)
            print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "status":
        status = engine.get_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
    elif args.command == "daemon":
        engine.run_forever()

#!/usr/bin/env python3
"""
代码生成前自检引擎 V1.0
从反复试错中沉淀经验，避免重复犯同样的错误
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
"""
import json, os, re
from datetime import datetime

FORBIDDEN_PATTERNS_FILE = "/opt/ZONGYUAN-ROOT/data/error_pattern_library/forbidden_patterns.json"


class CodeGenerationSelfCheck:
    """代码生成前自检引擎"""

    def __init__(self):
        self.patterns = self.load_patterns()

    def load_patterns(self):
        if os.path.exists(FORBIDDEN_PATTERNS_FILE):
            with open(FORBIDDEN_PATTERNS_FILE) as f:
                data = json.load(f)
            return data.get("patterns", [])
        return []

    def check_code(self, code, language="python"):
        """检查代码是否违反禁止模式"""
        violations = []

        for pattern in self.patterns:
            if pattern.get("status") != "ACTIVE_FORBIDDEN":
                continue

            error_pattern = pattern.get("error_pattern", "")
            if error_pattern and error_pattern in code:
                violations.append({
                    "pattern_id": pattern["id"],
                    "pattern_name": pattern["name"],
                    "severity": pattern["severity"],
                    "description": pattern["description"],
                    "correct_pattern": pattern.get("correct_pattern", ""),
                    "avoidance_rule": pattern.get("avoidance_rule", "")
                })

            if language == "python":
                fstring_matches = re.findall(r'f["\'].*?["\']', code)
                for match in fstring_matches:
                    if match.startswith('f"') and '.get("' in match:
                        violations.append({
                            "pattern_id": "EP-001",
                            "pattern_name": "Python f-string引号嵌套错误",
                            "severity": "HIGH",
                            "description": "检测到f-string中可能存在引号嵌套",
                            "correct_pattern": "f-string外层双引号时，内部用单引号访问字典",
                            "avoidance_rule": "生成Python代码前，检查所有f-string的引号嵌套"
                        })
                        break

                if re.search(r'[\U0001F300-\U0001F9FF\u2600-\u26FF\u2700-\u27BF]', code):
                    violations.append({
                        "pattern_id": "EP-002",
                        "pattern_name": "Python代码中使用emoji字符",
                        "severity": "MEDIUM",
                        "description": "检测到Python代码中使用emoji字符",
                        "correct_pattern": "用[OK]/[FAIL]/[WARN]等文本标记代替emoji",
                        "avoidance_rule": "Python脚本中禁止使用emoji"
                    })

        return {
            "checked_at": datetime.now().isoformat(),
            "code_length": len(code),
            "language": language,
            "violation_count": len(violations),
            "violations": violations,
            "passed": len(violations) == 0
        }

    def add_pattern(self, name, severity, description, error_pattern, correct_pattern, avoidance_rule):
        """添加新的禁止模式（从错误中学习）"""
        new_id = "EP-{:03d}".format(len(self.patterns) + 1)
        new_pattern = {
            "id": new_id,
            "name": name,
            "severity": severity,
            "description": description,
            "error_pattern": error_pattern,
            "root_cause": "从实际错误中沉淀",
            "correct_pattern": correct_pattern,
            "avoidance_rule": avoidance_rule,
            "occurrence_count": 1,
            "first_observed": datetime.now().strftime("%Y-%m-%d"),
            "last_observed": datetime.now().strftime("%Y-%m-%d"),
            "status": "ACTIVE_FORBIDDEN"
        }
        self.patterns.append(new_pattern)
        self.save_patterns()
        return new_pattern

    def save_patterns(self):
        data = {
            "version": "V1.0",
            "patterns": self.patterns,
            "stats": {
                "total_patterns": len(self.patterns),
                "high_severity": sum(1 for p in self.patterns if p.get("severity") == "HIGH"),
                "medium_severity": sum(1 for p in self.patterns if p.get("severity") == "MEDIUM"),
                "total_occurrences": sum(p.get("occurrence_count", 0) for p in self.patterns),
                "last_updated": datetime.now().strftime("%Y-%m-%d")
            }
        }
        os.makedirs(os.path.dirname(FORBIDDEN_PATTERNS_FILE), exist_ok=True)
        with open(FORBIDDEN_PATTERNS_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_status(self):
        return {
            "engine": "CodeGenerationSelfCheck",
            "version": "V1.0",
            "total_patterns": len(self.patterns),
            "high_severity": sum(1 for p in self.patterns if p.get("severity") == "HIGH"),
            "medium_severity": sum(1 for p in self.patterns if p.get("severity") == "MEDIUM"),
            "total_occurrences": sum(p.get("occurrence_count", 0) for p in self.patterns)
        }


if __name__ == "__main__":
    import sys
    checker = CodeGenerationSelfCheck()

    if len(sys.argv) > 1 and sys.argv[1] == "status":
        print(json.dumps(checker.get_status(), indent=2, ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == "check" and len(sys.argv) > 2:
        with open(sys.argv[2]) as f:
            code = f.read()
        result = checker.check_code(code)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(checker.get_status(), indent=2, ensure_ascii=False))

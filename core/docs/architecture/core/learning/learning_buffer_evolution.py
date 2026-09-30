"""
学习缓冲区进化处理器
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω

对S/A级问题执行进化处理，生成优化模式
"""
import json
from dataclasses import dataclass, asdict
from typing import List
from enum import Enum


class Grade(Enum):
    S = "S"
    A = "A"
    B = "B"
    C = "C"
    D = "D"


@dataclass
class LearningEntry:
    """学习缓冲区条目"""
    entry_id: str
    question: str
    answer: str
    grade: str
    context: dict
    learned_at: str


class LearningBufferEvolution:
    """学习缓冲区进化处理器"""

    def __init__(self):
        self.entries = []
        self.optimization_patterns = []

    def add_entry(self, entry: LearningEntry):
        """添加学习条目"""
        self.entries.append(entry)

    def process_high_grade(self) -> dict:
        """处理S/A级条目，生成优化模式"""
        high_grade = [
            e for e in self.entries
            if e.grade in [Grade.S.value, Grade.A.value]
        ]

        patterns = []
        for entry in high_grade:
            pattern = self._generate_pattern(entry)
            patterns.append(pattern)
            self.optimization_patterns.append(pattern)

        return {
            "processed_count": len(high_grade),
            "patterns_generated": len(patterns),
            "patterns": patterns
        }

    def _generate_pattern(self, entry: LearningEntry) -> dict:
        """从单个条目生成优化模式"""
        return {
            "pattern_id": f"OPT-{entry.entry_id}",
            "trigger_context": entry.context,
            "optimal_response": entry.answer,
            "source_question": entry.question,
            "grade": entry.grade,
            "applied_count": 0
        }

    def get_patterns(self) -> List[dict]:
        """获取所有优化模式"""
        return self.optimization_patterns

    def stats(self) -> dict:
        """统计信息"""
        by_grade = {}
        for e in self.entries:
            by_grade[e.grade] = by_grade.get(e.grade, 0) + 1

        return {
            "total_entries": len(self.entries),
            "by_grade": by_grade,
            "optimization_patterns": len(self.optimization_patterns)
        }


# 使用示例
if __name__ == "__main__":
    processor = LearningBufferEvolution()

    # 添加测试条目
    processor.add_entry(LearningEntry(
        entry_id="E001",
        question="如何处理内存泄漏？",
        answer="分析进程内存分配，优化连接池配置，定期重启worker",
        grade="A",
        context={"scenario": "memory_optimization"},
        learned_at="2026-09-09"
    ))

    result = processor.process_high_grade()
    print(f"处理结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

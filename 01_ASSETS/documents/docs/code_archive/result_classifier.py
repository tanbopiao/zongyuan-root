"""
成果自动分类器 V1.0
基于规则+关键词的成果分类，支持类型/元类/标签/优先级多维分类。

确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass

from interfaces.mechanism_interfaces import (
    ResultMetadata, ResultType, MetaClass, Priority, ProcessingResult
)


@dataclass
class ClassificationResult:
    """分类结果"""
    result_type: ResultType
    meta_class: MetaClass
    priority: Priority
    tags: List[str]
    confidence: float
    classification_reason: str


class ResultClassifier:
    """成果自动分类器"""

    # 关键词到元类的映射
    META_CLASS_KEYWORDS = {
        MetaClass.M1_ALGORITHM: ['算法', '代码', '程序', '函数', '类', '接口', 'API',
                                   '实现', '源码', '脚本', '工具', '库', '框架', 'engine'],
        MetaClass.M2_KERNEL: ['内核', '机制', '架构', '协议', '体系', '自治', '进化',
                               '算子', '元极恒一', 'ZONGYUAN', '闭环', '自洽', '智能体'],
        MetaClass.M3_PROTOCOL: ['协议', '规范', '标准', '接口定义', '契约', '规约',
                                 'SOP', '流程', '标准操作'],
        MetaClass.M4_THEORY: ['理论', '白皮书', '研究', '分析', '论文', '学术',
                               '概念', '模型', '方法论', '哲学', '公理', '定理'],
        MetaClass.M5_PRODUCT: ['产品', '方案', '设计', '规划', '路线图', '商业',
                                '定价', '功能', '需求', 'PRD', 'MVP'],
        MetaClass.M6_DELIVERY: ['报告', '交付', '文档', '总结', '汇报', '成果',
                                 '复盘', '总结报告', '检查报告'],
        MetaClass.M7_AUTOMATION: ['自动化', '调度', '定时', '巡检', '监控', '流水线',
                                   'CI/CD', '部署', '运维', '守护进程'],
        MetaClass.M8_INDUSTRY: ['行业', '市场', '竞品', '商业分析', '尽调',
                                 '法务', '案例', '企业'],
        MetaClass.M9_FOUNDATION: ['基础', '索引', '台账', '字典', '配置', '数据',
                                   '元数据', '全局', '根哈希', 'Merkle'],
    }

    # 关键词到优先级的映射
    PRIORITY_KEYWORDS = {
        Priority.P0_CRITICAL: ['核心', '关键', '紧急', '重要', '正式版', 'V1.0',
                                '生产', '上线', '发布', '安全', '故障', '漏洞'],
        Priority.P1_HIGH: ['机制', '架构', '协议', '体系', '升级', '优化', '重构',
                            '新功能', '里程碑', '阶段成果'],
        Priority.P2_MEDIUM: ['文档', '记录', '笔记', '草稿', '测试', '实验',
                              '临时', '备份'],
        Priority.P3_LOW: ['归档', '历史', '旧版', '废弃', '参考', '资料'],
    }

    # 标签关键词库
    TAG_KEYWORDS = [
        '物理仿真', '空间智能', '世界模型', '多模型', '场频谐振', '边缘设备',
        '具身智能', '成果可视化', '真值提炼', '元秩序', '锁档', '归档',
        '记忆网关', '因果推理', '奇点预测', '自进化', '自治', '轻量化',
        '商业化', '产品化', '工程化', '自动化', '可视化', '交互',
        '安全', '合规', '风险', '决策', '规划', '路线图',
        '火斗云智', 'AIOS', '昆仑洞天', '短剧', '派单系统', 'HRM',
        'EMMS', '评估标准', '断点检查', '补齐', '接口规范',
    ]

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self._classification_count = 0

    def classify(self, metadata: ResultMetadata, content: str = None) -> ProcessingResult:
        """
        对成果进行多维分类

        Args:
            metadata: 成果元数据
            content: 成果内容（可选，用于更精准分类）

        Returns:
            ProcessingResult，data中包含classification
        """
        self._classification_count += 1

        # 合并名称和内容用于关键词匹配
        text = f"{metadata.result_name} {' '.join(metadata.tags)}"
        if content:
            text += f" {content[:2000]}"  # 只取前2000字符
        text_lower = text.lower()

        # 1. 元类分类
        meta_class, meta_confidence, meta_reason = self._classify_meta_class(text_lower)

        # 2. 优先级分类
        priority, prio_confidence, prio_reason = self._classify_priority(text_lower, metadata.size_bytes)

        # 3. 标签提取
        tags = self._extract_tags(text_lower)

        # 4. 综合置信度
        overall_confidence = round((meta_confidence + prio_confidence) / 2, 2)

        # 5. 构建分类结果
        classification = ClassificationResult(
            result_type=metadata.result_type,
            meta_class=meta_class,
            priority=priority,
            tags=tags,
            confidence=overall_confidence,
            classification_reason=f"元类: {meta_reason}; 优先级: {prio_reason}"
        )

        # 更新元数据
        metadata.meta_class = meta_class
        metadata.priority = priority
        metadata.tags = list(set(metadata.tags + tags))[:8]  # 合并去重，最多8个
        metadata.confidence = max(metadata.confidence, overall_confidence)

        return ProcessingResult(
            success=True,
            message=f"分类完成: 元类={meta_class.value}, 优先级={priority.value}, 标签={len(tags)}个",
            data={
                "classification": {
                    "result_type": classification.result_type.value,
                    "meta_class": classification.meta_class.value,
                    "meta_class_name": classification.meta_class.name,
                    "priority": classification.priority.value,
                    "tags": classification.tags,
                    "confidence": classification.confidence,
                    "reason": classification.classification_reason,
                },
                "updated_metadata": self._metadata_to_dict(metadata),
            },
            processing_time_ms=0
        )

    def _classify_meta_class(self, text: str) -> Tuple[MetaClass, float, str]:
        """元类分类"""
        scores: Dict[MetaClass, int] = {}
        for meta_class, keywords in self.META_CLASS_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text)
            if score > 0:
                scores[meta_class] = score

        if not scores:
            return MetaClass.M4_THEORY, 0.5, "默认归类（无匹配关键词）"

        # 取最高分
        best = max(scores.items(), key=lambda x: x[1])
        total = sum(scores.values())
        confidence = round(best[1] / total, 2) if total > 0 else 0.5
        reason = f"匹配{best[1]}个关键词（{', '.join(self._get_matching_keywords(best[0], text)[:3])}）"

        return best[0], min(confidence, 0.95), reason

    def _classify_priority(self, text: str, file_size: int) -> Tuple[Priority, float, str]:
        """优先级分类"""
        for priority, keywords in self.PRIORITY_KEYWORDS.items():
            matches = [kw for kw in keywords if kw.lower() in text]
            if matches:
                confidence = min(0.7 + len(matches) * 0.1, 0.95)
                return priority, round(confidence, 2), f"匹配{len(matches)}个高优先级关键词"

        # 基于文件大小的辅助判断
        if file_size > 500 * 1024:  # >500KB
            return Priority.P1_HIGH, 0.6, "大文件（>500KB）默认高优先级"
        if file_size < 10 * 1024:  # <10KB
            return Priority.P3_LOW, 0.6, "小文件（<10KB）默认低优先级"

        return Priority.P2_MEDIUM, 0.5, "默认中优先级"

    def _extract_tags(self, text: str) -> List[str]:
        """提取标签"""
        tags = []
        for tag in self.TAG_KEYWORDS:
            if tag.lower() in text:
                tags.append(tag)
        return tags[:8]  # 最多8个标签

    def _get_matching_keywords(self, meta_class: MetaClass, text: str) -> List[str]:
        """获取匹配的关键词"""
        keywords = self.META_CLASS_KEYWORDS.get(meta_class, [])
        return [kw for kw in keywords if kw.lower() in text]

    def _metadata_to_dict(self, metadata: ResultMetadata) -> Dict:
        """元数据转字典"""
        return {
            "result_id": metadata.result_id,
            "result_name": metadata.result_name,
            "result_type": metadata.result_type.value,
            "meta_class": metadata.meta_class.value,
            "format": metadata.format,
            "size_bytes": metadata.size_bytes,
            "created_at": metadata.created_at,
            "creator": metadata.creator,
            "version": metadata.version,
            "tags": metadata.tags,
            "priority": metadata.priority.value,
            "confidence": metadata.confidence,
            "content_hash": metadata.content_hash,
        }

    def batch_classify(self, metadata_list: List[ResultMetadata]) -> ProcessingResult:
        """批量分类"""
        results = []
        for md in metadata_list:
            r = self.classify(md)
            if r.success:
                results.append(r.data.get("classification", {}))

        return ProcessingResult(
            success=True,
            message=f"批量分类完成: {len(results)}/{len(metadata_list)}",
            data={"classifications": results, "total": len(results)},
        )

    def get_status(self) -> Dict:
        """获取分类器状态"""
        return {
            "classification_count": self._classification_count,
            "supported_meta_classes": len(self.META_CLASS_KEYWORDS),
            "supported_priorities": len(self.PRIORITY_KEYWORDS),
            "tag_keywords_count": len(self.TAG_KEYWORDS),
            "status": "running",
        }

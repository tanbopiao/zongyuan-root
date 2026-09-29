#!/usr/bin/env python3
"""
自动分类归档提炼机制 V1.0
ZONGYUAN-ROOT 元极恒一自治体系

功能：
1. 从网关获取全量真值key列表
2. 自动分类unknown真值到九大元类
3. 提炼高价值结构化真值
4. 生成归档报告并上报网关

九大元类：公理/定理/方法/数据/案例/决策/创意/风险/协议

锚定：Ω₀⊂⊙∞⊂Ω | DID-BR-000002
"""

import json
import time
import datetime
import hashlib
import urllib.request
import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from collections import Counter, defaultdict

# ============ 配置 ============
GATEWAY_BASE = "https://www.huodouai.com"
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
SOURCE_NODE = "ZR-NODE-DC2E51C0"

# 九大元类定义
META_CLASSES = {
    "axiom": {
        "name": "公理类",
        "keywords": ["公理", "元规则", "meta_law", "metalaw", "META_LAW", "基础法则", "第一性原理",
                     "CONSTITUTION", "协议", "PROTOCOL", "规则", "RULE", "LAW", "宪法", "原则",
                     "PRINCIPLE", "FUNDAMENTAL", "基准", "BASELINE", "锚定", "ANCHOR", "确权",
                     "IDENTITY", "DID", "OMEGA", "ROOT", "核心法则"],
        "description": "不可动摇的基础公理与元规则"
    },
    "theorem": {
        "name": "定理类",
        "keywords": ["定理", "理论", "THEORY", "theorem", "模型", "MODEL", "公式", "FORMULA",
                     "推导", "证明", "PROOF", "数学", "MATHEMATICAL", "算法", "ALGORITHM",
                     "框架", "FRAMEWORK", "架构", "ARCHITECTURE", "范式", "PARADIGM"],
        "description": "经推导验证的理论定理与模型"
    },
    "method": {
        "name": "方法类",
        "keywords": ["方法", "METHOD", "SOP", "流程", "PIPELINE", "流水线", "操作", "PROCEDURE",
                     "技巧", "TECHNIQUE", "策略", "STRATEGY", "playbook", "指南", "GUIDE",
                     "教程", "TUTORIAL", "最佳实践", "BEST_PRACTICE", "工作流", "WORKFLOW",
                     "部署", "DEPLOY", "安装", "INSTALL", "配置", "CONFIG"],
        "description": "可执行的方法论与操作流程"
    },
    "data": {
        "name": "数据类",
        "keywords": ["数据", "DATA", "统计", "STATISTICS", "指标", "METRIC", "报表", "REPORT",
                     "日志", "LOG", "记录", "RECORD", "快照", "SNAPSHOT", "心跳", "HEARTBEAT",
                     "状态", "STATUS", "监控", "MONITOR", "观测", "OBSERVATION", "测量",
                     "MEASUREMENT", "采样", "SAMPLE", "AUDIT", "审计", "计数", "COUNT"],
        "description": "原始数据、统计指标与观测记录"
    },
    "case": {
        "name": "案例类",
        "keywords": ["案例", "CASE", "实例", "EXAMPLE", "实战", "实战闭环", "复盘", "RETROSPECTIVE",
                     "经验", "LESSON", "教训", "事件", "INCIDENT", "事故", "ACCIDENT",
                     "项目", "PROJECT", "任务", "TASK", "执行", "EXECUTION", "落地",
                     "IMPLEMENTATION", "成果", "ACHIEVEMENT", "完成", "COMPLETION"],
        "description": "实际案例、项目经验与事件复盘"
    },
    "decision": {
        "name": "决策类",
        "keywords": ["决策", "DECISION", "方案", "PLAN", "选择", "CHOICE", "评估", "EVALUATION",
                     "评审", "REVIEW", "审批", "APPROVAL", "决议", "RESOLUTION", "判断",
                     "JUDGMENT", "权衡", "TRADEOFF", "推荐", "RECOMMENDATION", "结论",
                     "CONCLUSION", "投票", "VOTE", "共识", "CONSENSUS"],
        "description": "决策记录、方案评估与审批结论"
    },
    "creative": {
        "name": "创意类",
        "keywords": ["创意", "CREATIVE", "设计", "DESIGN", "艺术", "ART", "作品", "ARTIFACT",
                     "创作", "CREATION", "灵感", "INSPIRATION", "创新", "INNOVATION",
                     "构想", "IDEA", "概念", "CONCEPT", "视觉", "VISUAL", "图像", "IMAGE",
                     "视频", "VIDEO", "音频", "AUDIO", "生成", "GENERATION", "海报", "POSTER"],
        "description": "创意作品、设计稿与生成内容"
    },
    "risk": {
        "name": "风险类",
        "keywords": ["风险", "RISK", "告警", "ALERT", "警告", "WARNING", "异常", "ANOMALY",
                     "断点", "BREAKPOINT", "故障", "FAILURE", "错误", "ERROR", "漏洞",
                     "VULNERABILITY", "威胁", "THREAT", "安全", "SECURITY", "合规",
                     "COMPLIANCE", "熔断", "CIRCUIT_BREAK", "降级", "DEGRADE", "应急",
                     "EMERGENCY", "红队", "RED"],
        "description": "风险识别、告警与安全合规"
    },
    "protocol": {
        "name": "协议类",
        "keywords": ["协议", "PROTOCOL", "接口", "API", "规范", "SPECIFICATION", "标准",
                     "STANDARD", "契约", "CONTRACT", "握手", "HANDSHAKE", "认证",
                     "AUTH", "授权", "AUTHORIZATION", "加密", "ENCRYPTION", "签名",
                     "SIGNATURE", "通信", "COMMUNICATION", "集成", "INTEGRATION",
                     "同步", "SYNC", "桥接", "BRIDGE", "适配", "ADAPTER"],
        "description": "通信协议、接口规范与集成契约"
    }
}

# ============ 数据结构 ============
@dataclass
class ClassifiedTruth:
    truth_key: str
    predicted_class: str
    confidence: float
    matched_keywords: List[str]
    original_category: str = "unknown"

@dataclass
class ClassificationResult:
    scan_time: str
    total_truths: int
    unknown_count: int
    classified_count: int
    failed_count: int
    class_distribution: Dict[str, int]
    high_value_extracted: int
    report_hash: str

# ============ 网关通信 ============
def gateway_get(path: str, timeout: int = 30) -> Tuple[int, dict]:
    url = f"{GATEWAY_BASE}{path}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return 0, {"error": str(e)}

def gateway_post(path: str, data: dict, timeout: int = 15) -> Tuple[int, dict]:
    url = f"{GATEWAY_BASE}{path}"
    body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=body, method='POST')
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return 0, {"error": str(e)}

# ============ 分类引擎 ============
class AutoClassifier:
    def __init__(self):
        self.meta_classes = META_CLASSES
        self.class_keyword_map = self._build_keyword_map()

    def _build_keyword_map(self) -> Dict[str, List[str]]:
        """构建关键词→类别的映射"""
        mapping = defaultdict(list)
        for class_id, class_info in self.meta_classes.items():
            for kw in class_info["keywords"]:
                mapping[kw.lower()].append(class_id)
        return mapping

    def classify(self, truth_key: str) -> Tuple[str, float, List[str]]:
        """对单个truth_key进行分类"""
        key_lower = truth_key.lower()
        scores = defaultdict(float)
        matched = []

        # 关键词匹配
        for kw, class_ids in self.class_keyword_map.items():
            if kw in key_lower:
                for cid in class_ids:
                    scores[cid] += 1.0
                    matched.append(kw)

        # 模式匹配增强
        # 日期结尾的通常是数据/记录类
        if re.search(r'\d{8}$', truth_key):
            scores["data"] += 0.5
        # HEARTBEAT/STATUS/MONITOR开头
        if re.match(r'^(HEARTBEAT|STATUS|MONITOR|OBSERVATION|AUDIT|LOG)', truth_key, re.I):
            scores["data"] += 1.5
        # DECISION/APPROVAL/PLAN开头
        if re.match(r'^(DECISION|APPROVAL|PLAN|EVALUATION|REVIEW)', truth_key, re.I):
            scores["decision"] += 1.5
        # RISK/ALERT/WARNING/ERROR开头
        if re.match(r'^(RISK|ALERT|WARNING|ERROR|ANOMALY|BREAKPOINT)', truth_key, re.I):
            scores["risk"] += 1.5
        # PROTOCOL/API/HANDSHAKE/AUTH开头
        if re.match(r'^(PROTOCOL|API|HANDSHAKE|AUTH|INTEGRATION|SYNC)', truth_key, re.I):
            scores["protocol"] += 1.5
        # CREATIVE/DESIGN/ART/GENERATION开头
        if re.match(r'^(CREATIVE|DESIGN|ART|GENERATION|IMAGE|VIDEO)', truth_key, re.I):
            scores["creative"] += 1.5
        # METHOD/SOP/PIPELINE/GUIDE开头
        if re.match(r'^(METHOD|SOP|PIPELINE|GUIDE|WORKFLOW|DEPLOY)', truth_key, re.I):
            scores["method"] += 1.5
        # THEORY/MODEL/THEOREM开头
        if re.match(r'^(THEORY|MODEL|THEOREM|FRAMEWORK|ARCHITECTURE)', truth_key, re.I):
            scores["theorem"] += 1.5
        # AXIOM/META_LAW/RULE/CONSTITUTION开头
        if re.match(r'^(AXIOM|META_LAW|METALAW|RULE|CONSTITUTION|PRINCIPLE)', truth_key, re.I):
            scores["axiom"] += 1.5
        # CASE/EXAMPLE/INCIDENT/RETROSPECTIVE开头
        if re.match(r'^(CASE|EXAMPLE|INCIDENT|RETROSPECTIVE|PROJECT)', truth_key, re.I):
            scores["case"] += 1.5

        if not scores:
            return "unknown", 0.0, []

        # 找出最高分
        best_class = max(scores, key=scores.get)
        best_score = scores[best_class]
        total_score = sum(scores.values())
        confidence = min(best_score / total_score, 0.95) if total_score > 0 else 0.0

        # 如果最高分很低，标记为low_confidence
        if best_score < 1.0:
            return "unknown", 0.3, matched

        return best_class, round(confidence, 3), matched[:5]

# ============ 提炼引擎 ============
class RefinementEngine:
    """从分类结果中提炼高价值真值"""

    def extract_high_value(self, classified: List[ClassifiedTruth]) -> List[ClassifiedTruth]:
        """提取高价值真值（高置信度+关键类别）"""
        high_value_classes = {"axiom", "theorem", "decision", "protocol", "risk"}
        return [
            t for t in classified
            if t.confidence >= 0.7 and t.predicted_class in high_value_classes
        ]

    def generate_summary(self, classified: List[ClassifiedTruth]) -> str:
        """生成分类摘要"""
        dist = Counter(t.predicted_class for t in classified)
        lines = ["自动分类归档提炼结果："]
        lines.append(f"共处理{len(classified)}条unknown分类真值")
        for class_id, count in dist.most_common():
            class_info = META_CLASSES.get(class_id, {"name": class_id})
            lines.append(f"  {class_info['name']}({class_id}): {count}条")
        return "\n".join(lines)

# ============ 主流程 ============
def run_classification():
    print("=" * 60)
    print("自动分类归档提炼机制 V1.0")
    print(f"锚定: {ANCHOR} | DID: {DID}")
    print(f"时间: {datetime.datetime.now().isoformat()}")
    print("=" * 60)

    # Step 1: 获取全量真值
    print("\n[1/5] 获取全量真值列表...")
    code, data = gateway_get("/api/report/truths")
    if code != 200:
        print(f"  获取失败: HTTP {code}")
        return None

    all_truths = data.get("truths", [])
    total = data.get("count", len(all_truths))
    print(f"  获取成功: {total}条")

    # Step 2: 筛选unknown分类
    print("\n[2/5] 筛选unknown分类真值...")
    # 由于API只返回key，我们通过key特征判断是否为unknown
    # 已知分类前缀（大写标准前缀）通常不是unknown
    known_prefixes = {"HEARTBEAT", "TRUTH", "AUTONOMY", "BREAKPOINT", "CLASSIFICATION",
                      "AUTO_", "META_", "SYSTEM", "GATEWAY", "APPROVAL", "DEPLOY",
                      "V3", "CTE", "SM", "BS", "P4", "P7", "LV", "DID", "OMEGA"}

    unknown_truths = []
    for key in all_truths:
        if not key:
            continue
        # 简单判断：如果key不在已知前缀中，且不含明确分类标识，视为unknown
        prefix = key.split('.')[0] if '.' in key else key
        # 实际上，我们对所有key都尝试分类，重点处理那些分类不明确的
        unknown_truths.append(key)

    print(f"  待分类: {len(unknown_truths)}条")

    # Step 3: 自动分类
    print("\n[3/5] 执行自动分类...")
    classifier = AutoClassifier()
    classified = []
    batch_size = 500

    for i, key in enumerate(unknown_truths):
        pred_class, confidence, matched = classifier.classify(key)
        classified.append(ClassifiedTruth(
            truth_key=key,
            predicted_class=pred_class,
            confidence=confidence,
            matched_keywords=matched
        ))
        if (i + 1) % batch_size == 0:
            print(f"  已处理 {i+1}/{len(unknown_truths)}...")

    # 统计
    dist = Counter(t.predicted_class for t in classified)
    high_conf = sum(1 for t in classified if t.confidence >= 0.7)
    still_unknown = dist.get("unknown", 0)

    print(f"  分类完成: 高置信度{high_conf}条, 仍unknown {still_unknown}条")
    print(f"  分布:")
    for class_id, count in dist.most_common():
        class_info = META_CLASSES.get(class_id, {"name": class_id})
        print(f"    {class_info['name']}({class_id}): {count}条")

    # Step 4: 提炼高价值真值
    print("\n[4/5] 提炼高价值真值...")
    engine = RefinementEngine()
    high_value = engine.extract_high_value(classified)
    print(f"  提炼高价值真值: {len(high_value)}条")

    # Step 5: 上报结果
    print("\n[5/5] 上报分类结果...")
    summary = engine.generate_summary(classified)
    report_data = {
        "scan_time": datetime.datetime.now().isoformat(),
        "total_truths": total,
        "classified_count": len(classified) - still_unknown,
        "still_unknown": still_unknown,
        "high_confidence": high_conf,
        "high_value_extracted": len(high_value),
        "class_distribution": dict(dist),
        "did": DID,
        "anchor": ANCHOR
    }
    report_hash = hashlib.sha256(json.dumps(report_data, sort_keys=True).encode()).hexdigest()

    # 上报分类报告
    payload = {
        "truth_key": f"CLASSIFICATION.AUTO_ARCHIVE.REPORT.{datetime.datetime.now().strftime('%Y%m%d%H%M')}",
        "truth_value": f"{summary}\n高价值提炼{len(high_value)}条。报告哈希{report_hash[:16]}。确权{DID}，锚定{ANCHOR}。",
        "source_node": SOURCE_NODE,
        "confidence": 0.92,
        "truth_type": "meta_law"
    }
    code, resp = gateway_post("/api/report/truth", payload)
    print(f"  上报: HTTP {code}, success={resp.get('success')}, truth_count={resp.get('truth_count')}")

    # 上报高价值真值样本（前10条）
    print("\n  上报高价值真值样本...")
    for i, item in enumerate(high_value[:10]):
        class_info = META_CLASSES.get(item.predicted_class, {"name": item.predicted_class})
        sample_payload = {
            "truth_key": f"CLASSIFIED.{item.predicted_class.upper()}.{int(time.time())}_{i}",
            "truth_value": f"自动分类归档：原key={item.truth_key[:80]}，预测类别={class_info['name']}，置信度={item.confidence}，匹配关键词={','.join(item.matched_keywords[:3])}。确权{DID}，锚定{ANCHOR}。",
            "source_node": SOURCE_NODE,
            "confidence": item.confidence,
            "truth_type": item.predicted_class if item.predicted_class in ["data","risk","creative","protocol","decision"] else "meta_law"
        }
        gateway_post("/api/report/truth", sample_payload)
        time.sleep(0.2)

    result = ClassificationResult(
        scan_time=datetime.datetime.now().isoformat(),
        total_truths=total,
        unknown_count=len(unknown_truths),
        classified_count=len(classified) - still_unknown,
        failed_count=still_unknown,
        class_distribution=dict(dist),
        high_value_extracted=len(high_value),
        report_hash=report_hash
    )

    print(f"\n{'=' * 60}")
    print(f"分类归档完成！报告哈希: {report_hash[:16]}...")
    print(f"{'=' * 60}")

    return result

if __name__ == "__main__":
    run_classification()

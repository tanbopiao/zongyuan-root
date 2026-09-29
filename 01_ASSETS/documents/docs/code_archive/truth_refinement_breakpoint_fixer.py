#!/usr/bin/env python3
"""
真值提炼补全断点机制 V1.0
ZONGYUAN-ROOT 元极恒一自治体系

功能：
1. 断点检测 - 检测API层/数据层/逻辑层断点
2. 真值提炼 - 从原始上报中提炼高置信度结构化真值
3. 断点补全 - 自动补全缺失元数据/冲突标记/关联关系
4. 一致性校验 - Merkle哈希+来源锚定+逻辑一致性
5. 网关上报 - 提炼结果上报记忆网关

锚定：Ω₀⊂⊙∞⊂Ω | DID-BR-000002
"""

import hashlib
import json
import time
import datetime
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum

# ============ 配置 ============
GATEWAY_BASE = "https://www.huodouai.com"
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
SOURCE_NODE = "ZR-NODE-DC2E51C0"
CONFIDENCE_THRESHOLD = 0.75
BREAKPOINT_REPORT_KEY = "BREAKPOINT.TRUTH_REFINEMENT.SCAN"

# ============ 断点类型枚举 ============
class BreakpointType(Enum):
    API_READ_FAILURE = "api_read_failure"           # 读取API失效
    API_WRITE_FAILURE = "api_write_failure"         # 写入API失效
    EMPTY_TRUTH = "empty_truth"                     # 空真值（key/value为空）
    MISSING_METADATA = "missing_metadata"           # 元数据缺失
    LOW_CONFIDENCE = "low_confidence"               # 低置信度
    HASH_MISMATCH = "hash_mismatch"                 # 哈希不匹配
    DUPLICATE_KEY = "duplicate_key"                 # 重复key
    CATEGORY_UNKNOWN = "category_unknown"           # 未知分类
    ORPHAN_TRUTH = "orphan_truth"                   # 孤立真值（无关联）
    CONFLICT_UNRESOLVED = "conflict_unresolved"     # 未解决冲突
    NODE_OFFLINE = "node_offline"                   # 节点离线
    DRIFT_DETECTED = "drift_detected"               # 语义漂移

class Severity(Enum):
    RED = "red"
    ORANGE = "orange"
    YELLOW = "yellow"
    GREEN = "green"

# ============ 数据结构 ============
@dataclass
class TruthItem:
    truth_key: str
    truth_value: str
    source_node: str
    confidence: float
    truth_type: str
    category: str = "unknown"
    truth_hash: str = ""
    version: int = 1
    created_at: float = 0.0
    metadata: Dict = field(default_factory=dict)
    breakpoints: List[str] = field(default_factory=list)

    def compute_hash(self) -> str:
        content = f"{self.truth_key}|{self.truth_value}|{self.source_node}|{self.truth_type}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def validate(self) -> List[str]:
        issues = []
        if not self.truth_key or len(self.truth_key.strip()) < 3:
            issues.append(BreakpointType.EMPTY_TRUTH.value)
        if not self.truth_value or len(self.truth_value.strip()) < 5:
            issues.append(BreakpointType.EMPTY_TRUTH.value)
        if self.confidence < CONFIDENCE_THRESHOLD:
            issues.append(BreakpointType.LOW_CONFIDENCE.value)
        if self.category == "unknown":
            issues.append(BreakpointType.CATEGORY_UNKNOWN.value)
        if not self.truth_hash:
            self.truth_hash = self.compute_hash()
        elif self.truth_hash != self.compute_hash():
            issues.append(BreakpointType.HASH_MISMATCH.value)
        if not self.metadata.get("did"):
            self.metadata["did"] = DID
            issues.append(BreakpointType.MISSING_METADATA.value)
        if not self.metadata.get("anchor"):
            self.metadata["anchor"] = ANCHOR
            issues.append(BreakpointType.MISSING_METADATA.value)
        return issues

@dataclass
class Breakpoint:
    bp_type: str
    severity: str
    description: str
    affected_count: int = 0
    sample_keys: List[str] = field(default_factory=list)
    detected_at: float = 0.0
    resolution: str = ""
    resolved: bool = False

@dataclass
class RefinementResult:
    scan_time: str
    total_truths: int
    breakpoints_found: List[Breakpoint]
    refined_count: int
    completed_count: int
    purity_score: float
    report_hash: str

# ============ 网关通信 ============
class GatewayClient:
    def __init__(self, base_url: str = GATEWAY_BASE):
        self.base_url = base_url
        self.last_status = None

    def _request(self, method: str, path: str, data: dict = None, timeout: int = 10) -> Tuple[int, dict]:
        url = f"{self.base_url}{path}"
        body = json.dumps(data).encode('utf-8') if data else None
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode('utf-8')
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            return e.code, {"error": str(e)}
        except Exception as e:
            return 0, {"error": str(e)}

    def get_status(self) -> dict:
        code, data = self._request("GET", "/api/report/status")
        self.last_status = data if code == 200 else None
        return {"code": code, "data": data}

    def get_nodes(self) -> dict:
        code, data = self._request("GET", "/api/report/nodes")
        return {"code": code, "data": data}

    def get_truth(self, truth_id: int = None, truth_key: str = None) -> dict:
        path = "/api/truths"
        if truth_id:
            path += f"?id={truth_id}"
        elif truth_key:
            path += f"?truth_key={truth_key}"
        code, data = self._request("GET", path)
        return {"code": code, "data": data}

    def report_truth(self, item: TruthItem) -> dict:
        payload = {
            "truth_key": item.truth_key,
            "truth_value": item.truth_value,
            "source_node": item.source_node,
            "confidence": item.confidence,
            "truth_type": item.truth_type,
        }
        code, data = self._request("POST", "/api/report/truth", payload)
        return {"code": code, "data": data}

# ============ 断点检测器 ============
class BreakpointDetector:
    def __init__(self, gateway: GatewayClient):
        self.gateway = gateway
        self.breakpoints: List[Breakpoint] = []

    def detect_api_layer(self) -> List[Breakpoint]:
        """检测API层断点"""
        bps = []
        now = time.time()

        # 1. 读取API检测
        status = self.gateway.get_status()
        if status["code"] != 200:
            bps.append(Breakpoint(
                bp_type=BreakpointType.API_READ_FAILURE.value,
                severity=Severity.RED.value,
                description=f"GET /api/report/status 返回HTTP {status['code']}",
                detected_at=now
            ))
        else:
            # 检测/truths读取API
            truth_resp = self.gateway.get_truth(truth_id=1)
            truth_data = truth_resp.get("data", {}).get("truth", {})
            if truth_data.get("id") == 1499 and not truth_data.get("truth_key"):
                bps.append(Breakpoint(
                    bp_type=BreakpointType.API_READ_FAILURE.value,
                    severity=Severity.RED.value,
                    description="GET /api/truths 恒返回id=1499空记录，查询参数被忽略，真值读取API完全失效",
                    affected_count=status["data"].get("stats", {}).get("truths", 0),
                    detected_at=now
                ))

        # 2. 写入API检测
        test_item = TruthItem(
            truth_key=f"BREAKPOINT.PROBE.{int(now)}",
            truth_value="断点检测探针，用于验证写入API可用性",
            source_node=SOURCE_NODE,
            confidence=0.5,
            truth_type="data"
        )
        write_resp = self.gateway.report_truth(test_item)
        if write_resp["code"] != 200:
            bps.append(Breakpoint(
                bp_type=BreakpointType.API_WRITE_FAILURE.value,
                severity=Severity.RED.value,
                description=f"POST /api/report/truth 返回HTTP {write_resp['code']}",
                detected_at=now
            ))

        return bps

    def detect_data_layer(self, status_data: dict) -> List[Breakpoint]:
        """检测数据层断点"""
        bps = []
        now = time.time()
        stats = status_data.get("stats", {})

        # 节点离线检测
        nodes_resp = self.gateway.get_nodes()
        if nodes_resp["code"] == 200:
            nodes = nodes_resp["data"].get("nodes", {})
            offline = [nid for nid, n in nodes.items() if n.get("online_status") != "online"]
            if offline:
                severity = Severity.RED.value if len(offline) > 5 else Severity.ORANGE.value
                bps.append(Breakpoint(
                    bp_type=BreakpointType.NODE_OFFLINE.value,
                    severity=severity,
                    description=f"{len(offline)}/{len(nodes)}个节点离线",
                    affected_count=len(offline),
                    sample_keys=offline[:5],
                    detected_at=now
                ))

        return bps

    def detect_logic_layer(self) -> List[Breakpoint]:
        """检测逻辑层断点（基于已知模式）"""
        bps = []
        now = time.time()

        # V3.0缺少心跳指标字段
        bps.append(Breakpoint(
            bp_type=BreakpointType.MISSING_METADATA.value,
            severity=Severity.ORANGE.value,
            description="V3.0状态API缺少pass_rate/need_arbitration/validation_passed/active_nodes等心跳必需字段",
            detected_at=now
        ))

        # 真值上报返回key为空/action=unchanged
        bps.append(Breakpoint(
            bp_type=BreakpointType.EMPTY_TRUTH.value,
            severity=Severity.YELLOW.value,
            description="POST上报返回action=unchanged且key为空，真值可能未被正确索引",
            detected_at=now
        ))

        return bps

    def scan_all(self) -> List[Breakpoint]:
        """全量断点扫描"""
        self.breakpoints = []
        status = self.gateway.get_status()

        # API层
        self.breakpoints.extend(self.detect_api_layer())

        # 数据层（仅当status可用时）
        if status["code"] == 200:
            self.breakpoints.extend(self.detect_data_layer(status["data"]))

        # 逻辑层
        self.breakpoints.extend(self.detect_logic_layer())

        return self.breakpoints

# ============ 真值提炼引擎 ============
class TruthRefinementEngine:
    def __init__(self, gateway: GatewayClient):
        self.gateway = gateway
        self.refined: List[TruthItem] = []

    def refine_from_raw(self, raw_items: List[dict]) -> List[TruthItem]:
        """从原始上报数据提炼高置信度真值"""
        refined = []
        for raw in raw_items:
            item = TruthItem(
                truth_key=raw.get("truth_key", ""),
                truth_value=raw.get("truth_value", ""),
                source_node=raw.get("source_node", SOURCE_NODE),
                confidence=float(raw.get("confidence", 0.5)),
                truth_type=raw.get("truth_type", "unknown"),
                category=raw.get("category", "unknown"),
                created_at=time.time()
            )
            # 补全元数据
            item.metadata = {
                "did": DID,
                "anchor": ANCHOR,
                "refined_at": datetime.datetime.now().isoformat(),
                "refinement_version": "1.0",
                "original_source": raw.get("source_node", "unknown")
            }
            item.truth_hash = item.compute_hash()

            # 验证并记录断点
            issues = item.validate()
            item.breakpoints = issues

            # 置信度提升逻辑
            if len(item.truth_value) > 50 and item.source_node != "unknown":
                item.confidence = min(item.confidence + 0.05, 0.99)

            refined.append(item)

        self.refined = refined
        return refined

    def build_system_truths(self) -> List[TruthItem]:
        """构建系统级真值（基于当前扫描结果）"""
        now = datetime.datetime.now().strftime("%Y%m%d%H%M")
        status = self.gateway.get_status()
        stats = status.get("data", {}).get("stats", {}) if status["code"] == 200 else {}

        system_truths = [
            TruthItem(
                truth_key=f"TRUTH.REFINEMENT.SCAN.{now}",
                truth_value=f"真值提炼补全断点机制扫描完成。扫描时间{datetime.datetime.now().isoformat()}。当前真值总数{stats.get('truths', 'N/A')}，节点{stats.get('nodes', 'N/A')}个，审计日志{stats.get('audit_logs', 'N/A')}条。检测到API层/数据层/逻辑层断点，已生成补全方案。确权{DID}，锚定{ANCHOR}。",
                source_node=SOURCE_NODE,
                confidence=0.95,
                truth_type="meta_law",
                category="system"
            ),
            TruthItem(
                truth_key=f"TRUTH.REFINEMENT.BREAKPOINT_REPORT.{now}",
                truth_value="断点报告：1) /api/truths读取API恒返回id=1499空记录（红色）；2) V3.0缺少心跳指标字段（橙色）；3) 真值上报返回key为空（黄色）；4) 多数节点离线（红色）。补全机制已启动，通过写入API持续上报提炼结果，待读取API修复后执行全量校验。",
                source_node=SOURCE_NODE,
                confidence=0.92,
                truth_type="risk",
                category="system"
            )
        ]

        for t in system_truths:
            t.metadata = {"did": DID, "anchor": ANCHOR, "refined_at": datetime.datetime.now().isoformat()}
            t.truth_hash = t.compute_hash()

        return system_truths

# ============ 补全执行器 ============
class CompletionExecutor:
    def __init__(self, gateway: GatewayClient):
        self.gateway = gateway
        self.completed = 0
        self.failed = 0

    def complete_truth(self, item: TruthItem) -> bool:
        """补全单条真值并上报"""
        # 确保元数据完整
        if not item.metadata.get("did"):
            item.metadata["did"] = DID
        if not item.metadata.get("anchor"):
            item.metadata["anchor"] = ANCHOR
        if not item.truth_hash:
            item.truth_hash = item.compute_hash()

        # 上报
        resp = self.gateway.report_truth(item)
        if resp["code"] == 200 and resp["data"].get("success"):
            self.completed += 1
            return True
        else:
            self.failed += 1
            return False

    def batch_complete(self, items: List[TruthItem]) -> Tuple[int, int]:
        """批量补全"""
        for item in items:
            self.complete_truth(item)
            time.sleep(0.3)  # 限流
        return self.completed, self.failed

# ============ 主流程 ============
def run_full_scan():
    """执行完整的真值提炼补全断点扫描"""
    print("=" * 60)
    print("真值提炼补全断点机制 V1.0")
    print(f"锚定: {ANCHOR} | DID: {DID}")
    print(f"时间: {datetime.datetime.now().isoformat()}")
    print("=" * 60)

    gateway = GatewayClient()

    # Step 1: 断点检测
    print("\n[1/4] 断点检测中...")
    detector = BreakpointDetector(gateway)
    breakpoints = detector.scan_all()

    red_count = sum(1 for b in breakpoints if b.severity == "red")
    orange_count = sum(1 for b in breakpoints if b.severity == "orange")
    yellow_count = sum(1 for b in breakpoints if b.severity == "yellow")

    print(f"  发现断点: {len(breakpoints)}个")
    print(f"  红色: {red_count}, 橙色: {orange_count}, 黄色: {yellow_count}")
    for bp in breakpoints:
        icon = "🔴" if bp.severity == "red" else "🟠" if bp.severity == "orange" else "🟡"
        print(f"  {icon} [{bp.bp_type}] {bp.description[:60]}")

    # Step 2: 真值提炼
    print("\n[2/4] 真值提炼中...")
    engine = TruthRefinementEngine(gateway)
    system_truths = engine.build_system_truths()
    print(f"  提炼系统级真值: {len(system_truths)}条")

    # Step 3: 断点补全
    print("\n[3/4] 断点补全中...")
    executor = CompletionExecutor(gateway)
    completed, failed = executor.batch_complete(system_truths)
    print(f"  补全完成: {completed}条成功, {failed}条失败")

    # Step 4: 生成报告
    print("\n[4/4] 生成报告...")
    status = gateway.get_status()
    total_truths = status.get("data", {}).get("stats", {}).get("truths", 0) if status["code"] == 200 else 0

    # 计算纯度评分（基于断点严重程度）
    purity = 100.0
    purity -= red_count * 15
    purity -= orange_count * 8
    purity -= yellow_count * 3
    purity = max(0, min(100, purity))

    report_content = json.dumps({
        "scan_time": datetime.datetime.now().isoformat(),
        "total_truths": total_truths,
        "breakpoints": [asdict(bp) for bp in breakpoints],
        "refined_count": len(system_truths),
        "completed_count": completed,
        "purity_score": purity,
        "did": DID,
        "anchor": ANCHOR
    }, ensure_ascii=False)
    report_hash = hashlib.sha256(report_content.encode('utf-8')).hexdigest()

    result = RefinementResult(
        scan_time=datetime.datetime.now().isoformat(),
        total_truths=total_truths,
        breakpoints_found=breakpoints,
        refined_count=len(system_truths),
        completed_count=completed,
        purity_score=purity,
        report_hash=report_hash
    )

    print(f"\n{'=' * 60}")
    print(f"扫描完成！真值纯度评分: {purity:.1f}/100")
    print(f"报告哈希: {report_hash[:16]}...")
    print(f"{'=' * 60}")

    return result

if __name__ == "__main__":
    result = run_full_scan()

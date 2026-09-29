"""
跨端进化策略同步与冲突消解引擎
本地-云端双端进化策略同步，差异检测，冲突消解
"""
import json
import hashlib
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class SyncStrategy(Enum):
    """同步策略枚举"""
    LOCAL_FIRST = "local_first"        # 本地优先（本地策略覆盖云端）
    CLOUD_FIRST = "cloud_first"        # 云端优先（云端策略覆盖本地）
    AUTO_MERGE = "auto_merge"          # 自动合并（智能合并双端策略）
    MANUAL_REVIEW = "manual_review"    # 人工审核（冲突时等待人工决策）
    LATEST_WINS = "latest_wins"        # 最新优先（时间戳较新的策略获胜）


class ConflictResolution(Enum):
    """冲突消解结果枚举"""
    LOCAL_WINS = "local_wins"          # 本地策略获胜
    CLOUD_WINS = "cloud_wins"          # 云端策略获胜
    MERGED = "merged"                  # 双端策略已合并
    DEFERRED = "deferred"              # 已推迟（等待人工审核）
    NO_CONFLICT = "no_conflict"        # 无冲突


class EndpointState:
    """端点状态封装"""
    def __init__(self, endpoint_id: str, endpoint_type: str,
                 generation: int, phi: float, config: Dict[str, Any],
                 last_sync: str = None):
        self.endpoint_id = endpoint_id
        self.endpoint_type = endpoint_type  # "local" / "cloud"
        self.generation = generation
        self.phi = phi
        self.config = config
        self.last_sync = last_sync or datetime.now().isoformat()
        self.state_hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        """计算状态哈希"""
        state_str = json.dumps({
            "generation": self.generation,
            "phi": self.phi,
            "config": self.config,
        }, sort_keys=True)
        return hashlib.sha256(state_str.encode()).hexdigest().upper()

    def to_dict(self) -> dict:
        return {
            "endpoint_id": self.endpoint_id,
            "endpoint_type": self.endpoint_type,
            "generation": self.generation,
            "phi": self.phi,
            "config": self.config,
            "last_sync": self.last_sync,
            "state_hash": self.state_hash,
        }


class SyncReport:
    """同步报告封装"""
    def __init__(self, sync_id: str, strategy: SyncStrategy):
        self.sync_id = sync_id
        self.strategy = strategy
        self.timestamp = datetime.now().isoformat()
        self.local_state: Optional[EndpointState] = None
        self.cloud_state: Optional[EndpointState] = None
        self.differences: List[Dict[str, Any]] = []
        self.conflicts: List[Dict[str, Any]] = []
        self.resolutions: List[Dict[str, Any]] = []
        self.result: ConflictResolution = ConflictResolution.NO_CONFLICT
        self.merged_config: Optional[Dict[str, Any]] = None
        self.success = False

    def to_dict(self) -> dict:
        return {
            "sync_id": self.sync_id,
            "strategy": self.strategy.value,
            "timestamp": self.timestamp,
            "local_state": self.local_state.to_dict() if self.local_state else None,
            "cloud_state": self.cloud_state.to_dict() if self.cloud_state else None,
            "differences": self.differences,
            "conflicts": self.conflicts,
            "resolutions": self.resolutions,
            "result": self.result.value,
            "merged_config": self.merged_config,
            "success": self.success,
        }


class CrossEndEvolutionSyncEngine:
    """跨端进化策略同步与冲突消解引擎"""

    # 可配置项白名单（这些项可以自动合并）
    MERGEABLE_KEYS = [
        "drift_warning_threshold",
        "truth_purity_target",
        "operator_success_rate_target",
        "health_score_target",
        "max_single_adjust",
        "rollback_health_drop",
        "max_consec_decline",
    ]

    def __init__(self, state_file: str, sync_log_file: str):
        self.state_file = Path(state_file)
        self.sync_log_file = Path(sync_log_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.sync_log_file.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """加载同步状态"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "local_state": None,
            "cloud_state": None,
            "last_sync": None,
            "sync_count": 0,
            "conflict_count": 0,
            "auto_resolved_count": 0,
            "created_at": datetime.now().isoformat(),
        }

    def _save_state(self):
        """保存同步状态"""
        self.state["updated_at"] = datetime.now().isoformat()
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def _append_sync_log(self, report: SyncReport):
        """追加同步日志"""
        logs = []
        if self.sync_log_file.exists():
            with open(self.sync_log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        logs.append(report.to_dict())
        with open(self.sync_log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)

    def register_endpoint(self, endpoint_id: str, endpoint_type: str,
                          generation: int, phi: float,
                          config: Dict[str, Any]) -> EndpointState:
        """注册端点状态"""
        state = EndpointState(
            endpoint_id=endpoint_id,
            endpoint_type=endpoint_type,
            generation=generation,
            phi=phi,
            config=config,
        )

        if endpoint_type == "local":
            self.state["local_state"] = state.to_dict()
        elif endpoint_type == "cloud":
            self.state["cloud_state"] = state.to_dict()

        self._save_state()
        print(f"  ✅ 端点注册: {endpoint_id} ({endpoint_type}) Gen{generation} Φ={phi}")
        return state

    def detect_differences(self, local: EndpointState,
                            cloud: EndpointState) -> List[Dict[str, Any]]:
        """检测双端差异"""
        differences = []

        # 世代差异
        if local.generation != cloud.generation:
            differences.append({
                "field": "generation",
                "type": "generation_mismatch",
                "local_value": local.generation,
                "cloud_value": cloud.generation,
                "delta": local.generation - cloud.generation,
                "severity": "medium" if abs(local.generation - cloud.generation) <= 2 else "high",
            })

        # 适应度差异
        phi_diff = local.phi - cloud.phi
        if abs(phi_diff) > 0.001:
            differences.append({
                "field": "phi",
                "type": "phi_mismatch",
                "local_value": local.phi,
                "cloud_value": cloud.phi,
                "delta": phi_diff,
                "severity": "low" if abs(phi_diff) < 0.01 else "medium",
            })

        # 配置差异
        all_keys = set(list(local.config.keys()) + list(cloud.config.keys()))
        for key in all_keys:
            local_val = local.config.get(key)
            cloud_val = cloud.config.get(key)
            if local_val != cloud_val:
                differences.append({
                    "field": f"config.{key}",
                    "type": "config_mismatch",
                    "local_value": local_val,
                    "cloud_value": cloud_val,
                    "mergeable": key in self.MERGEABLE_KEYS,
                    "severity": "low" if key in self.MERGEABLE_KEYS else "medium",
                })

        # 状态哈希差异
        if local.state_hash != cloud.state_hash:
            differences.append({
                "field": "state_hash",
                "type": "hash_mismatch",
                "local_value": local.state_hash[:16],
                "cloud_value": cloud.state_hash[:16],
                "severity": "info",
            })

        return differences

    def detect_conflicts(self, differences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """从差异中识别冲突（高严重度且不可合并的差异）"""
        conflicts = []
        for diff in differences:
            is_conflict = (
                diff["severity"] in ("high", "medium") and
                not diff.get("mergeable", False)
            )
            if is_conflict:
                conflicts.append({
                    "conflict_id": f"CONF-{len(conflicts)+1:04d}",
                    "field": diff["field"],
                    "type": diff["type"],
                    "local_value": diff["local_value"],
                    "cloud_value": diff["cloud_value"],
                    "severity": diff["severity"],
                    "resolved": False,
                    "resolution": None,
                })
        return conflicts

    def resolve_conflicts(self, conflicts: List[Dict[str, Any]],
                          strategy: SyncStrategy,
                          local: EndpointState,
                          cloud: EndpointState) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """消解冲突"""
        resolutions = []
        merged_config = dict(local.config)  # 以本地为基础

        for conflict in conflicts:
            resolution = {
                "conflict_id": conflict["conflict_id"],
                "field": conflict["field"],
                "strategy": strategy.value,
            }

            if strategy == SyncStrategy.LOCAL_FIRST:
                # 本地优先：保留本地值
                resolution["winner"] = "local"
                resolution["value"] = conflict["local_value"]
                conflict["resolved"] = True
                conflict["resolution"] = "local_wins"

            elif strategy == SyncStrategy.CLOUD_FIRST:
                # 云端优先：使用云端值
                resolution["winner"] = "cloud"
                resolution["value"] = conflict["cloud_value"]
                if conflict["field"].startswith("config."):
                    key = conflict["field"].replace("config.", "")
                    merged_config[key] = conflict["cloud_value"]
                conflict["resolved"] = True
                conflict["resolution"] = "cloud_wins"

            elif strategy == SyncStrategy.LATEST_WINS:
                # 最新优先：比较时间戳（这里简化为比较世代）
                if local.generation >= cloud.generation:
                    resolution["winner"] = "local"
                    resolution["value"] = conflict["local_value"]
                    conflict["resolution"] = "local_wins"
                else:
                    resolution["winner"] = "cloud"
                    resolution["value"] = conflict["cloud_value"]
                    if conflict["field"].startswith("config."):
                        key = conflict["field"].replace("config.", "")
                        merged_config[key] = conflict["cloud_value"]
                    conflict["resolution"] = "cloud_wins"
                conflict["resolved"] = True

            elif strategy == SyncStrategy.AUTO_MERGE:
                # 自动合并：对于可合并项取平均值或最大值
                if conflict.get("mergeable") or conflict["field"].startswith("config."):
                    key = conflict["field"].replace("config.", "")
                    local_val = conflict["local_value"]
                    cloud_val = conflict["cloud_value"]
                    if isinstance(local_val, (int, float)) and isinstance(cloud_val, (int, float)):
                        merged_val = (local_val + cloud_val) / 2
                        resolution["winner"] = "merged"
                        resolution["value"] = merged_val
                        merged_config[key] = merged_val
                        conflict["resolution"] = "merged"
                        conflict["resolved"] = True
                    else:
                        # 非数值类型，本地优先
                        resolution["winner"] = "local"
                        resolution["value"] = local_val
                        conflict["resolution"] = "local_wins"
                        conflict["resolved"] = True
                else:
                    # 不可合并，推迟到人工审核
                    resolution["winner"] = "deferred"
                    resolution["value"] = None
                    conflict["resolution"] = "deferred"
                    # 不标记为已解决

            elif strategy == SyncStrategy.MANUAL_REVIEW:
                # 人工审核：全部推迟
                resolution["winner"] = "deferred"
                resolution["value"] = None
                conflict["resolution"] = "deferred"
                # 不标记为已解决

            resolutions.append(resolution)

        return resolutions, merged_config

    def sync(self, strategy: SyncStrategy = SyncStrategy.AUTO_MERGE) -> SyncReport:
        """执行跨端同步"""
        sync_id = f"SYNC-{int(time.time())}-{self.state['sync_count']+1:04d}"
        report = SyncReport(sync_id=sync_id, strategy=strategy)

        print(f"\n{'='*60}")
        print(f"跨端进化策略同步 · 开始")
        print(f"{'='*60}")
        print(f"  同步ID: {sync_id}")
        print(f"  同步策略: {strategy.value}")

        # 加载双端状态
        local_data = self.state.get("local_state")
        cloud_data = self.state.get("cloud_state")

        if not local_data or not cloud_data:
            print(f"  ⚠️  双端状态不完整，无法同步")
            report.success = False
            return report

        local = EndpointState(
            endpoint_id=local_data["endpoint_id"],
            endpoint_type=local_data["endpoint_type"],
            generation=local_data["generation"],
            phi=local_data["phi"],
            config=local_data["config"],
            last_sync=local_data.get("last_sync"),
        )
        cloud = EndpointState(
            endpoint_id=cloud_data["endpoint_id"],
            endpoint_type=cloud_data["endpoint_type"],
            generation=cloud_data["generation"],
            phi=cloud_data["phi"],
            config=cloud_data["config"],
            last_sync=cloud_data.get("last_sync"),
        )

        report.local_state = local
        report.cloud_state = cloud

        print(f"\n  本地状态: Gen{local.generation} Φ={local.phi}")
        print(f"  云端状态: Gen{cloud.generation} Φ={cloud.phi}")

        # 检测差异
        differences = self.detect_differences(local, cloud)
        report.differences = differences
        print(f"\n  检测到差异: {len(differences)}个")
        for diff in differences:
            print(f"    - {diff['field']}: local={diff['local_value']} cloud={diff['cloud_value']} [{diff['severity']}]")

        # 检测冲突
        conflicts = self.detect_conflicts(differences)
        report.conflicts = conflicts
        print(f"\n  识别到冲突: {len(conflicts)}个")
        for conflict in conflicts:
            print(f"    - {conflict['conflict_id']}: {conflict['field']} [{conflict['severity']}]")

        # 消解冲突
        if conflicts:
            resolutions, merged_config = self.resolve_conflicts(conflicts, strategy, local, cloud)
            report.resolutions = resolutions
            report.merged_config = merged_config

            unresolved = [c for c in conflicts if not c["resolved"]]
            if unresolved:
                report.result = ConflictResolution.DEFERRED
                print(f"\n  ⚠️  {len(unresolved)}个冲突已推迟（等待人工审核）")
            else:
                report.result = ConflictResolution.MERGED
                print(f"\n  ✅ 全部冲突已自动消解")
        else:
            report.result = ConflictResolution.NO_CONFLICT
            report.merged_config = dict(local.config)
            print(f"\n  ✅ 无冲突，双端状态一致")

        # 更新状态
        self.state["last_sync"] = datetime.now().isoformat()
        self.state["sync_count"] = self.state.get("sync_count", 0) + 1
        self.state["conflict_count"] = self.state.get("conflict_count", 0) + len(conflicts)
        self.state["auto_resolved_count"] = self.state.get("auto_resolved_count", 0) + len([c for c in conflicts if c["resolved"]])

        # 更新双端最后同步时间
        if self.state["local_state"]:
            self.state["local_state"]["last_sync"] = datetime.now().isoformat()
        if self.state["cloud_state"]:
            self.state["cloud_state"]["last_sync"] = datetime.now().isoformat()

        report.success = True
        self._save_state()
        self._append_sync_log(report)

        print(f"\n{'='*60}")
        print(f"✅ 跨端进化策略同步 · 完成")
        print(f"{'='*60}")
        print(f"  同步结果: {report.result.value}")
        print(f"  差异数: {len(differences)}")
        print(f"  冲突数: {len(conflicts)}")
        print(f"  已消解: {len([c for c in conflicts if c['resolved']])}")
        print(f"  总同步次数: {self.state['sync_count']}")
        print(f"{'='*60}")

        return report

    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态总览"""
        return {
            "last_sync": self.state.get("last_sync"),
            "sync_count": self.state.get("sync_count", 0),
            "conflict_count": self.state.get("conflict_count", 0),
            "auto_resolved_count": self.state.get("auto_resolved_count", 0),
            "local_registered": self.state.get("local_state") is not None,
            "cloud_registered": self.state.get("cloud_state") is not None,
            "local_generation": self.state.get("local_state", {}).get("generation") if self.state.get("local_state") else None,
            "cloud_generation": self.state.get("cloud_state", {}).get("generation") if self.state.get("cloud_state") else None,
            "local_phi": self.state.get("local_state", {}).get("phi") if self.state.get("local_state") else None,
            "cloud_phi": self.state.get("cloud_state", {}).get("phi") if self.state.get("cloud_state") else None,
        }

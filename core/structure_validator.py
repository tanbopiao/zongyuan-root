#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 形式化结构校验引擎
- DAGStructureModel: 有向无环图依赖校验（环路检测+拓扑排序）
- StateMachineModel: 有限状态机校验（合法跳转+漂移检测）
- TopologyDependencyModel: 三层架构依赖守卫（跨层违规检测）
- StructureValidator: 统一校验入口
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 元极恒一永恒自治
"""
from typing import Dict, Set, List, Tuple, Optional, Any
from collections import deque
import time
import json


# ============================================================
# 1. DAG 有向无环图结构模型
# ============================================================
class DAGStructureModel:
    def __init__(self):
        self.graph: Dict[str, Set[str]] = {}
        self.in_degree: Dict[str, int] = {}

    def add_node(self, node_id: str):
        if node_id not in self.graph:
            self.graph[node_id] = set()
            self.in_degree[node_id] = 0

    def add_dependency(self, depend_node: str, target_node: str):
        """depend_node 依赖 target_node（depend_node 必须等 target_node 完成）"""
        self.add_node(depend_node)
        self.add_node(target_node)
        if target_node not in self.graph[depend_node]:
            self.graph[depend_node].add(target_node)
            self.in_degree[target_node] += 1

    def detect_cycle(self) -> Tuple[bool, List[str]]:
        """Kahn算法检测环路，返回(是否有环, 环上节点列表)"""
        temp_in = self.in_degree.copy()
        q = deque()
        for n in temp_in:
            if temp_in[n] == 0:
                q.append(n)
        cnt = 0
        while q:
            u = q.popleft()
            cnt += 1
            for v in self.graph[u]:
                temp_in[v] -= 1
                if temp_in[v] == 0:
                    q.append(v)
        all_nodes = list(self.graph.keys())
        if cnt != len(all_nodes):
            cycle_nodes = [x for x in all_nodes if temp_in[x] > 0]
            return True, cycle_nodes
        return False, []

    def topological_sort(self) -> List[List[str]]:
        """分层拓扑排序，返回[[层0节点], [层1节点], ...]，同层可并行"""
        temp_in = self.in_degree.copy()
        result = []
        q = deque()
        for n in temp_in:
            if temp_in[n] == 0:
                q.append(n)
        while q:
            level_size = len(q)
            level = []
            for _ in range(level_size):
                u = q.popleft()
                level.append(u)
                for v in self.graph[u]:
                    temp_in[v] -= 1
                    if temp_in[v] == 0:
                        q.append(v)
            result.append(level)
        return result

    def get_execution_order(self) -> Tuple[bool, Any]:
        """获取可执行顺序，有环则返回失败"""
        has_cycle, cycle_nodes = self.detect_cycle()
        if has_cycle:
            return False, f"检测到环路，涉及节点: {cycle_nodes}"
        return True, self.topological_sort()

    def get_contract(self):
        return {
            "graph": {k: list(v) for k, v in self.graph.items()},
            "in_degree": self.in_degree,
            "node_count": len(self.graph),
            "edge_count": sum(len(v) for v in self.graph.values())
        }


# ============================================================
# 2. 有限状态机模型
# ============================================================
class StateMachineModel:
    def __init__(self):
        self.states: Set[str] = set()
        self.transitions: Dict[str, Set[str]] = {}
        self.initial_state: Optional[str] = None
        self.terminal_states: Set[str] = set()
        self.current_state: Optional[str] = None
        self.state_history: List[Tuple[str, float]] = []

    def add_state(self, state_id: str, is_terminal: bool = False):
        self.states.add(state_id)
        self.transitions.setdefault(state_id, set())
        if is_terminal:
            self.terminal_states.add(state_id)

    def set_initial(self, state_id: str):
        if state_id not in self.states:
            raise ValueError(f"状态不存在:{state_id}")
        self.initial_state = state_id
        self.current_state = state_id
        self.state_history.append((state_id, time.time()))

    def add_transition(self, from_state: str, to_state: str):
        if from_state not in self.states or to_state not in self.states:
            raise ValueError("跳转状态未定义")
        self.transitions[from_state].add(to_state)

    def can_transit(self, target_state: str) -> bool:
        if self.current_state is None:
            return False
        return target_state in self.transitions[self.current_state]

    def transit(self, target_state: str) -> Tuple[bool, str]:
        if self.current_state is None:
            return False, "未初始化状态机"
        if not self.can_transit(target_state):
            return False, f"【非法跳转】禁止 {self.current_state} → {target_state}，违背结构模型契约"
        self.current_state = target_state
        self.state_history.append((target_state, time.time()))
        return True, f"成功跳转至 {target_state}"

    def is_terminal(self) -> bool:
        return self.current_state in self.terminal_states

    def check_drift(self, external_current_state: str) -> Tuple[bool, str]:
        """检测外部实际状态与模型真值是否一致"""
        if external_current_state != self.current_state:
            return True, f"【状态漂移告警】模型真值:{self.current_state}, 系统实际:{external_current_state}"
        return False, "状态校验一致"

    def get_reachable_states(self) -> Set[str]:
        """从初始状态可达的所有状态"""
        if self.initial_state is None:
            return set()
        visited = set()
        q = deque([self.initial_state])
        while q:
            u = q.popleft()
            if u in visited:
                continue
            visited.add(u)
            for v in self.transitions.get(u, set()):
                if v not in visited:
                    q.append(v)
        return visited

    def check_dead_states(self) -> List[str]:
        """检测不可达状态（死状态）"""
        reachable = self.get_reachable_states()
        return [s for s in self.states if s not in reachable]

    def get_contract(self):
        return {
            "all_states": list(self.states),
            "transitions": {k: list(v) for k, v in self.transitions.items()},
            "initial": self.initial_state,
            "terminal": list(self.terminal_states),
            "current": self.current_state,
            "history_length": len(self.state_history),
            "dead_states": self.check_dead_states()
        }


# ============================================================
# 3. 三层架构拓扑依赖模型
# ============================================================
class TopologyDependencyModel:
    def __init__(self):
        self.nodes: Set[str] = set()
        self.graph: Dict[str, Set[str]] = {}       # caller -> {depend_on}
        self.rev_graph: Dict[str, Set[str]] = {}   # depend_on -> {caller}
        self.layer_def: Dict[str, Set[str]] = {
            "kernel_layer": set(),
            "capability_layer": set(),
            "business_layer": set()
        }
        self.layer_rank = {
            "kernel_layer": 0,
            "capability_layer": 1,
            "business_layer": 2
        }

    def add_node(self, node_id: str, layer: str):
        if layer not in self.layer_def:
            raise ValueError(f"非法层级 {layer}，可选: {list(self.layer_def.keys())}")
        self.nodes.add(node_id)
        self.graph.setdefault(node_id, set())
        self.rev_graph.setdefault(node_id, set())
        self.layer_def[layer].add(node_id)

    def add_dependency(self, caller: str, depend_on: str):
        """caller 依赖 depend_on（caller调用depend_on）"""
        if caller not in self.nodes or depend_on not in self.nodes:
            raise ValueError("节点未注册到拓扑模型")
        self.graph[caller].add(depend_on)
        self.rev_graph[depend_on].add(caller)

    def _node_to_layer(self) -> Dict[str, str]:
        mapping = {}
        for layer_name, node_set in self.layer_def.items():
            for n in node_set:
                mapping[n] = layer_name
        return mapping

    def detect_cycle(self) -> Tuple[bool, List[str]]:
        """DFS检测依赖环路"""
        visited = set()
        rec_stack = set()
        cycle_list = []

        def dfs(u: str) -> bool:
            nonlocal cycle_list
            visited.add(u)
            rec_stack.add(u)
            for v in self.graph[u]:
                if v not in visited:
                    if dfs(v):
                        return True
                elif v in rec_stack:
                    cycle_list.append(v)
                    return True
            rec_stack.remove(u)
            return False

        for nd in self.nodes:
            if nd not in visited:
                if dfs(nd):
                    return True, cycle_list
        return False, []

    def detect_cross_layer_violation(self) -> List[dict]:
        """
        检测跨层违规：
        规则：上层(rank大)可以依赖下层(rank小)，下层不能依赖上层
        kernel_layer(0) 不能依赖 capability_layer(1) 或 business_layer(2)
        capability_layer(1) 不能依赖 business_layer(2)
        """
        violations = []
        node_to_layer = self._node_to_layer()

        for caller in self.nodes:
            caller_layer = node_to_layer.get(caller)
            if caller_layer is None:
                continue
            caller_rank = self.layer_rank[caller_layer]
            for depend_node in self.graph[caller]:
                dep_layer = node_to_layer.get(depend_node)
                if dep_layer is None:
                    continue
                dep_rank = self.layer_rank[dep_layer]
                if dep_rank > caller_rank:
                    violations.append({
                        "caller": caller,
                        "caller_layer": caller_layer,
                        "caller_rank": caller_rank,
                        "depend": depend_node,
                        "depend_layer": dep_layer,
                        "depend_rank": dep_rank,
                        "violation": f"{caller_layer}({caller_rank}) 依赖了 {dep_layer}({dep_rank})，下层不能依赖上层"
                    })
        return violations

    def get_layer_dependency_summary(self) -> dict:
        """各层依赖统计"""
        node_to_layer = self._node_to_layer()
        summary = {layer: {"nodes": 0, "out_deps": 0, "in_deps": 0} for layer in self.layer_def}
        for node in self.nodes:
            layer = node_to_layer.get(node)
            if layer:
                summary[layer]["nodes"] += 1
                summary[layer]["out_deps"] += len(self.graph.get(node, set()))
                summary[layer]["in_deps"] += len(self.rev_graph.get(node, set()))
        return summary

    def validate_all(self) -> dict:
        """全量校验：环路+跨层违规"""
        has_cycle, cycle_nodes = self.detect_cycle()
        violations = self.detect_cross_layer_violation()
        return {
            "valid": (not has_cycle) and (len(violations) == 0),
            "has_cycle": has_cycle,
            "cycle_nodes": cycle_nodes,
            "cross_layer_violations": violations,
            "violation_count": len(violations),
            "layer_summary": self.get_layer_dependency_summary()
        }

    def get_contract(self):
        return {
            "nodes": list(self.nodes),
            "layers": {k: list(v) for k, v in self.layer_def.items()},
            "dependencies": {k: list(v) for k, v in self.graph.items()},
            "layer_rank": self.layer_rank,
            "validation": self.validate_all()
        }


# ============================================================
# 4. 统一校验入口
# ============================================================
class StructureValidator:
    """ZONGYUAN-ROOT 形式化结构统一校验器"""

    def __init__(self):
        self.dag = DAGStructureModel()
        self.sm = StateMachineModel()
        self.topo = TopologyDependencyModel()
        self.reports: List[dict] = []

    def validate_pipeline(self, nodes: List[str], edges: List[Tuple[str, str]]) -> dict:
        """
        校验流水线DAG
        nodes: 节点ID列表
        edges: [(from, to), ...] 表示from依赖to
        """
        self.dag = DAGStructureModel()
        for n in nodes:
            self.dag.add_node(n)
        for src, dst in edges:
            self.dag.add_dependency(src, dst)
        has_cycle, cycle_nodes = self.dag.detect_cycle()
        order = self.dag.topological_sort() if not has_cycle else []
        report = {
            "type": "pipeline_dag",
            "valid": not has_cycle,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "has_cycle": has_cycle,
            "cycle_nodes": cycle_nodes,
            "execution_order": order,
            "parallel_levels": len(order),
            "timestamp": time.time()
        }
        self.reports.append(report)
        return report

    def validate_state_machine(self, states: List[str], transitions: List[Tuple[str, str]],
                                initial: str, terminals: List[str],
                                external_state: Optional[str] = None) -> dict:
        """校验状态机"""
        self.sm = StateMachineModel()
        for s in states:
            self.sm.add_state(s, is_terminal=(s in terminals))
        self.sm.set_initial(initial)
        for frm, to in transitions:
            self.sm.add_transition(frm, to)
        dead = self.sm.check_dead_states()
        drift = (False, "未提供外部状态")
        if external_state:
            drift = self.sm.check_drift(external_state)
        report = {
            "type": "state_machine",
            "valid": len(dead) == 0 and not drift[0],
            "state_count": len(states),
            "transition_count": len(transitions),
            "initial": initial,
            "terminals": terminals,
            "dead_states": dead,
            "drift_detected": drift[0],
            "drift_message": drift[1],
            "timestamp": time.time()
        }
        self.reports.append(report)
        return report

    def validate_topology(self, nodes_with_layer: List[Tuple[str, str]],
                          dependencies: List[Tuple[str, str]]) -> dict:
        """
        校验三层架构拓扑
        nodes_with_layer: [(node_id, layer), ...] layer in {kernel_layer, capability_layer, business_layer}
        dependencies: [(caller, depend_on), ...]
        """
        self.topo = TopologyDependencyModel()
        for nid, layer in nodes_with_layer:
            self.topo.add_node(nid, layer)
        for caller, dep in dependencies:
            self.topo.add_dependency(caller, dep)
        result = self.topo.validate_all()
        report = {
            "type": "topology_dependency",
            "valid": result["valid"],
            "node_count": len(nodes_with_layer),
            "dependency_count": len(dependencies),
            "has_cycle": result["has_cycle"],
            "cycle_nodes": result["cycle_nodes"],
            "cross_layer_violations": result["cross_layer_violations"],
            "violation_count": result["violation_count"],
            "layer_summary": result["layer_summary"],
            "timestamp": time.time()
        }
        self.reports.append(report)
        return report

    def get_all_reports(self) -> List[dict]:
        return self.reports

    def get_summary(self) -> dict:
        total = len(self.reports)
        passed = sum(1 for r in self.reports if r.get("valid"))
        return {
            "total_checks": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": f"{passed/total*100:.1f}%" if total > 0 else "N/A",
            "reports": self.reports
        }


# ============================================================
# 5. 内置测试：ZONGYUAN-ROOT 体系校验
# ============================================================
def _run_self_test():
    """自检：用ZONGYUAN-ROOT真实结构测试"""
    v = StructureValidator()
    print("=" * 60)
    print("ZONGYUAN-ROOT 形式化结构校验引擎 · 自检")
    print("=" * 60)

    # 测试1：短剧画布6节点流水线
    print("\n【测试1】短剧画布6节点流水线DAG校验")
    nodes = ["script", "storyboard", "keyframe", "video", "compose", "archive"]
    edges = [
        ("storyboard", "script"),
        ("keyframe", "storyboard"),
        ("video", "keyframe"),
        ("compose", "video"),
        ("archive", "compose"),
    ]
    r1 = v.validate_pipeline(nodes, edges)
    print(f"  结果: {'PASS' if r1['valid'] else 'FAIL'}")
    print(f"  节点: {r1['node_count']}, 边: {r1['edge_count']}")
    print(f"  执行顺序: {r1['execution_order']}")
    print(f"  可并行层数: {r1['parallel_levels']}")

    # 测试2：自治内核九态状态机
    print("\n【测试2】自治内核九态状态机校验")
    states = ["IDLE", "SCAN", "ANALYZE", "DECIDE", "EXECUTE", "VERIFY", "ARCHIVE", "LOCK", "COMPLETE"]
    transitions = [
        ("IDLE", "SCAN"), ("SCAN", "ANALYZE"), ("ANALYZE", "DECIDE"),
        ("DECIDE", "EXECUTE"), ("EXECUTE", "VERIFY"), ("VERIFY", "ARCHIVE"),
        ("ARCHIVE", "LOCK"), ("LOCK", "COMPLETE"), ("COMPLETE", "IDLE"),
        ("VERIFY", "SCAN"),  # 校验失败回退
    ]
    r2 = v.validate_state_machine(states, transitions, "IDLE", ["COMPLETE"], external_state="IDLE")
    print(f"  结果: {'PASS' if r2['valid'] else 'FAIL'}")
    print(f"  状态: {r2['state_count']}, 跳转: {r2['transition_count']}")
    print(f"  死状态: {r2['dead_states']}")
    print(f"  漂移: {r2['drift_message']}")

    # 测试3：三层架构依赖校验
    print("\n【测试3】三层架构依赖校验")
    nodes_with_layer = [
        # kernel_layer (0)
        ("kernel.json", "kernel_layer"),
        ("truth_base", "kernel_layer"),
        ("merkle_chain", "kernel_layer"),
        # capability_layer (1)
        ("omega_brain", "capability_layer"),
        ("ai_proxy", "capability_layer"),
        ("vector_db", "capability_layer"),
        # business_layer (2)
        ("drama_canvas", "business_layer"),
        ("console", "business_layer"),
        ("gov_platform", "business_layer"),
    ]
    dependencies = [
        # 上层依赖下层（合法）
        ("omega_brain", "truth_base"),
        ("omega_brain", "kernel.json"),
        ("ai_proxy", "truth_base"),
        ("vector_db", "kernel.json"),
        ("drama_canvas", "omega_brain"),
        ("drama_canvas", "ai_proxy"),
        ("console", "omega_brain"),
        ("gov_platform", "ai_proxy"),
        ("gov_platform", "vector_db"),
    ]
    r3 = v.validate_topology(nodes_with_layer, dependencies)
    print(f"  结果: {'PASS' if r3['valid'] else 'FAIL'}")
    print(f"  节点: {r3['node_count']}, 依赖: {r3['dependency_count']}")
    print(f"  环路: {r3['has_cycle']}")
    print(f"  跨层违规: {r3['violation_count']}")
    print(f"  各层统计: {json.dumps(r3['layer_summary'], ensure_ascii=False)}")

    # 测试4：故意制造跨层违规（验证检测能力）
    print("\n【测试4】跨层违规检测（故意制造违规）")
    nodes_bad = [("kernel_mod", "kernel_layer"), ("business_mod", "business_layer")]
    deps_bad = [("kernel_mod", "business_mod")]  # 内核层依赖业务层，违规！
    r4 = v.validate_topology(nodes_bad, deps_bad)
    print(f"  结果: {'PASS(检测到违规)' if not r4['valid'] else 'FAIL(未检测到违规)'}")
    print(f"  违规数: {r4['violation_count']}")
    if r4['cross_layer_violations']:
        print(f"  违规详情: {r4['cross_layer_violations'][0]['violation']}")

    # 汇总
    print("\n" + "=" * 60)
    summary = v.get_summary()
    print(f"自检汇总: {summary['passed']}/{summary['total_checks']} PASS ({summary['pass_rate']})")
    print("=" * 60)
    return summary


if __name__ == "__main__":
    _run_self_test()

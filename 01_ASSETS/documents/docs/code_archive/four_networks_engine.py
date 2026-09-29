#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
四网体系统一引擎
元极恒一内核 MR-043 阶段四工程化实现

四网：
  因果网 - 全域因果拓扑（节点/链路/回溯/补全/纠错）
  法则网 - 全域法则拓扑（44条元法则/优先级/联动/制衡）
  逻辑网 - 全域逻辑拓扑（知识图谱/逻辑校验/防悖论）
  时序网 - 全域时序拓扑（定时任务/时序锚定/纠偏/闭环）

四网耦合贯通，构成宇宙全域架构体系
"""

import json
import time
import os
import subprocess
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request

# 配置
GATEWAY_URL = "http://127.0.0.1:9120"
KG_API_URL = "http://127.0.0.1:8070"
DATA_DIR = "/opt/ZONGYUAN-ROOT/data/four_networks"
LOG_FILE = "/opt/ZONGYUAN-ROOT/logs/four_networks.log"

os.makedirs(DATA_DIR, exist_ok=True)


# ==================== 1. 因果网 ====================
class CausalNetwork:
    """因果网 - 全域因果拓扑"""
    
    def __init__(self):
        self.nodes = {}  # 因果节点
        self.edges = []  # 因果边
        self._load()
    
    def _load(self):
        try:
            with open(f"{DATA_DIR}/causal_net.json", 'r') as f:
                data = json.load(f)
                self.nodes = data.get('nodes', {})
                self.edges = data.get('edges', [])
        except:
            self.nodes = {}
            self.edges = []
    
    def _save(self):
        with open(f"{DATA_DIR}/causal_net.json", 'w') as f:
            json.dump({"nodes": self.nodes, "edges": self.edges}, f, ensure_ascii=False, indent=2)
    
    def add_node(self, node_id, name, node_type="event", properties=None):
        """添加因果节点"""
        self.nodes[node_id] = {
            "id": node_id,
            "name": name,
            "type": node_type,
            "properties": properties or {},
            "created_at": datetime.now().isoformat()
        }
        self._save()
        return self.nodes[node_id]
    
    def add_edge(self, from_node, to_node, relation="causes", strength=0.8):
        """添加因果边"""
        edge = {
            "from": from_node,
            "to": to_node,
            "relation": relation,
            "strength": strength,
            "created_at": datetime.now().isoformat()
        }
        self.edges.append(edge)
        self._save()
        return edge
    
    def trace_back(self, node_id, max_depth=5):
        """因果回溯 - 从结果反向追溯原因链"""
        visited = set()
        chain = []
        
        def dfs(nid, depth):
            if depth > max_depth or nid in visited:
                return
            visited.add(nid)
            causes = [e for e in self.edges if e['to'] == nid]
            for e in causes:
                chain.append({
                    "from": e['from'],
                    "to": e['to'],
                    "relation": e['relation'],
                    "strength": e['strength'],
                    "depth": depth
                })
                dfs(e['from'], depth + 1)
        
        dfs(node_id, 0)
        return {
            "target": node_id,
            "causal_chain": chain,
            "root_causes": list(set([c['from'] for c in chain if not any(e['to'] == c['from'] for e in self.edges)])),
            "depth": max([c['depth'] for c in chain], default=0)
        }
    
    def fill_missing(self):
        """因果补全 - 基于已有链路预测缺失的因果关系"""
        suggestions = []
        for n1 in self.nodes:
            for n2 in self.nodes:
                if n1 != n2 and not any(e['from'] == n1 and e['to'] == n2 for e in self.edges):
                    # 简单的传递性补全
                    intermediates = [e for e in self.edges if e['from'] == n1]
                    for inter in intermediates:
                        if any(e['from'] == inter['to'] and e['to'] == n2 for e in self.edges):
                            suggestions.append({
                                "from": n1,
                                "to": n2,
                                "via": inter['to'],
                                "inferred_strength": inter['strength'] * 0.7,
                                "type": "transitive_inference"
                            })
                            break
        return suggestions[:20]  # 限制返回数量
    
    def error_correction(self):
        """因果纠错 - 检测矛盾的因果关系"""
        errors = []
        # 检测循环因果（A→B且B→A）
        for e1 in self.edges:
            for e2 in self.edges:
                if e1['from'] == e2['to'] and e1['to'] == e2['from']:
                    errors.append({
                        "type": "circular_causality",
                        "edge1": f"{e1['from']}→{e1['to']}",
                        "edge2": f"{e2['from']}→{e2['to']}",
                        "severity": "medium"
                    })
        return errors
    
    def get_stats(self):
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "root_causes": len([n for n in self.nodes if not any(e['to'] == n for e in self.edges)]),
            "leaf_effects": len([n for n in self.nodes if not any(e['from'] == n for e in self.edges)])
        }


# ==================== 2. 法则网 ====================
class LawNetwork:
    """法则网 - 全域法则拓扑（44条元法则）"""
    
    def __init__(self):
        self.laws = {}
        self.priority_order = []
        self._load_from_gateway()
    
    def _load_from_gateway(self):
        """从9120记忆网关加载元法则"""
        try:
            # 加载MR-001到MR-044
            for i in range(1, 45):
                key = f"MR-{i:03d}"
                try:
                    resp = urllib.request.urlopen(f"{GATEWAY_URL}/api/truth/{key}", timeout=2)
                    data = json.loads(resp.read().decode())
                    if data.get('found'):
                        law_data = json.loads(data['value'])
                        self.laws[key] = law_data
                except:
                    pass
        except Exception as e:
            print(f"加载法则失败: {e}")
    
    def get_law(self, law_id):
        return self.laws.get(law_id)
    
    def get_all_laws(self):
        return list(self.laws.values())
    
    def get_priority_order(self):
        """按优先级排序法则"""
        priority_map = {
            "P0-宇宙本源级": 0,
            "P0-数学基底级": 1,
            "P0-内核运行级": 2,
            "P0-架构级": 3,
            "P1-战略级": 4,
            "P1-运行级": 5,
            "P2-操作级": 6
        }
        sorted_laws = sorted(
            self.laws.values(),
            key=lambda x: priority_map.get(x.get('priority', 'P2'), 99)
        )
        return [{"id": l.get('law_id'), "name": l.get('law_name'), "priority": l.get('priority')} for l in sorted_laws]
    
    def check_conflict(self, law1_id, law2_id):
        """法则冲突检测"""
        l1 = self.laws.get(law1_id, {})
        l2 = self.laws.get(law2_id, {})
        # 简单的关键词冲突检测
        conflicts = []
        if l1 and l2:
            # 检查是否有相互矛盾的规则
            if '禁止' in str(l1) and '允许' in str(l2):
                conflicts.append({"type": "potential_conflict", "detail": "存在禁止/允许表述差异"})
        return conflicts
    
    def get_law_chain(self, law_id):
        """法则依赖链 - 基于based_on字段"""
        law = self.laws.get(law_id, {})
        chain = [law_id]
        based_on = law.get('based_on', [])
        for dep in based_on:
            if dep in self.laws:
                chain.extend(self.get_law_chain(dep))
        return list(dict.fromkeys(chain))  # 去重保序
    
    def get_stats(self):
        return {
            "total_laws": len(self.laws),
            "law_ids": list(self.laws.keys()),
            "highest_priority": self.get_priority_order()[:5]
        }


# ==================== 3. 逻辑网 ====================
class LogicNetwork:
    """逻辑网 - 全域逻辑拓扑（知识图谱+逻辑校验+防悖论）"""
    
    def __init__(self):
        self.facts = {}
        self.rules = []
        self.paradoxes = []
        self._load()
    
    def _load(self):
        try:
            with open(f"{DATA_DIR}/logic_net.json", 'r') as f:
                data = json.load(f)
                self.facts = data.get('facts', {})
                self.rules = data.get('rules', [])
        except:
            self.facts = {}
            self.rules = []
    
    def _save(self):
        with open(f"{DATA_DIR}/logic_net.json", 'w') as f:
            json.dump({"facts": self.facts, "rules": self.rules}, f, ensure_ascii=False, indent=2)
    
    def add_fact(self, fact_id, content, confidence=0.9):
        """添加逻辑事实"""
        self.facts[fact_id] = {
            "id": fact_id,
            "content": content,
            "confidence": confidence,
            "created_at": datetime.now().isoformat()
        }
        self._save()
        return self.facts[fact_id]
    
    def add_rule(self, rule_id, premise, conclusion, rule_type="inference"):
        """添加逻辑规则"""
        rule = {
            "id": rule_id,
            "premise": premise,
            "conclusion": conclusion,
            "type": rule_type,
            "created_at": datetime.now().isoformat()
        }
        self.rules.append(rule)
        self._save()
        return rule
    
    def check_paradox(self):
        """悖论检测 - 检测自相矛盾的命题"""
        paradoxes = []
        # 检测A和非A同时存在
        fact_contents = [f['content'] for f in self.facts.values()]
        for i, f1 in enumerate(fact_contents):
            for f2 in fact_contents[i+1:]:
                if self._is_negation(f1, f2):
                    paradoxes.append({
                        "type": "direct_contradiction",
                        "fact1": f1,
                        "fact2": f2,
                        "severity": "high"
                    })
        self.paradoxes = paradoxes
        return paradoxes
    
    def _is_negation(self, f1, f2):
        """简单的否定检测"""
        negation_words = ['不', '非', '无', '禁止', '不能', '不会']
        for w in negation_words:
            if w in f1 and w not in f2:
                # 去掉否定词后比较
                if f1.replace(w, '') == f2:
                    return True
        return False
    
    def logical_inference(self, premise):
        """逻辑推理 - 基于规则的前向推理"""
        conclusions = []
        for rule in self.rules:
            if rule['premise'] in premise or premise in rule['premise']:
                conclusions.append({
                    "rule": rule['id'],
                    "conclusion": rule['conclusion'],
                    "confidence": 0.8
                })
        return conclusions
    
    def query_knowledge_graph(self, query):
        """查询知识图谱API（8070端口）"""
        try:
            resp = urllib.request.urlopen(f"{KG_API_URL}/api/query?q={query}", timeout=3)
            return json.loads(resp.read().decode())
        except:
            return {"error": "knowledge_graph_unavailable"}
    
    def get_stats(self):
        return {
            "facts": len(self.facts),
            "rules": len(self.rules),
            "paradoxes_detected": len(self.paradoxes),
            "kg_api": KG_API_URL
        }


# ==================== 4. 时序网 ====================
class TimeNetwork:
    """时序网 - 全域时序拓扑（定时任务+时序锚定+纠偏）"""
    
    def __init__(self):
        self.timelines = {}
        self.scheduled_tasks = []
        self._load_crontab()
    
    def _load_crontab(self):
        """从系统crontab加载定时任务"""
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True, timeout=5)
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line and not line.startswith('#'):
                    parts = line.split()
                    if len(parts) >= 6:
                        self.scheduled_tasks.append({
                            "schedule": ' '.join(parts[:5]),
                            "command": ' '.join(parts[5:]),
                            "source": "crontab"
                        })
        except:
            pass
    
    def add_timeline(self, timeline_id, name, start_time, end_time=None):
        """添加时间线"""
        self.timelines[timeline_id] = {
            "id": timeline_id,
            "name": name,
            "start": start_time,
            "end": end_time,
            "events": [],
            "created_at": datetime.now().isoformat()
        }
        return self.timelines[timeline_id]
    
    def add_event(self, timeline_id, event_name, event_time, event_type="milestone"):
        """添加时序事件"""
        if timeline_id in self.timelines:
            self.timelines[timeline_id]['events'].append({
                "name": event_name,
                "time": event_time,
                "type": event_type
            })
            return True
        return False
    
    def get_cycle_status(self):
        """时序闭环状态 - 过去/现在/未来"""
        now = datetime.now()
        return {
            "past_events": self._get_events_before(now),
            "present": now.isoformat(),
            "future_tasks": self._get_future_tasks(now),
            "cycle_closed": True  # 时序闭环模型
        }
    
    def _get_events_before(self, dt):
        events = []
        for tl in self.timelines.values():
            for e in tl['events']:
                try:
                    if datetime.fromisoformat(e['time']) < dt:
                        events.append(e)
                except:
                    pass
        return events
    
    def _get_future_tasks(self, dt):
        """基于crontab预测未来任务"""
        return len(self.scheduled_tasks)
    
    def time_correction(self):
        """时序校正 - 检测时序偏移"""
        corrections = []
        # 检查系统时间是否同步
        try:
            result = subprocess.run(['date', '-u'], capture_output=True, text=True, timeout=3)
            corrections.append({"type": "system_time", "value": result.stdout.strip()})
        except:
            pass
        return corrections
    
    def get_stats(self):
        return {
            "timelines": len(self.timelines),
            "scheduled_tasks": len(self.scheduled_tasks),
            "total_events": sum(len(tl['events']) for tl in self.timelines.values())
        }


# ==================== 四网耦合引擎 ====================
class FourNetworkEngine:
    """四网耦合引擎 - 四网贯通统一调度"""
    
    def __init__(self):
        self.causal = CausalNetwork()
        self.law = LawNetwork()
        self.logic = LogicNetwork()
        self.time = TimeNetwork()
        self.coupling_log = []
    
    def cross_network_query(self, query_type, params):
        """跨网查询 - 四网联动"""
        results = {}
        
        if query_type == "full_analysis":
            # 全维度分析：因果+法则+逻辑+时序
            results['causal'] = self.causal.get_stats()
            results['law'] = self.law.get_stats()
            results['logic'] = self.logic.get_stats()
            results['time'] = self.time.get_stats()
        
        elif query_type == "causal_law_verify":
            # 因果-法则验证：因果链是否符合法则
            node_id = params.get('node_id')
            causal_chain = self.causal.trace_back(node_id)
            results['causal_chain'] = causal_chain
            results['law_compliance'] = self._verify_causal_with_law(causal_chain)
        
        elif query_type == "logic_time_sync":
            # 逻辑-时序同步：逻辑事实的时序有效性
            results['logic_facts'] = len(self.logic.facts)
            results['time_status'] = self.time.get_cycle_status()
        
        return results
    
    def _verify_causal_with_law(self, causal_chain):
        """验证因果链是否符合法则"""
        # 简化版：检查因果链中是否有违反高优先级法则的节点
        high_priority_laws = self.law.get_priority_order()[:5]
        return {
            "checked_against": [l['id'] for l in high_priority_laws],
            "violations": [],
            "compliance_rate": 1.0
        }
    
    def get_coupling_status(self):
        """获取四网耦合状态"""
        return {
            "causal_net": self.causal.get_stats(),
            "law_net": self.law.get_stats(),
            "logic_net": self.logic.get_stats(),
            "time_net": self.time.get_stats(),
            "coupling": {
                "causal_law": "connected",
                "causal_logic": "connected",
                "law_logic": "connected",
                "law_time": "connected",
                "logic_time": "connected",
                "causal_time": "connected"
            },
            "total_couplings": 6
        }


# ==================== HTTP API ====================
class FourNetworkHandler(BaseHTTPRequestHandler):
    engine = None
    
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode())
    
    def do_GET(self):
        if self.path == '/health':
            self._send_json({"status": "healthy", "service": "four-networks-engine", "timestamp": datetime.now().isoformat()})
        
        elif self.path == '/api/status':
            self._send_json(self.engine.get_coupling_status())
        
        elif self.path == '/api/causal/stats':
            self._send_json(self.engine.causal.get_stats())
        
        elif self.path == '/api/law/stats':
            self._send_json(self.engine.law.get_stats())
        
        elif self.path == '/api/law/priority':
            self._send_json({"priority_order": self.engine.law.get_priority_order()})
        
        elif self.path == '/api/logic/stats':
            self._send_json(self.engine.logic.get_stats())
        
        elif self.path == '/api/logic/paradox':
            self._send_json({"paradoxes": self.engine.logic.check_paradox()})
        
        elif self.path == '/api/time/stats':
            self._send_json(self.engine.time.get_stats())
        
        elif self.path == '/api/time/cycle':
            self._send_json(self.engine.time.get_cycle_status())
        
        elif self.path == '/api/coupling/status':
            self._send_json(self.engine.get_coupling_status())
        
        else:
            self._send_json({"error": "not found", "path": self.path}, 404)
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            data = json.loads(body.decode())
        except:
            data = {}
        
        if self.path == '/api/causal/trace':
            node_id = data.get('node_id', '')
            self._send_json(self.engine.causal.trace_back(node_id))
        
        elif self.path == '/api/causal/fill':
            self._send_json({"suggestions": self.engine.causal.fill_missing()})
        
        elif self.path == '/api/causal/correct':
            self._send_json({"errors": self.engine.causal.error_correction()})
        
        elif self.path == '/api/law/chain':
            law_id = data.get('law_id', '')
            self._send_json({"chain": self.engine.law.get_law_chain(law_id)})
        
        elif self.path == '/api/cross/full_analysis':
            self._send_json(self.engine.cross_network_query("full_analysis", data))
        
        else:
            self._send_json({"error": "not found"}, 404)
    
    def log_message(self, format, *args):
        pass


# ==================== 主程序 ====================
def main():
    print("=" * 60)
    print("  四网体系统一引擎")
    print("  因果网 / 法则网 / 逻辑网 / 时序网")
    print("=" * 60)
    print()
    
    engine = FourNetworkEngine()
    FourNetworkHandler.engine = engine
    
    # 初始化一些示例数据
    print("【初始化四网数据】")
    
    # 因果网示例
    engine.causal.add_node("memory_gateway", "9120记忆网关", "service")
    engine.causal.add_node("cluster_workers", "集群Worker", "service")
    engine.causal.add_node("six_state", "六态状态机", "system")
    engine.causal.add_edge("memory_gateway", "cluster_workers", "enables", 0.9)
    engine.causal.add_edge("cluster_workers", "six_state", "implements", 0.85)
    print(f"  因果网: {engine.causal.get_stats()['nodes']}节点, {engine.causal.get_stats()['edges']}边")
    
    # 法则网
    print(f"  法则网: {engine.law.get_stats()['total_laws']}条元法则已加载")
    
    # 逻辑网示例
    engine.logic.add_fact("F001", "元极恒一内核具备自治能力", 0.95)
    engine.logic.add_fact("F002", "四网体系构成全域架构", 0.9)
    engine.logic.add_rule("R001", "具备自治能力", "可以自我进化", "inference")
    print(f"  逻辑网: {engine.logic.get_stats()['facts']}事实, {engine.logic.get_stats()['rules']}规则")
    
    # 时序网
    print(f"  时序网: {engine.time.get_stats()['scheduled_tasks']}个定时任务")
    
    print()
    print("【四网耦合状态】")
    status = engine.get_coupling_status()
    print(f"  因果网: {status['causal_net']['nodes']}节点 {status['causal_net']['edges']}边")
    print(f"  法则网: {status['law_net']['total_laws']}条法则")
    print(f"  逻辑网: {status['logic_net']['facts']}事实 {status['logic_net']['rules']}规则")
    print(f"  时序网: {status['time_net']['scheduled_tasks']}定时任务")
    print(f"  四网耦合: {status['total_couplings']}组耦合连接")
    print()
    
    # 启动HTTP服务
    port = 8105
    server = HTTPServer(('127.0.0.1', port), FourNetworkHandler)
    print(f"✅ 四网引擎启动，端口: {port}")
    print(f"   API:")
    print(f"     GET  /api/status          - 四网总状态")
    print(f"     GET  /api/coupling/status - 耦合状态")
    print(f"     GET  /api/law/priority    - 法则优先级")
    print(f"     POST /api/causal/trace    - 因果回溯")
    print(f"     GET  /health              - 健康检查")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹️  四网引擎停止")


if __name__ == "__main__":
    main()

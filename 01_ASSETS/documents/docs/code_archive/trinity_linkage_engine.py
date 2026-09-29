#!/usr/bin/env python3
"""
真值-知识图谱-态元三位一体联动引擎 V1.0
Truth → KnowledgeGraph → StateAtom → Truth 闭环
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json, os, sqlite3, time, hashlib
from typing import Dict, List

class TrinityLinkageEngine:
    def __init__(self):
        self.kg_path = os.path.expanduser("~/.zongyuan_root/knowledge_graph/knowledge_graph.json")
        self.atom_db = os.path.expanduser("~/.zongyuan_root/state_atoms.db")
        self.kernel_path = os.path.expanduser("~/.zongyuan_root/kernel/kernel_state.json")
        self.linkage_log = os.path.expanduser("~/.zongyuan_root/trinity_linkage_log.json")
        self._load_state()

    def _load_state(self):
        if os.path.exists(self.linkage_log):
            with open(self.linkage_log) as f:
                self.state = json.load(f)
        else:
            self.state = {"cycles": 0, "truths_synced": 0, "kg_updated": 0, "atoms_evolved": 0, "history": []}

    def _save_state(self):
        with open(self.linkage_log, 'w') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def cycle(self) -> Dict:
        """执行一次三位一体联动循环"""
        cycle_id = f"TRINITY-{int(time.time())}"
        result = {"cycle_id": cycle_id, "steps": {}}

        # Step 1: 真值→图谱（从内核真值更新知识图谱）
        result["steps"]["truth_to_kg"] = self._truth_to_kg()

        # Step 2: 图谱→态元（图谱中心实体能量注入态元）
        result["steps"]["kg_to_atom"] = self._kg_to_atom()

        # Step 3: 态元→真值（态元进化产生新真值）
        result["steps"]["atom_to_truth"] = self._atom_to_truth()

        self.state["cycles"] += 1
        self.state["truths_synced"] += result["steps"]["truth_to_kg"].get("synced", 0)
        self.state["kg_updated"] += result["steps"]["kg_to_atom"].get("entities_affected", 0)
        self.state["atoms_evolved"] += result["steps"]["atom_to_truth"].get("atoms_evolved", 0)
        self.state["history"].append({"cycle_id": cycle_id, "timestamp": int(time.time()), **result})
        if len(self.state["history"]) > 50:
            self.state["history"] = self.state["history"][-50:]
        self._save_state()

        return result

    def _truth_to_kg(self) -> Dict:
        """从内核真值/元法则更新知识图谱实体属性"""
        with open(self.kg_path) as f:
            kg = json.load(f)
        with open(self.kernel_path) as f:
            kernel = json.load(f)

        entities = {e["id"]: e for e in kg["entities"]}
        updated = 0

        # 同步内核版本信息到ZONGYUAN-ROOT实体
        if "SYS.ZONGYUAN_ROOT" in entities:
            entities["SYS.ZONGYUAN_ROOT"]["kernel_version"] = kernel.get("version", "unknown")
            entities["SYS.ZONGYUAN_ROOT"]["active_modules"] = len(kernel.get("active_modules", []))
            entities["SYS.ZONGYUAN_ROOT"]["meta_laws"] = len(kernel.get("meta_laws", {}))
            updated += 1

        # 同步态元统计
        if os.path.exists(self.atom_db):
            c = sqlite3.connect(self.atom_db)
            cur = c.cursor()
            cur.execute("SELECT COUNT(*), AVG(fitness_score), SUM(CASE WHEN energy_state='high_energy' THEN 1 ELSE 0 END) FROM atoms")
            total, avg_f, high_e = cur.fetchone()
            c.close()
            if "TECH.STATE_ATOM" in entities:
                entities["TECH.STATE_ATOM"]["total_atoms"] = total
                entities["TECH.STATE_ATOM"]["avg_fitness"] = round(avg_f or 0, 3)
                entities["TECH.STATE_ATOM"]["high_energy"] = high_e
                updated += 1

        kg["entities"] = list(entities.values())
        with open(self.kg_path, 'w') as f:
            json.dump(kg, f, ensure_ascii=False, indent=2)

        return {"synced": updated, "action": "内核真值→图谱实体属性同步"}

    def _kg_to_atom(self) -> Dict:
        """图谱中心实体能量注入态元"""
        with open(self.kg_path) as f:
            kg = json.load(f)

        degree = {}
        for r in kg["relations"]:
            degree[r["source"]] = degree.get(r["source"], 0) + 1
            degree[r["target"]] = degree.get(r["target"], 0) + 1
        top_entities = sorted(degree.items(), key=lambda x: -x[1])[:5]

        if not os.path.exists(self.atom_db):
            return {"entities_affected": 0, "action": "态元库不存在"}

        c = sqlite3.connect(self.atom_db)
        cur = c.cursor()
        cur.execute("SELECT atom_id, fitness_score FROM atoms ORDER BY fitness_score DESC LIMIT 5")
        top_atoms = cur.fetchall()

        # 图谱中心度映射到态元能量加成
        boosted = 0
        for i, (aid, fitness) in enumerate(top_atoms):
            if i < len(top_entities):
                entity_degree = top_entities[i][1]
                boost = min(0.05, entity_degree / 1000)
                new_fitness = min(0.95, fitness + boost)
                cur.execute("UPDATE atoms SET fitness_score=?, usage_frequency=usage_frequency+1, updated_at=? WHERE atom_id=?",
                           (new_fitness, str(int(time.time())), aid))
                boosted += 1

        c.commit()
        c.close()
        return {"entities_affected": boosted, "action": "图谱中心度→态元能量注入", "top_degree": [(e[0][:20], e[1]) for e in top_entities]}

    def _atom_to_truth(self) -> Dict:
        """态元进化产生新真值条目"""
        if not os.path.exists(self.atom_db):
            return {"atoms_evolved": 0, "action": "态元库不存在"}

        c = sqlite3.connect(self.atom_db)
        cur = c.cursor()
        cur.execute("SELECT atom_id, atom_type, content, fitness_score FROM atoms WHERE fitness_score >= 0.7 ORDER BY fitness_score DESC LIMIT 3")
        high_atoms = cur.fetchall()
        c.close()

        new_truths = []
        for aid, atype, content, fitness in high_atoms:
            truth_key = f"TRINITY.ATOM.{aid[:20]}"
            truth_value = f"态元{aid}({atype})进化产生真值: fitness={fitness:.3f}, content={str(content)[:100]}"
            new_truths.append({"key": truth_key, "value": truth_value, "source": "trinity_linkage"})

        return {"atoms_evolved": len(new_truths), "new_truths": new_truths, "action": "高能量态元→新真值生成"}

    def get_status(self) -> Dict:
        return {
            "total_cycles": self.state["cycles"],
            "truths_synced": self.state["truths_synced"],
            "kg_updated": self.state["kg_updated"],
            "atoms_evolved": self.state["atoms_evolved"],
            "recent_cycles": self.state["history"][-3:]
        }


if __name__ == "__main__":
    engine = TrinityLinkageEngine()
    print("=== 三位一体联动引擎 V1.0 ===")
    print("Truth → KnowledgeGraph → StateAtom → Truth 闭环")
    print()

    # 执行3次循环
    for i in range(3):
        result = engine.cycle()
        print(f"循环{i+1}: {result['cycle_id']}")
        for step, data in result["steps"].items():
            print(f"  {step}: {data.get('action', '')} ({data.get('synced', data.get('entities_affected', data.get('atoms_evolved', 0)))}项)")
        print()

    print("=== 联动状态 ===")
    status = engine.get_status()
    for k, v in status.items():
        if k != "recent_cycles":
            print(f"  {k}: {v}")

#!/usr/bin/env python3
"""27大算子统一执行器：按十层拓扑串行，上游输出=下游输入，输出每日巡检报告
来源：云端母本 27-operator-topology | 本地工程化契约骨架 v1.0
用法：python3 run_27_operators.py [--raw-truths N]"""
import sys, json, datetime, importlib, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ctx

OPS = [  # (层, 模块, 函数名)
    ("L1", "l1_truth_filter", "op01_p4_truth_reconcile"),
    ("L1", "l1_truth_filter", "op02_p7_external_anchor"),
    ("L1", "l1_truth_filter", "op03_truth_distill"),
    ("L2", "l2_manifold", "op04_riemann_metric"),
    ("L2", "l2_manifold", "op05_sm_bs_mapping"),
    ("L2", "l2_manifold", "op06_drift_patrol"),
    ("L3", "l3_graph", "op07_entity_extract"),
    ("L3", "l3_graph", "op08_graph_complete"),
    ("L3", "l3_graph", "op09_cross_doc_link"),
    ("L4", "l4_causal", "op10_causal_trace"),
    ("L4", "l4_causal", "op11_singularity_prob"),
    ("L4", "l4_causal", "op12_causal_intervene"),
    ("L5", "l5_cte", "op13_causal_to_truth"),
    ("L5", "l5_cte", "op14_truth_to_evolution"),
    ("L5", "l5_cte", "op15_evolution_to_causal"),
    ("L6", "l6_archive", "op16_four_layer_split"),
    ("L6", "l6_archive", "op17_nine_meta_class"),
    ("L6", "l6_archive", "op18_merkle_append"),
    ("L7", "l7_ledger", "op19_asset_reconcile"),
    ("L8", "l8_security", "op20_efuse"),
    ("L8", "l8_security", "op21_zkp"),
    ("L9", "l9_decision", "op22_plan_eval"),
    ("L9", "l9_decision", "op23_risk_classify"),
    ("L9", "l9_decision", "op24_legal_opinion"),
    ("L10", "l10_business", "op25_lv6_simulation"),
    ("L10", "l10_business", "op26_role_isolation"),
    ("L10", "l10_business", "op27_frame_consistency"),
]

def main():
    n_raw = int(sys.argv[sys.argv.index("--raw-truths")+1]) if "--raw-truths" in sys.argv else 20
    ctx.set("raw_truths", [{"source": "f" if i % 3 else "", "kind": ["fact","guess","opinion"][i % 3]} for i in range(n_raw)])
    report = {"date": datetime.date.today().isoformat(), "did": "DID-BR-000002",
              "operators": [], "ok": 0, "fail": 0}
    for layer, mod, fn in OPS:
        m = importlib.import_module(mod)
        try:
            r = getattr(m, fn)()
            report["operators"].append({"layer": layer, "op": fn, "status": "✅", "out": r})
            report["ok"] += 1
        except Exception as e:
            report["operators"].append({"layer": layer, "op": fn, "status": "❌", "err": str(e)[:80]})
            report["fail"] += 1
    report["drift_level"] = ctx.get("L2_level", "绿")
    report["singularity"] = ctx.get("L4_singularity", {})
    report["fitness_phi"] = ctx.get("L5_fitness", 0)
    report["merkle_root"] = ctx.get("L6_merkle_root", "")[:16]
    report["fuse_tripped"] = ctx.get("L8_fuse", {}).get("tripped", False)
    report["top_plan"] = ctx.get("L9_plans", [{}])[0] if ctx.get("L9_plans") else {}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n=== 27算子执行完成: ok={report['ok']} fail={report['fail']} ===")

if __name__ == "__main__":
    main()

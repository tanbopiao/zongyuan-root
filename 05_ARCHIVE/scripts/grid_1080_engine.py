#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""grid_1080_engine — 1080基准网格运行时引擎（G0-G2 部署层）

真值来源: MR-042 易经二进制-太玄三进制-1080基准网格元法则 (P0-数学基底级)
权威内核: 01_ASSETS/documents/docs/code_archive/grid_1080_engine.py
  —— 以 importlib 加载，数学逻辑零拷贝零改动（按真值实现，不发明规则）

本层提供:
  G0  部署入口与自测: 1080完备遍历/坐标往返/双进制三验证例/energy_avg=189.0/龙粒子五态
  G1  真值格点索引:   truth_to_point(key) —— MR-042 applications 规定"每条真值可编码为
                      一个坐标点"，编码算法为工程实现选择: sha256(key) % 1080（确定性/均匀/可复现）
  G2  可微算子原型:   连续坐标空间欧氏距离 + 解析梯度 + 数值梯度校验（gradcheck）

用法:
  python3 scripts/grid_1080_engine.py --selftest
  python3 scripts/grid_1080_engine.py --build-data [--data-dir DIR]
  python3 scripts/grid_1080_engine.py --index <truth-ledger.csv> [--out FILE]

数据默认输出 /opt/ZONGYUAN-ROOT/data/（MR-042 权威路径，云机即位即用），
沙箱可用 GRID1080_DATA_DIR 或 --data-dir 覆盖。
"""

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import sys

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTH_PATH = os.path.join(
    REPO_ROOT, "01_ASSETS", "documents", "docs", "code_archive", "grid_1080_engine.py"
)
DEFAULT_DATA_DIR = os.environ.get("GRID1080_DATA_DIR") or "/opt/ZONGYUAN-ROOT/data"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
DID = "DID-BR-000002"


def load_authority():
    """加载 MR-042 权威内核（只读复用，不修改）"""
    if not os.path.isfile(AUTH_PATH):
        raise FileNotFoundError(f"MR-042 权威内核缺失: {AUTH_PATH}")
    spec = importlib.util.spec_from_file_location("grid1080_authority", AUTH_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


K = load_authority()

# ==================== G1: 真值 → 格点 ====================

def truth_to_point(truth_key: str) -> dict:
    """确定性真值编码: sha256(key) % 1080 → (八卦, 太玄部, 五行) 坐标"""
    h = int(hashlib.sha256(truth_key.encode("utf-8")).hexdigest(), 16)
    idx = h % K.GRID_SIZE
    b, rem = divmod(idx, K.GRID_TAIXUAN * K.GRID_WUXING)
    t, w = divmod(rem, K.GRID_WUXING)
    return {
        "key": truth_key,
        "grid_id": f"G{idx:04d}",
        "global_index": idx,
        "coordinates": {"bagua_dim": b, "taixuan_dim": t, "wuxing_dim": w},
    }


def build_truth_index(keys) -> dict:
    """真值集合 → 1080 格点索引（含占用分布，供纯度/均衡观测）"""
    entries = [truth_to_point(k) for k in keys]
    occupancy = [0] * K.GRID_SIZE
    for e in entries:
        occupancy[e["global_index"]] += 1
    used = sum(1 for c in occupancy if c > 0)
    return {
        "engine": "grid_1080_engine (G1)",
        "authority": "MR-042",
        "did": DID,
        "anchor": ANCHOR,
        "formula": "8 x 27 x 5 = 2^3 x 3^3 x 5 = 1080",
        "total_keys": len(entries),
        "grid_points": K.GRID_SIZE,
        "points_occupied": used,
        "max_occupancy": max(occupancy) if occupancy else 0,
        "entries": entries,
    }


def load_ledger_keys(csv_path: str) -> list:
    """从 truth-ledger.csv 读取索引键（file_path 为主键素材）"""
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [r.get("file_path") or f"seq:{r.get('seq')}" for r in rows]


# ==================== G2: 可微算子 ====================

def grid_distance(x: np.ndarray, y: np.ndarray) -> float:
    """连续坐标空间欧氏距离（格点的连续松弛，可微算子基础）"""
    return float(np.linalg.norm(np.asarray(x, float) - np.asarray(y, float)))


def grid_distance_grad(x: np.ndarray, y: np.ndarray) -> tuple:
    """解析梯度: d/dx ||x-y|| = (x-y)/||x-y||, d/dy = -(x-y)/||x-y||"""
    d = np.asarray(x, float) - np.asarray(y, float)
    n = np.linalg.norm(d)
    g = d / (n + 1e-12)
    return g, -g


def gradcheck(eps: float = 1e-6) -> dict:
    """数值梯度校验（中心差分 vs 解析梯度），返回最大相对误差"""
    rng = np.random.default_rng(42)  # 固定种子 = 可复现
    max_rel = 0.0
    for _ in range(16):
        x = rng.uniform(-7, 7, 3)
        y = rng.uniform(-7, 7, 3)
        gx, gy = grid_distance_grad(x, y)
        gn_x = np.zeros(3)
        gn_y = np.zeros(3)
        for i in range(3):
            e = np.zeros(3)
            e[i] = eps
            gn_x[i] = (grid_distance(x + e, y) - grid_distance(x - e, y)) / (2 * eps)
            gn_y[i] = (grid_distance(x, y + e) - grid_distance(x, y - e)) / (2 * eps)
        for a, b in ((gx, gn_x), (gy, gn_y)):
            rel = np.max(np.abs(a - b)) / (np.max(np.abs(a)) + 1e-8)
            max_rel = max(max_rel, float(rel))
    return {"max_rel_err": max_rel, "threshold": 1e-6, "pass": max_rel < 1e-6}


# ==================== G0/G2 仿真自测 ====================

def run_selftest() -> dict:
    checks = []

    def check(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    # --- G0-1 1080 完备遍历、无重复 ---
    grid = K.build_1080_grid()
    idxs = [p["global_index"] for p in grid]
    check("G0 grid_complete_1080",
          len(grid) == K.GRID_SIZE == 1080 and len(set(idxs)) == 1080,
          f"points={len(grid)} unique_idx={len(set(idxs))}")

    # --- G0-2 坐标 ↔ 全局索引 双向往返 ---
    rt_ok = True
    for b in range(8):
        for t in range(27):
            for w in range(5):
                p = K.get_grid_point(b, t, w)
                idx = p["global_index"]
                b2, rem = divmod(idx, 27 * 5)
                t2, w2 = divmod(rem, 5)
                if (b2, t2, w2) != (b, t, w):
                    rt_ok = False
                    break
            if not rt_ok:
                break
        if not rt_ok:
            break
    check("G0 coord_roundtrip", rt_ok, "27*8*5 全坐标双向一致")

    # --- G0-3 双进制转换三验证例（MR-042 verified_examples） ---
    ex1 = K.binary_to_ternary_grid("000000")   # 坤 ↔ 中首 0000
    ex2 = K.binary_to_ternary_grid("111111")   # 乾 ↔ 最高首 2222
    ex3 = K.binary_to_ternary_grid("101010")   # 既济 → 减首 1222
    conv_ok = (ex1["ternary"] == "0000" and ex1["hexagram"]["name"] == "坤"
               and ex2["ternary"] == "2222" and ex2["hexagram"]["name"] == "乾"
               and ex3["ternary"] == "1222" and ex3["hexagram"]["name"] == "既济"
               and ex3["taixuan_head"]["name"] == "减")
    check("G0 conversion_examples_mr042", conv_ok,
          f"坤→{ex1['ternary']}{ex1['taixuan_head']['name']} | "
          f"乾→{ex2['ternary']}{ex2['taixuan_head']['name']} | "
          f"既济→{ex3['ternary']}{ex3['taixuan_head']['name']}")

    # --- G0-4 反向转换端点 ---
    back1 = K.ternary_to_binary_grid("0000")
    back2 = K.ternary_to_binary_grid("2222")
    check("G0 reverse_conversion_endpoints",
          back1["binary"] == "000000" and back2["binary"] == "111111",
          f"中首→{back1['binary']} 最高首→{back2['binary']}")

    # --- G0-5 energy_avg = 189.0（MR-042 常数互证） ---
    stats = K.grid_statistics()
    check("G0 energy_avg_189",
          abs(stats["energy_avg"] - 189.0) < 1e-9,
          f"avg={stats['energy_avg']}")

    # --- G0-6 龙粒子五态合一 ---
    lp = K.longlizi_encode(7, 26, 4, state=1)
    fs = lp["five_states"]
    five_ok = (fs["life_state"] == 1 and fs["energy_state"] == 1080
               and fs["info_state"] == "111" + format(26, "05b")   # 乾卦111 + 26=11010
               and fs["logic_state"] == "222" + "21"               # 太玄26=222 + 八卦7=21
               and fs["intelligence_state"] == "元极恒一")
    check("G0 longlizi_five_states", five_ok,
          f"info={fs['info_state']} logic={fs['logic_state']} energy={fs['energy_state']}")

    # --- G1-1 真值编码确定性 ---
    k1 = truth_to_point("MR-042")
    k2 = truth_to_point("MR-042")
    check("G1 truth_encode_deterministic", k1 == k2, f"MR-042 → {k1['grid_id']}")

    # --- G1-2 索引建立与坐标合法 ---
    demo_keys = ["MR-042", "MR-035", "MR-036", "MR-038", "MR-039",
                 "META-LAW-008", "META-LAW-009", "RULE-005", "DID-BR-000002"]
    idx = build_truth_index(demo_keys)
    coord_ok = all(
        0 <= e["coordinates"]["bagua_dim"] < 8
        and 0 <= e["coordinates"]["taixuan_dim"] < 27
        and 0 <= e["coordinates"]["wuxing_dim"] < 5
        for e in idx["entries"]
    )
    check("G1 index_build", idx["total_keys"] == len(demo_keys) and coord_ok,
          f"keys={idx['total_keys']} occupied={idx['points_occupied']}")

    # --- G2-1 数值梯度校验 ---
    gc = gradcheck()
    check("G2 gradcheck", gc["pass"],
          f"max_rel_err={gc['max_rel_err']:.2e} < {gc['threshold']}")

    passed = sum(1 for c in checks if c["ok"])
    return {
        "suite": "grid1080_sim_G0-G2",
        "authority": "MR-042",
        "did": DID,
        "total": len(checks),
        "passed": passed,
        "all_pass": passed == len(checks),
        "checks": checks,
    }


# ==================== 主入口 ====================

def cmd_build_data(data_dir: str) -> str:
    os.makedirs(data_dir, exist_ok=True)
    grid = K.build_1080_grid()
    stats = K.grid_statistics()
    out = os.path.join(data_dir, "grid_1080.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"grid": grid, "statistics": stats}, f, ensure_ascii=False, indent=2)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="1080 grid runtime engine (MR-042, G0-G2)")
    ap.add_argument("--selftest", action="store_true", help="run G0-G2 simulation tests")
    ap.add_argument("--build-data", action="store_true", help="build grid_1080.json")
    ap.add_argument("--index", metavar="CSV", help="build truth ledger grid index")
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--out", default="grid1080_out/truth_grid_index.json")
    args = ap.parse_args(argv)

    if args.selftest:
        rep = run_selftest()
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep["all_pass"] else 1

    if args.build_data:
        path = cmd_build_data(args.data_dir)
        print(f"[grid1080] data written: {path}")
        return 0

    if args.index:
        keys = load_ledger_keys(args.index)
        rep = build_truth_index(keys)
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
        print(f"[grid1080] index: keys={rep['total_keys']} "
              f"occupied={rep['points_occupied']} -> {args.out}")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

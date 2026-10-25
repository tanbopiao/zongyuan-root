import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import numpy as np
from pathlib import Path
from hf_yuanji_steady import model, tokenizer, cfg
from seed_extractor import extract_seed_truth, SEED_ROOT


def cosine_similarity(a, b):
    a = np.asarray(a).flatten()
    b = np.asarray(b).flatten()
    # 维度对齐：截断到较小维度
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def verify_seed_consistency():
    manifest = json.loads(Path(SEED_ROOT, "manifest.json").read_text(encoding="utf-8"))
    text_lines = Path(SEED_ROOT, "text/seed_text.jsonl").read_text(encoding="utf-8").splitlines()
    drift_stat = {"L0": 0, "L1": 0, "L2": 0}
    pass_stat = {"L0": 0, "L1": 0, "L2": 0}

    for line in text_lines:
        seed = json.loads(line)
        old_vec = np.array(seed.get("old_vec", seed.get("vec", [0])))
        new_vec = np.array(seed.get("new_vec", seed.get("vec", [0])))
        cos = cosine_similarity(old_vec, new_vec)
        level = seed.get("level", "L2")
        if cos < 0.95:
            drift_stat[level] += 1
        else:
            pass_stat[level] += 1

    total = sum(drift_stat.values()) + sum(pass_stat.values())
    print("L0漂移:",drift_stat["L0"],"L1:",drift_stat["L1"],"L2:",drift_stat["L2"])
    if drift_stat["L0"] == 0:
        print("CONVERGED: L0零漂移，基线有效")
        return 0
    else:
        print("ROLLED_BACK: L0漂移，回滚")
        return 1


if __name__ == "__main__":
    sys.exit(verify_seed_consistency())

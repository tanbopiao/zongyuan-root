import os
import shutil
import time
from pathlib import Path

_YR = os.environ.get("YUANJI_ROOT", "/home/user/ZONGYUAN-ROOT")
SEED_ROOT = Path(_YR) / "persist" / "seed_truth"
BACKUP_ROOT = Path(_YR) / "backup" / "seed_truth"


def snapshot_seed():
    ts = time.strftime("%Y%m%d_%H%M%S")
    dst = BACKUP_ROOT / f"seed_baseline_{ts}"
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SEED_ROOT, dst)
    print(f"✅种子基线快照已保存：{dst}")


if __name__ == "__main__":
    snapshot_seed()

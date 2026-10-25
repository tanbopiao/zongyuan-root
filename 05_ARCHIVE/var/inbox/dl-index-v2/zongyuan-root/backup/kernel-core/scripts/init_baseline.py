#!/usr/bin/env python3
"""哈希基线初始化/校验/查看。用法：
  python3 scripts/init_baseline.py [--verify] [--show] [根目录]
默认执行 init；根目录默认取 ZONGYUAN_ROOT 或包根目录。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kernel.core.config import Config
from kernel.core import merkle


def main():
    argv = sys.argv[1:]
    mode = "init"
    if "--verify" in argv:
        mode = "verify"
    elif "--show" in argv:
        mode = "show"
    root_arg = next((a for a in argv if not a.startswith("--")), None)

    cfg = Config(root_arg)
    root = cfg.path("meta_laws")
    state = cfg.path("baseline_state")

    if mode == "init":
        data = merkle.save_baseline(root, state)
        print(f"基线已生成: {state}")
        print(f"ROOT HASH: {data['root_hash']}")
        print(f"覆盖文件数: {len(data['files'])}")
    elif mode == "verify":
        status, cur, exp = merkle.verify(root, state)
        print(f"状态: {status}")
        print(f"当前: {cur}")
        print(f"基线: {exp}")
        if status != "ok":
            sys.exit(1)
    else:
        import json
        data = json.loads(state.read_text(encoding="utf-8")) if state.exists() else {}
        print(f"ROOT HASH: {data.get('root_hash', '(无基线)')}")
        print(f"创建时间: {data.get('created_at', '-')}")
        print(f"文件数: {len(data.get('files', {}))}")


if __name__ == "__main__":
    main()

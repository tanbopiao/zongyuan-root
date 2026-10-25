#!/usr/bin/env python3
"""人工解除内核熔断（仅运维人员手动执行）。

前提：先还原被篡改文件并重建哈希基线（scripts/init_baseline.py），
否则解除后下一次锁校验会再次触发熔断。

用法：
  python3 scripts/reset_fuse.py [根目录] [原因说明]
示例：
  python3 scripts/reset_fuse.py /opt/zongyuan-kernel "已还原文件并重建基线，人工解除"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kernel.core.config import Config


def main():
    argv = sys.argv[1:]
    root_arg = argv[0] if argv else None
    reason = " ".join(argv[1:]) or "人工解除熔断"

    cfg = Config(root_arg)
    req = cfg.path("reset_request")
    pid = cfg.path("pid_file")

    if not pid.exists():
        print("内核未在运行：熔断状态是进程内存态，重启内核即回到 NORMAL，无需本脚本。")
        print("（如果文件已被篡改，请先还原文件并重建基线再重启。）")
        return

    req.parent.mkdir(parents=True, exist_ok=True)
    req.write_text(reason, encoding="utf-8")
    print(f"已写入解除请求: {req}")
    print(f"原因: {reason}")
    print("内核调度器将在数秒内检测到请求并解除熔断，审计记录 state.reset(actor=operator)。")
    print("校验: curl -s http://127.0.0.1:8081/status   → fused 应为 false")


if __name__ == "__main__":
    main()

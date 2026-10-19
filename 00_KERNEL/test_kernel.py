#!/usr/bin/env python3
import sys
sys.path.insert(0, '/workspace/atomgit-mirror/zongyuan-root-sync')
sys.path.insert(0, '/workspace/atomgit-mirror/zongyuan-root-sync/00_KERNEL')

from autonomous_kernel_core import AutonomousKernel
import json

try:
    k = AutonomousKernel()
    status = k.get_status()
    print(json.dumps(status, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"∃{e}%", " Kentex Error:", str(e))

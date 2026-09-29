#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E4 配置执行器: JSON配置变更（diff+备份）"""
import os, json, copy, time

def execute(task: dict) -> dict:
    params = task.get("params", {})
    config_file = params.get("target", "")
    updates = params.get("updates", {})
    if not config_file or not os.path.exists(config_file):
        return {"status": "FAILED", "reason": f"配置不存在: {config_file}"}
    try:
        with open(config_file) as f:
            old = json.load(f)
        # 备份
        backup = f"{config_file}.bak_{int(time.time())}"
        with open(backup, "w") as f:
            json.dump(old, f, ensure_ascii=False, indent=2)
        # 应用变更
        new = copy.deepcopy(old)
        for k, v in updates.items():
            new[k] = v
        with open(config_file, "w") as f:
            json.dump(new, f, ensure_ascii=False, indent=2)
        return {"status": "OK", "backup": backup, "updated_keys": list(updates.keys())}
    except Exception as e:
        return {"status": "FAILED", "reason": str(e)}

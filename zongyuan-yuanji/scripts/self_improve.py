#!/usr/bin/env python3
import json, glob, os
# 自我改进：根据bug自动优化
bugs = [b for b in json.load(open("/root/zongyuan-yuanji/var/tasks/*.json")) if "not found" in str(b)]
print("自我改进：", len(bugs), "个bug待修")

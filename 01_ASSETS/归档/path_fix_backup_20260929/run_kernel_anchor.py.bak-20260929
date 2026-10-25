#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""启动 kernel_anchor_api 服务"""
import uvicorn
import sys
sys.path.insert(0, "/opt/ZONGYUAN-ROOT")
from kernel_anchor_api import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8013, workers=1)

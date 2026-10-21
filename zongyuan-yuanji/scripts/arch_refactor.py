#!/usr/bin/env python3
# 自我架构重构：检查并优化文件结构
import os, subprocess
SRC = "/root/zongyuan-yuanji/src"
scripts = "/root/zongyuan-yuanji/scripts"

def check():
    files = os.listdir(SRC)
    big = [f for f in files if os.path.getsize(os.path.join(SRC,f)) > 100000]
    return {"文件数": len(files), "大文件": big}

if __name__ == "__main__":
    print(check())

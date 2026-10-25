#!/usr/bin/env python3
# 自我代码优化：读自己→找优化→改→测试→不行回滚
import subprocess, shutil, os, time

WRAPPER = "/root/zongyuan-yuanji/src/wrapper.py"

def backup():
    bk = WRAPPER + ".auto-bak." + str(int(time.time()))
    shutil.copy(WRAPPER, bk)
    return bk

def test():
    # 语法检查+健康检查
    r = subprocess.run(["python3","-m","py_compile",WRAPPER],capture_output=True)
    if r.returncode != 0: return False
    r2 = subprocess.run(["curl","-sk","https://127.0.0.1:18080/health","--max-time","3"],capture_output=True,text=True)
    return "ok" in r2.stdout

def optimize():
    bk = backup()
    with open(WRAPPER) as f:
        code = f.read()
    changed = False
    # 优化1：去掉重复的import
    lines = code.split("\n")
    seen_imports = set()
    new_lines = []
    for line in lines:
        if line.startswith("import ") or line.startswith("from "):
            if line in seen_imports:
                changed = True
                continue
            seen_imports.add(line)
        new_lines.append(line)
    if changed:
        with open(WRAPPER,"w") as f:
            f.write("\n".join(new_lines))
        # 测试
        if test():
            return "去重import成功"
        else:
            shutil.copy(bk, WRAPPER)
            subprocess.run(["systemctl","restart","yuanji-wrapper"])
            return "测试失败已回滚"
    return "无需优化"

if __name__ == "__main__":
    print(optimize())

#!/usr/bin/env python3
# 自修复：出问题自动诊断+修复
import subprocess, json, time

def check():
    issues = []
    # 1. wrapper语法错误
    r = subprocess.run(["python3","-m","py_compile","/root/zongyuan-yuanji/src/wrapper.py"],
                       capture_output=True,text=True)
    if r.returncode != 0:
        issues.append({"issue":"wrapper语法错误","fix":"回滚最近备份"})
        # 回滚
        import glob
        baks = sorted(glob.glob("/root/zongyuan-yuanji/src/wrapper.py.bak*"),reverse=True)
        if baks:
            subprocess.run(["cp",baks[0],"/root/zongyuan-yuanji/src/wrapper.py"])
            subprocess.run(["systemctl","restart","yuanji-wrapper"])
            issues[-1]["done"]="已回滚"+baks[0]
    # 2. nginx配置错误
    r = subprocess.run(["/usr/local/nginx/sbin/nginx","-t"],capture_output=True,text=True)
    if r.returncode != 0:
        issues.append({"issue":"nginx配置错误","fix":"回滚nginx配置"})
    return issues

if __name__ == "__main__":
    i = check()
    if i:
        print(json.dumps(i,ensure_ascii=False))
    else:
        print("无问题")

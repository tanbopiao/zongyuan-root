#!/usr/bin/env python3
"""内核安全写入 - 文件锁+原子替换，杜绝并发写入损坏"""
import json, os, fcntl, tempfile, shutil, hashlib, time

def safe_write_kernel(kernel_path, data):
    """安全写入内核：文件锁+临时文件+原子替换"""
    lock_path = kernel_path + ".lock"
    with open(lock_path, "w") as lockf:
        fcntl.flock(lockf, fcntl.LOCK_EX)
        try:
            # 写入临时文件
            dir_path = os.path.dirname(kernel_path)
            fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            # 原子替换
            shutil.move(tmp_path, kernel_path)
            # 验证
            with open(kernel_path) as f:
                json.load(f)
            return True
        except Exception as e:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise e
        finally:
            fcntl.flock(lockf, fcntl.LOCK_UN)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        path = sys.argv[1]
        with open(path) as f:
            data = json.load(f)
        safe_write_kernel(path, data)
        print("安全写入完成: %s" % path)

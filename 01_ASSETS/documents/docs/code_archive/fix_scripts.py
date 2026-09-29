#!/usr/bin/env python3
"""修复NXShell审计和磁盘监控脚本为常驻循环模式"""
import re

# 修复NXShell审计脚本
filepath1 = "/opt/ZONGYUAN-ROOT/bin/nxshell_audit_reporter.py"
with open(filepath1, "r", encoding="utf-8") as f:
    content = f.read()

# 找到 if __name__ == "__main__": 的位置，截断后面的内容
idx = content.find('if __name__ == "__main__":')
if idx > 0:
    new_main = '''if __name__ == "__main__":
    ensure_dirs()
    print("NXShell审计事件上报器启动")
    print(f"网关地址: {GATEWAY_URL}")
    print(f"队列文件: {REPORT_QUEUE_FILE}")

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # 测试模式
        event = create_audit_event("file_upload", {
            "filename": "test_audit.webp",
            "size": 1024,
            "sha256": "abc123",
            "bucket": "images"
        })
        print("创建审计事件: " + event["event_id"])
        result = process_queue(max_batch=1)
        print("上报结果:", json.dumps(result, indent=2))
    else:
        # 常驻循环模式
        import time
        while True:
            try:
                result = process_queue(max_batch=20)
                if result["processed"] > 0:
                    ts = time.strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[{ts}] 处理了{result['processed']}个事件, 成功{result['success']}, 失败{result['failed']}, 剩余{result['remaining']}")
                time.sleep(30)
            except Exception as e:
                print(f"循环异常: {e}")
                time.sleep(30)
'''
    content = content[:idx] + new_main
    print("✅ NXShell审计脚本已修复为常驻循环")

with open(filepath1, "w", encoding="utf-8") as f:
    f.write(content)

# 修复磁盘监控脚本
filepath2 = "/opt/ZONGYUAN-ROOT/bin/disk_monitor.py"
with open(filepath2, "r", encoding="utf-8") as f:
    content2 = f.read()

old_disk_main = 'if __name__ == "__main__":\n    main()'
new_disk_main = '''if __name__ == "__main__":
    import time
    print("磁盘水位监控服务启动")
    while True:
        try:
            main()
        except Exception as e:
            print(f"监控异常: {e}")
        time.sleep(60)
'''

if old_disk_main in content2:
    content2 = content2.replace(old_disk_main, new_disk_main)
    print("✅ 磁盘监控脚本已修复为常驻循环")

with open(filepath2, "w", encoding="utf-8") as f:
    f.write(content2)

print("✅ 两个脚本都已修复")

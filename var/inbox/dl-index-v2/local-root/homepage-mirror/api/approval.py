"""
API调用审批闸门
所有API调用必须先经过审批
"""
import time

# 白名单：免费API不需要审批
WHITELIST = ["zhigu", "agnes_free", "ntfy"]

def need_approval(task_type):
    if task_type in WHITELIST:
        return False
    return True

def get_pending():
    return {"pending": []}

def approve(task_id):
    return {"approved": task_id}

#!/usr/bin/env python3
# 范式自迁移接入集群调度器
# 在任务提交时自动选择最优范式，执行完成后反馈结果

target = "/opt/ZONGYUAN-ROOT/cluster/orchestrator.py"

with open(target) as f:
    content = f.read()

# 1. 添加范式自迁移导入
if "paradigm_migration" not in content:
    content = content.replace(
        "import json\nfrom datetime import datetime",
        "import json\nimport sys\nimport os\nfrom datetime import datetime\n\n# 范式自迁移引擎\nsys.path.insert(0, '/opt/ZONGYUAN-ROOT/scripts')\ntry:\n    import paradigm_migration as pm\n    PARADIGM_AVAILABLE = True\nexcept Exception as e:\n    PARADIGM_AVAILABLE = False\n    print(f'[WARN] 范式自迁移引擎加载失败: {e}')"
    )
    print("✅ 已添加范式自迁移导入")

# 2. 在submit_task中添加范式选择
old_submit = """            task_id = orchestrator.submit_task(task_type, payload, priority, metadata)
            self._send_json({"status": "success", "task_id": task_id})"""

new_submit = """            # 范式自迁移：自动选择最优范式
            selected_paradigm = None
            if PARADIGM_AVAILABLE:
                try:
                    task_desc = payload.get('description', '') if isinstance(payload, dict) else ''
                    selected_paradigm = pm.select_paradigm(task_type, task_desc)
                    if isinstance(metadata, dict):
                        metadata['paradigm'] = selected_paradigm
                    else:
                        metadata = {'paradigm': selected_paradigm}
                except Exception as e:
                    print(f'[WARN] 范式选择失败: {e}')
            
            task_id = orchestrator.submit_task(task_type, payload, priority, metadata)
            self._send_json({"status": "success", "task_id": task_id, "paradigm": selected_paradigm})"""

if old_submit in content:
    content = content.replace(old_submit, new_submit)
    print("✅ 已在任务提交中集成范式选择")
else:
    print("⚠️ 未找到submit_task代码块，可能已修改过")

# 3. 添加范式反馈API端点
if "/api/task/complete" not in content:
    old_health = """        elif self.path == '/health':
            self._send_json({"status": "healthy", "service": "cluster-orchestrator", "timestamp": datetime.now().isoformat()})"""
    
    new_health = """        elif self.path == '/api/task/complete':
            # 任务完成反馈（用于范式自迁移学习）
            task_id = data.get('task_id', '')
            task_type = data.get('type', '')
            success = data.get('success', True)
            if PARADIGM_AVAILABLE and task_type:
                try:
                    pm.report_success(task_type, success)
                except Exception as e:
                    print(f'[WARN] 范式反馈失败: {e}')
            self._send_json({"status": "success", "feedback": "recorded"})
        
        elif self.path == '/api/paradigm/status':
            # 范式自迁移状态
            if PARADIGM_AVAILABLE:
                status = pm.get_status()
                self._send_json({"status": "ok", "paradigm": status})
            else:
                self._send_json({"status": "unavailable"})
        
        elif self.path == '/health':
            self._send_json({"status": "healthy", "service": "cluster-orchestrator", "timestamp": datetime.now().isoformat()})"""
    
    content = content.replace(old_health, new_health)
    print("✅ 已添加范式反馈和状态API端点")

# 4. 更新API文档
if "paradigm" not in content.split("API端点:")[-1].split("try:")[0]:
    content = content.replace(
        """    print(f"     POST /api/task/submit - 提交任务")
    print(f"     GET  /health        - 健康检查")""",
        """    print(f"     POST /api/task/submit - 提交任务（自动范式选择）")
    print(f"     POST /api/task/complete - 任务完成反馈（范式学习）")
    print(f"     GET  /api/paradigm/status - 范式自迁移状态")
    print(f"     GET  /health        - 健康检查")"""
    )
    print("✅ 已更新API文档")

with open(target, "w") as f:
    f.write(content)

print("\n✅ 范式自迁移已接入集群调度器")
print("   - 任务提交时自动选择最优范式")
print("   - 任务完成后反馈结果用于范式学习")
print("   - 新增 /api/paradigm/status 端点")

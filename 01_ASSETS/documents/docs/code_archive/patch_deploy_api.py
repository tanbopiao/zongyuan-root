#!/usr/bin/env python3
"""
给记忆网关添加 /api/deploy/* 系列API端点
支持多窗口部署任务队列管理
"""
import os
import shutil
import time
from datetime import datetime

GATEWAY_SCRIPT = "/opt/ZONGYUAN-ROOT/engine/scripts/unified_gateway_9120.py"
BACKUP_SUFFIX = ".bak." + datetime.now().strftime("%Y%m%d_%H%M%S")

# 备份
backup_path = GATEWAY_SCRIPT + BACKUP_SUFFIX
shutil.copy2(GATEWAY_SCRIPT, backup_path)
print("✅ 已备份原文件:", backup_path)

with open(GATEWAY_SCRIPT, "r", encoding="utf-8") as f:
    content = f.read()

# ========== 1. 在 do_GET 中添加 deploy 路径分发 ==========
old_get = """        # 语义校验API
        if path == "/api/semantic/stats":
            self._handle_semantic_stats()
            return
        if path == "/api/semantic/audit":
            self._handle_semantic_audit()
            return

        # 其他路径交给记忆网关处理
        super().do_GET()"""

new_get = """        # 语义校验API
        if path == "/api/semantic/stats":
            self._handle_semantic_stats()
            return
        if path == "/api/semantic/audit":
            self._handle_semantic_audit()
            return

        # ========== 部署调度中心API ==========
        if path == "/api/deploy/tasks":
            self._handle_deploy_list_tasks()
            return
        if path.startswith("/api/deploy/tasks/"):
            task_id = path[len("/api/deploy/tasks/"):]
            self._handle_deploy_get_task(task_id)
            return
        if path.startswith("/api/deploy/nodes/") and path.endswith("/status"):
            node_id = path[len("/api/deploy/nodes/"):-len("/status")]
            self._handle_deploy_node_status(node_id)
            return
        if path == "/api/deploy/nodes":
            self._handle_deploy_list_nodes()
            return
        if path == "/api/deploy/stats":
            self._handle_deploy_stats()
            return

        # 其他路径交给记忆网关处理
        super().do_GET()"""

if old_get in content:
    content = content.replace(old_get, new_get)
    print("✅ do_GET 已添加 deploy API 路径分发")
else:
    print("⚠️ 未找到 do_GET 目标代码段")

# ========== 2. 在 do_POST 中添加 deploy 路径分发 ==========
old_post = """        # 记忆网关写入前置校验拦截
        if path == "/api/truth/upsert":
            self._handle_truth_upsert_with_validation()
            return

        # 其他路径交给记忆网关处理
        super().do_POST()"""

new_post = """        # 记忆网关写入前置校验拦截
        if path == "/api/truth/upsert":
            self._handle_truth_upsert_with_validation()
            return

        # ========== 部署调度中心API ==========
        if path == "/api/deploy/tasks":
            self._handle_deploy_create_task()
            return
        if path.startswith("/api/deploy/tasks/") and path.endswith("/claim"):
            task_id = path[len("/api/deploy/tasks/"):-len("/claim")]
            self._handle_deploy_claim_task(task_id)
            return

        # 其他路径交给记忆网关处理
        super().do_POST()"""

if old_post in content:
    content = content.replace(old_post, new_post)
    print("✅ do_POST 已添加 deploy API 路径分发")
else:
    print("⚠️ 未找到 do_POST 目标代码段")

# ========== 3. 添加 do_PUT 和 do_DELETE 方法 ==========
# 在 do_POST 方法结束后、语义校验API处理方法之前插入
old_marker = """    # ========== 语义校验API处理方法 =========="""

new_methods = """    # ========== PUT 请求分发 ==========
    def do_PUT(self):
        path = self.path.split("?")[0]
        if path.startswith("/api/deploy/tasks/") and path.endswith("/status"):
            task_id = path[len("/api/deploy/tasks/"):-len("/status")]
            self._handle_deploy_update_task_status(task_id)
            return
        # 其他路径返回404
        self._send_json_unified({"success": False, "error": "not_found"}, 404)

    # ========== DELETE 请求分发 ==========
    def do_DELETE(self):
        path = self.path.split("?")[0]
        if path.startswith("/api/deploy/tasks/"):
            task_id = path[len("/api/deploy/tasks/"):]
            self._handle_deploy_cancel_task(task_id)
            return
        self._send_json_unified({"success": False, "error": "not_found"}, 404)

    # ========== 部署调度中心API处理方法 ==========
    def _deploy_get_db(self):
        import sqlite3
        return sqlite3.connect("/opt/ZONGYUAN-ROOT/data/memory_gateway.db")

    def _handle_deploy_list_tasks(self):
        \"\"\"查询任务队列，支持按node_id/status/limit/offset筛选\"\"\"
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            node_id = params.get("node_id", [None])[0]
            status = params.get("status", [None])[0]
            limit = int(params.get("limit", [50])[0])
            offset = int(params.get("offset", [0])[0])
            order_by = params.get("order_by", ["priority,created_at"])[0]

            conn = self._deploy_get_db()
            cursor = conn.cursor()

            query = "SELECT * FROM deploy_task WHERE 1=1"
            count_query = "SELECT COUNT(*) FROM deploy_task WHERE 1=1"
            args = []

            if node_id:
                query += " AND target_node = ?"
                count_query += " AND target_node = ?"
                args.append(node_id)
            if status:
                query += " AND task_status = ?"
                count_query += " AND task_status = ?"
                args.append(status)

            query += " ORDER BY " + order_by + " LIMIT ? OFFSET ?"
            args.extend([limit, offset])

            cursor.execute(query, args)
            columns = [desc[0] for desc in cursor.description]
            tasks = [dict(zip(columns, row)) for row in cursor.fetchall()]

            cursor.execute(count_query, args[:-2])
            total = cursor.fetchone()[0]
            conn.close()

            self._send_json_unified({
                "success": True,
                "data": tasks,
                "total": total,
                "limit": limit,
                "offset": offset
            })
        except Exception as e:
            self._send_json_unified({"success": False, "error": str(e)}, 500)

    def _handle_deploy_get_task(self, task_id):
        \"\"\"查询单个任务详情\"\"\"
        try:
            conn = self._deploy_get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM deploy_task WHERE task_id = ?", (task_id,))
            columns = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
            conn.close()

            if row:
                self._send_json_unified({"success": True, "data": dict(zip(columns, row))})
            else:
                self._send_json_unified({"success": False, "error": "task_not_found"}, 404)
        except Exception as e:
            self._send_json_unified({"success": False, "error": str(e)}, 500)

    def _handle_deploy_create_task(self):
        \"\"\"提交部署任务（带冲突检测：节点已有running任务则排队）\"\"\"
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            task_data = __import__("json").loads(body)

            task_id = task_data.get("task_id", "DEPLOY-" + datetime.now().strftime("%Y%m%d%H%M%S"))
            target_node = task_data.get("target_node", "tencent-cloud-main-01")

            # 冲突检测：检查节点是否有正在运行的任务
            conn = self._deploy_get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM deploy_task WHERE target_node = ? AND task_status = 'running'", (target_node,))
            running_count = cursor.fetchone()[0]

            # 检查是否已有相同task_id
            cursor.execute("SELECT COUNT(*) FROM deploy_task WHERE task_id = ?", (task_id,))
            exists_count = cursor.fetchone()[0]

            if exists_count > 0:
                conn.close()
                self._send_json_unified({"success": False, "error": "task_id_already_exists", "task_id": task_id}, 409)
                return

            # 插入任务（状态为pending，如果有running任务则自然排队）
            cursor.execute("\"\"\"INSERT INTO deploy_task
                (task_id, target_node, task_name, package_url, package_sha256, version,
                 task_status, check_script, callback_truth_key, deploy_script, priority,
                 submitted_by, approval_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\"\"\"\",
                (task_id, target_node, task_data.get("task_name", ""),
                 task_data.get("package_url", ""), task_data.get("package_sha256", ""),
                 task_data.get("version", ""), "pending",
                 task_data.get("check_script", ""),
                 task_data.get("callback_truth_key", "DEPLOY.RESULT." + task_id),
                 task_data.get("deploy_script", ""),
                 task_data.get("priority", 5),
                 task_data.get("submitted_by", "unknown"),
                 task_data.get("approval_id", ""),
                 datetime.now().isoformat()))
            conn.commit()

            # 查询队列位置
            cursor.execute("SELECT COUNT(*) FROM deploy_task WHERE target_node = ? AND task_status = 'pending' AND created_at < (SELECT created_at FROM deploy_task WHERE task_id = ?)", (target_node, task_id))
            queue_position = cursor.fetchone()[0] + 1
            conn.close()

            result = {
                "success": True,
                "task_id": task_id,
                "target_node": target_node,
                "status": "pending",
                "queue_position": queue_position,
                "node_has_running_task": running_count > 0,
                "message": "任务已提交，当前排队第" + str(queue_position) + "位" if running_count > 0 else "任务已提交"
            }
            self._send_json_unified(result, 201)
        except Exception as e:
            self._send_json_unified({"success": False, "error": str(e)}, 500)

    def _handle_deploy_claim_task(self, task_id):
        \"\"\"Agent认领任务（将pending改为running，防止重复执行）\"\"\"
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            data = __import__("json").loads(body)
            node_id = data.get("node_id", "")
            agent_version = data.get("agent_version", "")

            conn = self._deploy_get_db()
            cursor = conn.cursor()

            # 原子性认领：只有pending状态才能改为running
            cursor.execute("UPDATE deploy_task SET task_status = 'running', started_at = ?, node_agent_version = ? WHERE task_id = ? AND task_status = 'pending'",
                           (datetime.now().isoformat(), agent_version, task_id))
            conn.commit()

            if cursor.rowcount > 0:
                cursor.execute("SELECT * FROM deploy_task WHERE task_id = ?", (task_id,))
                columns = [desc[0] for desc in cursor.description]
                row = cursor.fetchone()
                conn.close()
                self._send_json_unified({"success": True, "message": "任务已认领", "data": dict(zip(columns, row))})
            else:
                conn.close()
                self._send_json_unified({"success": False, "error": "任务已被认领或不存在"}, 409)
        except Exception as e:
            self._send_json_unified({"success": False, "error": str(e)}, 500)

    def _handle_deploy_update_task_status(self, task_id):
        \"\"\"更新任务状态（Agent执行完成后调用）\"\"\"
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = __import__("json").loads(body)
            new_status = data.get("status", "")
            result_log = data.get("result_log", "")
            error_message = data.get("error_message", "")

            if new_status not in ["success", "failed", "timeout", "rolled_back"]:
                self._send_json_unified({"success": False, "error": "invalid_status"}, 400)
                return

            conn = self._deploy_get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE deploy_task SET task_status = ?, completed_at = ?, result_log = ?, error_message = ? WHERE task_id = ?",
                           (new_status, datetime.now().isoformat(), result_log, error_message, task_id))
            conn.commit()
            updated = cursor.rowcount
            conn.close()

            if updated > 0:
                self._send_json_unified({"success": True, "task_id": task_id, "status": new_status})
            else:
                self._send_json_unified({"success": False, "error": "task_not_found"}, 404)
        except Exception as e:
            self._send_json_unified({"success": False, "error": str(e)}, 500)

    def _handle_deploy_cancel_task(self, task_id):
        \"\"\"取消pending任务\"\"\"
        try:
            conn = self._deploy_get_db()
            cursor = conn.cursor()
            # 只能取消pending状态的任务
            cursor.execute("UPDATE deploy_task SET task_status = 'cancelled' WHERE task_id = ? AND task_status = 'pending'", (task_id,))
            conn.commit()
            cancelled = cursor.rowcount
            conn.close()

            if cancelled > 0:
                self._send_json_unified({"success": True, "task_id": task_id, "message": "任务已取消"})
            else:
                self._send_json_unified({"success": False, "error": "任务不存在或不可取消（非pending状态）"}, 409)
        except Exception as e:
            self._send_json_unified({"success": False, "error": str(e)}, 500)

    def _handle_deploy_node_status(self, node_id):
        \"\"\"查询节点部署状态（当前运行任务+队列长度）\"\"\"
        try:
            conn = self._deploy_get_db()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM deploy_task WHERE target_node = ? AND task_status = 'running' ORDER BY started_at DESC LIMIT 1", (node_id,))
            columns = [desc[0] for desc in cursor.description]
            running_row = cursor.fetchone()
            running_task = dict(zip(columns, running_row)) if running_row else None

            cursor.execute("SELECT COUNT(*) FROM deploy_task WHERE target_node = ? AND task_status = 'pending'", (node_id,))
            pending_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM deploy_task WHERE target_node = ? AND task_status = 'success'", (node_id,))
            success_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM deploy_task WHERE target_node = ? AND task_status = 'failed'", (node_id,))
            failed_count = cursor.fetchone()[0]

            # 节点注册信息
            cursor.execute("SELECT * FROM node_registry WHERE node_id = ?", (node_id,))
            node_columns = [desc[0] for desc in cursor.description]
            node_row = cursor.fetchone()
            node_info = dict(zip(node_columns, node_row)) if node_row else None
            conn.close()

            self._send_json_unified({
                "success": True,
                "node_id": node_id,
                "node_info": node_info,
                "current_running_task": running_task,
                "queue_length": pending_count,
                "stats": {
                    "success": success_count,
                    "failed": failed_count,
                    "pending": pending_count,
                    "running": 1 if running_task else 0
                }
            })
        except Exception as e:
            self._send_json_unified({"success": False, "error": str(e)}, 500)

    def _handle_deploy_list_nodes(self):
        \"\"\"列出所有注册节点\"\"\"
        try:
            conn = self._deploy_get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM node_registry ORDER BY node_id")
            columns = [desc[0] for desc in cursor.description]
            nodes = [dict(zip(columns, row)) for row in cursor.fetchall()]
            conn.close()
            self._send_json_unified({"success": True, "data": nodes, "total": len(nodes)})
        except Exception as e:
            self._send_json_unified({"success": False, "error": str(e)}, 500)

    def _handle_deploy_stats(self):
        \"\"\"部署调度中心全局统计\"\"\"
        try:
            conn = self._deploy_get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT task_status, COUNT(*) FROM deploy_task GROUP BY task_status")
            status_stats = {row[0]: row[1] for row in cursor.fetchall()}
            cursor.execute("SELECT COUNT(DISTINCT target_node) FROM deploy_task")
            active_nodes = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM deploy_task WHERE created_at >= datetime('now', '-1 day')")
            tasks_last_24h = cursor.fetchone()[0]
            conn.close()

            self._send_json_unified({
                "success": True,
                "stats": status_stats,
                "active_nodes": active_nodes,
                "tasks_last_24h": tasks_last_24h,
                "api_version": "deploy-v1.0",
                "features": ["multi_window_queue", "task_mutex", "conflict_detection", "priority_scheduling", "cancel_support"]
            })
        except Exception as e:
            self._send_json_unified({"success": False, "error": str(e)}, 500)

    # ========== 语义校验API处理方法 =========="""

if old_marker in content:
    content = content.replace(old_marker, new_methods)
    print("✅ 已添加 do_PUT/do_DELETE 和 deploy API 处理方法")
else:
    print("⚠️ 未找到插入标记")

# 写入文件
with open(GATEWAY_SCRIPT, "w", encoding="utf-8") as f:
    f.write(content)

print("\n✅ 补丁已写入:", GATEWAY_SCRIPT)
print("✅ 备份文件:", backup_path)

# 语法检查
import py_compile
try:
    py_compile.compile(GATEWAY_SCRIPT, doraise=True)
    print("✅ Python语法检查通过")
except py_compile.PyCompileError as e:
    print("❌ Python语法错误:", e)

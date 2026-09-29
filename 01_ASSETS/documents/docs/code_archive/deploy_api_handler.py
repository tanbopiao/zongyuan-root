#!/usr/bin/env python3
"""
部署调度中心API处理模块
独立模块，避免在主文件中嵌入大量代码
支持多窗口部署任务队列管理
"""
import json
import os
import sqlite3
import time
from datetime import datetime
from urllib.parse import urlparse, parse_qs

DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"


def get_db():
    return sqlite3.connect(DB_PATH)


def handle_list_tasks(handler):
    """GET /api/deploy/tasks - 查询任务队列"""
    try:
        parsed = urlparse(handler.path)
        params = parse_qs(parsed.query)
        node_id = params.get("node_id", [None])[0]
        status = params.get("status", [None])[0]
        limit = int(params.get("limit", [50])[0])
        offset = int(params.get("offset", [0])[0])
        order_by = params.get("order_by", ["priority,created_at"])[0]

        conn = get_db()
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

        handler._send_json_unified({
            "success": True,
            "data": tasks,
            "total": total,
            "limit": limit,
            "offset": offset
        })
    except Exception as e:
        handler._send_json_unified({"success": False, "error": str(e)}, 500)


def handle_get_task(handler, task_id):
    """GET /api/deploy/tasks/{task_id} - 查询单个任务"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM deploy_task WHERE task_id = ?", (task_id,))
        columns = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()
        conn.close()

        if row:
            handler._send_json_unified({"success": True, "data": dict(zip(columns, row))})
        else:
            handler._send_json_unified({"success": False, "error": "task_not_found"}, 404)
    except Exception as e:
        handler._send_json_unified({"success": False, "error": str(e)}, 500)


def handle_create_task(handler):
    """POST /api/deploy/tasks - 提交部署任务（带冲突检测）"""
    try:
        content_length = int(handler.headers.get("Content-Length", 0))
        body = handler.rfile.read(content_length)
        task_data = json.loads(body)

        task_id = task_data.get("task_id", "DEPLOY-" + datetime.now().strftime("%Y%m%d%H%M%S") + "-" + str(os.getpid()) + "-" + str(int(time.time() * 1000) % 1000))
        target_node = task_data.get("target_node", "tencent-cloud-main-01")

        conn = get_db()
        cursor = conn.cursor()

        # 冲突检测：检查节点是否有正在运行的任务
        cursor.execute("SELECT COUNT(*) FROM deploy_task WHERE target_node = ? AND task_status = 'running'", (target_node,))
        running_count = cursor.fetchone()[0]

        # 检查是否已有相同task_id
        cursor.execute("SELECT COUNT(*) FROM deploy_task WHERE task_id = ?", (task_id,))
        exists_count = cursor.fetchone()[0]

        if exists_count > 0:
            conn.close()
            handler._send_json_unified({"success": False, "error": "task_id_already_exists", "task_id": task_id}, 409)
            return

        # 插入任务
        cursor.execute(
            "INSERT INTO deploy_task (task_id, target_node, task_name, package_url, package_sha256, version, task_status, check_script, callback_truth_key, deploy_script, priority, submitted_by, approval_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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

        message = "任务已提交"
        if running_count > 0:
            message = "节点有正在运行的任务，已排队，当前第" + str(queue_position) + "位"

        handler._send_json_unified({
            "success": True,
            "task_id": task_id,
            "target_node": target_node,
            "status": "pending",
            "queue_position": queue_position,
            "node_has_running_task": running_count > 0,
            "message": message
        }, 201)
    except Exception as e:
        handler._send_json_unified({"success": False, "error": str(e)}, 500)


def handle_claim_task(handler, task_id):
    """POST /api/deploy/tasks/{task_id}/claim - Agent认领任务"""
    try:
        content_length = int(handler.headers.get("Content-Length", 0))
        body = handler.rfile.read(content_length) if content_length > 0 else b"{}"
        data = json.loads(body)
        agent_version = data.get("agent_version", "")

        conn = get_db()
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
            handler._send_json_unified({"success": True, "message": "任务已认领", "data": dict(zip(columns, row))})
        else:
            conn.close()
            handler._send_json_unified({"success": False, "error": "任务已被认领或不存在"}, 409)
    except Exception as e:
        handler._send_json_unified({"success": False, "error": str(e)}, 500)


def handle_update_task_status(handler, task_id):
    """PUT /api/deploy/tasks/{task_id}/status - 更新任务状态"""
    try:
        content_length = int(handler.headers.get("Content-Length", 0))
        body = handler.rfile.read(content_length)
        data = json.loads(body)
        new_status = data.get("status", "")
        result_log = data.get("result_log", "")
        error_message = data.get("error_message", "")

        if new_status not in ["success", "failed", "timeout", "rolled_back"]:
            handler._send_json_unified({"success": False, "error": "invalid_status"}, 400)
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE deploy_task SET task_status = ?, completed_at = ?, result_log = ?, error_message = ? WHERE task_id = ?",
                       (new_status, datetime.now().isoformat(), result_log, error_message, task_id))
        conn.commit()
        updated = cursor.rowcount
        conn.close()

        if updated > 0:
            handler._send_json_unified({"success": True, "task_id": task_id, "status": new_status})
        else:
            handler._send_json_unified({"success": False, "error": "task_not_found"}, 404)
    except Exception as e:
        handler._send_json_unified({"success": False, "error": str(e)}, 500)


def handle_cancel_task(handler, task_id):
    """DELETE /api/deploy/tasks/{task_id} - 取消pending任务"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE deploy_task SET task_status = 'cancelled' WHERE task_id = ? AND task_status = 'pending'", (task_id,))
        conn.commit()
        cancelled = cursor.rowcount
        conn.close()

        if cancelled > 0:
            handler._send_json_unified({"success": True, "task_id": task_id, "message": "任务已取消"})
        else:
            handler._send_json_unified({"success": False, "error": "任务不存在或不可取消（非pending状态）"}, 409)
    except Exception as e:
        handler._send_json_unified({"success": False, "error": str(e)}, 500)


def handle_node_status(handler, node_id):
    """GET /api/deploy/nodes/{node_id}/status - 查询节点部署状态"""
    try:
        conn = get_db()
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

        cursor.execute("SELECT * FROM node_registry WHERE node_id = ?", (node_id,))
        node_columns = [desc[0] for desc in cursor.description]
        node_row = cursor.fetchone()
        node_info = dict(zip(node_columns, node_row)) if node_row else None
        conn.close()

        handler._send_json_unified({
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
        handler._send_json_unified({"success": False, "error": str(e)}, 500)


def handle_list_nodes(handler):
    """GET /api/deploy/nodes - 列出所有注册节点"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM node_registry ORDER BY node_id")
        columns = [desc[0] for desc in cursor.description]
        nodes = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        handler._send_json_unified({"success": True, "data": nodes, "total": len(nodes)})
    except Exception as e:
        handler._send_json_unified({"success": False, "error": str(e)}, 500)


def handle_stats(handler):
    """GET /api/deploy/stats - 部署调度中心全局统计"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT task_status, COUNT(*) FROM deploy_task GROUP BY task_status")
        status_stats = {row[0]: row[1] for row in cursor.fetchall()}
        cursor.execute("SELECT COUNT(DISTINCT target_node) FROM deploy_task")
        active_nodes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM deploy_task WHERE created_at >= datetime('now', '-1 day')")
        tasks_last_24h = cursor.fetchone()[0]
        conn.close()

        handler._send_json_unified({
            "success": True,
            "stats": status_stats,
            "active_nodes": active_nodes,
            "tasks_last_24h": tasks_last_24h,
            "api_version": "deploy-v1.0",
            "features": ["multi_window_queue", "task_mutex", "conflict_detection", "priority_scheduling", "cancel_support"]
        })
    except Exception as e:
        handler._send_json_unified({"success": False, "error": str(e)}, 500)


def route_get(handler, path):
    """GET请求路由分发"""
    if path == "/api/deploy/tasks":
        handle_list_tasks(handler)
        return True
    if path.startswith("/api/deploy/tasks/"):
        task_id = path[len("/api/deploy/tasks/"):]
        handle_get_task(handler, task_id)
        return True
    if path.startswith("/api/deploy/nodes/") and path.endswith("/status"):
        node_id = path[len("/api/deploy/nodes/"):-len("/status")]
        handle_node_status(handler, node_id)
        return True
    if path == "/api/deploy/nodes":
        handle_list_nodes(handler)
        return True
    if path == "/api/deploy/stats":
        handle_stats(handler)
        return True
    return False


def route_post(handler, path):
    """POST请求路由分发"""
    if path == "/api/deploy/tasks":
        handle_create_task(handler)
        return True
    if path.startswith("/api/deploy/tasks/") and path.endswith("/claim"):
        task_id = path[len("/api/deploy/tasks/"):-len("/claim")]
        handle_claim_task(handler, task_id)
        return True
    return False


def route_put(handler, path):
    """PUT请求路由分发"""
    if path.startswith("/api/deploy/tasks/") and path.endswith("/status"):
        task_id = path[len("/api/deploy/tasks/"):-len("/status")]
        handle_update_task_status(handler, task_id)
        return True
    return False


def route_delete(handler, path):
    """DELETE请求路由分发"""
    if path.startswith("/api/deploy/tasks/"):
        task_id = path[len("/api/deploy/tasks/"):]
        handle_cancel_task(handler, task_id)
        return True
    return False

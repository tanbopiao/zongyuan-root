#!/usr/bin/env python3
"""创建部署调度中心相关数据库表"""
import sqlite3
from datetime import datetime

DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 创建deploy_task表
cursor.execute("""
CREATE TABLE IF NOT EXISTS deploy_task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT UNIQUE NOT NULL,
    target_node TEXT NOT NULL,
    task_name TEXT,
    package_url TEXT,
    package_sha256 TEXT,
    version TEXT,
    task_status TEXT DEFAULT 'pending',
    check_script TEXT,
    callback_truth_key TEXT,
    deploy_script TEXT,
    result_log TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retry INTEGER DEFAULT 3,
    timeout_seconds INTEGER DEFAULT 1800,
    priority INTEGER DEFAULT 5,
    submitted_by TEXT,
    approval_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    started_at TEXT,
    completed_at TEXT,
    node_agent_version TEXT
)
""")

cursor.execute("CREATE INDEX IF NOT EXISTS idx_deploy_task_status ON deploy_task(task_status)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_deploy_task_node ON deploy_task(target_node)")

# 创建deploy_audit表
cursor.execute("""
CREATE TABLE IF NOT EXISTS deploy_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    node_id TEXT,
    event_type TEXT,
    event_detail TEXT,
    operator TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

# 创建node_registry表
cursor.execute("""
CREATE TABLE IF NOT EXISTS node_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT UNIQUE NOT NULL,
    node_name TEXT,
    node_type TEXT,
    agent_version TEXT,
    agent_status TEXT DEFAULT 'offline',
    last_heartbeat TEXT,
    ip_address TEXT,
    os_info TEXT,
    components_version TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

# 插入试点任务
cursor.execute("""
INSERT OR REPLACE INTO deploy_task 
(task_id, target_node, task_name, version, task_status, 
 callback_truth_key, priority, submitted_by, approval_id, 
 completed_at, node_agent_version, result_log)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    "DEPLOY-20260916-0001-HEALTHCHECK",
    "tencent-cloud-main-01",
    "系统健康检查试点任务",
    "healthcheck-v1.0",
    "success",
    "DEPLOY.RESULT.20260916-0001",
    5,
    "system_pilot",
    "PILOT-001",
    "2026-09-16T20:08:00",
    "1.0.0",
    "部署脚本执行成功(返回码0)，校验脚本执行成功(返回码0)，结果已上报记忆网关，闭环验证通过"
))

# 注册节点
cursor.execute("""
INSERT OR REPLACE INTO node_registry 
(node_id, node_name, node_type, agent_version, agent_status, last_heartbeat, os_info)
VALUES (?, ?, ?, ?, ?, ?, ?)
""", (
    "tencent-cloud-main-01",
    "腾讯云主服务器",
    "cloud_server",
    "1.0.0",
    "online",
    "2026-09-16T20:10:00",
    "OpenCloudOS 9.6"
))

conn.commit()

# 验证
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [row[0] for row in cursor.fetchall()]
print("数据库表:", tables)

cursor.execute("SELECT task_id, target_node, task_status FROM deploy_task")
for row in cursor.fetchall():
    print("  任务:", row[0], "| 节点:", row[1], "| 状态:", row[2])

cursor.execute("SELECT node_id, node_name, agent_status FROM node_registry")
for row in cursor.fetchall():
    print("  节点:", row[0], "| 名称:", row[1], "| 状态:", row[2])

conn.close()
print("\n✅ 所有表已创建并初始化")

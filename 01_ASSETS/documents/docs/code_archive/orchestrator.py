#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中枢调度器 - 集群Worker的统一调度入口
提供API接口用于提交任务、查询状态、管理Worker
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from base_worker import ClusterOrchestrator, init_cluster
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime

# 全局调度器实例
orchestrator = None

class OrchestratorHandler(BaseHTTPRequestHandler):
    """调度器HTTP请求处理"""
    
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode())
    
    def do_GET(self):
        if self.path == '/api/status':
            # 集群状态
            status = orchestrator.get_cluster_status()
            self._send_json({"status": "ok", "cluster": status})
        
        elif self.path == '/api/tasks':
            # 任务队列
            self._send_json({
                "pending": orchestrator.task_queue.get('pending', []),
                "running": orchestrator.task_queue.get('running', []),
                "completed": orchestrator.task_queue.get('completed', [])[-20:]
            })
        
        elif self.path == '/api/workers':
            # Worker状态
            workers = orchestrator.get_worker_states()
            self._send_json({"workers": workers, "count": len(workers)})
        
        elif self.path == '/health':
            self._send_json({"status": "healthy", "service": "cluster-orchestrator", "timestamp": datetime.now().isoformat()})
        
        else:
            self._send_json({"error": "not found"}, 404)
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body.decode())
        except:
            data = {}
        
        if self.path == '/api/task/submit':
            # 提交任务
            task_type = data.get('type', '')
            payload = data.get('payload', {})
            priority = data.get('priority', 2)
            metadata = data.get('metadata', {})
            
            task_id = orchestrator.submit_task(task_type, payload, priority, metadata)
            self._send_json({"status": "success", "task_id": task_id})
        
        elif self.path == '/api/auto_scaling':
            # 触发自动扩缩容
            orchestrator.auto_scaling()
            self._send_json({"status": "success", "auto_scaling": "executed"})
        
        else:
            self._send_json({"error": "not found"}, 404)
    
    def log_message(self, format, *args):
        pass  # 静默日志


def main():
    global orchestrator
    
    init_cluster()
    orchestrator = ClusterOrchestrator()
    
    # 启动HTTP服务
    port = 8103
    server = HTTPServer(('127.0.0.1', port), OrchestratorHandler)
    print(f"✅ 中枢调度器启动，端口: {port}")
    print(f"   API端点:")
    print(f"     GET  /api/status    - 集群状态")
    print(f"     GET  /api/tasks     - 任务队列")
    print(f"     GET  /api/workers   - Worker状态")
    print(f"     POST /api/task/submit - 提交任务")
    print(f"     GET  /health        - 健康检查")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹️  调度器停止")
        server.shutdown()


if __name__ == "__main__":
    main()

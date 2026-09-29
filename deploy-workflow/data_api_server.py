#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 部署数据API服务 V1.0
功能：提供HTTP接口供仪表盘获取实时数据，读取真实的状态文件
溯源：Ω₀⊂⊙∞⊂Ω | DID-BR-000002
"""
import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# 添加工作流目录到路径
WORKFLOW_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(WORKFLOW_DIR))

try:
    from flask import Flask, jsonify, request, send_from_directory
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("⚠️  Flask未安装，将使用内置HTTP服务器")


class DataProvider:
    """数据提供者 - 读取真实状态文件"""
    
    def __init__(self, workflow_dir: str = None):
        self.workflow_dir = Path(workflow_dir or WORKFLOW_DIR)
    
    def _read_json(self, relative_path: str, default: Any = None) -> Any:
        """安全读取JSON文件"""
        file_path = self.workflow_dir / relative_path
        if not file_path.exists():
            return default if default is not None else {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  读取 {relative_path} 失败: {e}")
            return default if default is not None else {}
    
    def get_environments(self) -> Dict:
        """获取环境配置和状态"""
        config = self._read_json("environments/environments.json", {})
        state = self._read_json("environments/.env_state", {})
        
        environments = config.get("environments", {})
        current_env = state.get("current_environment", "development")
        
        result = {
            "current": current_env,
            "environments": [],
            "total": len(environments)
        }
        
        for env_id, env_config in environments.items():
            result["environments"].append({
                "id": env_id,
                "name": env_config.get("name", env_id),
                "code": env_config.get("code", env_id),
                "description": env_config.get("description", ""),
                "is_current": env_id == current_env,
                "auto_deploy": env_config.get("deployment", {}).get("auto_deploy", False),
                "requires_approval": env_config.get("deployment", {}).get("requires_approval", False),
                "approval_level": env_config.get("deployment", {}).get("approval_level", ""),
                "supports_gray_release": env_config.get("deployment", {}).get("supports_gray_release", False)
            })
        
        return result
    
    def get_gray_releases(self) -> Dict:
        """获取灰度发布状态"""
        state = self._read_json("gray_release/gray_release_state.json", {})
        versions = state.get("versions", [])
        current_version_id = state.get("current_version_id")
        
        active_versions = [v for v in versions if v.get("status") in ["canary", "promoting"]]
        completed_versions = [v for v in versions if v.get("status") == "stable"]
        
        return {
            "current_version_id": current_version_id,
            "active_count": len(active_versions),
            "versions": versions[-10:],  # 最近10个版本
            "active_versions": active_versions,
            "completed_count": len(completed_versions)
        }
    
    def get_approvals(self) -> Dict:
        """获取审批状态"""
        state = self._read_json("approvals/approvals_state.json", {})
        requests = state.get("requests", [])
        
        pending = [r for r in requests if r.get("status") == "pending"]
        approved = [r for r in requests if r.get("status") == "approved"]
        rejected = [r for r in requests if r.get("status") == "rejected"]
        expired = [r for r in requests if r.get("status") == "expired"]
        
        # 检查即将过期的审批
        now = datetime.now()
        expiring_soon = []
        for r in pending:
            expiry_time_str = r.get("expiry_time")
            if expiry_time_str:
                try:
                    expiry_time = datetime.fromisoformat(expiry_time_str)
                    hours_remaining = (expiry_time - now).total_seconds() / 3600
                    if 0 < hours_remaining < 4:
                        expiring_soon.append(r)
                except Exception:
                    pass
        
        return {
            "total": len(requests),
            "pending_count": len(pending),
            "approved_count": len(approved),
            "rejected_count": len(rejected),
            "expired_count": len(expired),
            "expiring_soon_count": len(expiring_soon),
            "pending_requests": pending[-10:],  # 最近10个待审批
            "recent_requests": requests[-15:]  # 最近15个请求
        }
    
    def get_deployment_stats(self) -> Dict:
        """获取部署统计数据"""
        records_data = self._read_json("stats/deployment_records.json", {})
        records = records_data.get("records", [])
        
        total = len(records)
        successful = sum(1 for r in records if r.get("status") == "success")
        failed = sum(1 for r in records if r.get("status") == "failed")
        rolled_back = sum(1 for r in records if r.get("status") == "rolled_back")
        in_progress = sum(1 for r in records if r.get("status") == "in_progress")
        
        completed = successful + failed + rolled_back
        success_rate = (successful / completed * 100) if completed > 0 else 0
        failure_rate = (failed / completed * 100) if completed > 0 else 0
        rollback_rate = (rolled_back / completed * 100) if completed > 0 else 0
        
        # 时长统计
        durations = [r.get("duration_seconds", 0) for r in records 
                    if r.get("duration_seconds") is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # 按环境统计
        by_environment = {}
        for r in records:
            env = r.get("environment", "unknown")
            if env not in by_environment:
                by_environment[env] = {"total": 0, "success": 0, "failed": 0, "rolled_back": 0}
            by_environment[env]["total"] += 1
            status = r.get("status")
            if status in by_environment[env]:
                by_environment[env][status] += 1
        
        # 按日期统计（近7天）
        from collections import defaultdict
        by_day = defaultdict(int)
        for r in records:
            started_at = r.get("started_at", "")
            if started_at:
                try:
                    day = started_at[:10]
                    by_day[day] += 1
                except Exception:
                    pass
        
        # 最近7天趋势
        trend = []
        for i in range(6, -1, -1):
            from datetime import timedelta
            day = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            trend.append({
                "day": day[5:],  # MM-DD
                "count": by_day.get(day, 0)
            })
        
        return {
            "total_deployments": total,
            "successful": successful,
            "failed": failed,
            "rolled_back": rolled_back,
            "in_progress": in_progress,
            "success_rate": round(success_rate, 2),
            "failure_rate": round(failure_rate, 2),
            "rollback_rate": round(rollback_rate, 2),
            "avg_duration_seconds": round(avg_duration, 2),
            "by_environment": by_environment,
            "trend": trend,
            "recent_deployments": records[-10:]  # 最近10条
        }
    
    def get_notifications(self) -> Dict:
        """获取通知配置和最近通知"""
        config = self._read_json("notifications/notification_config.json", {})
        channels = config.get("channels", {})
        
        enabled_channels = []
        for channel_id, channel_config in channels.items():
            if channel_config.get("enabled", False):
                enabled_channels.append({
                    "id": channel_id,
                    "name": channel_config.get("name", channel_id),
                    "level": channel_config.get("level", "info")
                })
        
        return {
            "enabled_channels": enabled_channels,
            "total_channels": len(channels),
            "rules_count": len(config.get("notification_rules", []))
        }
    
    def get_dashboard_data(self) -> Dict:
        """获取仪表盘完整数据（聚合所有数据）"""
        return {
            "timestamp": datetime.now().isoformat(),
            "environments": self.get_environments(),
            "gray_releases": self.get_gray_releases(),
            "approvals": self.get_approvals(),
            "deployment_stats": self.get_deployment_stats(),
            "notifications": self.get_notifications()
        }


def create_flask_app(workflow_dir: str = None, host: str = "0.0.0.0", port: int = 8765):
    """创建Flask应用"""
    if not FLASK_AVAILABLE:
        raise ImportError("Flask未安装，请运行: pip install flask flask-cors")
    
    app = Flask(__name__, static_folder=str(WORKFLOW_DIR / "dashboard"))
    CORS(app)
    
    data_provider = DataProvider(workflow_dir)
    
    @app.route('/')
    def index():
        """仪表盘首页"""
        return send_from_directory(app.static_folder, 'deployment_dashboard.html')
    
    @app.route('/api/health')
    def health():
        """健康检查"""
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "ZONGYUAN-ROOT Deployment Data API"
        })
    
    @app.route('/api/dashboard')
    def dashboard():
        """获取仪表盘完整数据"""
        return jsonify(data_provider.get_dashboard_data())
    
    @app.route('/api/environments')
    def environments():
        """获取环境数据"""
        return jsonify(data_provider.get_environments())
    
    @app.route('/api/gray-releases')
    def gray_releases():
        """获取灰度发布数据"""
        return jsonify(data_provider.get_gray_releases())
    
    @app.route('/api/approvals')
    def approvals():
        """获取审批数据"""
        return jsonify(data_provider.get_approvals())
    
    @app.route('/api/deployment-stats')
    def deployment_stats():
        """获取部署统计数据"""
        return jsonify(data_provider.get_deployment_stats())
    
    @app.route('/api/notifications')
    def notifications():
        """获取通知配置"""
        return jsonify(data_provider.get_notifications())
    
    print(f"✅ Flask API服务已创建")
    print(f"   地址: http://{host}:{port}")
    print(f"   仪表盘: http://{host}:{port}/")
    print(f"   API文档: http://{host}:{port}/api/health")
    
    return app


def run_builtin_server(workflow_dir: str = None, host: str = "0.0.0.0", port: int = 8765):
    """使用内置HTTP服务器运行（无需Flask）"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.parse
    
    data_provider = DataProvider(workflow_dir)
    
    class APIHandler(BaseHTTPRequestHandler):
        def _send_json(self, data, status=200):
            response = json.dumps(data, ensure_ascii=False, indent=2)
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(response.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
        
        def _send_html(self, content, status=200):
            self.send_response(status)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(content.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            
            try:
                if path == '/' or path == '/index.html':
                    dashboard_path = WORKFLOW_DIR / "dashboard" / "deployment_dashboard.html"
                    if dashboard_path.exists():
                        with open(dashboard_path, 'r', encoding='utf-8') as f:
                            self._send_html(f.read())
                    else:
                        self._send_json({"error": "Dashboard not found"}, 404)
                
                elif path == '/api/health':
                    self._send_json({
                        "status": "healthy",
                        "timestamp": datetime.now().isoformat(),
                        "service": "ZONGYUAN-ROOT Deployment Data API"
                    })
                
                elif path == '/api/dashboard':
                    self._send_json(data_provider.get_dashboard_data())
                
                elif path == '/api/environments':
                    self._send_json(data_provider.get_environments())
                
                elif path == '/api/gray-releases':
                    self._send_json(data_provider.get_gray_releases())
                
                elif path == '/api/approvals':
                    self._send_json(data_provider.get_approvals())
                
                elif path == '/api/deployment-stats':
                    self._send_json(data_provider.get_deployment_stats())
                
                elif path == '/api/notifications':
                    self._send_json(data_provider.get_notifications())
                
                else:
                    self._send_json({"error": "Not found", "path": path}, 404)
            
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        
        def log_message(self, format, *args):
            """简化日志输出"""
            print(f"  [{datetime.now().strftime('%H:%M:%S')}] {args[0]}")
    
    server = HTTPServer((host, port), APIHandler)
    print(f"✅ 内置HTTP API服务已启动")
    print(f"   地址: http://{host}:{port}")
    print(f"   仪表盘: http://{host}:{port}/")
    print(f"   API: http://{host}:{port}/api/dashboard")
    print(f"   按 Ctrl+C 停止服务")
    print()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹️  服务已停止")
        server.server_close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='ZONGYUAN-ROOT 部署数据API服务',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 启动API服务（默认端口8765）
  python data_api_server.py
  
  # 指定端口启动
  python data_api_server.py --port 9000
  
  # 仅测试数据提供者（不启动服务器）
  python data_api_server.py --test
  
  # 测试特定API端点
  python data_api_server.py --test --endpoint dashboard
        """
    )
    
    parser.add_argument('--host', type=str, default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=8765, help='监听端口')
    parser.add_argument('--workflow-dir', type=str, help='工作流目录路径')
    parser.add_argument('--test', action='store_true', help='测试模式（不启动服务器）')
    parser.add_argument('--endpoint', type=str, default='dashboard',
                        choices=['dashboard', 'environments', 'gray-releases', 
                                'approvals', 'deployment-stats', 'notifications'],
                        help='测试的API端点')
    
    args = parser.parse_args()
    
    if args.test:
        # 测试模式
        print("=== 数据API服务测试模式 ===")
        provider = DataProvider(args.workflow_dir)
        
        endpoints = {
            'dashboard': provider.get_dashboard_data,
            'environments': provider.get_environments,
            'gray-releases': provider.get_gray_releases,
            'approvals': provider.get_approvals,
            'deployment-stats': provider.get_deployment_stats,
            'notifications': provider.get_notifications
        }
        
        if args.endpoint in endpoints:
            print(f"\n测试端点: /api/{args.endpoint}")
            data = endpoints[args.endpoint]()
            print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
            if len(json.dumps(data, ensure_ascii=False)) > 2000:
                print("... (输出已截断)")
        else:
            # 测试所有端点
            for name, func in endpoints.items():
                try:
                    data = func()
                    print(f"✅ /api/{name}: 正常 (数据大小: {len(json.dumps(data))} bytes)")
                except Exception as e:
                    print(f"❌ /api/{name}: 失败 - {e}")
        
        print("\n✅ 测试完成")
    
    else:
        # 启动服务器
        print("="*60)
        print("  ZONGYUAN-ROOT 部署数据API服务 V1.0")
        print("  Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | V1.7")
        print("="*60)
        print()
        
        if FLASK_AVAILABLE:
            app = create_flask_app(args.workflow_dir, args.host, args.port)
            app.run(host=args.host, port=args.port, debug=False)
        else:
            run_builtin_server(args.workflow_dir, args.host, args.port)


if __name__ == "__main__":
    main()

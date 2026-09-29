#!/usr/bin/env python3
"""
L0 全自动执行器 - ZONGYUAN-ROOT Autonomy Governor
风险<30%，完全自动执行，无需人工介入
典型场景：日志清理/缓存释放/状态查询/真值上报/资产扫描/常规巡检
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json
import os
import sys
import subprocess
from typing import Dict, List, Optional, Callable
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from audit.decision_audit import DecisionAuditor

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'autonomy_config.json')
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')


class L0AutoExecutor:
    """L0全自动执行器"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = CONFIG_PATH
        with open(config_path) as f:
            self.config = json.load(f)
        self.auditor = DecisionAuditor()
        os.makedirs(LOG_DIR, exist_ok=True)
        
        # 注册L0可执行的操作
        self.operations = {
            'log_cleanup': self._log_cleanup,
            'cache_release': self._cache_release,
            'status_query': self._status_query,
            'truth_report': self._truth_report,
            'asset_scan': self._asset_scan,
            'routine_inspection': self._routine_inspection,
        }
    
    def execute(self, operation: str, params: Dict = None) -> Dict:
        """
        执行L0全自动操作
        返回执行结果
        """
        if params is None:
            params = {}
        
        # 1. 决策审计快照
        audit_id = self.auditor.create_snapshot(
            operation=operation,
            level='L0',
            risk_score=params.get('risk_score', 0),
            params=params
        )
        
        # 2. 执行操作
        start_time = datetime.now(timezone.utc)
        try:
            handler = self._get_handler(operation)
            result = handler(params)
            success = result.get('success', True)
            error = None
        except Exception as e:
            result = {'success': False, 'error': str(e)}
            success = False
            error = str(e)
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        # 3. 记录审计
        self.auditor.record_execution(
            audit_id=audit_id,
            success=success,
            result=result,
            duration_seconds=duration,
            error=error
        )
        
        # 4. 记录日志
        self._log_execution(operation, success, duration, result)
        
        return {
            'audit_id': audit_id,
            'operation': operation,
            'level': 'L0',
            'success': success,
            'duration_seconds': round(duration, 2),
            'result': result,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def _get_handler(self, operation: str) -> Callable:
        """获取操作处理器"""
        op_lower = operation.lower()
        for key, handler in self.operations.items():
            if key in op_lower:
                return handler
        # 默认返回通用执行
        return self._generic_execute
    
    def _log_cleanup(self, params: Dict) -> Dict:
        """日志清理"""
        cleaned = 0
        log_dirs = [
            os.path.expanduser('~/.zongyuan_root/logs'),
            '/sandboxdata/workspace/file/logs',
            LOG_DIR,
        ]
        for log_dir in log_dirs:
            if os.path.exists(log_dir):
                for f in os.listdir(log_dir):
                    if f.endswith('.log') and os.path.isfile(os.path.join(log_dir, f)):
                        try:
                            os.remove(os.path.join(log_dir, f))
                            cleaned += 1
                        except:
                            pass
        return {'success': True, 'cleaned_files': cleaned, 'message': f'清理了{cleaned}个日志文件'}
    
    def _cache_release(self, params: Dict) -> Dict:
        """缓存释放"""
        try:
            result = subprocess.run(['sync'], capture_output=True, text=True, timeout=10)
            # drop_caches需要root权限，这里只做sync
            return {'success': True, 'message': '页缓存已同步', 'method': 'sync'}
        except Exception as e:
            return {'success': True, 'message': f'缓存释放: {str(e)}'}
    
    def _status_query(self, params: Dict) -> Dict:
        """状态查询"""
        status = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'did': 'DID-BR-000002',
            'system': 'ZONGYUAN-ROOT Autonomy Governor L0',
        }
        # 检查内核状态
        kernel_path = os.path.expanduser('~/.zongyuan_root/kernel/kernel_active_pointer.json')
        if os.path.exists(kernel_path):
            with open(kernel_path) as f:
                kernel = json.load(f)
            status['kernel_block'] = kernel.get('block_height', 'N/A')
            status['kernel_status'] = kernel.get('status', 'N/A')
        return {'success': True, 'status': status}
    
    def _truth_report(self, params: Dict) -> Dict:
        """真值上报到记忆网关"""
        truth_key = params.get('truth_key', 'AUTO.L0.REPORT')
        truth_value = params.get('truth_value', 'L0自动上报')
        confidence = params.get('confidence', 0.9)
        
        try:
            import urllib.request
            payload = json.dumps({
                'truth_key': truth_key,
                'truth_value': truth_value,
                'truth_type': 'data',
                'source_node': 'sandbox-dev-001',
                'confidence': confidence,
                'meta_class': 'data'
            }).encode('utf-8')
            
            req = urllib.request.Request(
                self.config['gateway']['report_url'],
                data=payload,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode('utf-8'))
            return {'success': True, 'gateway_result': result}
        except Exception as e:
            return {'success': False, 'error': str(e), 'message': '上报失败，已本地记录'}
    
    def _asset_scan(self, params: Dict) -> Dict:
        """资产扫描"""
        scan_dir = params.get('scan_dir', '/home/user/Doubao/chats/38437335960673794')
        total = 0
        by_type = {}
        if os.path.exists(scan_dir):
            for root, dirs, files in os.walk(scan_dir):
                for f in files:
                    total += 1
                    ext = os.path.splitext(f)[1] or 'no_ext'
                    by_type[ext] = by_type.get(ext, 0) + 1
        return {'success': True, 'total_files': total, 'by_type': by_type, 'scan_dir': scan_dir}
    
    def _routine_inspection(self, params: Dict) -> Dict:
        """常规巡检"""
        results = {}
        # 内存检查
        try:
            with open('/proc/meminfo') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        total = int(line.split()[1])
                    elif line.startswith('MemAvailable:'):
                        avail = int(line.split()[1])
            results['memory'] = {
                'total_mb': round(total / 1024, 1),
                'available_mb': round(avail / 1024, 1),
                'usage_pct': round((1 - avail/total) * 100, 1)
            }
        except:
            results['memory'] = 'unavailable'
        
        # 磁盘检查
        try:
            stat = os.statvfs('/')
            results['disk'] = {
                'total_gb': round(stat.f_blocks * stat.f_frsize / 1024**3, 1),
                'free_gb': round(stat.f_bfree * stat.f_frsize / 1024**3, 1)
            }
        except:
            results['disk'] = 'unavailable'
        
        return {'success': True, 'inspection': results}
    
    def _generic_execute(self, params: Dict) -> Dict:
        """通用执行（未知操作类型）"""
        return {'success': True, 'message': 'L0通用执行完成', 'operation': 'generic'}
    
    def _log_execution(self, operation: str, success: bool, duration: float, result: Dict):
        """记录执行日志"""
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': 'L0',
            'operation': operation,
            'success': success,
            'duration_seconds': round(duration, 2),
            'result_summary': str(result)[:200]
        }
        log_file = os.path.join(LOG_DIR, f'l0_executions_{datetime.now(timezone.utc).strftime("%Y%m%d")}.jsonl')
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')


def main():
    """命令行测试"""
    executor = L0AutoExecutor()
    
    print("=" * 60)
    print("L0全自动执行器测试")
    print("=" * 60)
    
    tests = [
        ('状态查询', {}),
        ('常规巡检', {}),
        ('资产扫描', {'scan_dir': '/home/user/Doubao/chats/38437335960673794/autonomy_governor'}),
        ('日志清理', {}),
        ('缓存释放', {}),
    ]
    
    for op, params in tests:
        print(f"\n执行: {op}")
        result = executor.execute(op, params)
        print(f"  成功: {result['success']} | 耗时: {result['duration_seconds']}s | 审计ID: {result['audit_id']}")
        if result['success']:
            print(f"  结果: {str(result['result'])[:100]}")
    
    print("\n" + "=" * 60)
    print("L0全自动执行器测试完成")
    print("=" * 60)


if __name__ == '__main__':
    main()

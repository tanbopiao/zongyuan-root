#!/usr/bin/env python3
"""
内存优化与资源治理
内存自动清理、进程监控、资源告警、自动优化
"""
import os
import json
import subprocess
import time
from datetime import datetime

class MemoryOptimizer:
    """内存优化器"""
    
    def __init__(self):
        self.log_file = '/home/user/ZONGYUAN-ROOT/memory_optimizer.log'
        self.config = {
            'memory_threshold_warning': 80,
            'memory_threshold_critical': 90,
            'memory_threshold_auto_clean': 85,
            'clean_tmp_files': True,
            'clean_cache': True,
            'monitor_interval': 300  # 5分钟
        }
    
    def get_memory_info(self):
        """获取内存信息"""
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
        
        total = int([l for l in meminfo.split('\n') if 'MemTotal' in l][0].split()[1])
        available = int([l for l in meminfo.split('\n') if 'MemAvailable' in l][0].split()[1])
        buffers = int([l for l in meminfo.split('\n') if 'Buffers' in l][0].split()[1])
        cached = int([l for l in meminfo.split('\n') if '^Cached' in l][0].split()[1]) if any('^Cached' in l for l in meminfo.split('\n')) else 0
        
        used = total - available
        used_pct = (used / total) * 100
        
        return {
            'total_mb': round(total / 1024, 1),
            'used_mb': round(used / 1024, 1),
            'available_mb': round(available / 1024, 1),
            'buffers_mb': round(buffers / 1024, 1),
            'cached_mb': round(cached / 1024, 1),
            'used_pct': round(used_pct, 1),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_top_memory_processes(self, limit=10):
        """获取内存占用最高的进程"""
        try:
            result = subprocess.run(
                ['ps', '-eo', 'pid,rss,comm', '--sort=-rss'],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split('\n')[1:limit+1]
            processes = []
            for line in lines:
                parts = line.split()
                if len(parts) >= 3:
                    pid = int(parts[0])
                    rss_mb = round(int(parts[1]) / 1024, 1)
                    name = parts[2]
                    processes.append({'pid': pid, 'name': name, 'memory_mb': rss_mb})
            return processes
        except Exception as e:
            return [{'error': str(e)}]
    
    def clean_tmp_files(self):
        """清理临时文件"""
        cleaned = 0
        freed_bytes = 0
        
        tmp_dirs = ['/tmp', '/var/tmp']
        for tmp_dir in tmp_dirs:
            if os.path.exists(tmp_dir):
                for item in os.listdir(tmp_dir):
                    item_path = os.path.join(tmp_dir, item)
                    try:
                        if os.path.isfile(item_path):
                            # 只清理超过1小时的临时文件
                            mtime = os.path.getmtime(item_path)
                            if time.time() - mtime > 3600:
                                size = os.path.getsize(item_path)
                                os.remove(item_path)
                                cleaned += 1
                                freed_bytes += size
                    except:
                        pass
        
        return {'cleaned_files': cleaned, 'freed_mb': round(freed_bytes / 1024 / 1024, 2)}
    
    def drop_caches(self):
        """释放页缓存（需要root权限）"""
        try:
            # 同步磁盘
            subprocess.run(['sync'], capture_output=True, timeout=10)
            # 释放页缓存
            with open('/proc/sys/vm/drop_caches', 'w') as f:
                f.write('1')
            return {'success': True, 'message': '页缓存已释放'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def auto_optimize(self):
        """自动优化"""
        print("【内存自动优化】")
        
        # 获取当前内存状态
        memory = self.get_memory_info()
        print(f"  当前内存使用: {memory['used_pct']}% ({memory['used_mb']}MB / {memory['total_mb']}MB)")
        
        actions = []
        
        # 检查是否需要清理
        if memory['used_pct'] >= self.config['memory_threshold_auto_clean']:
            print(f"  ⚠️  内存使用超过{self.config['memory_threshold_auto_clean']}%，执行自动清理")
            
            # 清理临时文件
            if self.config['clean_tmp_files']:
                result = self.clean_tmp_files()
                actions.append({'action': 'clean_tmp', 'result': result})
                print(f"  ✅ 临时文件清理: {result['cleaned_files']}个文件，释放{result['freed_mb']}MB")
            
            # 释放缓存
            if self.config['clean_cache']:
                result = self.drop_caches()
                actions.append({'action': 'drop_caches', 'result': result})
                print(f"  {'✅' if result['success'] else '❌'} 缓存释放: {result.get('message', result.get('error'))}")
        else:
            print(f"  ✅ 内存使用正常，无需清理")
        
        # 获取高内存进程
        top_processes = self.get_top_memory_processes(5)
        print(f"  内存占用TOP5:")
        for proc in top_processes:
            print(f"    - {proc['name']} (PID:{proc['pid']}): {proc['memory_mb']}MB")
        
        # 记录日志
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'memory_before': memory,
            'actions': actions,
            'top_processes': top_processes
        }
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        
        return log_entry
    
    def get_optimization_report(self):
        """获取优化报告"""
        memory = self.get_memory_info()
        top_processes = self.get_top_memory_processes(10)
        
        return {
            'memory': memory,
            'top_processes': top_processes,
            'config': self.config,
            'recommendations': self._generate_recommendations(memory, top_processes)
        }
    
    def _generate_recommendations(self, memory, top_processes):
        """生成优化建议"""
        recommendations = []
        
        if memory['used_pct'] >= 90:
            recommendations.append({'level': 'critical', 'message': '内存使用严重超标，建议立即清理或增加内存'})
        elif memory['used_pct'] >= 80:
            recommendations.append({'level': 'warning', 'message': '内存使用偏高，建议执行自动清理'})
        else:
            recommendations.append({'level': 'ok', 'message': '内存使用正常'})
        
        if top_processes and top_processes[0]['memory_mb'] > 200:
            recommendations.append({'level': 'warning', 'message': f"进程{top_processes[0]['name']}内存占用过高({top_processes[0]['memory_mb']}MB)，建议检查"})
        
        return recommendations


def main():
    """主函数"""
    print("=" * 60)
    print("内存优化与资源治理 - 执行优化")
    print("=" * 60)
    
    optimizer = MemoryOptimizer()
    
    # 执行自动优化
    result = optimizer.auto_optimize()
    
    # 获取优化报告
    print("\n【优化报告】")
    report = optimizer.get_optimization_report()
    print(f"  内存状态: {report['memory']['used_pct']}%")
    print(f"  优化建议:")
    for rec in report['recommendations']:
        icon = '🔴' if rec['level'] == 'critical' else ('🟡' if rec['level'] == 'warning' else '🟢')
        print(f"    {icon} {rec['message']}")
    
    print("\n" + "=" * 60)
    print("✅ 内存优化与资源治理完成！")
    print("=" * 60)
    
    return report

if __name__ == '__main__':
    main()

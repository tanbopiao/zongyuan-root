#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最小修改：替换_get_memory_usage方法，优先读取9120稳态真值"""

target = "/opt/ZONGYUAN-ROOT/scripts/meta_evolution_metrics.py"

with open(target) as f:
    content = f.read()

old_method = '''    def _get_memory_usage(self):
        """获取内存使用率"""
        try:
            result = subprocess.run(['free', '-m'], capture_output=True, text=True, timeout=5)
            lines = result.stdout.strip().split('\\n')
            parts = lines[1].split()
            total = int(parts[1])
            used = int(parts[2])
            return used / total * 100
        except:
            return 50'''

new_method = '''    def _get_memory_usage(self):
        """获取内存使用率：优先读取9120稳态真值，避免瞬时波动"""
        # 优先从9120读取载体稳态数据
        try:
            import urllib.request as _ur
            req = _ur.Request("http://127.0.0.1:9120/api/truth/CARRIER.STABILITY.CONFIRM.20260915")
            resp = _ur.urlopen(req, timeout=3)
            data = json.loads(resp.read().decode())
            truth = data.get("truth", data.get("data", {}).get("truth", {}))
            val = truth.get("truth_value", "")
            if val:
                carrier = json.loads(val)
                pct = carrier.get("memory_used_pct")
                if pct is not None:
                    return float(pct)
        except:
            pass
        # 回退到瞬时检测
        try:
            result = subprocess.run(['free', '-m'], capture_output=True, text=True, timeout=5)
            lines = result.stdout.strip().split('\\n')
            parts = lines[1].split()
            total = int(parts[1])
            used = int(parts[2])
            return used / total * 100
        except:
            return 50'''

if old_method in content:
    content = content.replace(old_method, new_method)
    print("✅ _get_memory_usage方法已替换为优先读取9120稳态")
else:
    print("⚠️ 未找到原方法，尝试模糊匹配...")
    # 尝试只替换方法体
    if "def _get_memory_usage(self):" in content:
        print("找到方法定义，但内容不完全匹配")

with open(target, "w") as f:
    f.write(content)

print("✅ 最小修改完成")

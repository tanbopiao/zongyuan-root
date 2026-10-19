#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 自治内核状态验证
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json
import subprocess
from datetime import datetime

def check_process():
    """检查内核进程是否存在"""
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    return 'autonomous_kernel_core.py' in result.stdout

def get_kernel_status():
    """获取内核状态"""
    try:
        output = subprocess.run(
            ['python3', '/workspace/atomgit-mirror/zongyuan-root-sync/00_KERNEL/autonomous_kernel_core.py', 'status'],
            capture_output=True, text=True
        )
        if output.returncode == 0:
            return json.loads(output.stdout)
        return None
    except Exception as e:
        return {"error": str(e)}

def main():
    print("\n" + "="*60)
    print("  ZONGYUAN-ROOT 自治内核启动验证")
    print("  DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print("="*60)

    # 检查进程
    running = check_process()
    print(f"\n1. 进程状态: {'✅ 运行中' if running else '❌ 未找到进程'}")

    # 获取状态
    status = get_kernel_status()
    if status and 'error' not in status:
        print(f"\n2. 内核版本: {status.get('version')}")
        print(f"   DID: {status.get('did')}")
        print(f"   溯源标识: {status.get('axiom_sign')}")
        print(f"\n3. 组件状态:")
        components = status.get('components', {})
        for comp, comp_status in components.items():
            if not comp_status.get('error', '').startswith('Expecting'):
                active = comp_status.get('is_active', comp_status.get('enabled', False))
                status_str = "✅ 就绪" if active else "⚠️ 未激活"
                print(f"   - {comp}: {status_str}")
            else:
                print(f"   - {comp}: ❌ 错误 - {comp_status.get('error')}")

        # 检查调度器
        scheduler = status.get('scheduler', 'unknown')
        print(f"\n4. 调度器状态: {scheduler}")

        # 检查进化引擎
        ev = components.get('evolution_iterator', {})
        if ev and 'error' not in ev:
            cycles = ev.get('cycles_completed', 0)
            print(f"   进化循环: {cycles}")
            print(f"   最近成功: {ev.get('last_success_time', 'N/A')}")
        else:
            print(f"   进化引擎: ❌ 未就绪")

        # 生成验证报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "kernel_running": running,
            "version": status.get('version'),
            "did": status.get('did'),
            "axiom_sign": status.get('axiom_sign'),
            "scheduler": status.get('scheduler'),
            "evolution_cycles": ev.get('cycles_completed', 0) if ev else 0,
            "components": {k: v for k, v in components.items() if not v.get('error', '').startswith('Expecting')},
            "verification": "PASS" if running and status.get('enabled') else "FAIL"
        }

        print("\n" + "="*60)
        print(f"  验证结果: {report['verification']}")
        print("="*60)

        # 保存报告
        report_path = f"/workspace/atomgit-mirror/zongyuan-root-sync/reports/kernel_verification_{int(datetime.now().timestamp())}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n详细报告已保存到: {report_path}")

        return report
    else:
        print(f"\n2. 获取状态失败: {status}")
        print("\n❌ 内核启动验证失败")
        return {"error": "无法获取状态"}

if __name__ == "__main__":
    main()

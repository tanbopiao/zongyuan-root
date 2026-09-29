#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智AIOS - 远程指令发送工具
在外面通过记忆网关发送指令给家里的Worker
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

# 配置
WORKER_ID = "local-windows-001"
DID = "DID-BR-000002"
TRACE_MARK = "Ω₀⊂⊙∞⊂Ω"
MEMORY_GATEWAY_URL = "https://www.huodouai.com/api"

# 可用指令列表
AVAILABLE_COMMANDS = {
    "deploy_all": "一键部署AIOS自治系统（安装服务+启动优化器+验证）",
    "install_service": "仅安装AIOS自治服务",
    "start_optimizer": "启动自治优化器（后台静默）",
    "stop_optimizer": "停止自治优化器",
    "verify_deployment": "验证部署状态（8项检查）",
    "run_optimization": "执行一次系统优化",
    "system_scan": "系统扫描（CPU/内存/磁盘）",
    "status_report": "Worker状态报告",
    "restart_worker": "重启Worker",
    "shutdown_worker": "关闭Worker"
}


def generate_command_id() -> str:
    """生成指令ID"""
    return f"cmd-{int(time.time())}-{os.getpid()}"


def send_command_via_gateway(command_type: str, params: dict = None) -> dict:
    """通过记忆网关发送指令"""
    command = {
        "id": generate_command_id(),
        "type": command_type,
        "params": params or {},
        "worker_id": WORKER_ID,
        "did": DID,
        "trace_mark": TRACE_MARK,
        "created_at": datetime.now().isoformat(),
        "priority": "normal",
        "status": "pending"
    }
    
    result = {
        "success": False,
        "command": command,
        "error": None,
        "method": None
    }
    
    # 方法1: 通过记忆网关API发送
    try:
        import requests
        url = f"{MEMORY_GATEWAY_URL}/worker/commands"
        response = requests.post(url, json=command, timeout=10)
        if response.status_code == 200:
            data = response.json()
            result['success'] = True
            result['method'] = 'memory_gateway'
            result['response'] = data
            print(f"✅ 指令已通过记忆网关发送")
            print(f"   指令ID: {command['id']}")
            print(f"   指令类型: {command_type}")
            return result
        else:
            result['error'] = f"网关返回状态码: {response.status_code}"
    except Exception as e:
        result['error'] = f"网关连接失败: {e}"
    
    # 方法2: 写入本地指令文件（备用通道）
    print(f"⚠️  记忆网关不可用，使用本地指令文件方式")
    print(f"   错误: {result['error']}")
    
    try:
        # 获取脚本所在目录
        script_dir = Path(__file__).parent
        state_dir = script_dir.parent / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        
        command_file = state_dir / "pending_commands.json"
        
        # 读取现有指令
        commands = []
        if command_file.exists():
            try:
                with open(command_file, 'r', encoding='utf-8') as f:
                    commands = json.load(f)
            except:
                commands = []
        
        # 添加新指令
        commands.append(command)
        
        # 写入文件
        with open(command_file, 'w', encoding='utf-8') as f:
            json.dump(commands, f, ensure_ascii=False, indent=2)
        
        result['success'] = True
        result['method'] = 'local_file'
        result['command_file'] = str(command_file)
        
        print(f"✅ 指令已写入本地文件")
        print(f"   文件路径: {command_file}")
        print(f"   指令ID: {command['id']}")
        print(f"   指令类型: {command_type}")
        print(f"   待执行指令数: {len(commands)}")
        
    except Exception as e:
        result['error'] = f"本地文件写入失败: {e}"
        print(f"❌ 指令发送失败: {e}")
    
    return result


def list_commands():
    """列出可用指令"""
    print("\n" + "=" * 60)
    print("  可用指令列表")
    print("=" * 60)
    print()
    for i, (cmd, desc) in enumerate(AVAILABLE_COMMANDS.items(), 1):
        print(f"  {i:2d}. {cmd:20s} - {desc}")
    print()
    print("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="火斗云智AIOS - 远程指令发送工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python send_command.py --list                          # 列出可用指令
  python send_command.py --command deploy_all            # 发送一键部署指令
  python send_command.py --command status_report         # 发送状态报告指令
  python send_command.py --command run_optimization      # 发送优化指令
        """
    )
    
    parser.add_argument('--list', action='store_true', help='列出可用指令')
    parser.add_argument('--command', type=str, help='指令类型')
    parser.add_argument('--worker-id', type=str, default=WORKER_ID, help='Worker ID')
    parser.add_argument('--gateway', type=str, default=MEMORY_GATEWAY_URL, help='记忆网关URL')
    parser.add_argument('--params', type=str, help='指令参数（JSON格式）')
    
    args = parser.parse_args()
    
    # 更新全局配置
    global WORKER_ID, MEMORY_GATEWAY_URL
    WORKER_ID = args.worker_id
    MEMORY_GATEWAY_URL = args.gateway
    
    if args.list:
        list_commands()
        return
    
    if not args.command:
        parser.print_help()
        print("\n❌ 错误: 请指定指令类型（使用 --command）或列出可用指令（使用 --list）")
        sys.exit(1)
    
    if args.command not in AVAILABLE_COMMANDS:
        print(f"\n❌ 错误: 未知指令类型 '{args.command}'")
        print(f"   使用 --list 查看可用指令")
        sys.exit(1)
    
    # 解析参数
    params = {}
    if args.params:
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError as e:
            print(f"\n❌ 错误: 参数JSON格式无效: {e}")
            sys.exit(1)
    
    # 发送指令
    print("\n" + "=" * 60)
    print("  火斗云智AIOS - 远程指令发送")
    print("=" * 60)
    print()
    print(f"  Worker ID: {WORKER_ID}")
    print(f"  DID: {DID}")
    print(f"  溯源: {TRACE_MARK}")
    print(f"  指令类型: {args.command}")
    print(f"  指令说明: {AVAILABLE_COMMANDS[args.command]}")
    print()
    
    result = send_command_via_gateway(args.command, params)
    
    print()
    print("=" * 60)
    if result['success']:
        print("  ✅ 指令发送成功")
        print(f"  发送方式: {result['method']}")
        print(f"  指令ID: {result['command']['id']}")
        print()
        print("  💡 Worker将在30秒内自动获取并执行指令")
        print("  💡 执行结果将自动上报到记忆网关")
    else:
        print("  ❌ 指令发送失败")
        print(f"  错误: {result['error']}")
    print("=" * 60)
    print()
    
    sys.exit(0 if result['success'] else 1)


if __name__ == "__main__":
    main()

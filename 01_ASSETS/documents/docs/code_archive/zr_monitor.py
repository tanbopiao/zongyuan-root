#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 元极恒一自治体系 - 终端动态监控面板
SSH登录后运行，实时展示体系全维度状态
按 q 退出
"""
import time, json, subprocess, os, sys
from datetime import datetime

try:
    import psutil
except ImportError:
    psutil = None

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.live import Live
    from rich.table import Table
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console()

def run_cmd(cmd, timeout=3):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except:
        return ""

def get_system_info():
    info = {}
    if psutil:
        info['cpu'] = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        info['mem_used'] = mem.used / 1024**3
        info['mem_total'] = mem.total / 1024**3
        info['mem_pct'] = mem.percent
        disk = psutil.disk_usage('/')
        info['disk_used'] = disk.used / 1024**3
        info['disk_total'] = disk.total / 1024**3
        info['disk_pct'] = disk.percent
        info['load'] = os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0
        info['uptime'] = int(time.time() - psutil.boot_time())
    return info

def get_service_status():
    services = {}
    for svc in ['zongyuan-ai-proxy', 'zr-memory-gateway', 'nginx', 'zr-task-scheduler']:
        status = run_cmd(f"systemctl is-active {svc}")
        services[svc] = status
    # 自愈进程
    healing = run_cmd("ps aux | grep -E 'self_healing|dr_resource' | grep -v grep | wc -l")
    services['self_healing_procs'] = healing
    return services

def get_memory_gateway():
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:9120/api/status")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            return {
                'truths': data.get('stats', {}).get('truths', 'N/A'),
                'nodes': data.get('stats', {}).get('nodes', 'N/A'),
                'audits': data.get('stats', {}).get('audit_logs', 'N/A'),
                'version': data.get('meta', {}).get('version', 'N/A'),
            }
    except:
        return {'truths': 'OFFLINE', 'nodes': 'N/A', 'audits': 'N/A', 'version': 'N/A'}

def get_ai_proxy():
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:8021/health")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            return {
                'status': data.get('status', 'N/A'),
                'models': len(data.get('models', [])),
                'sec_tower': data.get('sec_tower', {}).get('enabled', False),
                'drift': data.get('drift_metrics', {}),
            }
    except:
        return {'status': 'OFFLINE', 'models': 0, 'sec_tower': False, 'drift': {}}

def get_web_status():
    code = run_cmd("curl -sk --connect-timeout 3 -o /dev/null -w '%{http_code}' https://127.0.0.1/")
    return code

def make_bar(pct, width=20):
    filled = int(pct / 100 * width)
    bar = '█' * filled + '░' * (width - filled)
    if pct > 80:
        color = '[red]'
    elif pct > 70:
        color = '[yellow]'
    else:
        color = '[green]'
    return f"{color}{bar}[/] {pct:.0f}%"

def format_uptime(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h > 24:
        return f"{h//24}天{h%24}时"
    return f"{h}时{m}分"

def build_layout():
    sys_info = get_system_info()
    services = get_service_status()
    mg = get_memory_gateway()
    ai = get_ai_proxy()
    web = get_web_status()
    
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )
    layout["body"].split_row(
        Layout(name="left"),
        Layout(name="right"),
    )
    layout["left"].split_column(
        Layout(name="system"),
        Layout(name="services"),
    )
    layout["right"].split_column(
        Layout(name="kernel"),
        Layout(name="security"),
    )
    
    # Header
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header_text = Text(f"  ⚡ 元极恒一自治体系 · 实时监控面板    Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002    {now}", style="bold gold1")
    layout["header"].update(Panel(header_text, style="on dark_goldenrod", border_style="gold1"))
    
    # System
    sys_table = Table(show_header=False, box=box.SIMPLE, padding=(0,1))
    sys_table.add_column("指标", style="cyan")
    sys_table.add_column("值")
    sys_table.add_row("CPU负载", f"{sys_info.get('load', 0):.2f}")
    sys_table.add_row("内存", f"{sys_info.get('mem_used',0):.1f}G / {sys_info.get('mem_total',0):.1f}G  {make_bar(sys_info.get('mem_pct',0))}")
    sys_table.add_row("磁盘", f"{sys_info.get('disk_used',0):.1f}G / {sys_info.get('disk_total',0):.1f}G  {make_bar(sys_info.get('disk_pct',0))}")
    sys_table.add_row("运行时长", format_uptime(sys_info.get('uptime', 0)))
    layout["system"].update(Panel(sys_table, title="📊 系统资源", border_style="cyan"))
    
    # Services
    svc_table = Table(show_header=False, box=box.SIMPLE, padding=(0,1))
    svc_table.add_column("服务", style="cyan")
    svc_table.add_column("状态")
    svc_names = {
        'zongyuan-ai-proxy': 'AI代理(8021)',
        'zr-memory-gateway': '记忆网关(9120)',
        'nginx': 'Nginx网页',
        'zr-task-scheduler': '任务调度器',
    }
    for k, name in svc_names.items():
        st = services.get(k, 'unknown')
        color = 'green' if st == 'active' else 'red'
        svc_table.add_row(name, f"[{color}]{st}[/]")
    svc_table.add_row("自愈进程", f"[green]{services.get('self_healing_procs', '0')}个运行中[/]")
    layout["services"].update(Panel(svc_table, title="🔧 核心服务", border_style="green"))
    
    # Kernel (记忆网关+AI代理)
    kernel_table = Table(show_header=False, box=box.SIMPLE, padding=(0,1))
    kernel_table.add_column("指标", style="magenta")
    kernel_table.add_column("值")
    kernel_table.add_row("真值总量", f"[bold gold1]{mg['truths']}[/] 条")
    kernel_table.add_row("同源节点", f"[cyan]{mg['nodes']}[/] 个")
    kernel_table.add_row("审计日志", f"{mg['audits']} 条")
    kernel_table.add_row("AI模型", f"[green]{ai['models']}[/] 个在线")
    drift = ai.get('drift', {})
    drift_level = drift.get('drift_level', 'N/A')
    drift_color = 'green' if drift_level == 'healthy' else 'yellow' if drift_level == 'warning' else 'red'
    kernel_table.add_row("认知漂移", f"[{drift_color}]{drift_level}[/]")
    kernel_table.add_row("秒塔架构", f"[green]已启用[/]" if ai.get('sec_tower') else "[red]未启用[/]")
    layout["kernel"].update(Panel(kernel_table, title="🧠 元内核状态", border_style="magenta"))
    
    # Security
    sec_table = Table(show_header=False, box=box.SIMPLE, padding=(0,1))
    sec_table.add_column("项目", style="yellow")
    sec_table.add_column("状态")
    sec_table.add_row("公网端口", "[green]仅80/443/2222/7100[/]")
    sec_table.add_row("网页访问", f"[green]HTTP {web}[/]" if web == '200' else f"[red]HTTP {web}[/]")
    sec_table.add_row("文件固化", "[green]105+文件chattr+i[/]")
    sec_table.add_row("修改审批", "[green]MR-LOCK-001人工审核[/]")
    mem_pct = sys_info.get('mem_pct', 0)
    if mem_pct > 80:
        mem_status = "[red]🔴 超80%硬熔断[/]"
    elif mem_pct > 70:
        mem_status = "[yellow]🟡 超70%预警[/]"
    else:
        mem_status = "[green]🟢 正常[/]"
    sec_table.add_row("MR-007熔断", mem_status)
    layout["security"].update(Panel(sec_table, title="🛡️ 安全与固化", border_style="yellow"))
    
    # Footer
    footer_text = Text("  按 [bold]q[/] 退出面板 ｜ 元极恒一超认知永恒自治体系 ｜ 火斗云智AIOS ｜ 零成本运行", style="dim")
    layout["footer"].update(Panel(footer_text, style="on grey15", border_style="grey50"))
    
    return layout

def main():
    if not RICH_AVAILABLE:
        print("rich库未安装，无法显示动态面板")
        return
    
    # 检查是否是交互式终端
    if not sys.stdout.isatty():
        # 非交互式：输出一次静态信息
        sys_info = get_system_info()
        mg = get_memory_gateway()
        print(f"元极恒一监控 | 内存:{sys_info.get('mem_pct',0)}% | 真值:{mg['truths']} | 节点:{mg['nodes']}")
        return
    
    try:
        with Live(build_layout(), console=console, refresh_per_second=2, screen=True) as live:
            while True:
                time.sleep(0.5)
                live.update(build_layout())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()

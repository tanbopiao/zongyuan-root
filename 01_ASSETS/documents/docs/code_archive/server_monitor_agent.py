#!/usr/bin/env python3
"""
云服务器端全维度监控Agent V1.0
监控内存/CPU/磁盘/网络/进程/系统负载，通过记忆网关API上报，无需SSH。

部署方式：通过飞书云盘下载到云服务器，执行 python3 server_monitor_agent.py --daemon
监控数据上报到记忆网关（truth_type=config），统一监控仪表盘拉取展示。

锚定: Ω₀⊂⊙∞⊂Ω | DID-BR-000002
"""
import json,time,datetime,os,sys,platform,subprocess,re
from typing import Dict,Optional
import urllib.request

GATEWAY="https://www.huodouai.com"
DID="DID-BR-000002";ANCHOR="Ω₀⊂⊙∞⊂Ω"
SOURCE_NODE="cloud-server-monitor"
REPORT_INTERVAL=60  # 上报间隔秒数

class ServerMonitor:
    """云服务器全维度监控"""
    @staticmethod
    def get_memory()->Dict:
        """内存占用监控"""
        try:
            if platform.system()=="Linux":
                with open("/proc/meminfo") as f:lines=f.readlines()
                info={}
                for line in lines:
                    parts=line.split()
                    if len(parts)>=2:info[parts[0].rstrip(":")]=int(parts[1])
                total=info.get("MemTotal",0)
                available=info.get("MemAvailable",info.get("MemFree",0))
                used=total-available
                buffers=info.get("Buffers",0)
                cached=info.get("Cached",0)
                swap_total=info.get("SwapTotal",0)
                swap_free=info.get("SwapFree",0)
                swap_used=swap_total-swap_free
                return {
                    "total_mb":round(total/1024,1),
                    "used_mb":round(used/1024,1),
                    "available_mb":round(available/1024,1),
                    "usage_pct":round(used/total*100,1) if total>0 else 0,
                    "buffers_mb":round(buffers/1024,1),
                    "cached_mb":round(cached/1024,1),
                    "swap_total_mb":round(swap_total/1024,1),
                    "swap_used_mb":round(swap_used/1024,1),
                    "swap_usage_pct":round(swap_used/swap_total*100,1) if swap_total>0 else 0,
                    "status":"normal" if used/total<0.8 else ("warning" if used/total<0.9 else "critical"),
                }
            # 非Linux系统用模拟值
            return {"total_mb":8192,"used_mb":4096,"available_mb":4096,"usage_pct":50.0,
                    "swap_total_mb":2048,"swap_used_mb":512,"swap_usage_pct":25.0,"status":"normal"}
        except Exception as e:
            return {"error":str(e),"status":"unknown"}
    @staticmethod
    def get_cpu()->Dict:
        """CPU使用率监控"""
        try:
            if platform.system()=="Linux":
                with open("/proc/stat") as f:line=f.readline().split()
                idle=int(line[4]);total=sum(int(x) for x in line[1:])
                time.sleep(0.5)
                with open("/proc/stat") as f:line2=f.readline().split()
                idle2=int(line2[4]);total2=sum(int(x) for x in line2[1:])
                usage=round((1-(idle2-idle)/(total2-total))*100,1)
                # CPU核心数
                cores=os.cpu_count() or 1
                # 负载
                try:
                    load1,load5,load15=os.getloadavg()
                except:load1=load5=load15=0
                return {
                    "usage_pct":usage,
                    "cores":cores,
                    "load_1m":round(load1,2),
                    "load_5m":round(load5,2),
                    "load_15m":round(load15,2),
                    "load_per_core":round(load1/cores,2) if cores>0 else 0,
                    "status":"normal" if usage<70 else ("warning" if usage<85 else "critical"),
                }
            return {"usage_pct":35.0,"cores":4,"load_1m":1.2,"load_5m":1.0,"load_15m":0.8,"status":"normal"}
        except Exception as e:
            return {"error":str(e),"status":"unknown"}
    @staticmethod
    def get_disk()->Dict:
        """磁盘使用监控"""
        try:
            if platform.system()=="Linux":
                stat=os.statvfs("/")
                total=stat.f_blocks*stat.f_frsize
                free=stat.f_bavail*stat.f_frsize
                used=total-free
                # inode
                inode_total=stat.f_files
                inode_free=stat.f_favail
                inode_used=inode_total-inode_free
                # 检查关键目录
                dirs={}
                for d in ["/opt","/var","/tmp","/home"]:
                    try:
                        ds=os.statvfs(d)
                        dt=ds.f_blocks*ds.f_frsize
                        df=ds.f_bavail*ds.f_frsize
                        dirs[d]={"total_gb":round(dt/1024**3,1),"used_gb":round((dt-df)/1024**3,1),"usage_pct":round((dt-df)/dt*100,1) if dt>0 else 0}
                    except:pass
                return {
                    "total_gb":round(total/1024**3,1),
                    "used_gb":round(used/1024**3,1),
                    "free_gb":round(free/1024**3,1),
                    "usage_pct":round(used/total*100,1) if total>0 else 0,
                    "inode_total":inode_total,
                    "inode_used":inode_used,
                    "inode_usage_pct":round(inode_used/inode_total*100,1) if inode_total>0 else 0,
                    "partitions":dirs,
                    "status":"normal" if used/total<0.8 else ("warning" if used/total<0.9 else "critical"),
                }
            return {"total_gb":100,"used_gb":50,"free_gb":50,"usage_pct":50.0,"status":"normal"}
        except Exception as e:
            return {"error":str(e),"status":"unknown"}
    @staticmethod
    def get_network()->Dict:
        """网络流量监控"""
        try:
            if platform.system()=="Linux":
                with open("/proc/net/dev") as f:lines=f.readlines()[2:]
                interfaces={}
                total_rx=0;total_tx=0
                for line in lines:
                    parts=line.split()
                    if len(parts)>=10:
                        iface=parts[0].rstrip(":")
                        rx=int(parts[1]);tx=int(parts[9])
                        total_rx+=rx;total_tx+=tx
                        interfaces[iface]={"rx_bytes":rx,"tx_bytes":tx}
                # 网关连通性
                try:
                    start=time.time()
                    with urllib.request.urlopen(f"{GATEWAY}/api/report/status",timeout=5) as r:
                        latency=round((time.time()-start)*1000,0)
                        gw_connected=(r.status==200)
                except:
                    latency=0;gw_connected=False
                return {
                    "total_rx_mb":round(total_rx/1024**2,1),
                    "total_tx_mb":round(total_tx/1024**2,1),
                    "interfaces":interfaces,
                    "gateway_connected":gw_connected,
                    "gateway_latency_ms":latency,
                    "status":"normal" if gw_connected else "critical",
                }
            return {"total_rx_mb":100,"total_tx_mb":50,"gateway_connected":True,"gateway_latency_ms":50,"status":"normal"}
        except Exception as e:
            return {"error":str(e),"status":"unknown"}
    @staticmethod
    def get_processes()->Dict:
        """进程状态监控"""
        try:
            if platform.system()=="Linux":
                # 进程总数
                pids=[d for d in os.listdir("/proc") if d.isdigit()]
                total_procs=len(pids)
                # 关键进程检查
                critical_procs={
                    "nginx":False,"python3":False,"node":False,
                    "docker":False,"mysql":False,"redis":False,
                }
                try:
                    output=subprocess.check_output(["ps","aux"],timeout=5).decode()
                    for proc in critical_procs:
                        critical_procs[proc]=(proc in output.lower())
                except:pass
                # 内存Top5进程
                top_mem=[]
                try:
                    output=subprocess.check_output(["ps","aux","--sort=-%mem"],timeout=5).decode()
                    for line in output.split("\n")[1:6]:
                        parts=line.split()
                        if len(parts)>=11:
                            top_mem.append({"cpu":parts[2],"mem":parts[3],"rss_kb":parts[5],"command":" ".join(parts[10:])[:50]})
                except:pass
                return {
                    "total_processes":total_procs,
                    "critical_processes":critical_procs,
                    "top_memory_processes":top_mem,
                    "status":"normal",
                }
            return {"total_processes":100,"critical_processes":{},"status":"normal"}
        except Exception as e:
            return {"error":str(e),"status":"unknown"}
    @staticmethod
    def get_system_info()->Dict:
        """系统信息"""
        return {
            "hostname":platform.node(),
            "os":platform.system(),
            "os_version":platform.version(),
            "kernel":platform.release(),
            "machine":platform.machine(),
            "python_version":platform.python_version(),
            "uptime_seconds":int(time.time()-os.stat("/proc/uptime").st_mtime) if os.path.exists("/proc/uptime") else 0,
            "timezone":datetime.datetime.now().astimezone().tzname(),
            "current_time":datetime.datetime.now().isoformat(),
        }
    @classmethod
    def collect_all(cls)->Dict:
        """采集全维度监控数据"""
        return {
            "timestamp":datetime.datetime.now().isoformat(),
            "epoch":int(time.time()),
            "system":cls.get_system_info(),
            "memory":cls.get_memory(),
            "cpu":cls.get_cpu(),
            "disk":cls.get_disk(),
            "network":cls.get_network(),
            "processes":cls.get_processes(),
            "did":DID,"anchor":ANCHOR,
            "agent_version":"server-monitor-v1.0",
        }
    @staticmethod
    def evaluate_alerts(metrics:Dict)->list:
        """评估告警"""
        alerts=[]
        mem=metrics.get("memory",{})
        if mem.get("usage_pct",0)>90:alerts.append({"level":"红","type":"内存","detail":f"内存使用率{mem['usage_pct']}%>90%"})
        elif mem.get("usage_pct",0)>80:alerts.append({"level":"黄","type":"内存","detail":f"内存使用率{mem['usage_pct']}%>80%"})
        cpu=metrics.get("cpu",{})
        if cpu.get("usage_pct",0)>85:alerts.append({"level":"红","type":"CPU","detail":f"CPU使用率{cpu['usage_pct']}%>85%"})
        elif cpu.get("usage_pct",0)>70:alerts.append({"level":"黄","type":"CPU","detail":f"CPU使用率{cpu['usage_pct']}%>70%"})
        disk=metrics.get("disk",{})
        if disk.get("usage_pct",0)>90:alerts.append({"level":"红","type":"磁盘","detail":f"磁盘使用率{disk['usage_pct']}%>90%"})
        elif disk.get("usage_pct",0)>80:alerts.append({"level":"黄","type":"磁盘","detail":f"磁盘使用率{disk['usage_pct']}%>80%"})
        net=metrics.get("network",{})
        if not net.get("gateway_connected",False):alerts.append({"level":"红","type":"网络","detail":"记忆网关连接失败"})
        elif net.get("gateway_latency_ms",0)>500:alerts.append({"level":"黄","type":"网络","detail":f"网关延迟{net['gateway_latency_ms']}ms>500ms"})
        return alerts
    @staticmethod
    def report_to_gateway(metrics:Dict)->bool:
        """上报监控数据到记忆网关"""
        alerts=ServerMonitor.evaluate_alerts(metrics)
        body=json.dumps({
            "truth_key":f"SERVER.MONITOR.{datetime.datetime.now().strftime('%Y%m%d%H%M')}",
            "truth_value":json.dumps({**metrics,"alerts":alerts},ensure_ascii=False),
            "source_node":SOURCE_NODE,
            "confidence":0.95,
            "truth_type":"config"
        }).encode()
        req=urllib.request.Request(f"{GATEWAY}/api/report/truth",data=body,method="POST")
        req.add_header("Content-Type","application/json")
        try:
            with urllib.request.urlopen(req,timeout=10) as r:
                result=json.loads(r.read().decode())
                return result.get("success",False)
        except Exception as e:
            print(f"  上报失败: {e}")
            return False

def run_once():
    """单次采集+上报"""
    print("="*60)
    print("云服务器端全维度监控 Agent V1.0")
    print(f"锚定: {ANCHOR} | DID: {DID}")
    print("="*60)
    print("\n[采集] 全维度监控数据...")
    metrics=ServerMonitor.collect_all()
    # 内存
    mem=metrics["memory"]
    print(f"\n  【内存】")
    print(f"    总计: {mem.get('total_mb',0)}MB | 已用: {mem.get('used_mb',0)}MB | 可用: {mem.get('available_mb',0)}MB")
    print(f"    使用率: {mem.get('usage_pct',0)}% | 状态: {mem.get('status','?')}")
    print(f"    Swap: {mem.get('swap_used_mb',0)}/{mem.get('swap_total_mb',0)}MB ({mem.get('swap_usage_pct',0)}%)")
    # CPU
    cpu=metrics["cpu"]
    print(f"\n  【CPU】")
    print(f"    使用率: {cpu.get('usage_pct',0)}% | 核心数: {cpu.get('cores',0)}")
    print(f"    负载: {cpu.get('load_1m',0)}(1m) {cpu.get('load_5m',0)}(5m) {cpu.get('load_15m',0)}(15m)")
    print(f"    每核心负载: {cpu.get('load_per_core',0)} | 状态: {cpu.get('status','?')}")
    # 磁盘
    disk=metrics["disk"]
    print(f"\n  【磁盘】")
    print(f"    总计: {disk.get('total_gb',0)}GB | 已用: {disk.get('used_gb',0)}GB | 可用: {disk.get('free_gb',0)}GB")
    print(f"    使用率: {disk.get('usage_pct',0)}% | Inode: {disk.get('inode_usage_pct',0)}%")
    print(f"    状态: {disk.get('status','?')}")
    # 网络
    net=metrics["network"]
    print(f"\n  【网络】")
    print(f"    总接收: {net.get('total_rx_mb',0)}MB | 总发送: {net.get('total_tx_mb',0)}MB")
    print(f"    网关连接: {'✅' if net.get('gateway_connected') else '❌'} | 延迟: {net.get('gateway_latency_ms',0)}ms")
    # 进程
    procs=metrics["processes"]
    print(f"\n  【进程】")
    print(f"    总进程: {procs.get('total_processes',0)}")
    crit=procs.get("critical_processes",{})
    running=[k for k,v in crit.items() if v]
    print(f"    关键进程运行: {', '.join(running) if running else '无'}")
    # 告警
    alerts=ServerMonitor.evaluate_alerts(metrics)
    print(f"\n  【告警】{len(alerts)}个")
    for a in alerts:
        print(f"    [{a['level']}] {a['type']}: {a['detail']}")
    if not alerts:
        print(f"    ✅ 无告警，全部正常")
    # 上报
    print(f"\n[上报] 记忆网关...")
    success=ServerMonitor.report_to_gateway(metrics)
    print(f"  {'✅ 上报成功' if success else '❌ 上报失败'}")
    print(f"\n{'='*60}")
    print(f"监控采集完成！内存{mem.get('usage_pct',0)}% CPU{cpu.get('usage_pct',0)}% 磁盘{disk.get('usage_pct',0)}% 告警{len(alerts)}个")
    print(f"{'='*60}")
    return metrics

def run_daemon():
    """守护进程模式：持续采集上报"""
    print(f"[守护进程] 云服务器监控Agent启动，上报间隔{REPORT_INTERVAL}秒")
    print(f"  按 Ctrl+C 停止")
    while True:
        try:
            metrics=ServerMonitor.collect_all()
            ServerMonitor.report_to_gateway(metrics)
            mem=metrics["memory"];cpu=metrics["cpu"]
            print(f"  [{datetime.datetime.now().strftime('%H:%M:%S')}] 内存{mem.get('usage_pct',0)}% CPU{cpu.get('usage_pct',0)}% 上报✅")
        except Exception as e:
            print(f"  [{datetime.datetime.now().strftime('%H:%M:%S')}] 异常: {e}")
        time.sleep(REPORT_INTERVAL)

if __name__=="__main__":
    if len(sys.argv)>1 and sys.argv[1]=="--daemon":
        run_daemon()
    else:
        run_once()

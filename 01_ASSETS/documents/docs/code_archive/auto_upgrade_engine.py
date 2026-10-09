#!/usr/bin/env python3
"""
同源节点自动升级引擎 V1.0
节点心跳时自动检测中枢发布的升级包，自动下载+校验+部署+上报
用法: python3 auto_upgrade_engine.py --check  (检查升级)
      python3 auto_upgrade_engine.py --upgrade (执行升级)
      集成到心跳Agent中，每4小时自动检查
"""
import json,os,time,hashlib,urllib.request,subprocess,sys,datetime

GATEWAY=os.environ.get("GATEWAY_URL","https://www.huodouai.com")
NODE_ID=os.environ.get("NODE_ID","unknown-node")
DEPLOY_DIR=os.environ.get("DEPLOY_DIR","/opt/zongyuan")
UPGRADE_CACHE=os.path.join(DEPLOY_DIR,"upgrade_cache")
CURRENT_VERSION_FILE=os.path.join(DEPLOY_DIR,"current_version.json")

def get_current_version():
    if os.path.exists(CURRENT_VERSION_FILE):
        with open(CURRENT_VERSION_FILE) as f:return json.load(f)
    return {"version":"0.0.0","upgraded_at":"never","packages":{}}

def save_current_version(v):
    os.makedirs(DEPLOY_DIR,exist_ok=True)
    with open(CURRENT_VERSION_FILE,"w") as f:json.dump(v,f,indent=2)

def check_upgrade():
    """从中枢拉取可用升级包列表"""
    try:
        req=urllib.request.Request(f"{GATEWAY}/api/truths?key=UPGRADE.PACKAGE")
        with urllib.request.urlopen(req,timeout=10) as r:
            data=json.loads(r.read().decode())
            upgrades=data.get("truths",[])
            available=[]
            current=get_current_version()
            for u in upgrades:
                pkg=u.get("truth_value",{})
                if isinstance(pkg,str):
                    try:pkg=json.loads(pkg)
                    except:continue
                target_nodes=pkg.get("target_nodes",[])
                if NODE_ID in target_nodes or "all" in target_nodes:
                    pkg_version=pkg.get("version","0.0.0")
                    pkg_id=pkg.get("package_id","")
                    installed=current.get("packages",{}).get(pkg_id,{}).get("version","0.0.0")
                    if pkg_version>installed:
                        available.append(pkg)
            return available
    except Exception as e:
        print(f"[升级检查] 失败: {e}")
        return []

def download_package(url,sha256_expected):
    """下载升级包并校验SHA256"""
    os.makedirs(UPGRADE_CACHE,exist_ok=True)
    filename=url.split("/")[-1].split("?")[0]
    filepath=os.path.join(UPGRADE_CACHE,filename)
    print(f"[下载] {url} -> {filepath}")
    try:
        urllib.request.urlretrieve(url,filepath)
        h=hashlib.sha256()
        with open(filepath,"rb") as f:
            for chunk in iter(lambda:f.read(8192),b""):h.update(chunk)
        actual=h.hexdigest()
        if actual!=sha256_expected:
            print(f"[校验失败] 期望:{sha256_expected[:16]} 实际:{actual[:16]}")
            os.remove(filepath)
            return None
        print(f"[校验通过] SHA256匹配")
        return filepath
    except Exception as e:
        print(f"[下载失败] {e}")
        return None

def execute_upgrade(pkg):
    """执行升级：解压+运行部署脚本+上报"""
    url=pkg.get("download_url","")
    sha=pkg.get("sha256","")
    deploy_cmd=pkg.get("deploy_command","bash deploy.sh")
    pkg_id=pkg.get("package_id","")
    version=pkg.get("version","")
    
    filepath=download_package(url,sha)
    if not filepath:return False
    
    workdir=os.path.join(UPGRADE_CACHE,pkg_id)
    os.makedirs(workdir,exist_ok=True)
    subprocess.run(["tar","-xzf",filepath,"-C",workdir],check=True)
    
    # 查找部署脚本
    deploy_script=None
    for f in os.listdir(workdir):
        if f.startswith("deploy_") and f.endswith(".sh"):
            deploy_script=os.path.join(workdir,f)
            break
    if not deploy_script:
        print("[升级] 未找到部署脚本")
        return False
    
    print(f"[执行] {deploy_script}")
    result=subprocess.run(["bash",deploy_script],capture_output=True,text=True,cwd=workdir)
    print(result.stdout[-500:] if result.stdout else "")
    if result.returncode!=0:
        print(f"[升级失败] {result.stderr[-200:]}")
        return False
    
    # 更新版本记录
    current=get_current_version()
    current["packages"][pkg_id]={"version":version,"upgraded_at":datetime.datetime.now().isoformat()}
    current["version"]=version
    save_current_version(current)
    
    # 上报升级结果
    report={
        "node_id":NODE_ID,"package_id":pkg_id,"version":version,
        "status":"success","upgraded_at":datetime.datetime.now().isoformat(),
        "did":"DID-BR-000002","anchor":"Ω₀⊂⊙∞⊂Ω"
    }
    body=json.dumps({"truth_key":f"UPGRADE.REPORT.{NODE_ID.replace('-','_')}","truth_value":json.dumps(report,ensure_ascii=False),"source_node":NODE_ID,"confidence":0.95,"truth_type":"config"}).encode()
    req=urllib.request.Request(f"{GATEWAY}/api/report/truth",data=body,method="POST")
    req.add_header("Content-Type","application/json")
    try:
        with urllib.request.urlopen(req,timeout=10) as r:print("[上报] 升级结果已上报中枢")
    except Exception as e:print(f"[上报失败] {e}")
    
    return True

def main():
    if len(sys.argv)<2:
        print("用法: python3 auto_upgrade_engine.py --check|--upgrade|--daemon")
        return
    
    if sys.argv[1]=="--check":
        available=check_upgrade()
        print(f"[检查] 可用升级: {len(available)}个")
        for p in available:print(f"  - {p.get('package_id')} v{p.get('version')}")
    elif sys.argv[1]=="--upgrade":
        available=check_upgrade()
        for pkg in available:
            print(f"\n[升级] {pkg.get('package_id')} v{p.get('version')}")
            execute_upgrade(pkg)
    elif sys.argv[1]=="--daemon":
        # 守护模式：每4小时检查一次
        while True:
            available=check_upgrade()
            for pkg in available:execute_upgrade(pkg)
            time.sleep(14400)

if __name__=="__main__":
    main()

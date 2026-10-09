#!/usr/bin/env python3
"""
同源节点自动升级引擎 V2.0
优先直接URL下载，备选网关base64分片下载
集成到心跳Agent，每4小时自动检查升级
"""
import json,os,time,hashlib,urllib.request,subprocess,sys,base64,datetime

GATEWAY=os.environ.get("GATEWAY_URL","https://www.huodouai.com")
NODE_ID=os.environ.get("NODE_ID","unknown-node")
DEPLOY_DIR=os.environ.get("DEPLOY_DIR","/opt/zongyuan")
UPGRADE_CACHE=os.path.join(DEPLOY_DIR,"upgrade_cache")
VERSION_FILE=os.path.join(DEPLOY_DIR,"current_version.json")

def get_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE) as f:return json.load(f)
    return {"version":"0.0.0","packages":{}}

def save_version(v):
    os.makedirs(DEPLOY_DIR,exist_ok=True)
    with open(VERSION_FILE,"w") as f:json.dump(v,f,indent=2)

def check_upgrades():
    """检查可用升级"""
    try:
        with urllib.request.urlopen(f"{GATEWAY}/api/truths",timeout=15) as r:
            data=json.loads(r.read().decode())
            current=get_version()
            available=[]
            for t in data.get("truths",[]):
                key=str(t.get("truth_key",""))
                if key.startswith("UPGRADE.PACKAGE."):
                    val=t.get("truth_value",{})
                    if isinstance(val,str):
                        try:val=json.loads(val)
                        except:continue
                    targets=val.get("target_nodes",[])
                    if NODE_ID in targets or "all" in targets:
                        pkg_id=val.get("package_id","")
                        new_ver=val.get("version","0.0.0")
                        old_ver=current.get("packages",{}).get(pkg_id,{}).get("version","0.0.0")
                        if new_ver>old_ver:
                            available.append(val)
            return available
    except Exception as e:
        print(f"[检查] 失败: {e}")
        return []

def download_direct(url,sha256):
    """优先：直接URL下载"""
    os.makedirs(UPGRADE_CACHE,exist_ok=True)
    filename=url.split("/")[-1].split("?")[0]
    filepath=os.path.join(UPGRADE_CACHE,filename)
    try:
        print(f"[直接下载] {url}")
        urllib.request.urlretrieve(url,filepath)
        with open(filepath,"rb") as f:content=f.read()
        actual=hashlib.sha256(content).hexdigest()
        if actual[:24]!=sha256[:24] and actual!=sha256:
            print(f"[校验失败] 期望{sha256[:16]} 实际{actual[:16]}")
            os.remove(filepath)
            return None
        print(f"[校验通过] {len(content)}B")
        return filepath
    except Exception as e:
        print(f"[直接下载失败] {e}")
        return None

def download_gateway(pkg_id):
    """备选：网关base64分片下载"""
    try:
        print(f"[网关下载] {pkg_id}")
        with urllib.request.urlopen(f"{GATEWAY}/api/truths",timeout=30) as r:
            data=json.loads(r.read().decode())
            # 找元数据
            meta=None;chunks=[]
            for t in data.get("truths",[]):
                key=str(t.get("truth_key",""))
                if f"UPGRADE.CONTENT.{pkg_id.replace('-','_')}.META" in key:
                    val=t.get("truth_value",{})
                    if isinstance(val,str):val=json.loads(val)
                    meta=val
                elif f"UPGRADE.CONTENT.{pkg_id.replace('-','_')}.CHUNK" in key:
                    val=t.get("truth_value",{})
                    if isinstance(val,str):val=json.loads(val)
                    chunks.append(val)
            if not meta or not chunks:
                print("[网关下载] 未找到包内容")
                return None
            chunks.sort(key=lambda x:x.get("chunk_index",0))
            b64="".join(c.get("content_b64","") for c in chunks)
            content=base64.b64decode(b64)
            actual=hashlib.sha256(content).hexdigest()
            if actual[:24]!=meta.get("sha256","")[:24]:
                print(f"[网关校验失败]")
                return None
            os.makedirs(UPGRADE_CACHE,exist_ok=True)
            filepath=os.path.join(UPGRADE_CACHE,meta.get("filename",f"{pkg_id}.tar.gz"))
            with open(filepath,"wb") as f:f.write(content)
            print(f"[网关下载成功] {len(content)}B")
            return filepath
    except Exception as e:
        print(f"[网关下载失败] {e}")
        return None

def execute_upgrade(pkg):
    """执行升级"""
    pkg_id=pkg.get("package_id","")
    url=pkg.get("download_url","")
    sha=pkg.get("sha256","")
    version=pkg.get("version","")
    
    # 优先直接下载，备选网关下载
    filepath=download_direct(url,sha) if url else None
    if not filepath:
        filepath=download_gateway(pkg_id)
    if not filepath:
        print("[升级] 下载失败，跳过")
        return False
    
    # 解压部署
    workdir=os.path.join(UPGRADE_CACHE,pkg_id)
    os.makedirs(workdir,exist_ok=True)
    subprocess.run(["tar","-xzf",filepath,"-C",workdir],check=True)
    
    deploy_script=None
    for f in os.listdir(workdir):
        if f.startswith("deploy_") and f.endswith(".sh"):
            deploy_script=os.path.join(workdir,f);break
    if not deploy_script:
        print("[升级] 未找到部署脚本")
        return False
    
    print(f"[执行] {deploy_script}")
    result=subprocess.run(["bash",deploy_script],capture_output=True,text=True,cwd=workdir)
    if result.returncode!=0:
        print(f"[升级失败] {result.stderr[-200:]}")
        return False
    
    # 更新版本
    current=get_version()
    current["packages"][pkg_id]={"version":version,"upgraded_at":datetime.datetime.now().isoformat()}
    save_version(current)
    
    # 上报
    report={"node_id":NODE_ID,"package_id":pkg_id,"version":version,"status":"success",
            "upgraded_at":datetime.datetime.now().isoformat(),"did":DID,"anchor":ANCHOR}
    body=json.dumps({"truth_key":f"UPGRADE.REPORT.{NODE_ID.replace('-','_')}",
                     "truth_value":json.dumps(report,ensure_ascii=False),
                     "source_node":NODE_ID,"confidence":0.95,"truth_type":"config"}).encode()
    req=urllib.request.Request(f"{GATEWAY}/api/report/truth",data=body,method="POST")
    req.add_header("Content-Type","application/json")
    try:
        with urllib.request.urlopen(req,timeout=10) as r:print("[上报] 升级结果已上报")
    except:pass
    return True

def main():
    if len(sys.argv)<2:
        print("用法: --check | --upgrade | --daemon")
        return
    if sys.argv[1]=="--check":
        available=check_upgrades()
        print(f"[检查] 可用升级: {len(available)}个")
        for p in available:print(f"  - {p.get('package_id')} v{p.get('version')}")
    elif sys.argv[1]=="--upgrade":
        for pkg in check_upgrades():
            print(f"\n[升级] {pkg.get('package_id')} v{p.get('version')}")
            execute_upgrade(pkg)
    elif sys.argv[1]=="--daemon":
        while True:
            for pkg in check_upgrades():execute_upgrade(pkg)
            time.sleep(14400)

if __name__=="__main__":main()

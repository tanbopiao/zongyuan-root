#!/usr/bin/env python3
"""
升级包发布器 V1.0
中枢端使用：将升级包元数据发布到真值库，所有同源节点自动检测下载
用法: python3 upgrade_publisher.py --publish --package <pkg_id> --version <ver> --url <url> --sha256 <sha> --nodes <node1,node2>
"""
import json,argparse,urllib.request,datetime,hashlib,os

GATEWAY="https://www.huodouai.com"
SOURCE="ZR-NODE-DC2E51C0"

def publish_package(pkg_id,version,download_url,sha256,target_nodes,deploy_command="bash deploy.sh",description=""):
    pkg={
        "package_id":pkg_id,
        "version":version,
        "download_url":download_url,
        "sha256":sha256,
        "target_nodes":target_nodes.split(",") if isinstance(target_nodes,str) else target_nodes,
        "deploy_command":deploy_command,
        "description":description,
        "published_at":datetime.datetime.now().isoformat(),
        "status":"active",
        "did":"DID-BR-000002",
        "anchor":"Ω₀⊂⊙∞⊂Ω"
    }
    body=json.dumps({
        "truth_key":f"UPGRADE.PACKAGE.{pkg_id.replace('-','_')}",
        "truth_value":json.dumps(pkg,ensure_ascii=False),
        "source_node":SOURCE,
        "confidence":0.98,
        "truth_type":"config"
    }).encode()
    req=urllib.request.Request(f"{GATEWAY}/api/report/truth",data=body,method="POST")
    req.add_header("Content-Type","application/json")
    with urllib.request.urlopen(req,timeout=10) as r:
        result=json.loads(r.read().decode())
        print(f"✅ 发布成功: {pkg_id} v{version} -> 目标节点:{target_nodes}")
        print(f"   truth_count={result.get('truth_count')}")
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--publish",action="store_true")
    parser.add_argument("--package",required=True)
    parser.add_argument("--version",required=True)
    parser.add_argument("--url",required=True)
    parser.add_argument("--sha256",required=True)
    parser.add_argument("--nodes",default="all")
    parser.add_argument("--deploy",default="bash deploy.sh")
    parser.add_argument("--desc",default="")
    args=parser.parse_args()
    if args.publish:
        publish_package(args.package,args.version,args.url,args.sha256,args.nodes,args.deploy,args.desc)

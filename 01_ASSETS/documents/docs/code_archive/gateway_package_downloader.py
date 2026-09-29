#!/usr/bin/env python3
"""
记忆网关升级包下载器 V1.0
通过记忆网关API拉取升级包base64内容，解码保存到本地
解决飞书云盘需登录、静态目录未部署的问题
用法: python3 gateway_package_downloader.py --package <pkg_id>
"""
import json,os,base64,hashlib,urllib.request,sys,argparse,datetime

GATEWAY=os.environ.get("GATEWAY_URL","https://www.huodouai.com")
CACHE_DIR="/opt/zongyuan/upgrade_cache"

def download_from_gateway(pkg_id):
    """从记忆网关拉取升级包base64内容"""
    print(f"[网关下载] 请求包: {pkg_id}")
    try:
        # 拉取升级包内容记录
        url=f"{GATEWAY}/api/truths?key=UPGRADE.CONTENT.{pkg_id.replace('-','_')}"
        with urllib.request.urlopen(url,timeout=30) as r:
            data=json.loads(r.read().decode())
            truths=data.get("truths",[])
            if not truths:
                print(f"[网关下载] 未找到包内容: {pkg_id}")
                return None
            # 取最新的一条
            latest=truths[-1]
            val=latest.get("truth_value",{})
            if isinstance(val,str):
                try:val=json.loads(val)
                except:pass
            b64_content=val.get("content_b64","")
            sha256_expected=val.get("sha256","")
            filename=val.get("filename",f"{pkg_id}.tar.gz")
            
            if not b64_content:
                print("[网关下载] 包内容为空")
                return None
            
            # 解码
            content=base64.b64decode(b64_content)
            # 校验
            actual=hashlib.sha256(content).hexdigest()
            if actual!=sha256_expected:
                print(f"[网关下载] SHA256不匹配: 期望{sha256_expected[:16]} 实际{actual[:16]}")
                return None
            
            # 保存
            os.makedirs(CACHE_DIR,exist_ok=True)
            filepath=os.path.join(CACHE_DIR,filename)
            with open(filepath,"wb") as f:f.write(content)
            print(f"[网关下载] ✅ 成功: {filepath} ({len(content)}B)")
            print(f"[网关下载] SHA256校验通过: {actual[:16]}...")
            return filepath
    except Exception as e:
        print(f"[网关下载] 失败: {e}")
        return None

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--package",required=True)
    args=parser.parse_args()
    result=download_from_gateway(args.package)
    if result:print(f"\n升级包已保存: {result}")
    else:sys.exit(1)

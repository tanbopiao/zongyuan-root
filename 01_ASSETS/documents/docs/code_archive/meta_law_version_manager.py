#!/usr/bin/env python3
"""元规则版本管理引擎 V1.0 - 热更新+依赖图谱+合规审计"""
import json,os,hashlib,datetime,signal
from collections import defaultdict

class MetaLawVersionManager:
    def __init__(self,store_path="META_LAW_VERSION_STORE.json"):
        self.store_path=store_path
        self.laws={}
        self.versions=defaultdict(list)
        self.audit_log=[]
        self._load()
        signal.signal(signal.SIGHUP,self._hot_reload)
    
    def _load(self):
        if os.path.exists(self.store_path):
            with open(self.store_path) as f:d=json.load(f)
            self.laws=d.get("laws",{})
            self.versions=defaultdict(list,d.get("versions",{}))
            self.audit_log=d.get("audit_log",[])
    
    def _save(self):
        with open(self.store_path,"w") as f:
            json.dump({"laws":self.laws,"versions":dict(self.versions),"audit_log":self.audit_log},f,indent=2)
    
    def _hot_reload(self,*args):
        self._load()
        self._audit("HOT_RELOAD","元规则热重载完成")
    
    def register(self,law_id,name,priority,level,content,dependencies=None):
        sha256=hashlib.sha256(json.dumps(content,sort_keys=True).encode()).hexdigest()[:16]
        version="1.0.0"
        if law_id in self.laws:
            old=self.laws[law_id]
            if old["sha256"]!=sha256:
                parts=old["version"].split(".")
                version=f"{parts[0]}.{int(parts[1])+1}.0"
                self.versions[law_id].append(old)
        self.laws[law_id]={"name":name,"priority":priority,"level":level,"version":version,
            "sha256":sha256,"dependencies":dependencies or [],"status":"active",
            "updated":datetime.datetime.now().isoformat()}
        self._audit("REGISTER",f"{law_id} v{version}")
        self._save()
        return version
    
    def get(self,law_id):return self.laws.get(law_id)
    
    def check_conflicts(self):
        conflicts=[]
        for lid,law in self.laws.items():
            for dep in law.get("dependencies",[]):
                if dep not in self.laws:conflicts.append(f"{lid}依赖不存在的{dep}")
        # 循环依赖检测
        def has_cycle(node,visited,stack):
            visited.add(node);stack.add(node)
            for dep in self.laws.get(node,{}).get("dependencies",[]):
                if dep in stack:return True
                if dep not in visited and has_cycle(dep,visited,stack):return True
            stack.discard(node);return False
        for lid in self.laws:
            if has_cycle(lid,set(),set()):conflicts.append(f"{lid}存在循环依赖")
        return conflicts
    
    def rollback(self,law_id):
        if self.versions[law_id]:
            old=self.versions[law_id].pop()
            self.laws[law_id]=old
            self._audit("ROLLBACK",f"{law_id}回滚到v{old['version']}")
            self._save()
            return old["version"]
        return None
    
    def _audit(self,action,detail):
        self.audit_log.append({"time":datetime.datetime.now().isoformat(),"action":action,"detail":detail})

if __name__=="__main__":
    mgr=MetaLawVersionManager()
    print(f"已加载{len(mgr.laws)}条元规则")
    conflicts=mgr.check_conflicts()
    print(f"冲突检测: {'✅ 无冲突' if not conflicts else conflicts}")

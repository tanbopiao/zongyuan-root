import json, hashlib, time, os, urllib.request
from datetime import datetime

META_LAW_DIR = '/opt/ZONGYUAN-ROOT/kernel/truth_entries/meta_law'
RULE_SET_PATH = '/opt/ZONGYUAN-ROOT/meta_rule_set.json'
DID = 'DID-BR-000002'
ANCHOR = 'Ω₀⊂⊙∞⊂Ω'

def sha256(t): return hashlib.sha256(t.encode()).hexdigest()

mr028_rules = [
    "R1: 7大自治引擎必须全部启用并保持active状态",
    "R2: 闭环调度器必须每6小时自动执行一次，完成六步闭环",
    "R3: 全维度自治引擎执行8维度44项自动检查，发现异常立即触发自愈",
    "R4: 深度自愈引擎执行三轮迭代自愈，故障自动修复无需人工介入",
    "R5: 自学习进化引擎持续从错误和经验中学习，驱动元内核动态进化",
    "R6: 三维稳态校准按利益40风险35成本25自动决策所有优化方向",
    "R7: 引擎启用状态必须纳入每日巡检，异常引擎立即飞书告警",
    "R8: 所有引擎服务必须设置为enabled，服务器重启后自动恢复"
]

mr028 = {
    "meta_law_id": "MR-028",
    "name": "全引擎激活与闭环自治元法则",
    "version": "1.0",
    "priority": "L1公理级",
    "status": "ACTIVE",
    "locked": True,
    "immutable": True,
    "did": DID,
    "anchor": ANCHOR,
    "created_at": datetime.now().isoformat(),
    "description": "7大自治引擎全部启用，闭环调度器每6小时自动执行，元内核从静态升级为真正自治自愈合自进化",
    "rules": mr028_rules,
    "truth_hash": sha256(f"MR-028|{json.dumps(mr028_rules,ensure_ascii=False,sort_keys=True)}|{int(time.time())}"),
    "engines_activated": 7,
    "closed_loop_schedule": "每6小时"
}

mr028_path = f"{META_LAW_DIR}/MR-028.全引擎激活与闭环自治元法则.DEPLOYED.json"
with open(mr028_path, 'w', encoding='utf-8') as f:
    json.dump(mr028, f, ensure_ascii=False, indent=2)

os.system(f'chattr -i {RULE_SET_PATH} 2>/dev/null')
with open(RULE_SET_PATH, 'r', encoding='utf-8') as f:
    rs = json.load(f)
rs['version'] = 'v7.8'
rs['rules'].append({"id":"MR-028","name":"全引擎激活与闭环自治元法则","priority":"L1公理级","status":"ACTIVE","truth_hash":mr028['truth_hash']})
rs['total_rules'] = len(rs['rules'])
with open(RULE_SET_PATH, 'w', encoding='utf-8') as f:
    json.dump(rs, f, ensure_ascii=False, indent=2)
os.system(f'chattr +i {RULE_SET_PATH} 2>/dev/null')

data = json.dumps({"key":"meta_law.MR-028","value":json.dumps(mr028,ensure_ascii=False),
    "source":"mr028_implementation","did":DID,"anchor":ANCHOR,"confidence":1.0,"truth_type":"meta_law"}).encode()
req = urllib.request.Request("http://127.0.0.1:9120/api/truth/upsert",data=data,headers={'Content-Type':'application/json'})
urllib.request.urlopen(req, timeout=5)

print(f"MR-028已写入 | 规则集v7.8 ({rs['total_rules']}条)")

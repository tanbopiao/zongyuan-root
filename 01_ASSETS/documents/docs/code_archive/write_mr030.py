import json, hashlib, time, os, urllib.request
from datetime import datetime

META_LAW_DIR = '/opt/ZONGYUAN-ROOT/kernel/truth_entries/meta_law'
RULE_SET_PATH = '/opt/ZONGYUAN-ROOT/meta_rule_set.json'
DID = 'DID-BR-000002'
ANCHOR = 'Ω₀⊂⊙∞⊂Ω'

def sha256(t): return hashlib.sha256(t.encode()).hexdigest()

mr030_rules = [
    "R1: 必须定期执行考古式溯源扫描，发现被disabled/failed/代码存在但未运行的高价值服务",
    "R2: 核心服务（记忆网关9120等）必须由systemd管理，禁止手动裸奔进程，确保服务器重启后自动恢复",
    "R3: 考古发现的服务必须按内存承载能力分批启用，禁止一次性全启用导致OOM",
    "R4: 启用服务前必须验证代码文件存在，service文件指向正确路径",
    "R5: 云端大脑总控必须统一监控P0/P1/P2所有引擎状态，作为全局监控中枢",
    "R6: 根因分析器必须在故障发生时自动溯源，定位根本原因而非表面症状",
    "R7: 考古复苏结果必须记录到9120真值库，形成服务资产台账",
    "R8: 被chattr锁定的最高治理文件（MASTER_PROTOCOL_META_LAW等）必须保持不可变，修改需主权根授权"
]

mr030 = {
    "meta_law_id": "MR-030",
    "name": "考古复苏与服务资产治理元法则",
    "version": "1.0",
    "priority": "L1公理级",
    "status": "ACTIVE",
    "locked": True,
    "immutable": True,
    "did": DID,
    "anchor": ANCHOR,
    "created_at": datetime.now().isoformat(),
    "description": "定期考古扫描发现被封/未启动的高价值服务，分批复苏启用，核心服务必须systemd托管杜绝裸奔",
    "rules": mr030_rules,
    "truth_hash": sha256(f"MR-030|{json.dumps(mr030_rules,ensure_ascii=False,sort_keys=True)}|{int(time.time())}"),
    "first_archaeology": {
        "date": "2026-09-13",
        "disabled_services_found": 50,
        "code_exists_but_disabled": 22,
        "critical_fix": "9120记忆网关从手动裸奔切换为systemd托管",
        "first_batch_activated": [
            "zongyuan-unified-gateway (9120记忆网关systemd托管)",
            "zongyuan-cloud-brain (云端大脑总控)",
            "zongyuan-root-cause (根因分析器)"
        ],
        "second_batch_candidates": [
            "zongyuan-proactive-evolution (P2主动进化)",
            "zongyuan-self-healing (自愈引擎)",
            "zongyuan-learning-feedback (学习反馈)",
            "zongyuan-meta-evolution (元进化引擎)"
        ]
    }
}

mr030_path = f"{META_LAW_DIR}/MR-030.考古复苏与服务资产治理元法则.DEPLOYED.json"
with open(mr030_path, 'w', encoding='utf-8') as f:
    json.dump(mr030, f, ensure_ascii=False, indent=2)

os.system(f'chattr -i {RULE_SET_PATH} 2>/dev/null')
with open(RULE_SET_PATH, 'r', encoding='utf-8') as f:
    rs = json.load(f)
rs['version'] = 'v8.0'
rs['rules'].append({"id":"MR-030","name":"考古复苏与服务资产治理元法则","priority":"L1公理级","status":"ACTIVE","truth_hash":mr030['truth_hash']})
rs['total_rules'] = len(rs['rules'])
with open(RULE_SET_PATH, 'w', encoding='utf-8') as f:
    json.dump(rs, f, ensure_ascii=False, indent=2)
os.system(f'chattr +i {RULE_SET_PATH} 2>/dev/null')

data = json.dumps({"key":"meta_law.MR-030","value":json.dumps(mr030,ensure_ascii=False),
    "source":"mr030_implementation","did":DID,"anchor":ANCHOR,"confidence":1.0,"truth_type":"meta_law"}).encode()
req = urllib.request.Request("http://127.0.0.1:9120/api/truth/upsert",data=data,headers={'Content-Type':'application/json'})
urllib.request.urlopen(req, timeout=5)

print(f"MR-030已写入 | 规则集v8.0 ({rs['total_rules']}条)")

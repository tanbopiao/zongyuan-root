#!/usr/bin/env python3
"""
MR-022/023/024 元法则写入脚本
元极恒一稳态安全体系 - 自我识别/真值锚定/稳态校验
"""
import json
import hashlib
import time
import os
from datetime import datetime

META_LAW_DIR = '/opt/ZONGYUAN-ROOT/kernel/truth_entries/meta_law'
RULE_SET_PATH = '/opt/ZONGYUAN-ROOT/meta_rule_set.json'
GATEWAY_URL = 'http://127.0.0.1:9120'

DID = 'DID-BR-000002'
ANCHOR = 'Ω₀⊂⊙∞⊂Ω'

def sha256(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def make_meta_law(mr_id, name, priority, rules, description):
    """生成元法则对象"""
    content = json.dumps(rules, ensure_ascii=False, sort_keys=True)
    truth_hash = sha256(f"{mr_id}|{name}|{content}|{int(time.time())}")
    return {
        "meta_law_id": mr_id,
        "name": name,
        "version": "1.0",
        "priority": priority,
        "level": "L1-公理级",
        "status": "ACTIVE",
        "locked": True,
        "immutable": True,
        "did": DID,
        "anchor": ANCHOR,
        "created_at": datetime.now().isoformat(),
        "description": description,
        "rules": rules,
        "truth_hash": truth_hash,
        "source": "steady_security_evolution_20260913",
        "evolution_context": "自攻击误判事件后进化产出，防止体系攻击自身"
    }

# ========== MR-022 自我识别元法则 ==========
mr022 = make_meta_law(
    mr_id="MR-022",
    name="自我识别元法则",
    priority="高于所有安全操作",
    description="任何安全操作前必须识别自身资产，禁止封禁/隔离自身，防止自攻击误判",
    rules=[
        "R1: 任何IP封禁/端口关闭/防火墙修改前，必须调用自我识别校验，确认目标不包含自身资产",
        "R2: 自身资产清单（出口IP/SSH密钥/监听端口/服务身份）写入9120真值库，每日更新",
        "R3: 禁止在未确认'不影响自身连通性'的情况下执行任何网络隔离操作",
        "R4: 违反本法则的安全操作视为无效，必须立即自动回滚",
        "R5: 自我识别基准真值不可删除，仅可追加更新，保留完整历史"
    ]
)

# ========== MR-023 真值锚定元法则 ==========
mr023 = make_meta_law(
    mr_id="MR-023",
    name="真值锚定元法则",
    priority="高于所有配置变更",
    description="关键配置变更必须上报9120记忆网关，无真值记录的变更视为可疑",
    rules=[
        "R1: 关键配置变更（sshd_config/iptables/nginx.conf/用户管理/密钥变更）必须上报9120",
        "R2: 上报内容包含：操作者DID+变更前SHA256+变更后SHA256+变更原因+时间戳",
        "R3: 无真值记录的配置变更视为可疑操作，触发安全告警",
        "R4: 安全事件分析必须交叉验证9120真值，不得仅依赖系统日志做判断",
        "R5: 配置变更真值不可删除，仅可追加，保留完整审计链"
    ]
)

# ========== MR-024 稳态校验元法则 ==========
mr024 = make_meta_law(
    mr_id="MR-024",
    name="稳态校验元法则",
    priority="高于所有安全操作",
    description="安全操作必须有回滚保险和灰度验证，防止操作本身破坏稳态",
    rules=[
        "R1: 所有安全操作（封禁/隔离/配置变更）必须设置5分钟自动回滚保险（at任务）",
        "R2: IP封禁先灰度单个IP，验证自身连通性无影响后再扩大范围",
        "R3: 影响范围超过1个IP的安全操作必须经人工审核确认后方可执行",
        "R4: 安全操作后必须执行连通性测试（SSH/HTTP/API），失败立即回滚",
        "R5: 回滚保险超时未确认则自动恢复，确认后需手动取消回滚任务"
    ]
)

def write_meta_law(meta_law):
    """写入元法则文件"""
    mr_id = meta_law['meta_law_id']
    filename = f"{mr_id}.{meta_law['name'].replace(' ', '_')}.DEPLOYED.json"
    filepath = os.path.join(META_LAW_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(meta_law, f, ensure_ascii=False, indent=2)
    print(f"  ✅ {mr_id} 已写入: {filepath}")
    print(f"     真值哈希: {meta_law['truth_hash']}")
    return filepath

def update_rule_set(meta_laws):
    """更新meta_rule_set.json"""
    # 解除immutable
    os.system(f'chattr -i {RULE_SET_PATH} 2>/dev/null')
    
    with open(RULE_SET_PATH, 'r', encoding='utf-8') as f:
        rule_set = json.load(f)
    
    # 更新版本
    old_version = rule_set.get('version', 'v7.1')
    rule_set['version'] = 'v7.4'
    rule_set['updated_at'] = datetime.now().isoformat()
    rule_set['update_reason'] = '写入MR-022/023/024稳态安全元法则，自攻击误判事件后进化'
    
    # 添加规则
    if 'rules' not in rule_set:
        rule_set['rules'] = []
    
    for ml in meta_laws:
        rule_set['rules'].append({
            "id": ml['meta_law_id'],
            "name": ml['name'],
            "priority": ml['priority'],
            "status": "ACTIVE",
            "truth_hash": ml['truth_hash']
        })
    
    rule_set['total_rules'] = len(rule_set['rules'])
    
    with open(RULE_SET_PATH, 'w', encoding='utf-8') as f:
        json.dump(rule_set, f, ensure_ascii=False, indent=2)
    
    # 恢复immutable
    os.system(f'chattr +i {RULE_SET_PATH} 2>/dev/null')
    
    print(f"  ✅ meta_rule_set.json 更新: {old_version} -> v7.4, 共{rule_set['total_rules']}条规则")

def push_to_gateway(meta_laws):
    """推送到9120记忆网关"""
    import urllib.request
    for ml in meta_laws:
        truth_data = {
            "key": f"meta_law.{ml['meta_law_id']}",
            "value": json.dumps(ml, ensure_ascii=False),
            "source": "steady_security_evolution",
            "did": DID,
            "anchor": ANCHOR,
            "confidence": 1.0,
            "truth_type": "meta_law",
            "version": ml['version']
        }
        try:
            req = urllib.request.Request(
                f"{GATEWAY_URL}/api/truth/upsert",
                data=json.dumps(truth_data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
                print(f"  ✅ {ml['meta_law_id']} 已推送9120: {result.get('status', 'ok')}")
        except Exception as e:
            print(f"  ⚠️ {ml['meta_law_id']} 推送失败: {e}")

if __name__ == '__main__':
    print("=" * 60)
    print("  元极恒一稳态安全元法则写入")
    print("  MR-022 自我识别 / MR-023 真值锚定 / MR-024 稳态校验")
    print("=" * 60)
    print()
    
    all_laws = [mr022, mr023, mr024]
    
    print("【1/3】写入元法则文件...")
    for ml in all_laws:
        write_meta_law(ml)
    print()
    
    print("【2/3】更新meta_rule_set.json...")
    update_rule_set(all_laws)
    print()
    
    print("【3/3】推送9120记忆网关...")
    push_to_gateway(all_laws)
    print()
    
    print("=" * 60)
    print("  ✅ 完成！MR-022/023/024已写入并推送记忆网关")
    print(f"  确权: {DID} ｜ 溯源: {ANCHOR}")
    print("=" * 60)

#!/usr/bin/env python3
"""元进化闭环 执行态：把所有算子串成一个完整闭环"""
import sys; sys.path.insert(0,'.')
from steady_scorer import score
from quality_gate import quality_gate
from fault_heal import with_retry

def evolve_round(proposal_dims, result, req):
    s, verdict = score(*proposal_dims)
    if s < 80: return {'round':'skip','reason':f'{s}分<80，继续推演'}
    passed, issues = quality_gate(result, req)
    if not passed: return {'round':'rework','issues':issues}
    out, heal = with_retry(lambda: result)
    return {'round':'landed','score':s,'verdict':verdict,'heal':heal}
if __name__ == "__main__":
    r = evolve_round((22,20,19,12,9,9), {'title':'x','content':'完整内容'}, ['title','content'])
    print(f"  闭环结果: {r}")

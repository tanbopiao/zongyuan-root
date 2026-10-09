#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 代码优化适配器
扫描体系内所有代码，用豆包模型生成优化建议，人工审核后执行
安全原则：只生成建议，不自动修改
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω | MR-055
"""
import json
import os
import re
import subprocess
import urllib.request
from datetime import datetime

BASE = "/opt/ZONGYUAN-ROOT"
REPORT_DIR = os.path.join(BASE, "reports")
AI_PROXY_API = "http://127.0.0.1:8021/v1/chat/completions"

def scan_files():
    """扫描体系内核心代码目录（只扫scripts/self-healing/kernel/engine_proxy）"""
    scan_dirs = [
        os.path.join(BASE, "scripts"),
        os.path.join(BASE, "self-healing"),
        os.path.join(BASE, "kernel"),
        os.path.join(BASE, "engine_proxy"),
    ]
    patterns = {
        'python': ('.py',),
        'shell': ('.sh',),
        'config': ('.conf', '.cfg', '.ini'),
        'systemd': ('.service',),
    }
    
    files = []
    for scan_dir in scan_dirs:
        if not os.path.exists(scan_dir):
            continue
        for root, dirs, filenames in os.walk(scan_dir):
            dirs[:] = [d for d in dirs if d not in ['__pycache__', 'backups', '.git']]
            for fname in filenames:
                fpath = os.path.join(root, fname)
                ftype = 'other'
                for ftype_name, exts in patterns.items():
                    if fname.endswith(exts):
                        ftype = ftype_name
                        break
                if ftype == 'other':
                    continue
                try:
                    size = os.path.getsize(fpath)
                    with open(fpath, 'r', errors='ignore') as f:
                        lines = f.readlines()
                    files.append({
                        'path': fpath,
                        'type': ftype,
                        'size': size,
                        'lines': len(lines),
                        'has_todo': any('TODO' in l or 'FIXME' in l for l in lines),
                        'has_exception_pass': any('except:' in l and i+1 < len(lines) and 'pass' in lines[i+1] for i, l in enumerate(lines)),
                        'has_hardcode': bool(re.search(r'(password|secret|key|token)\s*=\s*["\'][^"\']+["\']', '\n'.join(lines), re.I)),
                    })
                except:
                    pass
    return files

def prioritize(files):
    """计算优化优先级"""
    for f in files:
        score = 0
        # 大文件优先
        if f['lines'] > 200: score += 3
        elif f['lines'] > 100: score += 2
        elif f['lines'] > 50: score += 1
        # 有问题标记优先
        if f['has_todo']: score += 2
        if f['has_exception_pass']: score += 2
        if f['has_hardcode']: score += 3
        # Python脚本优先（优化空间大）
        if f['type'] == 'python': score += 1
        f['priority_score'] = score
        f['priority'] = '高' if score >= 5 else ('中' if score >= 3 else '低')
    return sorted(files, key=lambda x: -x['priority_score'])

def analyze_with_doubao(filepath, max_lines=150):
    """用豆包模型分析单个文件，生成优化建议"""
    try:
        with open(filepath, 'r', errors='ignore') as f:
            content = f.read()
        if len(content) > 8000:
            content = content[:8000] + "\n...(文件过长，已截断)"
    except:
        return None
    
    prompt = """你是资深代码优化专家。请分析以下代码，给出优化建议。

文件: %s

代码:
```
%s
```

请只输出JSON格式：
{"issues":[{"type":"性能/安全/健壮性/可读性","location":"行号或函数","description":"问题描述","suggestion":"具体优化建议"}],"overall_score":0-10,"priority":"高/中/低"}""" % (filepath, content)
    
    payload = {
        "model": "doubao",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }
    
    try:
        req = urllib.request.Request(
            AI_PROXY_API, data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            result = json.loads(r.read())
            content = result["choices"][0]["message"]["content"].strip()
            # 清理markdown
            if content.startswith("```"):
                lines = content.split("\n")
                lines = lines[1:] if lines[0].startswith("```") else lines
                lines = lines[:-1] if lines and lines[-1].strip() == "```" else lines
                content = "\n".join(lines).strip()
            return json.loads(content)
    except Exception as e:
        return {"error": str(e), "issues": [], "overall_score": 0, "priority": "低"}

def generate_report(files, analyzed):
    """生成优化报告"""
    os.makedirs(REPORT_DIR, exist_ok=True)
    report = {
        "report_id": "CODE-OPT-%s" % datetime.now().strftime("%Y%m%d_%H%M%S"),
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_files": len(files),
            "by_type": {},
            "by_priority": {"高": 0, "中": 0, "低": 0},
            "total_lines": sum(f['lines'] for f in files),
            "issues_found": 0,
            "analyzed_files": len(analyzed)
        },
        "high_priority_files": [],
        "all_files": files,
        "detailed_analysis": analyzed
    }
    
    for f in files:
        report['summary']['by_type'][f['type']] = report['summary']['by_type'].get(f['type'], 0) + 1
        report['summary']['by_priority'][f['priority']] += 1
    
    for a in analyzed:
        if a.get('issues'):
            report['summary']['issues_found'] += len(a['issues'])
    
    # 高优先级文件列表
    report['high_priority_files'] = [
        {"path": f['path'], "lines": f['lines'], "score": f['priority_score'], "issues": [i for a in analyzed if a['path']==f['path'] for i in a.get('issues',[])]}
        for f in files if f['priority'] == '高'
    ][:10]
    
    report_path = os.path.join(REPORT_DIR, "code_optimization_%s.json" % datetime.now().strftime("%Y%m%d_%H%M%S"))
    with open(report_path, 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 生成可读的Markdown报告
    md_path = os.path.join(REPORT_DIR, "code_optimization_report.md")
    with open(md_path, 'w') as f:
        f.write("# ZONGYUAN-ROOT 代码优化扫描报告\n\n")
        f.write("生成时间: %s\n\n" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        f.write("## 概览\n\n")
        f.write("- 扫描文件总数: %d\n" % report['summary']['total_files'])
        f.write("- 代码总行数: %d\n" % report['summary']['total_lines'])
        f.write("- 发现问题数: %d\n" % report['summary']['issues_found'])
        f.write("- 高优先级文件: %d个\n" % report['summary']['by_priority']['高'])
        f.write("- 中优先级文件: %d个\n" % report['summary']['by_priority']['中'])
        f.write("- 低优先级文件: %d个\n\n" % report['summary']['by_priority']['低'])
        
        f.write("## 文件类型分布\n\n")
        for ftype, count in report['summary']['by_type'].items():
            f.write("- %s: %d个\n" % (ftype, count))
        
        f.write("\n## 高优先级优化目标（TOP10）\n\n")
        for i, hf in enumerate(report['high_priority_files'], 1):
            f.write("### %d. %s\n" % (i, hf['path'].replace(BASE+'/', '')))
            f.write("- 行数: %d | 优先级分数: %d\n" % (hf['lines'], hf['score']))
            if hf['issues']:
                f.write("- 问题:\n")
                for issue in hf['issues'][:3]:
                    f.write("  - [%s] %s → %s\n" % (issue.get('type','?'), issue.get('description','')[:50], issue.get('suggestion','')[:50]))
            f.write("\n")
        
        f.write("## 详细分析\n\n")
        for a in analyzed:
            if a.get('issues'):
                f.write("### %s (评分: %d/10)\n\n" % (a['path'].replace(BASE+'/', ''), a.get('overall_score', 0)))
                for issue in a['issues']:
                    f.write("- **[%s]** %s\n  - 建议: %s\n" % (
                        issue.get('type','?'), issue.get('description',''), issue.get('suggestion','')))
                f.write("\n")
    
    return report_path, md_path

if __name__ == '__main__':
    print("=" * 60)
    print("ZONGYUAN-ROOT 代码优化适配器")
    print("=" * 60)
    
    # 1. 扫描
    print("\n【1/4】扫描代码文件...")
    files = scan_files()
    print("  找到 %d 个代码文件" % len(files))
    
    # 2. 优先级排序
    print("\n【2/4】计算优化优先级...")
    files = prioritize(files)
    high = [f for f in files if f['priority'] == '高']
    medium = [f for f in files if f['priority'] == '中']
    print("  高优先级: %d个, 中优先级: %d个, 低优先级: %d个" % (len(high), len(medium), len(files)-len(high)-len(medium)))
    
    # 3. 豆包分析高优先级文件（最多5个，控制API调用）
    print("\n【3/4】豆包模型深度分析（高优先级TOP5）...")
    analyzed = []
    for f in high[:5]:
        print("  分析: %s" % f['path'].replace(BASE+'/', ''))
        result = analyze_with_doubao(f['path'])
        if result:
            result['path'] = f['path']
            analyzed.append(result)
            print("    评分: %d/10, 问题: %d个" % (result.get('overall_score', 0), len(result.get('issues', []))))
    
    # 4. 生成报告
    print("\n【4/4】生成优化报告...")
    report_path, md_path = generate_report(files, analyzed)
    print("  JSON报告: %s" % report_path)
    print("  Markdown报告: %s" % md_path)
    
    print("\n" + "=" * 60)
    print("扫描完成！所有建议仅供参考，需人工审核后执行")
    print("MR-055 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")

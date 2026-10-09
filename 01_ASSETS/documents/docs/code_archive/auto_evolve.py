#!/usr/bin/env python3
"""
火斗云智AIOS 全自动进化巡检脚本v1.0
功能：全站扫描+低风险自动修复+报告生成
"""
import os
import re
import json
import time
import hashlib
import subprocess
from datetime import datetime

WEB_ROOT = "/www/wwwroot/huodouai.com"
REPORT_DIR = "/opt/auto-evolve/reports"
os.makedirs(REPORT_DIR, exist_ok=True)

def scan_all_pages():
    """扫描所有HTML页面"""
    pages = []
    for root, dirs, files in os.walk(WEB_ROOT):
        # 跳过隐藏目录和备份
        dirs[:] = [d for d in dirs if not d.startswith('.') and not d.startswith('_backup')]
        for f in files:
            if f.endswith('.html'):
                pages.append(os.path.join(root, f))
    return pages

def check_page_issues(page_path):
    """检查单个页面的问题"""
    issues = []
    try:
        with open(page_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查1：是否缺少统一导航
        if 'nav-unified' not in content and 'global-theme.css' not in content:
            issues.append({
                'type': 'missing_nav',
                'severity': 'low',
                'fixable': True,
                'description': '缺少统一导航组件'
            })
        
        # 检查2：是否缺少全局样式
        if 'global-theme.css' not in content:
            issues.append({
                'type': 'missing_css',
                'severity': 'low',
                'fixable': True,
                'description': '缺少全局样式引用'
            })
        
        # 检查3：是否缺少溯源标识
        if 'Ω₀' not in content and 'DID-BR-000002' not in content:
            issues.append({
                'type': 'missing_trace',
                'severity': 'medium',
                'fixable': True,
                'description': '缺少溯源标识'
            })
        
        # 检查4：是否缺少页脚
        if 'footer' not in content.lower():
            issues.append({
                'type': 'missing_footer',
                'severity': 'low',
                'fixable': True,
                'description': '缺少页脚'
            })
        
        # 检查5：是否有内部死链接（简单检查）
        internal_links = re.findall(r'href="(/[^"#]+?\.html)"', content)
        for link in internal_links:
            link_path = os.path.join(WEB_ROOT, link.lstrip('/'))
            if not os.path.exists(link_path):
                issues.append({
                    'type': 'dead_link',
                    'severity': 'low',
                    'fixable': False,
                    'link': link,
                    'description': f'死链接: {link}'
                })
    
    except Exception as e:
        issues.append({
            'type': 'read_error',
            'severity': 'high',
            'fixable': False,
            'description': f'读取失败: {str(e)}'
        })
    
    return issues

def auto_fix_issues(page_path, issues):
    """自动修复低风险问题"""
    fixes_applied = []
    try:
        with open(page_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        modified = False
        
        # 自动修复：缺少全局样式
        if any(i['type'] == 'missing_css' for i in issues):
            if '<link rel="stylesheet"' not in content:
                # 在<head>中插入全局样式
                content = re.sub(
                    r'</head>',
                    '<link rel="stylesheet" href="/global-theme.css">\n</head>',
                    content,
                    count=1
                )
                fixes_applied.append('添加全局样式引用')
                modified = True
        
        # 自动修复：缺少溯源标识
        if any(i['type'] == 'missing_trace' for i in issues):
            if 'Ω₀⊂⊙∞⊂Ω' not in content:
                # 在</body>前插入溯源
                trace_html = '''
<footer style="text-align:center;padding:20px;color:#888;font-size:12px;">
    Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 火斗云智AIOS
</footer>
'''
                content = re.sub(r'</body>', trace_html + '\n</body>', content, count=1)
                fixes_applied.append('添加溯源标识')
                modified = True
        
        if modified:
            # 备份后写入
            backup_path = page_path + '.auto_backup'
            if not os.path.exists(backup_path):
                os.system(f'cp "{page_path}" "{backup_path}"')
            with open(page_path, 'w', encoding='utf-8') as f:
                f.write(content)
    
    except Exception as e:
        fixes_applied.append(f'修复失败: {str(e)}')
    
    return fixes_applied

def main():
    print(f"=== 全自动进化巡检 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    # 1. 扫描所有页面
    print("扫描所有页面...")
    pages = scan_all_pages()
    print(f"共发现 {len(pages)} 个HTML页面")
    
    # 2. 检查每个页面
    all_issues = {}
    total_issues = 0
    for page in pages:
        rel_path = page.replace(WEB_ROOT, '')
        issues = check_page_issues(page)
        if issues:
            all_issues[rel_path] = issues
            total_issues += len(issues)
    
    print(f"共发现 {total_issues} 个问题")
    
    # 3. 自动修复低风险问题
    print("自动修复低风险问题...")
    total_fixes = 0
    for page_path_str, issues in all_issues.items():
        page_path = os.path.join(WEB_ROOT, page_path_str.lstrip('/'))
        fixable = [i for i in issues if i.get('fixable') and i['severity'] == 'low']
        if fixable:
            fixes = auto_fix_issues(page_path, fixable)
            total_fixes += len(fixes)
    
    print(f"自动修复了 {total_fixes} 个问题")
    
    # 4. 生成报告
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_pages': len(pages),
        'total_issues': total_issues,
        'auto_fixed': total_fixes,
        'issues_by_type': {},
        'pages_with_issues': len(all_issues)
    }
    
    for page, issues in all_issues.items():
        for issue in issues:
            itype = issue['type']
            report['issues_by_type'][itype] = report['issues_by_type'].get(itype, 0) + 1
    
    report_path = os.path.join(REPORT_DIR, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"报告已生成: {report_path}")
    
    # 5. 上报中枢智能
    try:
        import urllib.request
        data = json.dumps({
            'truth_key': f'AUTO_EVOLVE.REPORT.{datetime.now().strftime("%Y%m%d")}',
            'truth_value': f'全自动进化巡检完成：扫描{len(pages)}页面，发现{total_issues}问题，自动修复{total_fixes}个',
            'source_node': 'auto-evolve-cron',
            'confidence': 0.9,
            'truth_type': 'data'
        }).encode()
        req = urllib.request.Request(
            'https://www.huodouai.com/api/report/truth',
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=10)
        print("已上报中枢智能")
    except Exception as e:
        print(f"上报失败: {e}")
    
    print("=== 巡检完成 ===")

if __name__ == '__main__':
    main()

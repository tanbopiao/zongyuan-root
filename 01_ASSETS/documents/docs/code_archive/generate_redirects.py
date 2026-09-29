#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 生成Nginx 301重定向配置
# 旧URL -> 新URL

REDIRECTS = [
    # 产品中心
    ('/products.html', '/products/'),
    ('/vector.html', '/products/vector-kb.html'),
    ('/kb-saas.html', '/products/vector-kb-saas.html'),
    ('/gov-line.html', '/products/gov-ai.html'),
    ('/workbench.html', '/products/workbench.html'),
    ('/kunlun-drama.html', '/products/kunlun-drama.html'),
    ('/drama-factory.html', '/products/drama-factory.html'),
    ('/ai-gateway.html', '/products/ai-gateway.html'),
    ('/token-gateway.html', '/products/token-gateway.html'),
    ('/dlp-gateway.html', '/products/dlp-gateway.html'),
    ('/notary-api.html', '/products/notary-api.html'),
    ('/ai-asset-lock.html', '/products/ai-asset-lock.html'),
    ('/character-ai.html', '/products/character-ai.html'),
    ('/agent-network.html', '/products/agent-network.html'),
    ('/agent-studio.html', '/products/agent-studio.html'),
    ('/aios-image.html', '/products/aios-image.html'),
    ('/engines.html', '/products/engines.html'),
    ('/product-map.html', '/products/product-map.html'),
    ('/product-matrix.html', '/products/product-matrix.html'),
    
    # 解决方案
    ('/solutions.html', '/solutions/'),
    ('/cases.html', '/solutions/cases.html'),
    ('/compare.html', '/solutions/compare.html'),
    ('/roi-calculator.html', '/solutions/roi-calculator.html'),
    ('/ecosystem-line.html', '/solutions/ecosystem.html'),
    ('/content-line.html', '/solutions/content-production.html'),
    ('/education-line.html', '/solutions/education.html'),
    
    # 技术架构
    ('/architecture.html', '/architecture/'),
    ('/architecture-deep.html', '/architecture/deep-dive.html'),
    ('/microkernel-architecture.html', '/architecture/microkernel.html'),
    ('/decision-intelligence.html', '/architecture/decision-intelligence.html'),
    ('/commercial.html', '/architecture/commercial.html'),
    ('/diff.html', '/architecture/diff.html'),
    ('/safe-evolution.html', '/architecture/safe-evolution.html'),
    ('/governance.html', '/architecture/governance.html'),
    
    # 白皮书
    ('/whitepaper.html', '/whitepapers/aios-v1.html'),
    ('/high-order-state.html', '/whitepapers/high-order-state.html'),
    ('/startup-loop-defense-whitepaper.html', '/whitepapers/startup-loop-defense.html'),
    
    # 开发者文档
    ('/docs.html', '/docs/'),
    ('/developers.html', '/docs/developers.html'),
    ('/developer-center.html', '/docs/developer-center.html'),
    ('/prometheus-api-docs.html', '/docs/prometheus-api.html'),
    ('/opensource.html', '/docs/opensource.html'),
    
    # 博客
    ('/blog.html', '/blog/'),
    
    # 关于我们
    ('/about-line.html', '/about/'),
    ('/philosophy.html', '/about/philosophy.html'),
    ('/research.html', '/about/research.html'),
    ('/education.html', '/about/education.html'),
    ('/knowledge.html', '/about/knowledge.html'),
    ('/book-demo.html', '/about/book-demo.html'),
    ('/logo-design.html', '/about/logo-design.html'),
    
    # 定价
    ('/pricing.html', '/pricing/'),
    
    # 内部系统（301到internal，但internal设置了noindex）
    ('/monitor.html', '/internal/monitor.html'),
    ('/ops-monitor.html', '/internal/ops-monitor.html'),
    ('/server-monitor.html', '/internal/server-monitor.html'),
    ('/status.html', '/internal/status.html'),
    ('/status-center.html', '/internal/status-center.html'),
    ('/kernel-status.html', '/internal/kernel-status.html'),
    ('/kernel-lock-visual.html', '/internal/kernel-lock-visual.html'),
    ('/semantic-dashboard.html', '/internal/semantic-dashboard.html'),
    ('/ops-center.html', '/internal/ops-center.html'),
    ('/checker.html', '/internal/checker.html'),
    ('/drift.html', '/internal/drift.html'),
    ('/search.html', '/internal/search.html'),
    ('/demo.html', '/internal/demo.html'),
    ('/portal.html', '/internal/portal.html'),
]

def generate_nginx_config():
    lines = []
    lines.append('# ============================================================')
    lines.append('# 架构重构：旧URL 301重定向映射（阶段二）')
    lines.append('# 生成时间：2026-09-13')
    lines.append('# 共 %d 条规则' % len(REDIRECTS))
    lines.append('# ============================================================')
    lines.append('')
    
    for old, new in REDIRECTS:
        if old.endswith('.html') and new.endswith('/'):
            # 精确匹配
            lines.append('    location = %s { return 301 %s; }' % (old, new))
        elif old.endswith('.html'):
            lines.append('    location = %s { return 301 %s; }' % (old, new))
        else:
            lines.append('    location ^~ %s { return 301 %s; }' % (old, new))
    
    lines.append('')
    lines.append('    # 内部目录设置noindex')
    lines.append('    location ^~ /internal/ {')
    lines.append('        add_header X-Robots-Tag "noindex, nofollow" always;')
    lines.append('    }')
    lines.append('')
    
    return '\n'.join(lines)

if __name__ == '__main__':
    config = generate_nginx_config()
    output_path = '/tmp/redirects_phase2.conf'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(config)
    print('已生成 %d 条重定向规则' % len(REDIRECTS))
    print('输出文件: %s' % output_path)
    print()
    print(config[:500])
    print('...')

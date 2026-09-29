#!/usr/bin/env python3
"""修复/drama/作品库移动端适配"""

mobile_css = """
/* ===== 移动端适配 ===== */
@media(max-width:768px){
  .wrap{padding:12px}
  header h1{font-size:20px!important}
  header .sub{font-size:11px!important}
  .dash{grid-template-columns:repeat(2,1fr)!important;gap:8px!important}
  .metric{padding:12px 8px!important}
  .metric b{font-size:20px!important}
  .metric span{font-size:10px!important}
  .group h2{font-size:16px!important}
  .grid{grid-template-columns:repeat(2,1fr)!important;gap:8px!important}
  .vgrid{grid-template-columns:repeat(2,1fr)!important;gap:8px!important}
  .card .tag{font-size:.6rem!important;padding:4px 6px!important}
  .vcard .tag{font-size:.6rem!important;padding:4px 6px!important}
  .timeline{height:120px!important;padding:8px!important}
  .bar{min-width:32px!important}
  .col{width:16px!important}
  footer{font-size:.65rem!important}
}
@media(max-width:480px){
  .dash{grid-template-columns:1fr 1fr!important}
  .grid{grid-template-columns:repeat(2,1fr)!important;gap:6px!important}
  .vgrid{grid-template-columns:1fr!important;gap:10px!important}
  .vcard video{aspect-ratio:9/16!important}
  header h1{font-size:18px!important}
}
"""

files = [
    "/www/wwwroot/huodouai.com/drama/index.html",
    "/www/wwwroot/www.huodouai.com/drama/index.html"
]

for f in files:
    try:
        with open(f, 'r') as fh:
            content = fh.read()
        if '@media(max-width:768px)' not in content:
            content = content.replace('</style>', mobile_css + '</style>', 1)
            with open(f, 'w') as fh:
                fh.write(content)
            print(f"  ✅ {f} 已添加移动端适配")
        else:
            print(f"  ⏭️  {f} 已有移动端适配，跳过")
    except Exception as e:
        print(f"  ❌ {f} 失败: {e}")

print("\n修复完成")

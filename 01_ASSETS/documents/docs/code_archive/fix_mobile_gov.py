#!/usr/bin/env python3
"""修复/gov-ai/政务AI平台移动端适配"""

mobile_css = """
/* ===== 移动端适配（自动添加） ===== */
@media(max-width:768px){
  body{font-size:14px}
  .container,.wrap{padding:0 12px!important}
  .section-title{font-size:18px!important;margin:20px 0 12px!important}
  /* 快速入口网格 */
  .quick-grid,.grid-4,.grid-3{grid-template-columns:repeat(2,1fr)!important;gap:10px!important}
  .quick-item{padding:12px 8px!important}
  .q-icon{width:36px!important;height:36px!important;font-size:18px!important}
  .q-title{font-size:13px!important}
  .q-desc{font-size:11px!important}
  /* 引导功能 */
  .guide-grid,.features-grid{grid-template-columns:1fr!important;gap:12px!important}
  .guide-feature{padding:14px!important}
  /* FAQ */
  .faq-item{padding:12px!important}
  .faq-question{font-size:14px!important}
  .faq-answer{font-size:13px!important}
  /* 模态框 */
  .modal{padding:12px!important}
  .modal-content{max-width:100%!important;margin:10px!important}
  .modal-header{padding:12px 16px!important}
  .modal-body{padding:16px!important;max-height:60vh!important}
  /* 按钮 */
  .btn{padding:10px 18px!important;font-size:13px!important}
  .btn-group{flex-direction:column!important;gap:8px!important}
  /* 标签 */
  .label{font-size:11px!important;padding:2px 8px!important}
  /* 页面切换 */
  .page{padding:12px 0!important}
  /* 头部 */
  header,.header{padding:12px 0!important}
  .logo{font-size:18px!important}
  /* Hero */
  .hero{padding:30px 0!important}
  .hero h1{font-size:22px!important;line-height:1.3}
  .hero p{font-size:14px!important}
  /* 统计数据 */
  .stats{grid-template-columns:repeat(2,1fr)!important;gap:10px!important}
  .stat-num{font-size:24px!important}
  .stat-label{font-size:11px!important}
}
@media(max-width:480px){
  .quick-grid,.grid-4,.grid-3{grid-template-columns:1fr!important}
  .hero h1{font-size:20px!important}
  .section-title{font-size:16px!important}
}
"""

files = [
    "/www/wwwroot/huodouai.com/gov-ai/index.html",
]

for f in files:
    try:
        with open(f, 'r') as fh:
            content = fh.read()
        if '移动端适配（自动添加）' not in content:
            # 在最后一个</style>前插入
            last_style = content.rfind('</style>')
            if last_style > 0:
                content = content[:last_style] + mobile_css + content[last_style:]
                with open(f, 'w') as fh:
                    fh.write(content)
                print(f"  ✅ {f} 已添加移动端适配")
            else:
                print(f"  ⚠️  {f} 未找到</style>标签")
        else:
            print(f"  ⏭️  {f} 已有移动端适配，跳过")
    except Exception as e:
        print(f"  ❌ {f} 失败: {e}")

print("\n修复完成")

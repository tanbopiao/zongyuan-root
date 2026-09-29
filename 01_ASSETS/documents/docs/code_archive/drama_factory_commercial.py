#!/usr/bin/env python3
# 短剧工厂页面商业化优化脚本
file_path = "/www/wwwroot/huodouai.com/drama-factory.html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 要插入的商业化内容（在</body>之前）
commercial_content = '''
    <!-- ===== 数据证明板块 ===== -->
    <section class="section" style="background: linear-gradient(135deg, rgba(212,175,55,0.08) 0%, rgba(184,148,31,0.05) 100%);">
        <div class="container">
            <h2 style="text-align:center;margin-bottom:40px;">数据说话，真实可查</h2>
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:30px;text-align:center;">
                <div>
                    <div style="font-size:48px;font-weight:800;color:#d4af37;line-height:1;">2,907+</div>
                    <div style="color:#a0a0c0;margin-top:8px;">累计生成作品</div>
                </div>
                <div>
                    <div style="font-size:48px;font-weight:800;color:#d4af37;line-height:1;">90%</div>
                    <div style="color:#a0a0c0;margin-top:8px;">成本降低幅度</div>
                </div>
                <div>
                    <div style="font-size:48px;font-weight:800;color:#d4af37;line-height:1;">30<span style="font-size:24px;">分钟</span></div>
                    <div style="color:#a0a0c0;margin-top:8px;">单部短剧生成周期</div>
                </div>
                <div>
                    <div style="font-size:48px;font-weight:800;color:#d4af37;line-height:1;">5+</div>
                    <div style="color:#a0a0c0;margin-top:8px;">国风角色IP</div>
                </div>
            </div>
        </div>
    </section>

    <!-- ===== 作品库展示板块 ===== -->
    <section class="section">
        <div class="container">
            <h2 style="text-align:center;margin-bottom:16px;">真实作品，眼见为实</h2>
            <p style="text-align:center;color:#a0a0c0;margin-bottom:40px;">2,907+部作品持续产出中，点击查看完整作品库</p>
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px;margin-bottom:40px;">
                <a href="/drama/" style="background:rgba(255,255,255,0.05);border-radius:12px;padding:24px;text-decoration:none;border:1px solid rgba(255,255,255,0.1);transition:all .3s;" onmouseover="this.style.borderColor='#d4af37';this.style.transform='translateY(-4px)'" onmouseout="this.style.borderColor='rgba(255,255,255,0.1)';this.style.transform='translateY(0)'">
                    <div style="font-size:36px;margin-bottom:12px;">🎬</div>
                    <h4 style="color:#fff;margin-bottom:8px;">短剧作品库</h4>
                    <p style="color:#a0a0c0;font-size:14px;line-height:1.6;">2,907+部短剧作品，70+视频成品，2,642+张关键帧图片</p>
                    <div style="color:#d4af37;margin-top:12px;font-size:14px;font-weight:600;">查看全部作品 →</div>
                </a>
                <a href="/characters.html" style="background:rgba(255,255,255,0.05);border-radius:12px;padding:24px;text-decoration:none;border:1px solid rgba(255,255,255,0.1);transition:all .3s;" onmouseover="this.style.borderColor='#d4af37';this.style.transform='translateY(-4px)'" onmouseout="this.style.borderColor='rgba(255,255,255,0.1)';this.style.transform='translateY(0)'">
                    <div style="font-size:36px;margin-bottom:12px;">👤</div>
                    <h4 style="color:#fff;margin-bottom:8px;">角色IP宇宙</h4>
                    <p style="color:#a0a0c0;font-size:14px;line-height:1.6;">九天玄女、太阴月神、女娲等国风角色，多形态切换</p>
                    <div style="color:#d4af37;margin-top:12px;font-size:14px;font-weight:600;">探索角色宇宙 →</div>
                </a>
                <a href="/keyframe-gallery.html" style="background:rgba(255,255,255,0.05);border-radius:12px;padding:24px;text-decoration:none;border:1px solid rgba(255,255,255,0.1);transition:all .3s;" onmouseover="this.style.borderColor='#d4af37';this.style.transform='translateY(-4px)'" onmouseout="this.style.borderColor='rgba(255,255,255,0.1)';this.style.transform='translateY(0)'">
                    <div style="font-size:36px;margin-bottom:12px;">🖼️</div>
                    <h4 style="color:#fff;margin-bottom:8px;">关键帧资产库</h4>
                    <p style="color:#a0a0c0;font-size:14px;line-height:1.6;">2,642+张国风高质量关键帧，按角色/场景/风格分类</p>
                    <div style="color:#d4af37;margin-top:12px;font-size:14px;font-weight:600;">浏览关键帧 →</div>
                </a>
            </div>
        </div>
    </section>

    <!-- ===== 定价套餐板块 ===== -->
    <section class="section" style="background:rgba(0,0,0,0.2);">
        <div class="container">
            <h2 style="text-align:center;margin-bottom:16px;">选择适合你的套餐</h2>
            <p style="text-align:center;color:#a0a0c0;margin-bottom:50px;">从免费体验到企业定制，总有一款适合你</p>
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:24px;align-items:stretch;">
                <!-- 体验版 -->
                <div style="background:rgba(255,255,255,0.05);border-radius:16px;padding:32px 24px;border:1px solid rgba(255,255,255,0.1);display:flex;flex-direction:column;">
                    <h3 style="color:#fff;font-size:20px;margin-bottom:8px;">体验版</h3>
                    <div style="font-size:36px;font-weight:800;color:#fff;margin:16px 0;">免费</div>
                    <p style="color:#a0a0c0;font-size:14px;margin-bottom:24px;">适合个人尝鲜体验</p>
                    <ul style="list-style:none;padding:0;margin-bottom:32px;flex-grow:1;">
                        <li style="padding:8px 0;color:#ccc;font-size:14px;border-bottom:1px solid rgba(255,255,255,0.05);">✓ 3部短剧/月</li>
                        <li style="padding:8px 0;color:#ccc;font-size:14px;border-bottom:1px solid rgba(255,255,255,0.05);">✓ 标清输出（720P）</li>
                        <li style="padding:8px 0;color:#ccc;font-size:14px;border-bottom:1px solid rgba(255,255,255,0.05);">✓ 基础角色（3个）</li>
                        <li style="padding:8px 0;color:#ccc;font-size:14px;border-bottom:1px solid rgba(255,255,255,0.05);">✓ 1GB云存储</li>
                        <li style="padding:8px 0;color:#666;font-size:14px;">✗ 团队协作</li>
                    </ul>
                    <a href="/kunlun/" style="display:block;text-align:center;padding:12px;border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;text-decoration:none;font-weight:600;transition:all .3s;" onmouseover="this.style.borderColor='#d4af37';this.style.color='#d4af37'" onmouseout="this.style.borderColor='rgba(255,255,255,0.2)';this.style.color='#fff'">免费开始</a>
                </div>
                <!-- 专业版（推荐） -->
                <div style="background:linear-gradient(135deg,rgba(212,175,55,0.15) 0%,rgba(184,148,31,0.1) 100%);border-radius:16px;padding:32px 24px;border:2px solid #d4af37;display:flex;flex-direction:column;position:relative;transform:scale(1.03);box-shadow:0 10px 40px rgba(212,175,55,0.2);">
                    <div style="position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:linear-gradient(135deg,#d4af37,#b8941f);color:#1a1a2e;padding:4px 16px;border-radius:12px;font-size:12px;font-weight:700;">最受欢迎</div>
                    <h3 style="color:#d4af37;font-size:20px;margin-bottom:8px;">专业版</h3>
                    <div style="font-size:36px;font-weight:800;color:#fff;margin:16px 0;">¥299<span style="font-size:16px;color:#a0a0c0;font-weight:400;">/月</span></div>
                    <p style="color:#a0a0c0;font-size:14px;margin-bottom:24px;">适合自媒体创作者/小团队</p>
                    <ul style="list-style:none;padding:0;margin-bottom:32px;flex-grow:1;">
                        <li style="padding:8px 0;color:#fff;font-size:14px;border-bottom:1px solid rgba(255,255,255,0.05);">✓ 无限短剧生成</li>
                        <li style="padding:8px 0;color:#fff;font-size:14px;border-bottom:1px solid rgba(255,255,255,0.05);">✓ 高清输出（1080P）</li>
                        <li style="padding:8px 0;color:#fff;font-size:14px;border-bottom:1px solid rgba(255,255,255,0.05);">✓ 全部角色（5+个）</li>
                        <li style="padding:8px 0;color:#fff;font-size:14px;border-bottom:1px solid rgba(255,255,255,0.05);">✓ 50GB云存储</li>
                        <li style="padding:8px 0;color:#fff;font-size:14px;border-bottom:1px solid rgba(255,255,255,0.05);">✓ 批量生成</li>
                        <li style="padding:8px 0;color:#666;font-size:14px;">✗ API接入</li>
                    </ul>
                    <a href="/kunlun/" style="display:block;text-align:center;padding:12px;background:linear-gradient(135deg,#d4af37,#b8941f);border-radius:8px;color:#1a1a2e;text-decoration:none;font-weight:700;transition:all .3s;" onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 20px rgba(212,175,55,0.4)'" onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='none'">立即升级</a>
                </div>
                <!-- 团队版 -->
                <div style="background:rgba(255,255,255,0.05);border-radius:16px;padding:32px 24px;border:1px solid rgba(255,255,255,0.1);display:flex;flex-direction:column;">
                    <h3 style="color:#fff;font-size:20px;margin-bottom:8px;">团队版</h3>
                    <div style="font-size:36px;font-weight:800;color:#fff;margin:16px 0;">¥999<span style="font-size:16px;color:#a0a0c0;font-weight:400;">/月</span></div>
                    <p style="color:#a0a0c0;font-size:14px;margin-bottom:24px;">适合MCN机构/工作室</p>
                    <ul style="list-style:none;padding:0;margin-bottom:32px;flex-grow:1;">
                        <li style="padding:8px 0;color:#ccc;font-size:14px;border-bottom:1px solid rgba(255,255,255,0.05);">✓ 5个团队席位</li>
                        <li style="padding:8px 0;color:#ccc;font-size:14px;border-bottom:1px solid rgba(255,255,255,0.05);">✓ 4K超高清输出</li>
                        <li style="padding:8px 0;color:#ccc;font-size:14px;border-bottom:1px solid rgba(255,255,255,0.05);">✓ 定制角色训练</li>
                        <li style="padding:8px 0;color:#ccc;font-size:14px;border-bottom:1px solid rgba(255,255,255,0.05);">✓ 500GB云存储</li>
                        <li style="padding:8px 0;color:#ccc;font-size:14px;border-bottom:1px solid rgba(255,255,255,0.05);">✓ API接入</li>
                        <li style="padding:8px 0;color:#ccc;font-size:14px;">✓ 团队协作管理</li>
                    </ul>
                    <a href="/book-demo.html" style="display:block;text-align:center;padding:12px;border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;text-decoration:none;font-weight:600;transition:all .3s;" onmouseover="this.style.borderColor='#d4af37';this.style.color='#d4af37'" onmouseout="this.style.borderColor='rgba(255,255,255,0.2)';this.style.color='#fff'">预约演示</a>
                </div>
                <!-- 企业版 -->
                <div style="background:rgba(255,255,255,0.05);border-radius:16px;padding:32px 24px;border:1px solid rgba(255,255,255,0.1);display:flex;flex-direction:column;">
                    <h3 style="color:#fff;font-size:20px;margin-bottom:8px;">企业版</h3>
                    <div style="font-size:36px;font-weight:800;color:#fff;margin:16px 0;">¥5000<span style="font-size:16px;color:#a0a0c0;font-weight:400;">/月起</span></div>
                    <p style="color:#a0a0c0;font-size:14px;margin-bottom:24px;">适合影视公司/平台</p>
                    <ul style="list-style:none;padding:0;margin-bottom:32px;flex-grow:1;">
                        <li style="padding:8px 0;color:#ccc;font-size:14px;border-bottom:1px solid rgba(255,255,255,0.05);">✓ 无限团队席位</li>
                        <li style="padding:8px 0;color:#ccc;font-size:14px;border-bottom:1px solid rgba(255,255,255,0.05);">✓ 私有化部署</li>
                        <li style="padding:8px 0;color:#ccc;font-size:14px;border-bottom:1px solid rgba(255,255,255,0.05);">✓ 专属模型训练</li>
                        <li style="padding:8px 0;color:#ccc;font-size:14px;border-bottom:1px solid rgba(255,255,255,0.05);">✓ 无限云存储</li>
                        <li style="padding:8px 0;color:#ccc;font-size:14px;border-bottom:1px solid rgba(255,255,255,0.05);">✓ 99.9% SLA保障</li>
                        <li style="padding:8px 0;color:#ccc;font-size:14px;">✓ 专属技术支持</li>
                    </ul>
                    <a href="/book-demo.html" style="display:block;text-align:center;padding:12px;border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;text-decoration:none;font-weight:600;transition:all .3s;" onmouseover="this.style.borderColor='#d4af37';this.style.color='#d4af37'" onmouseout="this.style.borderColor='rgba(255,255,255,0.2)';this.style.color='#fff'">联系销售</a>
                </div>
            </div>
            <p style="text-align:center;color:#666;font-size:13px;margin-top:30px;">年付享8折优惠 · 支持支付宝/微信/对公转账 · 7天无理由退款</p>
        </div>
    </section>

    <!-- ===== 底部CTA板块 ===== -->
    <section class="section" style="background:linear-gradient(135deg,rgba(212,175,55,0.1) 0%,rgba(184,148,31,0.05) 100%);text-align:center;">
        <div class="container">
            <h2 style="margin-bottom:16px;">准备好开启你的AI短剧之旅了吗？</h2>
            <p style="color:#a0a0c0;margin-bottom:40px;font-size:18px;">免费体验3部短剧，无需信用卡，立即开始</p>
            <div style="display:flex;gap:20px;justify-content:center;flex-wrap:wrap;">
                <a href="/kunlun/" class="btn btn-gold" style="padding:16px 48px;font-size:18px;">🚀 免费开始创作</a>
                <a href="/book-demo.html" class="btn btn-outline" style="padding:16px 48px;font-size:18px;">📅 预约产品演示</a>
            </div>
            <p style="color:#666;margin-top:30px;font-size:14px;">已有 <strong style="color:#d4af37;">2,907+</strong> 部作品通过昆仑洞天生成</p>
        </div>
    </section>
'''

# 在</body>之前插入商业化内容
if "</body>" in content:
    content = content.replace("</body>", commercial_content + "\n</body>")
    print("✅ 已插入商业化内容（数据证明+作品库+定价套餐+底部CTA）")
else:
    print("⚠️ 未找到</body>标签")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\n✅ 短剧工厂页面商业化优化完成！")
print("  - 数据证明板块：2907+作品/90%成本降低/30分钟周期/5+角色IP")
print("  - 作品库展示板块：短剧作品库/角色IP宇宙/关键帧资产库")
print("  - 定价套餐板块：体验版(免费)/专业版(299元)/团队版(999元)/企业版(5000元起)")
print("  - 底部CTA板块：免费开始创作+预约产品演示")

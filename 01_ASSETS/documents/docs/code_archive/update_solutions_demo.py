
with open("/www/wwwroot/aios.huodouai.com/solutions.html", "r") as f:
    content = f.read()

# 在政务卡片里加体验按钮
old_gov_card = """            <!-- 政务 -->
            <div class="solution-card">
                <div class="solution-icon">🏛️</div>
                <div class="solution-name">政务AI助手</div>
                <div class="solution-desc">
                    政务咨询、政策解答、办事指南，7×24小时在线
                </div>
                <ul class="solution-features">
                    <li class="solution-feature">政策法规知识库</li>
                    <li class="solution-feature">办事流程指引</li>
                    <li class="solution-feature">敏感内容审核</li>
                    <li class="solution-feature">全链路可审计</li>
                    <li class="solution-feature">私有化部署</li>
                </ul>
            </div>"""

new_gov_card = """            <!-- 政务 -->
            <div class="solution-card">
                <div class="solution-icon">🏛️</div>
                <div class="solution-name">政务AI助手</div>
                <div class="solution-desc">
                    政务咨询、政策解答、办事指南，7×24小时在线
                </div>
                <ul class="solution-features">
                    <li class="solution-feature">政策法规知识库</li>
                    <li class="solution-feature">办事流程指引</li>
                    <li class="solution-feature">敏感内容审核</li>
                    <li class="solution-feature">全链路可审计</li>
                    <li class="solution-feature">私有化部署</li>
                </ul>
                <div style="margin-top: 24px; text-align: center;">
                    <a href="/gov-ai.html" style="display: inline-block; padding: 10px 24px; background: #c8102e; color: #fff; text-decoration: none; border-radius: 8px; font-weight: 500;">
                        🚀 立即体验Demo
                    </a>
                </div>
            </div>"""

content = content.replace(old_gov_card, new_gov_card)

with open("/tmp/solutions_with_demo.html", "w") as f:
    f.write(content)
print("✅ Demo链接已添加到解决方案页")

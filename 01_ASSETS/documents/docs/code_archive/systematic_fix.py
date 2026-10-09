import re

with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 修复1: 所有 works-grid 改成 gallery-grid
content = content.replace('getElementById("works-grid")', 'getElementById("gallery-grid")')
print("✅ 修复1: works-grid -> gallery-grid (2处)")

# 修复2: 添加 createWorkCard 函数
# 先检查是否已存在
if "function createWorkCard" not in content:
    # 在 loadMoreWorks 函数前面添加 createWorkCard 函数
    create_work_card_func = '''function createWorkCard(work) {
  const card = document.createElement("div");
  card.className = "work-card";
  card.onclick = () => handleWorkClick(work);
  
  let html = '<img class="work-card-thumbnail" src="' + (work.thumbnail || "") + '" alt="' + (work.title || "") + '" loading="lazy">';
  html += '<div class="work-card-badge">' + (work.category || work.type || "") + '</div>';
  if (work.type === "video") html += '<div class="work-card-play"></div>';
  html += '<div class="work-card-overlay"><div class="work-card-title">' + (work.title || "") + '</div>';
  html += '<div class="work-card-meta">' + (work.character || "") + ' · ' + (work.type === "video" ? "视频" : "图片") + '</div></div>';
  card.innerHTML = html;
  
  return card;
}

'''
    # 在 loadMoreWorks 前面插入
    content = content.replace("function loadMoreWorks(works) {", create_work_card_func + "function loadMoreWorks(works) {")
    print("✅ 修复2: 已添加 createWorkCard 函数")
else:
    print("ℹ️ createWorkCard 函数已存在")

# 写入文件
with open("/www/wwwroot/huodouai.com/drama/gallery/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print(f"\n文件大小: {len(content)} 字符")

# 验证JavaScript语法
scripts = re.findall(r"<script[^>]*>(.*?)</script>", content, re.DOTALL)
if scripts:
    with open("/tmp/final_js.js", "w", encoding="utf-8") as f:
        f.write(scripts[0])
    print(f"JavaScript大小: {len(scripts[0])} 字符")

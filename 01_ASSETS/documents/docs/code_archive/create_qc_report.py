import json
import os

# 读取质检结果
qc_file = "/www/wwwroot/huodouai.com/drama/qc_results.json"
with open(qc_file, "r", encoding="utf-8") as f:
    qc_data = json.load(f)

total_checked = qc_data.get("total_checked", 0)
passed_count = qc_data.get("passed_count", 0)
failed_count = qc_data.get("failed_count", 0)
pass_rate = round(passed_count / total_checked * 100, 1) if total_checked > 0 else 0

# 生成通过和未通过的作品列表HTML
passed_items = ""
failed_items = ""

for filename, result in qc_data.get("results", {}).items():
    quality_score = result.get("quality_score", 0)
    has_multi_hand = result.get("has_multi_hand", False)
    has_deformity = result.get("has_deformity", False)
    issues = result.get("issues", [])
    checked_at = result.get("checked_at", "")
    
    issues_text = ", ".join(issues) if issues else "无"
    
    score_class = "score-pass" if quality_score >= 70 else "score-fail"
    multi_hand_text = "❌ 存在" if has_multi_hand else "✅ 无"
    deformity_text = "❌ 存在" if has_deformity else "✅ 无"
    
    item_html = f"""
    <div class="qc-item">
      <div class="qc-item-header">
        <span class="qc-item-name">{filename}</span>
        <span class="qc-item-score {score_class}">{quality_score}分</span>
      </div>
      <div class="qc-item-details">
        <span>多手问题: {multi_hand_text}</span>
        <span>肢体畸形: {deformity_text}</span>
        <span>问题: {issues_text}</span>
        <span>检测时间: {checked_at}</span>
      </div>
    </div>
    """
    
    if result.get("passed", False):
        passed_items += item_html
    else:
        failed_items += item_html

# 质检报告页面HTML
qc_report_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>质检报告 · 昆仑洞天 | 火斗云智AIOS</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    :root {{
      --gold-primary: #d4af37;
      --gold-light: #f5e6a3;
      --gold-dark: #b8941f;
      --bg-primary: #050508;
      --bg-secondary: #0a0a10;
      --bg-card: rgba(20, 15, 10, 0.6);
      --border-color: rgba(212, 175, 55, 0.2);
      --text-primary: #f0e6d2;
      --text-secondary: #a89880;
      --text-muted: #6b5d4f;
    }}
    body {{
      font-family: "Noto Serif SC", "PingFang SC", "Microsoft YaHei", serif;
      background: var(--bg-primary);
      color: var(--text-primary);
      line-height: 1.8;
      padding-top: 56px;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
    .page-header {{ text-align: center; margin-bottom: 40px; }}
    .page-title {{ font-size: 36px; font-weight: 900; background: linear-gradient(135deg, var(--gold-light), var(--gold-primary), var(--gold-dark)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px; }}
    .page-subtitle {{ color: var(--text-secondary); font-size: 15px; }}
    .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 40px; }}
    .stat-card {{ background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 24px; text-align: center; transition: all 0.3s; }}
    .stat-card:hover {{ border-color: var(--gold-primary); transform: translateY(-2px); }}
    .stat-value {{ font-size: 42px; font-weight: 900; color: var(--gold-primary); margin-bottom: 8px; }}
    .stat-label {{ font-size: 13px; color: var(--text-secondary); }}
    .stat-pass .stat-value {{ color: #27ae60; }}
    .stat-fail .stat-value {{ color: #e74c3c; }}
    .progress-bar {{ width: 100%; height: 12px; background: var(--bg-secondary); border-radius: 6px; overflow: hidden; margin-top: 12px; }}
    .progress-fill {{ height: 100%; background: linear-gradient(90deg, var(--gold-dark), var(--gold-light)); border-radius: 6px; transition: width 1s; }}
    .section {{ margin-bottom: 40px; }}
    .section-title {{ font-size: 22px; font-weight: 700; color: var(--gold-primary); margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }}
    .section-title::before {{ content: ""; width: 4px; height: 24px; background: linear-gradient(180deg, var(--gold-primary), var(--gold-dark)); border-radius: 2px; }}
    .qc-list {{ display: flex; flex-direction: column; gap: 12px; }}
    .qc-item {{ background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 16px 20px; transition: all 0.3s; }}
    .qc-item:hover {{ border-color: var(--gold-primary); }}
    .qc-item-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
    .qc-item-name {{ font-size: 15px; font-weight: 600; color: var(--text-primary); word-break: break-all; }}
    .qc-item-score {{ font-size: 16px; font-weight: 700; padding: 4px 12px; border-radius: 12px; }}
    .score-pass {{ background: rgba(39,174,96,0.15); color: #27ae60; }}
    .score-fail {{ background: rgba(231,76,60,0.15); color: #e74c3c; }}
    .qc-item-details {{ display: flex; flex-wrap: wrap; gap: 16px; font-size: 12px; color: var(--text-secondary); }}
    .qc-item-details span {{ white-space: nowrap; }}
    .engine-status {{ background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 24px; margin-bottom: 40px; }}
    .engine-status-row {{ display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid rgba(212,175,55,0.1); }}
    .engine-status-row:last-child {{ border-bottom: none; }}
    .engine-status-label {{ color: var(--text-secondary); font-size: 14px; }}
    .engine-status-value {{ color: var(--gold-primary); font-size: 14px; font-weight: 600; }}
    .status-running {{ color: #27ae60; }}
    @media (max-width: 768px) {{
      .page-title {{ font-size: 28px; }}
      .stat-value {{ font-size: 32px; }}
      .qc-item-details {{ flex-direction: column; gap: 6px; }}
    }}
  </style>
</head>
<body>
  <!-- 统一导航栏 -->
  <style>
  .zy-unified-nav {{ position: fixed; top: 0; left: 0; right: 0; z-index: 9999; background: rgba(5, 5, 8, 0.95); backdrop-filter: blur(10px); border-bottom: 1px solid rgba(212, 175, 55, 0.2); padding: 0 20px; height: 56px; display: flex; align-items: center; justify-content: space-between; font-family: "Noto Serif SC", "PingFang SC", "Microsoft YaHei", serif; }}
  .zy-nav-logo {{ display: flex; align-items: center; gap: 10px; text-decoration: none; color: #d4af37; font-size: 18px; font-weight: 700; }}
  .zy-nav-logo-icon {{ width: 32px; height: 32px; background: linear-gradient(135deg, #d4af37, #b8941f); border-radius: 6px; display: flex; align-items: center; justify-content: center; color: #050508; font-size: 16px; font-weight: 900; }}
  .zy-nav-links {{ display: flex; align-items: center; gap: 24px; list-style: none; margin: 0; padding: 0; }}
  .zy-nav-links a {{ color: #a89880; text-decoration: none; font-size: 14px; transition: color 0.3s; white-space: nowrap; }}
  .zy-nav-links a:hover {{ color: #d4af37; }}
  .zy-nav-toggle {{ display: none; background: none; border: none; color: #d4af37; font-size: 24px; cursor: pointer; padding: 8px; }}
  .zy-nav-mobile {{ display: none; position: fixed; top: 56px; left: 0; right: 0; background: rgba(5, 5, 8, 0.98); border-bottom: 1px solid rgba(212, 175, 55, 0.2); padding: 16px 20px; z-index: 9998; }}
  .zy-nav-mobile a {{ display: block; padding: 12px 0; color: #a89880; text-decoration: none; font-size: 15px; border-bottom: 1px solid rgba(212, 175, 55, 0.1); }}
  .zy-nav-mobile a:last-child {{ border-bottom: none; }}
  .zy-nav-mobile a:hover {{ color: #d4af37; }}
  @media (max-width: 768px) {{ .zy-nav-links {{ display: none; }} .zy-nav-toggle {{ display: block; }} .zy-nav-mobile.open {{ display: block; }} }}
  </style>
  <nav class="zy-unified-nav">
    <a href="https://www.huodouai.com/" class="zy-nav-logo"><div class="zy-nav-logo-icon">昆</div><span>火斗云智AIOS</span></a>
    <ul class="zy-nav-links">
      <li><a href="https://www.huodouai.com/">首页</a></li>
      <li><a href="https://www.huodouai.com/drama/">作品库</a></li>
      <li><a href="https://www.huodouai.com/drama/characters/">角色宇宙</a></li>
      <li><a href="https://www.huodouai.com/drama/pipeline.html">生产流水线</a></li>
      <li><a href="https://www.huodouai.com/drama/qc-report.html" style="color:#d4af37;">质检报告</a></li>
      <li><a href="https://www.huodouai.com/gov/">政务AI</a></li>
    </ul>
    <button class="zy-nav-toggle" onclick="document.querySelector('.zy-nav-mobile').classList.toggle('open')">☰</button>
  </nav>
  <div class="zy-nav-mobile">
    <a href="https://www.huodouai.com/">首页</a>
    <a href="https://www.huodouai.com/drama/">作品库</a>
    <a href="https://www.huodouai.com/drama/characters/">角色宇宙</a>
    <a href="https://www.huodouai.com/drama/pipeline.html">生产流水线</a>
    <a href="https://www.huodouai.com/drama/qc-report.html">质检报告</a>
    <a href="https://www.huodouai.com/gov/">政务AI</a>
  </div>

  <div class="container">
    <div class="page-header">
      <h1 class="page-title">自动视觉质检报告</h1>
      <p class="page-subtitle">昆仑洞天AI创世宇宙 · 全自动质量检测系统 · 智谱GLM-4V-Flash</p>
    </div>

    <!-- 质检引擎状态 -->
    <div class="engine-status">
      <div class="engine-status-row">
        <span class="engine-status-label">质检引擎状态</span>
        <span class="engine-status-value status-running">● 运行中 (zongyuan-auto-qc.service)</span>
      </div>
      <div class="engine-status-row">
        <span class="engine-status-label">质检模型</span>
        <span class="engine-status-value">智谱GLM-4V-Flash (免费)</span>
      </div>
      <div class="engine-status-row">
        <span class="engine-status-label">检测维度</span>
        <span class="engine-status-value">多手问题 / 肢体畸形 / 面部质量 / 清晰度 / AI瑕疵</span>
      </div>
      <div class="engine-status-row">
        <span class="engine-status-label">扫描频率</span>
        <span class="engine-status-value">每10分钟自动扫描新作品</span>
      </div>
      <div class="engine-status-row">
        <span class="engine-status-label">问题文件处理</span>
        <span class="engine-status-value">自动归档隔离 (不删除，保留溯源)</span>
      </div>
    </div>

    <!-- 统计数据 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{total_checked}</div>
        <div class="stat-label">总检测作品</div>
      </div>
      <div class="stat-card stat-pass">
        <div class="stat-value">{passed_count}</div>
        <div class="stat-label">质检通过</div>
      </div>
      <div class="stat-card stat-fail">
        <div class="stat-value">{failed_count}</div>
        <div class="stat-label">质检未通过</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{pass_rate}%</div>
        <div class="stat-label">通过率</div>
        <div class="progress-bar"><div class="progress-fill" style="width: {pass_rate}%"></div></div>
      </div>
    </div>

    <!-- 质检未通过的作品 -->
    <div class="section">
      <h2 class="section-title">质检未通过的作品 ({failed_count})</h2>
      <div class="qc-list">
        {failed_items if failed_items else '<div style="text-align:center;padding:40px;color:var(--text-muted);">暂无未通过的作品</div>'}
      </div>
    </div>

    <!-- 质检通过的作品 -->
    <div class="section">
      <h2 class="section-title">质检通过的作品 ({passed_count})</h2>
      <div class="qc-list">
        {passed_items if passed_items else '<div style="text-align:center;padding:40px;color:var(--text-muted);">暂无通过的作品</div>'}
      </div>
    </div>
  </div>
</body>
</html>"""

# 写入文件
output_path = "/www/wwwroot/huodouai.com/drama/qc-report.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(qc_report_html)

print("✅ 质检报告页面已创建")
print("  总检测:", total_checked)
print("  通过:", passed_count)
print("  未通过:", failed_count)
print("  通过率:", pass_rate, "%")
print("  输出文件:", output_path)

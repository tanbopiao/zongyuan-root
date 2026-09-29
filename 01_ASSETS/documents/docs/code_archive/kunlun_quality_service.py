#!/usr/bin/env python3
"""
昆仑洞天作品质检服务 v1.0
功能：
1. 新作品自动质检（监听目录变化）
2. 每周全量复检
3. 不合格作品自动移入冷库
4. 质检报告生成与推送
"""

import requests
import base64
import json
import os
import time
import shutil
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

# ============ 配置 ============
ZHIPU_API_KEY = "1dfafcccce4e483287fe39bcdea7691c.78z9iYwdDTRiquIk"
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
MODEL = "glm-4v-flash"

# 作品目录
WORKS_DIRS = [
    "/www/wwwroot/huodouai.com/drama/keyframes",
    "/www/wwwroot/huodouai.com/drama/gallery/keyframes",
    "/www/wwwroot/huodouai.com/drama/videos",
]

# 冷库目录
COLD_STORAGE_DIR = "/www/wwwroot/huodouai.com/drama/_archive_low_quality"

# 报告目录
REPORT_DIR = "/www/wwwroot/huodouai.com/drama/_quality_reports"

# 质检状态文件
STATE_FILE = "/opt/ZONGYUAN-ROOT/services/quality_checker/state.json"

# 质检通过线
PASS_SCORE = 70
MIN_DIMENSION_SCORE = 50

# 昆仑洞天质检提示词
QUALITY_PROMPT = """质检这张昆仑洞天东方神话AI作品。输出JSON：
{"overall_score":0-100,"image_quality":0-100,"character_consistency":0-100,"composition_aesthetics":0-100,"story_expression":0-100,"technical_completeness":0-100,"character_detected":"角色名","has_issues":true/false,"issues":["问题"],"pass":true/false}
维度：画面质量/角色一致(玄女银甲红缨/月神月白玄黑)/构图美学/剧情表达/技术完整(无多手扭曲)。只输出JSON。"""

# ============ 工具函数 ============

def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def get_file_hash(filepath):
    """计算文件SHA256哈希"""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def load_state():
    """加载质检状态"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"checked_files": {}, "last_full_check": None}

def save_state(state):
    """保存质检状态"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def check_image_quality(image_path):
    """质检单张图片"""
    image_base64 = encode_image(image_path)
    try:
        response = requests.post(
            f"{ZHIPU_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {ZHIPU_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": QUALITY_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]}],
                "max_tokens": 1024,
                "temperature": 0.1
            },
            timeout=45
        )
        result = response.json()
        if "choices" in result:
            content = result["choices"][0]["message"]["content"]
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(content[json_start:json_end])
        return {"overall_score": 0, "pass": False, "issues": ["API解析失败"]}
    except Exception as e:
        return {"overall_score": 0, "pass": False, "issues": [f"请求失败: {str(e)}"]}

def move_to_cold_storage(filepath, reason):
    """将不合格作品移入冷库"""
    filename = os.path.basename(filepath)
    # 创建按日期分类的冷库目录
    date_dir = os.path.join(COLD_STORAGE_DIR, datetime.now().strftime("%Y%m%d"))
    os.makedirs(date_dir, exist_ok=True)
    
    dest = os.path.join(date_dir, filename)
    shutil.move(filepath, dest)
    
    # 记录移动原因
    reason_file = os.path.join(date_dir, f"{filename}.reason.txt")
    with open(reason_file, "w") as f:
        f.write(f"文件: {filepath}\n")
        f.write(f"移动时间: {datetime.now().isoformat()}\n")
        f.write(f"原因: {reason}\n")
    
    return dest

def scan_new_files(state):
    """扫描新增/变更的文件"""
    new_files = []
    for works_dir in WORKS_DIRS:
        if not os.path.exists(works_dir):
            continue
        for root, dirs, files in os.walk(works_dir):
            # 跳过冷库目录
            if "_archive_low_quality" in root or "_quality_reports" in root:
                continue
            for f in files:
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    filepath = os.path.join(root, f)
                    file_hash = get_file_hash(filepath)
                    # 检查是否是新文件或已变更
                    if filepath not in state["checked_files"] or state["checked_files"][filepath].get("hash") != file_hash:
                        new_files.append(filepath)
    return new_files

def generate_report(results, mode="incremental"):
    """生成质检报告"""
    os.makedirs(REPORT_DIR, exist_ok=True)
    
    passed = sum(1 for r in results if r.get("pass"))
    failed = len(results) - passed
    avg_score = sum(r.get("overall_score", 0) for r in results) // len(results) if results else 0
    
    report = {
        "report_time": datetime.now().isoformat(),
        "mode": mode,
        "model": MODEL,
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{passed*100//len(results)}%" if results else "0%",
        "avg_score": avg_score,
        "results": results
    }
    
    report_file = os.path.join(REPORT_DIR, f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report, report_file

# ============ 主流程 ============

def run_incremental_check():
    """增量质检：只检查新增/变更的文件"""
    print(f"[{datetime.now().isoformat()}] 开始增量质检...")
    
    state = load_state()
    new_files = scan_new_files(state)
    
    if not new_files:
        print("  没有新增/变更文件，跳过质检")
        return None
    
    print(f"  发现 {len(new_files)} 个新增/变更文件")
    
    results = []
    for filepath in new_files:
        filename = os.path.basename(filepath)
        print(f"  质检: {filename}")
        
        result = check_image_quality(filepath)
        result["filepath"] = filepath
        result["filename"] = filename
        result["check_time"] = datetime.now().isoformat()
        result["file_hash"] = get_file_hash(filepath)
        
        score = result.get("overall_score", 0)
        passed = result.get("pass", False)
        
        if not passed or score < PASS_SCORE:
            reason = f"综合评分{score}分，低于通过线{PASS_SCORE}分。问题: {result.get('issues', [])}"
            print(f"    ❌ 不通过 ({score}分)，移入冷库")
            cold_path = move_to_cold_storage(filepath, reason)
            result["moved_to_cold"] = cold_path
        else:
            print(f"    ✅ 通过 ({score}分)")
        
        # 更新状态
        state["checked_files"][filepath] = {
            "hash": result["file_hash"],
            "score": score,
            "pass": passed,
            "check_time": result["check_time"]
        }
        
        results.append(result)
        time.sleep(1)  # 避免限流
    
    save_state(state)
    report, report_file = generate_report(results, mode="incremental")
    
    print(f"\n增量质检完成: 通过{report['passed']}/{report['total']}，平均分{report['avg_score']}")
    print(f"报告已保存: {report_file}")
    
    return report

def run_full_check():
    """全量复检：检查所有正式作品"""
    print(f"[{datetime.now().isoformat()}] 开始全量复检...")
    
    state = load_state()
    
    # 扫描所有正式作品
    all_files = []
    for works_dir in WORKS_DIRS:
        if not os.path.exists(works_dir):
            continue
        for root, dirs, files in os.walk(works_dir):
            if "_archive_low_quality" in root or "_quality_reports" in root:
                continue
            for f in files:
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    all_files.append(os.path.join(root, f))
    
    print(f"  发现 {len(all_files)} 个正式作品")
    
    results = []
    for filepath in all_files:
        filename = os.path.basename(filepath)
        print(f"  复检: {filename}")
        
        result = check_image_quality(filepath)
        result["filepath"] = filepath
        result["filename"] = filename
        result["check_time"] = datetime.now().isoformat()
        result["file_hash"] = get_file_hash(filepath)
        
        score = result.get("overall_score", 0)
        passed = result.get("pass", False)
        
        if not passed or score < PASS_SCORE:
            reason = f"全量复检综合评分{score}分，低于通过线{PASS_SCORE}分。问题: {result.get('issues', [])}"
            print(f"    ❌ 不通过 ({score}分)，移入冷库")
            cold_path = move_to_cold_storage(filepath, reason)
            result["moved_to_cold"] = cold_path
            # 从状态中移除
            if filepath in state["checked_files"]:
                del state["checked_files"][filepath]
        else:
            print(f"    ✅ 通过 ({score}分)")
            state["checked_files"][filepath] = {
                "hash": result["file_hash"],
                "score": score,
                "pass": passed,
                "check_time": result["check_time"]
            }
        
        results.append(result)
        time.sleep(1)
    
    state["last_full_check"] = datetime.now().isoformat()
    save_state(state)
    
    report, report_file = generate_report(results, mode="full")
    
    print(f"\n全量复检完成: 通过{report['passed']}/{report['total']}，平均分{report['avg_score']}")
    print(f"报告已保存: {report_file}")
    
    return report

# ============ 入口 ============

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        run_full_check()
    else:
        run_incremental_check()

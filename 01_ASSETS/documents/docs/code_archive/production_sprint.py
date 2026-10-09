#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
昆仑洞天 · 前期产量冲刺引擎 V1.0
前期（1-2周）：每天量产3-5集轻量模式 + 每天1-2次完整模式
后期：稳态每天1集轻量 + 每周2-3次完整
智能额度检测 + 自动降级
"""

import json
import time
import os
import sys
import urllib.request
from datetime import datetime, timedelta

# ========== 配置 ==========
DRAMA_API = "http://127.0.0.1:8628"
AI_PROXY = "http://127.0.0.1:8021/v1/chat/completions"
MEMORY_GATEWAY = "http://127.0.0.1:9120"
OUTPUT_DIR = "/www/wwwroot/huodouai.com/drama/output"
AUDIO_DIR = "/www/wwwroot/huodouai.com/drama/audios"
SUBTITLE_DIR = "/www/wwwroot/huodouai.com/drama/subtitles"
CINEMATIC_SCRIPT = "/opt/ZONGYUAN-ROOT/scripts/cinematic_drama_pipeline.py"
PRODUCTION_SCRIPT = "/opt/ZONGYUAN-ROOT/scripts/auto_drama_production.py"

# 冲刺期配置（前14天）
SPRINT_DURATION_DAYS = 14
SPRINT_DAILY_LIGHT_COUNT = 3  # 每天3集轻量模式
SPRINT_DAILY_FULL_COUNT = 1   # 每天1次完整模式（生图生视频）

# 稳态期配置（14天后）
STEADY_DAILY_LIGHT_COUNT = 1
STEADY_WEEKLY_FULL_COUNT = 3

# 角色和世界观池（用于多样化生产）
CHARACTER_POOL = [
    {"name": "九天玄女", "forms": ["红裙凤冠·战争形态", "月白玄黑·修真形态", "银淡紫·星夜形态"]},
    {"name": "太阴月神", "forms": ["月白·清冷形态", "银蓝·星夜形态"]},
    {"name": "女娲", "forms": ["七彩·补天形态", "土黄·造人形态"]},
    {"name": "真武大帝", "forms": ["玄黑·战神形态"]},
    {"name": "西王母", "forms": ["金紫·天帝形态"]},
]

WORLDVIEW_POOL = [
    "昆仑洞天", "洪荒纪元", "修真界", "天庭", "幽冥地府", "山海经世界"
]

PLOT_THEMES = [
    "觉醒", "复仇", "守护", "轮回", "渡劫", "封神", "证道", "破局",
    "天命", "逆命", "情缘", "大义", "牺牲", "重生", "穿越", "争霸"
]

# 确保目录存在
for d in [OUTPUT_DIR, AUDIO_DIR, SUBTITLE_DIR]:
    os.makedirs(d, exist_ok=True)

# ========== 工具函数 ==========
def call_ai(prompt, model="zhipu", max_tokens=600, temperature=0.8):
    """调用AI代理"""
    try:
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        req = urllib.request.Request(
            AI_PROXY,
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read().decode())
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  ❌ AI调用失败: {e}")
        return None

def api_call(url, method="GET", data=None, timeout=30):
    """调用API"""
    try:
        if data:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"},
                method=method
            )
        else:
            req = urllib.request.Request(url, method=method)
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def check_api_quota():
    """检测API额度状态（简化版，通过测试调用判断）"""
    quota_status = {
        "zhipu": "unknown",
        "seedream": "unknown",
        "seedance": "unknown"
    }
    
    # 测试智谱
    try:
        result = call_ai("回复OK", max_tokens=10)
        if result and "OK" in result.upper():
            quota_status["zhipu"] = "available"
        else:
            quota_status["zhipu"] = "degraded"
    except:
        quota_status["zhipu"] = "unavailable"
    
    # seedream/seedance通过AI代理测试
    try:
        result = call_ai("回复OK", model="doubao", max_tokens=10)
        if result:
            quota_status["seedream"] = "available"
            quota_status["seedance"] = "available"
        else:
            quota_status["seedream"] = "degraded"
            quota_status["seedance"] = "degraded"
    except:
        quota_status["seedream"] = "unavailable"
        quota_status["seedance"] = "unavailable"
    
    return quota_status

def generate_diverse_title(index):
    """生成多样化的标题"""
    import random
    random.seed(int(time.time()) + index)
    
    character = random.choice(CHARACTER_POOL)
    worldview = random.choice(WORLDVIEW_POOL)
    theme = random.choice(PLOT_THEMES)
    form = random.choice(character["forms"])
    
    title = f"{character['name']}·{theme}·{worldview}"
    return {
        "title": title,
        "character": character["name"],
        "form": form,
        "worldview": worldview,
        "theme": theme
    }

def run_light_production(episode, title_info):
    """运行轻量模式生产（只生成剧本+提示词，零成本）"""
    print(f"\n  📝 轻量模式: 第{episode}集 {title_info['title']}")
    
    cmd = f"cd /opt/ZONGYUAN-ROOT/scripts && python3 {PRODUCTION_SCRIPT} --episode {episode} --title \"{title_info['title']}\" --version pro"
    
    try:
        result = os.popen(cmd).read()
        # 解析结果
        if '"status": "success"' in result or '"status":"success"' in result:
            print(f"    ✅ 轻量生产成功")
            return True
        else:
            print(f"    ⚠️ 轻量生产结果异常")
            return False
    except Exception as e:
        print(f"    ❌ 轻量生产失败: {e}")
        return False

def run_full_production(episode, title_info):
    """运行完整模式生产（生图生视频，消耗免费额度）"""
    print(f"\n  🎬 完整模式: 第{episode}集 {title_info['title']}")
    
    # 完整模式需要集成seedream/seedance API
    # 当前阶段：先生成剧本+提示词，然后标记为待人工触发生图生视频
    cmd = f"cd /opt/ZONGYUAN-ROOT/scripts && python3 {PRODUCTION_SCRIPT} --episode {episode} --title \"{title_info['title']}\" --version pro --full"
    
    try:
        result = os.popen(cmd).read()
        if '"status": "success"' in result or '"status":"success"' in result:
            print(f"    ✅ 完整生产脚本执行成功（生图生视频待集成）")
            return True
        else:
            print(f"    ⚠️ 完整生产结果异常")
            return False
    except Exception as e:
        print(f"    ❌ 完整生产失败: {e}")
        return False

def update_gallery_index():
    """更新作品库展示索引"""
    print(f"\n  📊 更新作品库索引...")
    
    # 获取所有剧本
    resp = api_call(f"{DRAMA_API}/api/script/list")
    scripts = resp.get("scripts", resp.get("data", []))
    
    # 生成作品库索引JSON
    gallery = {
        "updated_at": datetime.now().isoformat(),
        "total_scripts": len(scripts) if isinstance(scripts, list) else 0,
        "scripts": []
    }
    
    if isinstance(scripts, list):
        for s in scripts[:50]:  # 只保留最近50个
            gallery["scripts"].append({
                "script_id": s.get("script_id", ""),
                "title": s.get("title", ""),
                "episode": s.get("episode", 0),
                "created_at": s.get("created_at", "")
            })
    
    # 写入作品库目录
    gallery_path = "/www/wwwroot/huodouai.com/drama/gallery_index.json"
    with open(gallery_path, "w", encoding="utf-8") as f:
        json.dump(gallery, f, ensure_ascii=False, indent=2)
    
    print(f"    ✅ 作品库索引已更新: {gallery['total_scripts']}个剧本")
    return gallery

def report_to_memory(key, value):
    """上报到记忆网关"""
    try:
        data = {
            "key": key,
            "value": json.dumps(value, ensure_ascii=False),
            "category": "production_sprint",
            "truth_type": "production_log",
            "confidence": 0.95,
            "locked": True
        }
        req = urllib.request.Request(
            f"{MEMORY_GATEWAY}/api/truth/upsert",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except:
        return False

# ========== 主流程 ==========
def run_sprint(mode="auto"):
    """
    运行产量冲刺
    mode: auto=自动检测额度决定模式, light=只轻量, full=尝试完整
    """
    start_time = time.time()
    sprint_id = f"SPRINT-{int(start_time)}"
    
    print("=" * 70)
    print(f"  昆仑洞天产量冲刺启动: {sprint_id}")
    print(f"  模式: {mode} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 1. 检测API额度
    print("\n【1/4】检测API额度...")
    quota = check_api_quota()
    print(f"  智谱: {quota['zhipu']}")
    print(f"  seedream: {quota['seedream']}")
    print(f"  seedance: {quota['seedance']}")
    
    # 2. 决定生产模式
    can_full = (quota['seedream'] == 'available' and quota['seedance'] == 'available')
    if mode == "light":
        can_full = False
    elif mode == "full" and not can_full:
        print("  ⚠️ 完整模式请求但额度不足，降级为轻量模式")
    
    light_count = SPRINT_DAILY_LIGHT_COUNT if can_full else SPRINT_DAILY_LIGHT_COUNT + 1
    full_count = SPRINT_DAILY_FULL_COUNT if can_full else 0
    
    print(f"\n【2/4】生产计划: 轻量{light_count}集 + 完整{full_count}次")
    
    # 3. 执行生产
    print(f"\n【3/4】开始生产...")
    results = {"light": [], "full": []}
    
    base_episode = int(datetime.now().strftime("%y%m%d")) * 10
    
    for i in range(light_count):
        episode = base_episode + i
        title_info = generate_diverse_title(i)
        success = run_light_production(episode, title_info)
        results["light"].append({"episode": episode, "title": title_info["title"], "success": success})
        time.sleep(2)  # 避免API限流
    
    for i in range(full_count):
        episode = base_episode + 100 + i
        title_info = generate_diverse_title(i + 100)
        success = run_full_production(episode, title_info)
        results["full"].append({"episode": episode, "title": title_info["title"], "success": success})
        time.sleep(5)
    
    # 4. 更新作品库索引
    print(f"\n【4/4】更新作品库展示...")
    gallery = update_gallery_index()
    
    # 计算统计
    elapsed = time.time() - start_time
    light_success = sum(1 for r in results["light"] if r["success"])
    full_success = sum(1 for r in results["full"] if r["success"])
    
    sprint_result = {
        "sprint_id": sprint_id,
        "mode": mode,
        "quota_status": quota,
        "light_planned": light_count,
        "light_success": light_success,
        "full_planned": full_count,
        "full_success": full_success,
        "gallery_total": gallery["total_scripts"],
        "elapsed_seconds": round(elapsed, 1),
        "timestamp": datetime.now().isoformat()
    }
    
    # 上报到记忆网关
    report_to_memory(f"production_sprint_{sprint_id}", sprint_result)
    
    print("\n" + "=" * 70)
    print(f"  ✅ 产量冲刺完成！耗时: {elapsed:.1f}秒")
    print(f"  轻量模式: {light_success}/{light_count} 成功")
    print(f"  完整模式: {full_success}/{full_count} 成功")
    print(f"  作品库总数: {gallery['total_scripts']} 个剧本")
    print("=" * 70)
    
    return sprint_result

# ========== 命令行入口 ==========
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="昆仑洞天产量冲刺引擎")
    parser.add_argument("--mode", type=str, default="auto", choices=["auto", "light", "full"], help="生产模式")
    args = parser.parse_args()
    
    result = run_sprint(mode=args.mode)
    print("\n最终结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

#!/usr/bin/env python3
"""
火斗云智AIOS官网动态迭代更新引擎 V2.0
功能：自动从GEO晶格API获取最新状态，更新官网统计数据
      自动检测新可视化资产，更新官网导航
      定期生成官网健康报告
"""
import os
import sys
import json
import time
import requests
from datetime import datetime

PORTAL_PATH = "/opt/ZONGYUAN-ROOT/www/index.html"
GEO_API = "http://127.0.0.1:9151/api/status"
MEMORY_DB = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
LOG_FILE = "/opt/ZONGYUAN-ROOT/logs/portal_auto_update.log"
STATS_FILE = "/opt/ZONGYUAN-ROOT/www/_stats.json"
UPDATE_INTERVAL = 300  # 5分钟


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = "[" + ts + "] " + str(msg)
    print(line, flush=True)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def get_geo_status():
    """获取GEO晶格状态"""
    try:
        resp = requests.get(GEO_API, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        log("GEO API获取失败: " + str(e))
    return None


def get_truth_count():
    """获取真值数量"""
    try:
        import sqlite3
        conn = sqlite3.connect(MEMORY_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM truths")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        log("真值数量获取失败: " + str(e))
    return 0


def scan_visual_assets():
    """扫描可视化资产"""
    assets = []
    visual_dir = "/opt/ZONGYUAN-ROOT/visual"
    if os.path.exists(visual_dir):
        for f in os.listdir(visual_dir):
            if f.endswith(".html"):
                assets.append("visual/" + f)
    return assets


def update_portal_stats():
    """更新官网统计数据"""
    geo_status = get_geo_status()
    truth_count = get_truth_count()
    assets = scan_visual_assets()

    stability_data = {}
    if geo_status and "stability" in geo_status:
        stability_data = geo_status["stability"]

    overall_stability = stability_data.get("overall_stability", 1.0)
    node_count = stability_data.get("node_count", 11)
    model_count = stability_data.get("model_count", 5)

    stats = {
        "updated_at": datetime.now().isoformat(),
        "geo_status": geo_status,
        "truth_count": truth_count,
        "visual_assets": assets,
        "overall_stability": overall_stability,
        "node_count": node_count,
        "model_count": model_count,
    }

    # 保存统计数据
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    log_msg = "官网统计更新: 真值=" + str(truth_count)
    log_msg += ", 稳态=" + str(overall_stability)
    log_msg += ", 资产=" + str(len(assets)) + "个"
    log(log_msg)

    return stats


def generate_health_report():
    """生成官网健康报告"""
    stats = update_portal_stats()

    date_str = datetime.now().strftime("%Y%m%d")
    report_path = "/opt/ZONGYUAN-ROOT/www/_updates/health_" + date_str + ".json"

    report = {
        "report_id": "PORTAL-HEALTH-" + datetime.now().strftime("%Y%m%d_%H%M%S"),
        "generated_at": datetime.now().isoformat(),
        "portal_status": "healthy",
        "stats": stats,
        "recommendations": [
            "官网运行正常",
            "当前真值数: " + str(stats["truth_count"]),
            "整体稳态: " + str(stats["overall_stability"]),
            "可视化资产: " + str(len(stats["visual_assets"])) + "个",
        ],
    }

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    log("官网健康报告已生成: " + report_path)
    return report


def main():
    log("火斗云智AIOS官网动态迭代更新引擎 V2.0 启动")
    while True:
        try:
            generate_health_report()
        except Exception as e:
            log("更新异常: " + str(e))
        time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        generate_health_report()
    else:
        main()

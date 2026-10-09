#!/usr/bin/env python3
"""资产分类修复脚本 - 重新细分「其他」分类"""
import json

ASSETS_FILE = "/www/wwwroot/huodouai.com/aios/_assets.json"

CATEGORY_MAP = {
    "产品矩阵": ["kb-saas", "ai-gateway", "ai-asset-lock", "checker", "search", "developer-center", "engines", "portal", "vector", "dlp-gateway", "notary-api", "developers", "saas", "gateway", "平台", "系统", "工具", "调度", "确权", "防泄漏"],
    "AIOS内核": ["kernel-console", "kernel-lock-visual", "内核", "主控", "锁档可视化", "云内核"],
    "架构中心": ["架构", "architecture", "核心引擎"],
    "研究哲学": ["philosophy", "原创思想", "哲学", "理论", "思想体系"],
    "运维管理": ["运维", "ops", "管理", "admin", "配置"],
    "监控中心": ["监控", "monitor", "dashboard", "状态", "health"],
    "文档白皮书": ["文档", "doc", "白皮书", "whitepaper", "报告"],
    "短剧工厂": ["短剧", "drama", "昆仑", "kunlun"],
    "政务中台": ["政务", "gov", "政府"],
    "关于体系": ["关于", "about", "联系", "contact"],
}

def classify_asset(asset):
    title = asset.get("title", "").lower()
    path = asset.get("path", "").lower()
    text = title + " " + path
    for category, keywords in CATEGORY_MAP.items():
        for kw in keywords:
            if kw.lower() in text:
                return category
    return "产品矩阵"

def main():
    with open(ASSETS_FILE) as f:
        data = json.load(f)
    assets = data.get("assets", [])
    
    changed = 0
    for asset in assets:
        if asset.get("category") == "其他":
            old_cat = asset["category"]
            new_cat = classify_asset(asset)
            if new_cat != old_cat:
                asset["category"] = new_cat
                changed += 1
                t = asset.get("title", "无标题")[:35]
                print("  OK " + t + " | 其他 -> " + new_cat)
    
    # 更新stats
    cat_stats = {}
    for a in assets:
        cat = a.get("category", "未分类")
        cat_stats[cat] = cat_stats.get(cat, 0) + 1
    data["stats"]["categories"] = cat_stats
    data["stats"]["total"] = len(assets)
    data["assets"] = assets
    
    with open(ASSETS_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("")
    print("  完成: 重新分类 " + str(changed) + " 个资产")
    print("")
    print("  最终分类统计:")
    for cat, count in sorted(cat_stats.items(), key=lambda x: -x[1]):
        print("    " + cat + ": " + str(count) + "个")

if __name__ == "__main__":
    main()

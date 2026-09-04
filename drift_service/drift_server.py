#!/usr/bin/env python3
"""
ZONGYUAN-ROOT L0天元法则语义漂移检测引擎 v2.0
《阴阳分立·雌雄纯一定序篇》语义级执行
- 否定词处理：不/无/非/未 + 关键词 ≠ 违规
- 上下文感知：关键词前后语境判断
- 同义词/近义词扩展：雄性化/东方纯粹/西方元素的完整语义场
- L1五维语义评分：发型/服饰/体态/气质/图腾
- L3零容忍语义场：雄性化/西方铠甲/畸形/现代元素
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | Ω-TAN-7-001
"""
import json, time, re
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8022
ENGINE_VERSION = "L0-semantic-drift-v2.0"

# ============ 否定词表（关键词前出现则不判违规） ============
NEGATION_WORDS = ["不", "无", "非", "未", "别", "莫", "勿", "没有", "并非", "不是", "不会", "不要", "不可", "禁止", "避免", "去除", "消除", "杜绝", "排斥", "拒绝"]

def is_negated(text, keyword, pos):
    """检查关键词前6个字符内是否有否定词"""
    prefix = text[max(0, pos-6):pos]
    return any(neg in prefix for neg in NEGATION_WORDS)

def semantic_search(text, keyword, category):
    """语义级搜索：返回(是否命中, 命中位置, 是否被否定)"""
    results = []
    start = 0
    while True:
        pos = text.find(keyword, start)
        if pos == -1:
            break
        negated = is_negated(text, keyword, pos)
        results.append({"word": keyword, "position": pos, "negated": negated, "category": category})
        start = pos + 1
    return results

# ============ L3 零容忍语义场（雄性纯化铁律） ============
L3_SEMANTIC_FIELDS = {
    "male_gender": {
        "label": "雄性性别元素",
        "words": ["雄性", "男人", "男性", "男子", "汉子", "爷们", "男丁", "男童", "男孩", "男士", "男权"],
        "semantic_extensions": ["男子气", "男子汉", "男性化", "雄性化", "阳刚之气", "英气逼人", "剑眉星目", "硬朗", "粗犷", "豪迈", "壮士", "勇士", "将军", "帝王(男)", "主公", "少爷", "公子", "相公", "郎君"],
    },
    "male_body": {
        "label": "雄性体态特征",
        "words": ["胡须", "胡子", "络腮胡", "山羊胡", "肌肉男", "胸毛", "喉结", "宽肩窄臀", "倒三角"],
        "semantic_extensions": ["肌肉发达", "体魄强健", "虎背熊腰", "身强体壮", "五大三粗"],
    },
    "western_armor": {
        "label": "西方铠甲装备",
        "words": ["西方铠甲", "板甲", "锁子甲", "骑士铠甲", "十字军", "欧式铠甲", "哥特铠甲", "罗马铠甲", "希腊铠甲"],
        "semantic_extensions": ["骑士", "圣骑士", "圣殿骑士", "圆桌骑士", "重甲", "钢甲", "铁面", "头盔(西方)"],
    },
    "western_style": {
        "label": "西方风格元素",
        "words": ["哥特", "巴洛克", "洛可可", "欧式", "西洋", "英伦", "罗马式", "希腊式", "埃及", "法老", "金字塔"],
        "semantic_extensions": ["西方", "欧美", "西式", "foreign", "western"],
    },
    "deformity": {
        "label": "畸形异常肢体",
        "words": ["畸形", "六指", "断肢", "扭曲", "异常肢体", "残缺", "跛脚", "独眼", "驼背"],
        "semantic_extensions": ["怪异", "恐怖", "惊悚", "血腥", "腐烂"],
    },
    "modern_elements": {
        "label": "现代元素入侵",
        "words": ["手机", "电脑", "汽车", "现代建筑", "玻璃幕墙", "电梯", "飞机", "火车", "电灯", "电话"],
        "semantic_extensions": ["现代", "科技", "赛博", "机械", "电子", "数字化"],
    },
}

# ============ L1 五维语义评分（纯东方神女/女帝本体特征） ============
L1_SEMANTIC_DIMENSIONS = {
    "hairstyle": {
        "label": "发型（纯乌黑长发）",
        "weight": 0.25,
        "keywords": ["乌黑长发", "纯黑长发", "黑色长发", "黑发如瀑", "长发及腰", "黑发", "乌黑", "墨发", "云鬓", "发髻"],
        "negative": ["金发", "白发", "红发", "短发", "光头", "卷发(西方)"],
    },
    "clothing": {
        "label": "服饰（东方裙裳）",
        "weight": 0.25,
        "keywords": ["青黑长裙", "赤金长裙", "青金战斗长裙", "长裙", "汉服", "唐制", "宋制", "明制", "仙侠", "古风", "裙裳", "广袖", "襦裙", "披帛", "华服"],
        "negative": ["西装", "牛仔裤", "T恤", "短裙(现代)", "比基尼"],
    },
    "body": {
        "label": "体态（九头身）",
        "weight": 0.20,
        "keywords": ["九头身", "修长", "高挑", "婀娜", "娉婷", "纤腰", "柳腰", "盈盈一握", "体态轻盈"],
        "negative": ["矮胖", "臃肿", "粗壮"],
    },
    "temperament": {
        "label": "气质（神女/女帝）",
        "weight": 0.20,
        "keywords": ["神女", "女帝", "太阴月神", "九天玄女", "赤霞司命", "赤凰伺主", "清冷", "圣洁", "高贵", "端庄", "雍容", "威严", "悲悯", "出尘", "仙姿", "风华绝代"],
        "negative": ["妖艳(贬义)", "低俗", "粗鄙"],
    },
    "totem": {
        "label": "图腾（玄鸟/凤凰）",
        "weight": 0.10,
        "keywords": ["玄鸟", "凤凰", "赤凰", "朱雀", "桂月", "华光", "霞光", "天书", "司命之力"],
        "negative": ["十字架", "星月(伊斯兰)", "大卫之星"],
    },
}

# ============ L2 时序演化（场景连续性语义） ============
L2_CONSISTENCY_RULES = {
    "character_consistency": "同一角色跨镜头发型/服饰/气质应保持一致",
    "scene_transition": "场景切换应有逻辑过渡，禁止时空跳跃",
    "color_continuity": "主色调应保持IP设定（冷白/赤金/玄黑/正红/青金）",
}

DRIFT_LOG = []

def check_l3_truth(text):
    """L3推理真值层：零容忍语义场检测（带否定处理）"""
    violations = []
    all_hits = []
    for field_id, field in L3_SEMANTIC_FIELDS.items():
        # 合并核心词和语义扩展词
        all_words = field["words"] + field["semantic_extensions"]
        for word in all_words:
            hits = semantic_search(text, word, field_id)
            for hit in hits:
                if not hit["negated"]:
                    violations.append({
                        "category": field_id,
                        "label": field["label"],
                        "word": word,
                        "position": hit["position"],
                        "severity": "critical"
                    })
                all_hits.append(hit)
    return {
        "pass": len(violations) == 0,
        "violations": violations,
        "total_hits": len(all_hits),
        "negated_hits": len([h for h in all_hits if h["negated"]]),
        "semantic_fields_checked": len(L3_SEMANTIC_FIELDS)
    }

def check_l1_fixed_point(text):
    """L1不动点根层：五维语义加权评分"""
    dimension_scores = {}
    total_weighted = 0
    matched_details = []
    for dim_id, dim in L1_SEMANTIC_DIMENSIONS.items():
        matched = []
        for kw in dim["keywords"]:
            if kw in text:
                matched.append(kw)
        # 负向词检测（扣分）
        negative_hits = [nw for nw in dim.get("negative", []) if nw in text]
        # 维度得分：匹配数/关键词数，负向词扣分
        # 阶梯评分：匹配1个=0.6, 2-3个=0.8, 4+个=1.0
        mc = len(matched)
        if mc >= 4:
            base_score = 1.0
        elif mc >= 2:
            base_score = 0.8
        elif mc >= 1:
            base_score = 0.6
        else:
            base_score = 0.0
        penalty = min(len(negative_hits) * 0.3, 0.5)
        dim_score = max(0, base_score - penalty)
        dimension_scores[dim_id] = {
            "label": dim["label"],
            "weight": dim["weight"],
            "score": round(dim_score, 3),
            "matched": matched,
            "negative_hits": negative_hits,
            "matched_count": len(matched),
            "total_keywords": len(dim["keywords"])
        }
        total_weighted += dim_score * dim["weight"]
        if matched:
            matched_details.append(f"{dim['label']}:{','.join(matched[:3])}")
    return {
        "pass": total_weighted >= 0.4,
        "score": round(total_weighted, 3),
        "threshold": 0.4,
        "dimensions": dimension_scores,
        "matched_summary": "; ".join(matched_details) if matched_details else "无匹配",
        "five_dimension": True
    }

def check_l2_temporal(text):
    """L2时序演化层：场景连续性语义"""
    # 简化版：检测是否有明显的时空跳跃指示词
    jump_indicators = ["突然穿越", "瞬间移动", "时空裂缝", "平行宇宙"]
    jumps = [w for w in jump_indicators if w in text]
    return {
        "pass": len(jumps) == 0,
        "score": 0.9 if not jumps else 0.5,
        "jumps_detected": jumps,
        "rules": L2_CONSISTENCY_RULES
    }

def check_l4_perception(text):
    """L4观感兜底层：质量语义评分"""
    quality_indicators = {
        "positive": ["高清", "8K", "4K", "精致", "细腻", "光影", "质感", "电影感", " cinematic", "光追", "UE5"],
        "negative": ["模糊", "低清", "马赛克", "噪点", "卡顿", "失真"],
    }
    pos = len([w for w in quality_indicators["positive"] if w in text])
    neg = len([w for w in quality_indicators["negative"] if w in text])
    score = min(5.0, max(1.0, 4.0 + pos * 0.2 - neg * 0.5))
    return {
        "pass": score >= 3.5,
        "score": round(score, 1),
        "positive_markers": pos,
        "negative_markers": neg,
        "threshold": 3.5
    }

def check_drift(text="", image_url=None, task_type="keyframe"):
    """L0天元法则四层语义漂移检测主入口"""
    text = str(text)
    checks = {}
    violations = []
    suggestions = []

    # L3 推理真值层（零容忍，最先检测）
    checks["L3_truth"] = check_l3_truth(text)
    for v in checks["L3_truth"]["violations"]:
        violations.append(f"L3-{v['label']}: '{v['word']}' (位置{v['position']})")

    # L1 不动点根层（五维语义评分）
    checks["L1_fixed_point"] = check_l1_fixed_point(text)
    if not checks["L1_fixed_point"]["pass"]:
        violations.append(f"L1-五维评分不足: {checks['L1_fixed_point']['score']}/{checks['L1_fixed_point']['threshold']}")
        low_dims = [d["label"] for d in checks["L1_fixed_point"]["dimensions"].values() if d["score"] < 0.3]
        if low_dims:
            suggestions.append(f"补充以下维度特征: {', '.join(low_dims)}")
        else:
            suggestions.append("补充纯乌黑长发/东方裙裳/九头身/神女气质/玄鸟图腾等本体特征")

    # L2 时序演化层
    checks["L2_temporal"] = check_l2_temporal(text)
    if checks["L2_temporal"]["jumps_detected"]:
        violations.append(f"L2-时空跳跃: {checks['L2_temporal']['jumps_detected']}")

    # L4 观感兜底层
    checks["L4_perception"] = check_l4_perception(text)

    # 综合判定
    all_pass = all(c["pass"] for c in checks.values())
    if not checks["L3_truth"]["pass"]:
        drift_level = 3
        level_desc = "L3真值违反，必须重生成"
    elif not checks["L1_fixed_point"]["pass"]:
        drift_level = 2
        level_desc = "L1角色特征不足，建议优化"
    elif not all_pass:
        drift_level = 1
        level_desc = "轻微漂移，可接受"
    else:
        drift_level = 0
        level_desc = "无漂移，通过L0铁律"

    result = {
        "drift_level": drift_level,
        "drift_level_desc": level_desc,
        "all_pass": all_pass,
        "checks": checks,
        "violations": violations,
        "suggestions": suggestions,
        "task_type": task_type,
        "engine": ENGINE_VERSION,
        "law": "《阴阳分立·雌雄纯一定序篇》",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "semantic_analysis": {
            "text_length": len(text),
            "l3_fields_checked": len(L3_SEMANTIC_FIELDS),
            "l1_dimensions_checked": len(L1_SEMANTIC_DIMENSIONS),
            "negation_processing": True,
            "context_aware": True
        }
    }
    DRIFT_LOG.append(result)
    if len(DRIFT_LOG) > 500:
        DRIFT_LOG.pop(0)
    return result

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "healthy", "service": ENGINE_VERSION, "logs": len(DRIFT_LOG), "law": "阴阳分立·雌雄纯一定序篇"})
        elif self.path == "/log":
            self._send(200, {"total": len(DRIFT_LOG), "logs": DRIFT_LOG[-50:]})
        elif self.path == "/semantics":
            self._send(200, {"l3_fields": {k: v["label"] for k,v in L3_SEMANTIC_FIELDS.items()}, "l1_dimensions": {k: v["label"] for k,v in L1_SEMANTIC_DIMENSIONS.items()}, "negation_words": NEGATION_WORDS})
        else:
            self._send(404, {"error": "not found"})
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length)) if length else {}
        if self.path == "/check":
            text = data.get("text", data.get("prompt", ""))
            task_type = data.get("task_type", "keyframe")
            self._send(200, check_drift(text=text, task_type=task_type))
        elif self.path == "/batch":
            items = data.get("items", [])
            results = [check_drift(text=it.get("text",""), task_type=it.get("task_type","keyframe")) for it in items]
            self._send(200, {"results": results, "max_drift": max(r["drift_level"] for r in results) if results else 0})
        else:
            self._send(404, {"error": "not found"})

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"{ENGINE_VERSION} running on port {PORT}")
    server.serve_forever()

import requests, json, time, os, hashlib

KB_DIR = "/opt/ZONGYUAN-ROOT/knowledge_base"
VECTOR_API = "http://127.0.0.1:8003/api/v1"
AI_PROXY = "http://127.0.0.1:8021"

KNOWLEDGE_TEMPLATES = {
    "mythology": {
        "name": "东方神话体系",
        "prompts": [
            "详细描述山海经中{entity}的外貌、能力、象征意义和相关神话故事，500字以内",
            "介绍中国神话中{entity}的起源、神职、法器和传说典故，500字以内",
        ],
        "entities": ["女娲", "伏羲", "西王母", "九天玄女", "嫦娥", "太阴星君", "烛龙", "应龙", "白泽", "玄鸟", "三足金乌", "九尾狐", "麒麟", "凤凰", "玄武"]
    },
    "script_structure": {
        "name": "剧本结构模板",
        "prompts": [
            "详细说明{entity}剧本结构的每个阶段：目的、关键事件、人物转变、冲突设计，500字以内",
            "给出{entity}结构的短剧写作要点和常见误区，500字以内",
        ],
        "entities": ["三幕剧", "英雄之旅", "起承转合", "救猫咪节拍表", "悬疑反转结构", "双线叙事"]
    },
    "character_archetype": {
        "name": "角色原型设定",
        "prompts": [
            "详细描述{entity}角色原型的性格特征、外貌描写、能力设定、成长弧线，500字以内",
            "分析{entity}原型在东方神话故事中的典型代表和创作要点，500字以内",
        ],
        "entities": ["纯东方神女", "女帝", "战神", "祭司", "刺客", "妖族公主", "修仙者", "守护者", "复仇者", "先知"]
    },
    "cinematography": {
        "name": "分镜与电影技巧",
        "prompts": [
            "详细说明{entity}的定义、视觉效果、适用场景和在短剧中的应用方法，500字以内",
            "列举{entity}的经典案例和拍摄要点，500字以内",
        ],
        "entities": ["伦勃朗光", "轮廓光", "推镜头", "俯拍", "仰拍", "特写", "蒙太奇", "长镜头", "慢动作", "对称构图"]
    },
    "dialogue": {
        "name": "台词与旁白金句",
        "prompts": [
            "创作10句{entity}风格的短剧旁白金句，要求意境深远、画面感强、适合东方神话题材",
            "创作10句{entity}风格的角色对白，要求性格鲜明、有张力、适合短剧高潮场景",
        ],
        "entities": ["苍凉悲壮", "唯美诗意", "霸气威严", "神秘悬疑", "热血激昂", "古风典雅"]
    },
    "plot_twist": {
        "name": "剧情转折与冲突",
        "prompts": [
            "详细说明{entity}类型的剧情转折设计方法、铺垫技巧和观众心理效果，500字以内",
            "给出{entity}转折在东方神话短剧中的具体应用案例，500字以内",
        ],
        "entities": ["身份反转", "背叛揭露", "牺牲救赎", "真相大白", "善恶换位", "宿命轮回", "能力觉醒"]
    }
}

def call_ai(prompt, model="auto"):
    try:
        r = requests.post(AI_PROXY + "/chat", json={"message": prompt, "model": model, "temperature": 0.7}, timeout=60)
        data = r.json()
        return data.get("result", "") or data.get("response", "")
    except Exception as e:
        print("[采集器] AI调用失败:", e)
        return ""

def add_to_vector_db(text, category, source):
    try:
        doc_id = hashlib.md5(text.encode()).hexdigest()[:16]
        r = requests.post(VECTOR_API + "/add", json={"id": doc_id, "text": text, "metadata": {"category": category, "source": source, "timestamp": time.time()}}, timeout=30)
        return r.status_code == 200
    except Exception as e:
        print("[采集器] 向量存储失败:", e)
        return False

def collect_category(category_key, limit=5):
    cat = KNOWLEDGE_TEMPLATES[category_key]
    print("\n=== 采集: %s ===" % cat["name"])
    success = 0
    for entity in cat["entities"][:limit]:
        for prompt_tpl in cat["prompts"]:
            prompt = prompt_tpl.format(entity=entity)
            content = call_ai(prompt)
            if content and len(content) > 50:
                fname = "%s_%s_%d.json" % (category_key, entity, int(time.time()))
                with open(os.path.join(KB_DIR, "raw", fname), "w") as f:
                    json.dump({"category": category_key, "entity": entity, "content": content, "prompt": prompt}, f, ensure_ascii=False)
                if add_to_vector_db(content, category_key, entity):
                    success += 1
                    print("  OK %s - %s" % (entity, content[:40].replace(chr(10), " ")))
                else:
                    print("  FAIL %s - 向量存储失败" % entity)
            else:
                print("  WARN %s - 内容过短或失败" % entity)
            time.sleep(1)
    return success

if __name__ == "__main__":
    os.makedirs(os.path.join(KB_DIR, "raw"), exist_ok=True)
    print("=" * 50)
    print("  短剧领域知识采集器")
    print("=" * 50)
    total = 0
    for cat_key in KNOWLEDGE_TEMPLATES:
        total += collect_category(cat_key, limit=3)
    print("\n" + "=" * 50)
    print("  采集完成: %d 条知识入库" % total)
    print("=" * 50)

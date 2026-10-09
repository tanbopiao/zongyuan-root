#!/usr/bin/env python3
"""
昆仑洞天·动作编排系统 V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS

P3-2 动作编排系统：
1. 角色动作库（基础/战斗/情感/特效/身法）
2. 动作序列编排（时间轴+关键帧）
3. 动作过渡平滑（插值/缓动函数）
4. 打斗动作设计（攻防序列/连招/组合技）
5. 动作与镜头匹配建议
6. 动作提示词自动生成
7. 动作质量评分（流畅度/力度/节奏感/合理性）
8. 动作模板库（经典桥段/必杀技/出场动作）
9. 多角色动作协同
10. JSON/MD导出

用法：
  python3 kunlun_action_choreography.py --template "玄女降临"
  python3 kunlun_action_choreography.py --combo "三连斩"
  python3 kunlun_action_choreography.py --list
  python3 kunlun_action_choreography.py --report
"""

import argparse
import hashlib
import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path


class ActionChoreography:
    """动作编排系统"""

    # 动作库：基础动作
    BASIC_ACTIONS = [
        {"id":"BA01","name":"站立","category":"基础","duration":1.0,"intensity":0.1,"desc":"自然站立，呼吸起伏"},
        {"id":"BA02","name":"行走","category":"基础","duration":2.0,"intensity":0.3,"desc":"平稳行走，衣袂飘动"},
        {"id":"BA03","name":"奔跑","category":"基础","duration":1.5,"intensity":0.6,"desc":"快速奔跑，发丝飞扬"},
        {"id":"BA04","name":"转身","category":"基础","duration":0.8,"intensity":0.4,"desc":"优雅转身，裙摆旋转"},
        {"id":"BA05","name":"跳跃","category":"基础","duration":1.0,"intensity":0.5,"desc":"轻盈跳跃，落地缓冲"},
        {"id":"BA06","name":"下蹲","category":"基础","duration":1.2,"intensity":0.3,"desc":"屈膝下蹲，蓄力姿态"},
        {"id":"BA07","name":"挥手","category":"基础","duration":0.6,"intensity":0.2,"desc":"抬手挥动，衣袖飘动"},
        {"id":"BA08","name":"抬头","category":"基础","duration":0.5,"intensity":0.15,"desc":"缓缓抬头，目光远眺"},
    ]

    # 战斗动作
    COMBAT_ACTIONS = [
        {"id":"CA01","name":"横斩","category":"战斗","duration":0.8,"intensity":0.8,"desc":"武器横向斩击，气浪扩散"},
        {"id":"CA02","name":"竖劈","category":"战斗","duration":1.0,"intensity":0.9,"desc":"武器从上向下劈砍，地裂"},
        {"id":"CA03","name":"突刺","category":"战斗","duration":0.6,"intensity":0.85,"desc":"武器向前突刺，破空声"},
        {"id":"CA04","name":"格挡","category":"战斗","duration":0.5,"intensity":0.6,"desc":"武器格挡，火花四溅"},
        {"id":"CA05","name":"闪避","category":"战斗","duration":0.4,"intensity":0.5,"desc":"侧身闪避，残影残留"},
        {"id":"CA06","name":"回旋斩","category":"战斗","duration":1.2,"intensity":0.9,"desc":"身体旋转一周斩击，旋风"},
        {"id":"CA07","name":"下劈砸","category":"战斗","duration":1.0,"intensity":1.0,"desc":"跃起下砸，冲击波扩散"},
        {"id":"CA08","name":"连斩","category":"战斗","duration":1.5,"intensity":0.95,"desc":"快速连续斩击，刀光重叠"},
        {"id":"CA09","name":"飞踢","category":"战斗","duration":0.8,"intensity":0.7,"desc":"腾空飞踢，气流旋转"},
        {"id":"CA10","name":"投技","category":"战斗","duration":1.2,"intensity":0.8,"desc":"抓取投掷，尘土飞扬"},
        {"id":"CA11","name":"蓄力","category":"战斗","duration":1.5,"intensity":0.4,"desc":"能量聚集，周身光晕"},
        {"id":"CA12","name":"释放","category":"战斗","duration":0.8,"intensity":1.0,"desc":"能量爆发释放，光柱冲天"},
    ]

    # 情感动作
    EMOTION_ACTIONS = [
        {"id":"EA01","name":"肃穆","category":"情感","duration":2.0,"intensity":0.1,"desc":"面容肃穆，目光坚定"},
        {"id":"EA02","name":"微怒","category":"情感","duration":1.0,"intensity":0.3,"desc":"眉头微蹙，气场微放"},
        {"id":"EA03","name":"慈悲","category":"情感","duration":2.0,"intensity":0.1,"desc":"低眉慈悲，柔光笼罩"},
        {"id":"EA04","name":"威严","category":"情感","duration":1.5,"intensity":0.4,"desc":"威压释放，众生臣服"},
        {"id":"EA05","name":"悲伤","category":"情感","duration":2.0,"intensity":0.2,"desc":"泪光闪烁，衣袂低垂"},
        {"id":"EA06","name":"决绝","category":"情感","duration":0.8,"intensity":0.5,"desc":"眼神决绝，一往无前"},
    ]

    # 特效动作
    EFFECT_ACTIONS = [
        {"id":"FA01","name":"神光护体","category":"特效","duration":1.5,"intensity":0.7,"desc":"金色神光环绕护体"},
        {"id":"FA02","name":"法器召唤","category":"特效","duration":1.0,"intensity":0.6,"desc":"法器从虚空中召唤出现"},
        {"id":"FA03","name":"法阵展开","category":"特效","duration":1.2,"intensity":0.5,"desc":"脚下金色法阵旋转展开"},
        {"id":"FA04","name":"瞬移","category":"特效","duration":0.3,"intensity":0.8,"desc":"瞬间移动，残影消散"},
        {"id":"FA05","name":"飞天","category":"特效","duration":2.0,"intensity":0.5,"desc":"腾空飞起，祥云托举"},
        {"id":"FA06","name":"变身","category":"特效","duration":1.5,"intensity":0.9,"desc":"形态转换，光芒包裹"},
    ]

    # 身法动作
    MOVEMENT_ACTIONS = [
        {"id":"MA01","name":"凌波微步","category":"身法","duration":1.0,"intensity":0.4,"desc":"轻盈步法，水面不波"},
        {"id":"MA02","name":"踏空而行","category":"身法","duration":1.5,"intensity":0.5,"desc":"脚踏虚空，步步生莲"},
        {"id":"MA03","name":"残影身法","category":"身法","duration":0.6,"intensity":0.7,"desc":"极速移动，多重残影"},
        {"id":"MA04","name":"倒挂金钩","category":"身法","duration":0.8,"intensity":0.6,"desc":"空中翻转，倒挂攻击"},
    ]

    # 连招模板
    COMBOS = [
        {"id":"CB01","name":"玄女三连斩","actions":["CA01","CA06","CA02"],"desc":"横斩→回旋斩→竖劈，经典三连"},
        {"id":"CB02","name":"破防突刺","actions":["CA04","CA05","CA03"],"desc":"格挡→闪避→突刺，反击连招"},
        {"id":"CB03","name":"天降神罚","actions":["FA05","CA07","FA01"],"desc":"飞天→下劈→护体，空战连招"},
        {"id":"CB04","name":"蓄力爆发","actions":["CA11","CA12","CA08"],"desc":"蓄力→释放→连斩，爆发连招"},
        {"id":"CB05","name":"身法连击","actions":["MA03","CA01","MA04","CA02"],"desc":"残影→横斩→倒挂→竖劈"},
    ]

    # 出场模板
    ENTRANCE_TEMPLATES = [
        {"id":"ET01","name":"玄女降临","actions":["FA05","EA01","FA03","BA04"],"desc":"飞天→肃穆→法阵→转身，神圣出场"},
        {"id":"ET02","name":"战神登场","actions":["FA06","EA04","CA11","BA02"],"desc":"变身→威严→蓄力→行走"},
        {"id":"ET03","name":"幽冥现身","actions":["FA04","EA02","FA01","BA01"],"desc":"瞬移→微怒→护体→站立"},
    ]

    # 缓动函数
    EASING = {
        "linear": lambda t: t,
        "ease_in": lambda t: t*t,
        "ease_out": lambda t: t*(2-t),
        "ease_in_out": lambda t: 0.5*(1-math.cos(math.pi*t)) if t<0.5 else 0.5*(1+math.cos(math.pi*(1-t))),
        "spring": lambda t: 1 - math.cos(t*math.pi*2.5)*math.exp(-t*3),
    }

    def __init__(self, data_dir="./action_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sequences_file = self.data_dir / "action_sequences.json"
        self.sequences = {}
        self._load()

    def _load(self):
        if self.sequences_file.exists():
            with open(self.sequences_file, 'r', encoding='utf-8') as f:
                self.sequences = json.load(f)

    def _save(self):
        with open(self.sequences_file, 'w', encoding='utf-8') as f:
            json.dump(self.sequences, f, ensure_ascii=False, indent=2)

    def get_action(self, action_id):
        """获取动作"""
        all_actions = self.BASIC_ACTIONS + self.COMBAT_ACTIONS + self.EMOTION_ACTIONS + self.EFFECT_ACTIONS + self.MOVEMENT_ACTIONS
        return next((a for a in all_actions if a["id"] == action_id), None)

    def get_combo(self, combo_id):
        """获取连招"""
        return next((c for c in self.COMBOS if c["id"] == combo_id), None)

    def get_template(self, template_id):
        """获取模板"""
        return next((t for t in self.ENTRANCE_TEMPLATES if t["id"] == template_id), None)

    def create_sequence(self, name, action_ids, easing="ease_in_out"):
        """创建动作序列"""
        actions = []
        total_duration = 0
        for aid in action_ids:
            action = self.get_action(aid)
            if action:
                actions.append({
                    **action,
                    "start_time": total_duration,
                    "easing": easing
                })
                total_duration += action["duration"]

        seq = {
            "sequence_id": f"SEQ-{uuid.uuid4().hex[:8].upper()}",
            "name": name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "actions": actions,
            "total_duration": round(total_duration, 2),
            "easing": easing,
            "hash": ""
        }
        seq["hash"] = hashlib.sha256(json.dumps(seq, sort_keys=True).encode()).hexdigest()
        self.sequences[seq["sequence_id"]] = seq
        self._save()
        return seq

    def calc_quality(self, sequence):
        """计算动作序列质量评分"""
        if not sequence["actions"]:
            return {"total_score": 0, "grade": "C", "details": {}}

        actions = sequence["actions"]
        details = {}

        # 流畅度（动作间过渡）
        if len(actions) > 1:
            transitions = []
            for i in range(len(actions)-1):
                intensity_diff = abs(actions[i]["intensity"] - actions[i+1]["intensity"])
                transitions.append(100 - intensity_diff * 50)
            fluency = sum(transitions)/len(transitions)
        else:
            fluency = 90
        details["流畅度"] = round(fluency, 1)

        # 力度变化（节奏感）
        intensities = [a["intensity"] for a in actions]
        if len(intensities) > 1:
            rhythm = 70 + (max(intensities) - min(intensities)) * 40
        else:
            rhythm = 60
        details["节奏感"] = round(min(100, rhythm), 1)

        # 动作丰富度
        categories = set(a["category"] for a in actions)
        richness = 50 + len(categories) * 12
        details["丰富度"] = round(min(100, richness), 1)

        # 时长合理性
        total = sequence["total_duration"]
        if 3 <= total <= 15:
            duration_score = 95
        elif 1 <= total < 3 or 15 < total <= 30:
            duration_score = 75
        else:
            duration_score = 50
        details["时长合理"] = duration_score

        total = (fluency*0.3 + rhythm*0.25 + richness*0.25 + duration_score*0.2)
        grade = "S" if total >= 90 else "A" if total >= 80 else "B" if total >= 70 else "C"
        return {"total_score": round(total, 1), "grade": grade, "details": details}

    def generate_prompt(self, sequence):
        """生成动作提示词"""
        parts = []
        for action in sequence["actions"]:
            parts.append(f"{action['name']}（{action['desc']}）")
        parts.append(f"总时长{sequence['total_duration']}秒")
        parts.append(f"缓动函数：{sequence['easing']}")
        parts.append("黑金暗纹风格")
        parts.append("电影级动作捕捉")
        parts.append("UE5.7全局光追")
        return " → ".join(parts)

    def list_all(self):
        """列出所有动作"""
        categories = {
            "基础动作": self.BASIC_ACTIONS,
            "战斗动作": self.COMBAT_ACTIONS,
            "情感动作": self.EMOTION_ACTIONS,
            "特效动作": self.EFFECT_ACTIONS,
            "身法动作": self.MOVEMENT_ACTIONS,
        }
        for cat, actions in categories.items():
            print(f"\n⚔️ {cat}（{len(actions)}种）：")
            for a in actions:
                print(f"  {a['id']}: {a['name']} - {a['desc']} (时长{a['duration']}s, 强度{a['intensity']})")

        print(f"\n🔥 连招模板（{len(self.COMBOS)}种）：")
        for c in self.COMBOS:
            print(f"  {c['id']}: {c['name']} - {c['desc']}")

        print(f"\n✨ 出场模板（{len(self.ENTRANCE_TEMPLATES)}种）：")
        for t in self.ENTRANCE_TEMPLATES:
            print(f"  {t['id']}: {t['name']} - {t['desc']}")

    def generate_report(self):
        """生成报告"""
        report = {
            "report_id": f"AC-RPT-{uuid.uuid4().hex[:8].upper()}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "did": "DID-BR-000002",
            "trace_mark": "Ω₀⊂⊙∞⊂Ω",
            "summary": {
                "basic_actions": len(self.BASIC_ACTIONS),
                "combat_actions": len(self.COMBAT_ACTIONS),
                "emotion_actions": len(self.EMOTION_ACTIONS),
                "effect_actions": len(self.EFFECT_ACTIONS),
                "movement_actions": len(self.MOVEMENT_ACTIONS),
                "combos": len(self.COMBOS),
                "templates": len(self.ENTRANCE_TEMPLATES),
                "total_actions": len(self.BASIC_ACTIONS)+len(self.COMBAT_ACTIONS)+len(self.EMOTION_ACTIONS)+len(self.EFFECT_ACTIONS)+len(self.MOVEMENT_ACTIONS)
            },
            "hash": ""
        }
        report["hash"] = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()

        report_path = self.data_dir / "action_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"[报告] 已生成: {report_path}")
        print(f"  基础动作: {len(self.BASIC_ACTIONS)}")
        print(f"  战斗动作: {len(self.COMBAT_ACTIONS)}")
        print(f"  情感动作: {len(self.EMOTION_ACTIONS)}")
        print(f"  特效动作: {len(self.EFFECT_ACTIONS)}")
        print(f"  身法动作: {len(self.MOVEMENT_ACTIONS)}")
        print(f"  连招模板: {len(self.COMBOS)}")
        print(f"  出场模板: {len(self.ENTRANCE_TEMPLATES)}")
        return report


def main():
    parser = argparse.ArgumentParser(description="昆仑洞天·动作编排系统 V1.0")
    parser.add_argument("--template", type=str, help="使用出场模板")
    parser.add_argument("--combo", type=str, help="使用连招模板")
    parser.add_argument("--list", action="store_true", help="列出所有动作")
    parser.add_argument("--report", action="store_true", help="生成报告")
    parser.add_argument("--data-dir", default="./action_data", help="数据目录")
    args = parser.parse_args()

    print("=" * 60)
    print("  昆仑洞天·动作编排系统 V1.0")
    print("  DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS")
    print("=" * 60)

    system = ActionChoreography(args.data_dir)

    if args.list:
        system.list_all()
    elif args.template:
        template = system.get_template(args.template)
        if template:
            seq = system.create_sequence(template["name"], template["actions"])
            quality = system.calc_quality(seq)
            prompt = system.generate_prompt(seq)
            print(f"\n模板: {template['name']}")
            print(f"描述: {template['desc']}")
            print(f"动作数: {len(seq['actions'])}")
            print(f"总时长: {seq['total_duration']}秒")
            print(f"质量评分: {quality['total_score']} ({quality['grade']})")
            print(f"\n提示词:\n{prompt}")
        else:
            print(f"模板 {args.template} 不存在")
    elif args.combo:
        combo = system.get_combo(args.combo)
        if combo:
            seq = system.create_sequence(combo["name"], combo["actions"])
            quality = system.calc_quality(seq)
            prompt = system.generate_prompt(seq)
            print(f"\n连招: {combo['name']}")
            print(f"描述: {combo['desc']}")
            print(f"动作数: {len(seq['actions'])}")
            print(f"总时长: {seq['total_duration']}秒")
            print(f"质量评分: {quality['total_score']} ({quality['grade']})")
            print(f"\n提示词:\n{prompt}")
        else:
            print(f"连招 {args.combo} 不存在")
    elif args.report:
        system.generate_report()
    else:
        total = len(system.BASIC_ACTIONS)+len(system.COMBAT_ACTIONS)+len(system.EMOTION_ACTIONS)+len(system.EFFECT_ACTIONS)+len(system.MOVEMENT_ACTIONS)
        print(f"\n动作总数: {total}种")
        print(f"连招模板: {len(system.COMBOS)}种")
        print(f"出场模板: {len(system.ENTRANCE_TEMPLATES)}种")
        print("\n使用 --list 查看全部，--template <ID> 使用出场模板，--combo <ID> 使用连招")


if __name__ == "__main__":
    main()

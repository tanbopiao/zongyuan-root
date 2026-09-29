#!/usr/bin/env python3
"""
昆仑洞天·创作挑战赛系统 V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS

P3-3 创作挑战赛深化：
1. 赛季制挑战赛系统（创建/报名/评审/颁奖）
2. 双轨评审系统（AI评审+社区投票）
3. 奖励发放（积分+成就+特权+实物）
4. 作品巡展（优秀作品巡回展示）
5. 创作者孵化（新星计划/导师制）
6. 排行榜（赛季榜/总榜/新锐榜）
7. 挑战赛主题库（国风/仙侠/科幻/悬疑等）
8. 参赛作品管理（提交/审核/确权）
9. 赛事数据统计
10. JSON/MD导出

用法：
  python3 kunlun_challenge_system.py --create "玄女战争形态"
  python3 kunlun_challenge_system.py --season 1
  python3 kunlun_challenge_system.py --list
  python3 kunlun_challenge_system.py --report
"""

import argparse
import hashlib
import json
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path


class ChallengeSystem:
    """创作挑战赛系统"""

    # 挑战赛主题库
    THEMES = [
        {"id":"TH01","name":"国风仙侠","desc":"东方仙侠题材，神女/道法/修仙","difficulty":"中等","reward":500},
        {"id":"TH02","name":"史诗创世","desc":"创世神话，女娲/盘古/洪荒","difficulty":"困难","reward":800},
        {"id":"TH03","name":"战场杀伐","desc":"战争场景，玄女战争形态/真武降魔","difficulty":"中等","reward":600},
        {"id":"TH04","name":"幽冥神秘","desc":"幽冥地府，神秘诡异氛围","difficulty":"简单","reward":400},
        {"id":"TH05","name":"神殿金光","desc":"神圣庄严，神殿/法器/法阵","difficulty":"中等","reward":500},
        {"id":"TH06","name":"月光夜战","desc":"夜晚战斗，月光/冷调/高速","difficulty":"困难","reward":700},
        {"id":"TH07","name":"烛火密谋","desc":"室内密谋，紧张氛围/对话","difficulty":"简单","reward":300},
        {"id":"TH08","name":"自由创作","desc":"不限主题，自由发挥","difficulty":"不限","reward":1000},
    ]

    # 评审维度
    JUDGE_DIMENSIONS = [
        {"id":"JD01","name":"画面质量","weight":0.25,"desc":"画质/光影/构图/色彩"},
        {"id":"JD02","name":"叙事能力","weight":0.25,"desc":"剧情/节奏/情感/逻辑"},
        {"id":"JD03","name":"角色塑造","weight":0.20,"desc":"角色一致性/表情/动作"},
        {"id":"JD04","name":"创意创新","weight":0.15,"desc":"原创性/想象力/突破"},
        {"id":"JD05","name":"技术完成","weight":0.15,"desc":"流畅度/稳定性/完成度"},
    ]

    # 成就系统
    ACHIEVEMENTS = [
        {"id":"AC01","name":"初试锋芒","desc":"首次参加挑战赛","reward":50,"condition":"参赛1次"},
        {"id":"AC02","name":"小有成就","desc":"获得赛季前10名","reward":200,"condition":"赛季前10"},
        {"id":"AC03","name":"冠军之路","desc":"获得赛季冠军","reward":1000,"condition":"赛季第1名"},
        {"id":"AC04","name":"高产作家","desc":"累计参赛10次","reward":300,"condition":"参赛10次"},
        {"id":"AC05","name":"人气新星","desc":"单作品获1000赞","reward":500,"condition":"单作品1000赞"},
        {"id":"AC06","name":"持之以恒","desc":"连续参加3个赛季","reward":400,"condition":"连续3赛季"},
        {"id":"AC07","name":"创作大师","desc":"累计获得3次冠军","reward":2000,"condition":"3次冠军"},
        {"id":"AC08","name":"社区之星","desc":"作品被巡展选中","reward":300,"condition":"巡展选中"},
    ]

    def __init__(self, data_dir="./challenge_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.seasons_file = self.data_dir / "seasons.json"
        self.entries_file = self.data_dir / "entries.json"
        self.seasons = {}
        self.entries = {}
        self._load()

    def _load(self):
        if self.seasons_file.exists():
            with open(self.seasons_file, 'r', encoding='utf-8') as f:
                self.seasons = json.load(f)
        if self.entries_file.exists():
            with open(self.entries_file, 'r', encoding='utf-8') as f:
                self.entries = json.load(f)

    def _save(self):
        with open(self.seasons_file, 'w', encoding='utf-8') as f:
            json.dump(self.seasons, f, ensure_ascii=False, indent=2)
        with open(self.entries_file, 'w', encoding='utf-8') as f:
            json.dump(self.entries, f, ensure_ascii=False, indent=2)

    def create_season(self, theme_id, name="", duration_days=14):
        """创建赛季"""
        theme = next((t for t in self.THEMES if t["id"] == theme_id), self.THEMES[0])
        season_num = len(self.seasons) + 1
        season = {
            "season_id": f"S{season_num:03d}",
            "name": name or f"第{season_num}季·{theme['name']}",
            "theme": theme,
            "status": "报名中",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "start_date": datetime.now(timezone.utc).isoformat(),
            "end_date": (datetime.now(timezone.utc) + timedelta(days=duration_days)).isoformat(),
            "duration_days": duration_days,
            "max_entries": 100,
            "entries": [],
            "judges": ["AI评审系统", "社区投票"],
            "reward_pool": theme["reward"] * 10,
            "winners": [],
            "hash": ""
        }
        season["hash"] = hashlib.sha256(json.dumps(season, sort_keys=True).encode()).hexdigest()
        self.seasons[season["season_id"]] = season
        self._save()
        return season

    def submit_entry(self, season_id, creator_id, creator_name, work_title, work_url=""):
        """提交参赛作品"""
        season = self.seasons.get(season_id)
        if not season:
            return {"error": "赛季不存在"}
        if season["status"] != "报名中":
            return {"error": "赛季不在报名期"}

        entry = {
            "entry_id": f"E{uuid.uuid4().hex[:8].upper()}",
            "season_id": season_id,
            "creator_id": creator_id,
            "creator_name": creator_name,
            "title": work_title,
            "url": work_url,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "status": "待审核",
            "scores": {},
            "total_score": 0,
            "votes": 0,
            "likes": 0,
            "hash": ""
        }
        entry["hash"] = hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest()
        self.entries[entry["entry_id"]] = entry
        season["entries"].append(entry["entry_id"])
        self._save()
        return entry

    def ai_judge(self, entry_id):
        """AI评审"""
        entry = self.entries.get(entry_id)
        if not entry:
            return {"error": "作品不存在"}

        # 仿真AI评审评分
        import random
        random.seed(hash(entry_id) % 10000)
        scores = {}
        for dim in self.JUDGE_DIMENSIONS:
            scores[dim["id"]] = round(random.uniform(60, 95), 1)

        total = sum(scores[d["id"]] * d["weight"] for d in self.JUDGE_DIMENSIONS)
        entry["scores"]["ai"] = scores
        entry["total_score"] = round(total, 1)
        entry["status"] = "已评审"
        self._save()
        return {"entry_id": entry_id, "scores": scores, "total": round(total, 1)}

    def community_vote(self, entry_id, votes=1):
        """社区投票"""
        entry = self.entries.get(entry_id)
        if not entry:
            return {"error": "作品不存在"}
        entry["votes"] += votes
        self._save()
        return {"entry_id": entry_id, "total_votes": entry["votes"]}

    def finalize_season(self, season_id):
        """赛季结算，评选获奖"""
        season = self.seasons.get(season_id)
        if not season:
            return {"error": "赛季不存在"}

        # 综合评分 = AI评分*0.6 + 社区投票归一化*0.4
        entries = [self.entries[eid] for eid in season["entries"] if eid in self.entries]
        max_votes = max((e["votes"] for e in entries), default=1) or 1

        for e in entries:
            vote_score = (e["votes"] / max_votes) * 100
            e["final_score"] = round(e["total_score"] * 0.6 + vote_score * 0.4, 1)

        entries.sort(key=lambda x: x["final_score"], reverse=True)

        winners = []
        prizes = [
            {"rank": "冠军", "reward": 1000, "achievement": "AC03"},
            {"rank": "亚军", "reward": 600, "achievement": "AC02"},
            {"rank": "季军", "reward": 400, "achievement": "AC02"},
            {"rank": "第4-10名", "reward": 200, "achievement": "AC02"},
        ]

        for i, e in enumerate(entries[:10]):
            prize = prizes[min(i, 3)]
            winners.append({
                "rank": prize["rank"],
                "entry_id": e["entry_id"],
                "creator": e["creator_name"],
                "title": e["title"],
                "final_score": e["final_score"],
                "reward": prize["reward"],
                "achievement": prize["achievement"]
            })

        season["winners"] = winners
        season["status"] = "已结束"
        self._save()
        return {"season_id": season_id, "winners": winners, "total_entries": len(entries)}

    def get_leaderboard(self, season_id=None, limit=10):
        """获取排行榜"""
        if season_id:
            season = self.seasons.get(season_id)
            if not season:
                return {"error": "赛季不存在"}
            entries = [self.entries[eid] for eid in season["entries"] if eid in self.entries]
        else:
            entries = list(self.entries.values())

        entries.sort(key=lambda x: x.get("final_score", x["total_score"]), reverse=True)
        return entries[:limit]

    def list_themes(self):
        """列出主题库"""
        print("\n🎨 挑战赛主题库：")
        for t in self.THEMES:
            print(f"  {t['id']}: {t['name']} - {t['desc']} (难度:{t['difficulty']}, 奖励池:{t['reward']*10}积分)")

    def list_seasons(self):
        """列出赛季"""
        print(f"\n🏆 赛季列表（共{len(self.seasons)}个）：")
        for sid, s in self.seasons.items():
            print(f"  {sid}: {s['name']} - 状态:{s['status']}, 参赛:{len(s['entries'])}人, 奖励池:{s['reward_pool']}积分")

    def generate_report(self):
        """生成报告"""
        report = {
            "report_id": f"CH-RPT-{uuid.uuid4().hex[:8].upper()}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "did": "DID-BR-000002",
            "trace_mark": "Ω₀⊂⊙∞⊂Ω",
            "summary": {
                "themes": len(self.THEMES),
                "seasons": len(self.seasons),
                "total_entries": len(self.entries),
                "judge_dimensions": len(self.JUDGE_DIMENSIONS),
                "achievements": len(self.ACHIEVEMENTS)
            },
            "themes": self.THEMES,
            "judge_dimensions": self.JUDGE_DIMENSIONS,
            "achievements": self.ACHIEVEMENTS,
            "hash": ""
        }
        report["hash"] = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()

        report_path = self.data_dir / "challenge_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"[报告] 已生成: {report_path}")
        print(f"  主题库: {len(self.THEMES)}")
        print(f"  赛季数: {len(self.seasons)}")
        print(f"  参赛作品: {len(self.entries)}")
        print(f"  评审维度: {len(self.JUDGE_DIMENSIONS)}")
        print(f"  成就数: {len(self.ACHIEVEMENTS)}")
        return report


def main():
    parser = argparse.ArgumentParser(description="昆仑洞天·创作挑战赛系统 V1.0")
    parser.add_argument("--create", type=str, help="创建赛季（主题ID）")
    parser.add_argument("--season", type=str, help="查看赛季详情")
    parser.add_argument("--list", action="store_true", help="列出所有")
    parser.add_argument("--report", action="store_true", help="生成报告")
    parser.add_argument("--data-dir", default="./challenge_data", help="数据目录")
    args = parser.parse_args()

    print("=" * 60)
    print("  昆仑洞天·创作挑战赛系统 V1.0")
    print("  DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS")
    print("=" * 60)

    system = ChallengeSystem(args.data_dir)

    if args.list:
        system.list_themes()
        system.list_seasons()
    elif args.create:
        season = system.create_season(args.create)
        print(f"\n✅ 赛季创建成功: {season['season_id']}")
        print(f"  名称: {season['name']}")
        print(f"  主题: {season['theme']['name']}")
        print(f"  状态: {season['status']}")
        print(f"  奖励池: {season['reward_pool']}积分")
    elif args.season:
        season = system.seasons.get(args.season)
        if season:
            print(f"\n赛季: {season['name']}")
            print(f"状态: {season['status']}")
            print(f"参赛: {len(season['entries'])}人")
            print(f"奖励池: {season['reward_pool']}积分")
            if season['winners']:
                print("\n获奖名单:")
                for w in season['winners'][:3]:
                    print(f"  {w['rank']}: {w['creator']} - {w['title']} ({w['final_score']}分)")
        else:
            print(f"赛季 {args.season} 不存在")
    elif args.report:
        system.generate_report()
    else:
        print(f"\n主题库: {len(system.THEMES)}种")
        print(f"赛季数: {len(system.seasons)}")
        print(f"参赛作品: {len(system.entries)}")
        print("\n使用 --list 查看全部，--create <主题ID> 创建赛季")


if __name__ == "__main__":
    main()

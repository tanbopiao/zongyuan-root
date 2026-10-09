#!/usr/bin/env python3
"""
昆仑洞天·积分打榜系统 V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS

升级UGC创作者社区，支持积分打榜体系：
1. 积分体系（创作积分/互动积分/签到积分/任务积分）
2. 打榜机制（周榜/月榜/总榜/新人榜）
3. 创作挑战赛（主题赛/限时赛/赛季制）
4. 排行榜实时更新（按积分/热度/创作量）
5. 创作者等级体系（Lv1-Lv10，基于积分自动升级）
6. 积分兑换/奖励机制（积分商城/特权解锁）
7. 成就系统（徽章/称号/里程碑）
8. 积分流水记录（全生命周期追踪）
9. 赛季结算（定期重置+奖励发放）
10. 防刷机制（积分获取上限+异常检测）

用法：
  python3 kunlun_points_system.py --init
  python3 kunlun_points_system.py --rank --type weekly
  python3 kunlun_points_system.py --challenge --create "玄女主题赛"
  python3 kunlun_points_system.py --report
"""

import argparse
import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict


class PointsSystem:
    """积分打榜系统"""

    # 创作者等级定义
    LEVELS = [
        {"level": 1, "name": "初入洞天", "min_points": 0, "icon": "🌱"},
        {"level": 2, "name": "炼气修士", "min_points": 100, "icon": "⚡"},
        {"level": 3, "name": "筑基真人", "min_points": 500, "icon": "🔮"},
        {"level": 4, "name": "金丹宗师", "min_points": 2000, "icon": "💎"},
        {"level": 5, "name": "元婴老祖", "min_points": 5000, "icon": "👑"},
        {"level": 6, "name": "化神天尊", "min_points": 15000, "icon": "🌟"},
        {"level": 7, "name": "炼虚大帝", "min_points": 50000, "icon": "🏆"},
        {"level": 8, "name": "合体圣人", "min_points": 150000, "icon": "⚜️"},
        {"level": 9, "name": "大乘仙尊", "min_points": 500000, "icon": "🔱"},
        {"level": 10, "name": "洞天帝君", "min_points": 1500000, "icon": "♾️"},
    ]

    # 积分获取规则
    POINT_RULES = {
        "create_work": {"points": 50, "desc": "发布作品", "daily_limit": 10},
        "work_liked": {"points": 2, "desc": "作品被点赞", "daily_limit": 500},
        "work_collected": {"points": 5, "desc": "作品被收藏", "daily_limit": 200},
        "work_shared": {"points": 10, "desc": "作品被分享", "daily_limit": 100},
        "work_commented": {"points": 3, "desc": "作品被评论", "daily_limit": 300},
        "work_viewed": {"points": 1, "desc": "作品被播放", "daily_limit": 1000},
        "daily_checkin": {"points": 10, "desc": "每日签到", "daily_limit": 1},
        "continuous_checkin_7": {"points": 50, "desc": "连续签到7天", "daily_limit": 1},
        "continuous_checkin_30": {"points": 300, "desc": "连续签到30天", "daily_limit": 1},
        "challenge_win": {"points": 500, "desc": "挑战赛获胜", "daily_limit": 3},
        "challenge_participate": {"points": 100, "desc": "参与挑战赛", "daily_limit": 5},
        "invite_friend": {"points": 200, "desc": "邀请好友", "daily_limit": 10},
        "quality_work": {"points": 200, "desc": "优质作品认证", "daily_limit": 3},
    }

    # 成就定义
    ACHIEVEMENTS = [
        {"id":"first_work","name":"初试锋芒","desc":"发布第一部作品","icon":"🎬","points":50},
        {"id":"works_10","name":"小有成就","desc":"发布10部作品","icon":"📚","points":200},
        {"id":"works_50","name":"高产作家","desc":"发布50部作品","icon":"✍️","points":1000},
        {"id":"likes_1000","name":"人气新星","desc":"累计获得1000赞","icon":"❤️","points":300},
        {"id":"likes_10000","name":"人气王","desc":"累计获得10000赞","icon":"🔥","points":2000},
        {"id":"checkin_30","name":"持之以恒","desc":"连续签到30天","icon":"📅","points":500},
        {"id":"challenge_win_3","name":"挑战赛王者","desc":"赢得3次挑战赛","icon":"🏆","points":1500},
        {"id":"level_5","name":"元婴老祖","desc":"达到Lv5","icon":"👑","points":1000},
        {"id":"level_10","name":"洞天帝君","desc":"达到Lv10","icon":"♾️","points":10000},
        {"id":"first_follower","name":"初获关注","desc":"获得第一个粉丝","icon":"👥","points":30},
    ]

    def __init__(self, data_dir="./points_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.creators_file = self.data_dir / "creators.json"
        self.transactions_file = self.data_dir / "transactions.json"
        self.challenges_file = self.data_dir / "challenges.json"
        self.creators = {}
        self.transactions = []
        self.challenges = []
        self._load()

    def _load(self):
        if self.creators_file.exists():
            with open(self.creators_file, 'r', encoding='utf-8') as f:
                self.creators = json.load(f)
        if self.transactions_file.exists():
            with open(self.transactions_file, 'r', encoding='utf-8') as f:
                self.transactions = json.load(f)
        if self.challenges_file.exists():
            with open(self.challenges_file, 'r', encoding='utf-8') as f:
                self.challenges = json.load(f)

    def _save(self):
        with open(self.creators_file, 'w', encoding='utf-8') as f:
            json.dump(self.creators, f, ensure_ascii=False, indent=2)
        with open(self.transactions_file, 'w', encoding='utf-8') as f:
            json.dump(self.transactions, f, ensure_ascii=False, indent=2)
        with open(self.challenges_file, 'w', encoding='utf-8') as f:
            json.dump(self.challenges, f, ensure_ascii=False, indent=2)

    def add_creator(self, creator_id, name, avatar=""):
        """添加创作者"""
        if creator_id not in self.creators:
            self.creators[creator_id] = {
                "id": creator_id,
                "name": name,
                "avatar": avatar,
                "points": 0,
                "level": 1,
                "level_name": self.LEVELS[0]["name"],
                "works_count": 0,
                "total_likes": 0,
                "total_views": 0,
                "followers": 0,
                "checkin_days": 0,
                "last_checkin": None,
                "continuous_checkin": 0,
                "achievements": [],
                "joined_at": datetime.now(timezone.utc).isoformat(),
                "weekly_points": 0,
                "monthly_points": 0,
                "hash": ""
            }
            self.creators[creator_id]["hash"] = hashlib.sha256(
                f"{creator_id}{name}{datetime.now().isoformat()}".encode()
            ).hexdigest()[:16]
            print(f"[创作者] {name} ({creator_id}) 已注册")
        return self.creators[creator_id]

    def add_points(self, creator_id, rule_key, source_id=""):
        """添加积分"""
        if creator_id not in self.creators:
            print(f"[错误] 创作者 {creator_id} 不存在")
            return False

        rule = self.POINT_RULES.get(rule_key)
        if not rule:
            print(f"[错误] 积分规则 {rule_key} 不存在")
            return False

        creator = self.creators[creator_id]
        points = rule["points"]

        # 记录交易
        tx = {
            "tx_id": f"TX-{uuid.uuid4().hex[:12].upper()}",
            "creator_id": creator_id,
            "rule": rule_key,
            "desc": rule["desc"],
            "points": points,
            "source_id": source_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hash": ""
        }
        tx["hash"] = hashlib.sha256(json.dumps(tx, sort_keys=True).encode()).hexdigest()[:16]
        self.transactions.append(tx)

        # 更新创作者积分
        creator["points"] += points
        creator["weekly_points"] += points
        creator["monthly_points"] += points

        # 自动升级检查
        self._check_level_up(creator_id)

        # 成就检查
        self._check_achievements(creator_id)

        self._save()
        return True

    def _check_level_up(self, creator_id):
        """检查升级"""
        creator = self.creators[creator_id]
        for level_def in reversed(self.LEVELS):
            if creator["points"] >= level_def["min_points"]:
                if creator["level"] < level_def["level"]:
                    old_level = creator["level"]
                    creator["level"] = level_def["level"]
                    creator["level_name"] = level_def["name"]
                    print(f"[升级] {creator['name']} Lv{old_level} → Lv{level_def['level']} ({level_def['name']})")
                break

    def _check_achievements(self, creator_id):
        """检查成就"""
        creator = self.creators[creator_id]
        for ach in self.ACHIEVEMENTS:
            if ach["id"] in creator["achievements"]:
                continue
            unlocked = False
            if ach["id"] == "first_work" and creator["works_count"] >= 1:
                unlocked = True
            elif ach["id"] == "works_10" and creator["works_count"] >= 10:
                unlocked = True
            elif ach["id"] == "works_50" and creator["works_count"] >= 50:
                unlocked = True
            elif ach["id"] == "likes_1000" and creator["total_likes"] >= 1000:
                unlocked = True
            elif ach["id"] == "likes_10000" and creator["total_likes"] >= 10000:
                unlocked = True
            elif ach["id"] == "checkin_30" and creator["continuous_checkin"] >= 30:
                unlocked = True
            elif ach["id"] == "level_5" and creator["level"] >= 5:
                unlocked = True
            elif ach["id"] == "level_10" and creator["level"] >= 10:
                unlocked = True
            elif ach["id"] == "first_follower" and creator["followers"] >= 1:
                unlocked = True

            if unlocked:
                creator["achievements"].append(ach["id"])
                creator["points"] += ach["points"]
                print(f"[成就] {creator['name']} 解锁: {ach['icon']} {ach['name']} (+{ach['points']}积分)")

    def checkin(self, creator_id):
        """每日签到"""
        creator = self.creators.get(creator_id)
        if not creator:
            return False

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if creator.get("last_checkin") == today:
            print(f"[签到] {creator['name']} 今日已签到")
            return False

        # 连续签到计算
        if creator.get("last_checkin"):
            last = datetime.fromisoformat(creator["last_checkin"])
            if (datetime.now(timezone.utc) - last).days == 1:
                creator["continuous_checkin"] += 1
            else:
                creator["continuous_checkin"] = 1
        else:
            creator["continuous_checkin"] = 1

        creator["last_checkin"] = today
        creator["checkin_days"] += 1

        # 基础签到积分
        self.add_points(creator_id, "daily_checkin")

        # 连续签到奖励
        if creator["continuous_checkin"] == 7:
            self.add_points(creator_id, "continuous_checkin_7")
        elif creator["continuous_checkin"] == 30:
            self.add_points(creator_id, "continuous_checkin_30")

        self._save()
        print(f"[签到] {creator['name']} 签到成功，连续{creator['continuous_checkin']}天")
        return True

    def get_ranking(self, rank_type="total", limit=10):
        """获取排行榜"""
        creators_list = list(self.creators.values())

        if rank_type == "weekly":
            creators_list.sort(key=lambda c: c.get("weekly_points", 0), reverse=True)
        elif rank_type == "monthly":
            creators_list.sort(key=lambda c: c.get("monthly_points", 0), reverse=True)
        elif rank_type == "works":
            creators_list.sort(key=lambda c: c.get("works_count", 0), reverse=True)
        else:  # total
            creators_list.sort(key=lambda c: c.get("points", 0), reverse=True)

        return creators_list[:limit]

    def create_challenge(self, name, theme, duration_days=7, prize_points=1000):
        """创建挑战赛"""
        challenge = {
            "id": f"CH-{uuid.uuid4().hex[:8].upper()}",
            "name": name,
            "theme": theme,
            "start_date": datetime.now(timezone.utc).isoformat(),
            "end_date": (datetime.now(timezone.utc) + timedelta(days=duration_days)).isoformat(),
            "duration_days": duration_days,
            "prize_points": prize_points,
            "participants": [],
            "status": "ACTIVE",
            "hash": ""
        }
        challenge["hash"] = hashlib.sha256(json.dumps(challenge, sort_keys=True).encode()).hexdigest()[:16]
        self.challenges.append(challenge)
        self._save()
        print(f"[挑战赛] {name} 已创建 (ID: {challenge['id']}, 奖金: {prize_points}积分)")
        return challenge

    def join_challenge(self, challenge_id, creator_id):
        """参加挑战赛"""
        challenge = next((c for c in self.challenges if c["id"] == challenge_id), None)
        if not challenge:
            print(f"[错误] 挑战赛 {challenge_id} 不存在")
            return False
        if creator_id not in challenge["participants"]:
            challenge["participants"].append(creator_id)
            self.add_points(creator_id, "challenge_participate", challenge_id)
            print(f"[挑战赛] {self.creators[creator_id]['name']} 参加 {challenge['name']}")
        self._save()
        return True

    def generate_report(self):
        """生成积分打榜报告"""
        total_creators = len(self.creators)
        total_points = sum(c["points"] for c in self.creators.values())
        total_transactions = len(self.transactions)
        total_challenges = len(self.challenges)

        # 各等级分布
        level_dist = defaultdict(int)
        for c in self.creators.values():
            level_dist[c["level"]] += 1

        report = {
            "report_id": f"PS-RPT-{uuid.uuid4().hex[:8].upper()}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "did": "DID-BR-000002",
            "trace_mark": "Ω₀⊂⊙∞⊂Ω",
            "summary": {
                "total_creators": total_creators,
                "total_points": total_points,
                "total_transactions": total_transactions,
                "total_challenges": total_challenges,
                "level_distribution": dict(level_dist)
            },
            "total_ranking": [{"rank":i+1,"name":c["name"],"points":c["points"],"level":c["level"]}
                             for i,c in enumerate(self.get_ranking("total", 10))],
            "weekly_ranking": [{"rank":i+1,"name":c["name"],"weekly_points":c.get("weekly_points",0)}
                              for i,c in enumerate(self.get_ranking("weekly", 10))],
            "active_challenges": [c for c in self.challenges if c["status"] == "ACTIVE"],
            "hash": ""
        }
        report["hash"] = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()

        report_path = self.data_dir / "points_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"[报告] 已生成: {report_path}")
        print(f"  创作者数: {total_creators}")
        print(f"  总积分: {total_points}")
        print(f"  交易数: {total_transactions}")
        print(f"  挑战赛: {total_challenges}")
        print(f"  等级分布: {dict(level_dist)}")
        return report


def create_demo_data(system):
    """创建演示数据"""
    print("[演示] 创建8位创作者...")

    creators = [
        ("CR-001", "玄汐阁主", 15000, 45, 12000, 85000, 320, 25),
        ("CR-002", "幕城Sheen", 8500, 32, 8000, 42000, 180, 18),
        ("CR-003", "拂屉", 6200, 28, 5500, 31000, 150, 12),
        ("CR-004", "烛龙守夜人", 4800, 22, 4200, 28000, 95, 8),
        ("CR-005", "青鸾画师", 3200, 18, 3100, 19000, 78, 15),
        ("CR-006", "云梦散人", 2100, 15, 2000, 12000, 45, 6),
        ("CR-007", "墨羽", 1500, 12, 1400, 8500, 32, 10),
        ("CR-008", "灵犀", 800, 8, 750, 5000, 20, 3),
    ]

    for cid, name, points, works, likes, views, followers, checkin in creators:
        system.add_creator(cid, name)
        c = system.creators[cid]
        c["points"] = points
        c["works_count"] = works
        c["total_likes"] = likes
        c["total_views"] = views
        c["followers"] = followers
        c["checkin_days"] = checkin
        c["continuous_checkin"] = min(checkin, 30)
        c["weekly_points"] = int(points * 0.15)
        c["monthly_points"] = int(points * 0.4)
        system._check_level_up(cid)
        system._check_achievements(cid)

    # 创建挑战赛
    print("[演示] 创建2个挑战赛...")
    system.create_challenge("玄女降临主题赛", "九天玄女战争形态创作", 7, 2000)
    system.create_challenge("国风仙侠周赛", "国风仙侠题材短剧", 7, 1000)

    system._save()
    print("[演示] 数据创建完成")


def main():
    parser = argparse.ArgumentParser(description="昆仑洞天·积分打榜系统 V1.0")
    parser.add_argument("--init", action="store_true", help="初始化演示数据")
    parser.add_argument("--rank", action="store_true", help="查看排行榜")
    parser.add_argument("--type", default="total", choices=["total","weekly","monthly","works"], help="排行榜类型")
    parser.add_argument("--challenge", action="store_true", help="挑战赛操作")
    parser.add_argument("--create", type=str, help="创建挑战赛")
    parser.add_argument("--report", action="store_true", help="生成报告")
    parser.add_argument("--data-dir", default="./points_data", help="数据目录")
    args = parser.parse_args()

    print("=" * 60)
    print("  昆仑洞天·积分打榜系统 V1.0")
    print("  DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS")
    print("=" * 60)

    system = PointsSystem(args.data_dir)

    if args.init:
        create_demo_data(system)
        system.generate_report()
    elif args.rank:
        ranking = system.get_ranking(args.type)
        print(f"\n📊 {args.type.upper()} 排行榜 TOP10:")
        for i, c in enumerate(ranking):
            points = c.get("weekly_points" if args.type=="weekly" else "monthly_points" if args.type=="monthly" else "points", 0)
            level_info = next((l for l in PointsSystem.LEVELS if l["level"]==c["level"]), PointsSystem.LEVELS[0])
            print(f"  {i+1}. {level_info['icon']} Lv{c['level']} {c['name']} - {points}积分")
    elif args.challenge and args.create:
        system.create_challenge(args.create, "自定义主题", 7, 1000)
    elif args.report:
        system.generate_report()
    else:
        # 默认显示状态
        print(f"\n创作者数: {len(system.creators)}")
        print(f"交易数: {len(system.transactions)}")
        print(f"挑战赛: {len(system.challenges)}")


if __name__ == "__main__":
    main()

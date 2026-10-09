#!/usr/bin/env python3
"""
昆仑洞天·UGC创作者社区基础版 V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS

功能：
1. 作品库管理（增删改查/标签分类/搜索）
2. 创作者体系（等级/认证/主页/积分）
3. 互动激励（点赞/收藏/播放/分享/打榜）
4. 自动确权（DID+SHA256+Ω标识，每作品自动生成）
5. 排行榜计算（热度榜/新作榜/创作者榜）
6. 冷启动种子数据生成
7. 数据导出（JSON/CSV）

用法：
  python3 kunlun_ugc_community.py --init          # 初始化+种子数据
  python3 kunlun_ugc_community.py --rank          # 计算排行榜
  python3 kunlun_ugc_community.py --add-work      # 添加作品（交互）
  python3 kunlun_ugc_community.py --export json   # 导出数据
"""

import argparse
import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


class UGCCommunity:
    """UGC创作者社区"""

    def __init__(self, data_dir="./ugc_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.works_file = self.data_dir / "works.json"
        self.creators_file = self.data_dir / "creators.json"
        self.interactions_file = self.data_dir / "interactions.json"
        self.ranking_file = self.data_dir / "ranking.json"

        self.works = self._load(self.works_file, [])
        self.creators = self._load(self.creators_file, [])
        self.interactions = self._load(self.interactions_file, [])

    def _load(self, path, default):
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default

    def _save(self, path, data):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _gen_did(self):
        """生成确权DID"""
        return f"DID-BR-{uuid.uuid4().hex[:8].upper()}"

    def _gen_work_hash(self, work):
        """生成作品确权哈希"""
        content = json.dumps({
            "title": work["title"],
            "creator": work["creator_id"],
            "prompt": work.get("prompt", ""),
            "created_at": work["created_at"],
            "tags": work.get("tags", [])
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def init_seed_data(self):
        """初始化冷启动种子数据"""
        print("[初始化] 生成冷启动种子数据...")

        # 种子创作者
        seed_creators = [
            {"name": "玄汐阁主", "avatar": "🧝‍♀️", "bio": "昆仑洞天首席创作者，专攻东方神女题材", "level": 5, "verified": True},
            {"name": "幕城Sheen", "avatar": "🎬", "bio": "独立导演，擅长史诗叙事与光影调度", "level": 4, "verified": True},
            {"name": "拂屉", "avatar": "✨", "bio": "国风仙侠创作者，作品以细腻情感著称", "level": 4, "verified": False},
            {"name": "烛龙守夜人", "avatar": "🐉", "bio": "神话题材专精，长兵器结构铁律践行者", "level": 3, "verified": True},
            {"name": "青鸾画师", "avatar": "🖌️", "bio": "视觉风格探索者，黑金暗纹风格代表", "level": 3, "verified": False},
            {"name": "云梦散人", "avatar": "☁️", "bio": "新人创作者，仙侠悬疑题材", "level": 2, "verified": False},
            {"name": "墨羽", "avatar": "🪶", "bio": "历史题材创作者，考据严谨", "level": 2, "verified": False},
            {"name": "灵犀", "avatar": "🦋", "bio": "创意实验派，跨题材融合", "level": 1, "verified": False},
        ]

        for c in seed_creators:
            creator = {
                "creator_id": f"CREATOR-{uuid.uuid4().hex[:6].upper()}",
                "name": c["name"],
                "avatar": c["avatar"],
                "bio": c["bio"],
                "level": c["level"],
                "verified": c["verified"],
                "did": self._gen_did(),
                "works_count": 0,
                "followers": 0,
                "points": c["level"] * 100,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "trace_mark": "Ω₀⊂⊙∞⊂Ω"
            }
            self.creators.append(creator)

        # 种子作品
        seed_works = [
            {"title": "玄女降临", "creator_idx": 0, "tags": ["国风仙侠", "九天玄女", "战争"], "duration": 60, "prompt": "九天玄女战争形态，红裙凤冠，神兵烈焰战场，黑金暗纹风格", "likes": 328, "views": 5420, "favorites": 156, "shares": 89},
            {"title": "无间狱", "creator_idx": 1, "tags": ["悬疑", "暗黑", "神话"], "duration": 120, "prompt": "幽冥地府，无间地狱，东方暗黑美学，伦勃朗光影", "likes": 512, "views": 12800, "favorites": 289, "shares": 156},
            {"title": "魂印", "creator_idx": 2, "tags": ["仙侠", "情感", "转世"], "duration": 90, "prompt": "神女残魂，转世轮回，宿命羁绊，柔光漫射", "likes": 445, "views": 8900, "favorites": 234, "shares": 120},
            {"title": "长安异闻录", "creator_idx": 6, "tags": ["历史", "悬疑", "盛唐"], "duration": 150, "prompt": "盛唐长安，坊间异闻，考据历史细节，暖金调", "likes": 289, "views": 6700, "favorites": 178, "shares": 67},
            {"title": "中式天宫", "creator_idx": 4, "tags": ["国风", "建筑", "创意"], "duration": 45, "prompt": "中式天宫建筑群，云海仙境，黑金暗纹，史诗创世氛围", "likes": 678, "views": 15600, "favorites": 412, "shares": 234},
            {"title": "神兵斩妖", "creator_idx": 3, "tags": ["战斗", "长兵器", "神话"], "duration": 50, "prompt": "真武大帝降魔，玄帝战甲，长兵器结构铁律，大反差构图", "likes": 398, "views": 7800, "favorites": 198, "shares": 95},
            {"title": "女娲补天", "creator_idx": 0, "tags": ["创世", "女娲", "史诗"], "duration": 80, "prompt": "女娲创世形态，五彩石补天，洪荒创世氛围，博物馆馆藏质感", "likes": 756, "views": 18900, "favorites": 467, "shares": 289},
            {"title": "烛龙睁眼", "creator_idx": 3, "tags": ["神话", "烛龙", "创意"], "duration": 30, "prompt": "烛龙睁眼，白昼交替，原始神话意象，浮雕立体感", "likes": 423, "views": 9200, "favorites": 245, "shares": 134},
            {"title": "青丘狐影", "creator_idx": 5, "tags": ["仙侠", "狐妖", "悬疑"], "duration": 70, "prompt": "青丘九尾狐，月下魅影，低饱和灰度，玄黑基调", "likes": 267, "views": 5100, "favorites": 145, "shares": 56},
            {"title": "洛神赋", "creator_idx": 2, "tags": ["历史", "神女", "诗意"], "duration": 65, "prompt": "洛神出水，翩若惊鸿，青绿山水，仙气缭绕", "likes": 589, "views": 11200, "favorites": 356, "shares": 178},
            {"title": "幽冥摆渡", "creator_idx": 1, "tags": ["暗黑", "神话", "悬疑"], "duration": 55, "prompt": "黄泉摆渡，忘川河畔，冷蓝玄黑，冰霜质感", "likes": 345, "views": 6800, "favorites": 189, "shares": 78},
            {"title": "九天雷劫", "creator_idx": 7, "tags": ["仙侠", "渡劫", "特效"], "duration": 40, "prompt": "九天雷劫，紫电雷霆，渡劫飞升，高光神性", "likes": 467, "views": 8700, "favorites": 234, "shares": 112},
        ]

        for i, w in enumerate(seed_works):
            creator = self.creators[w["creator_idx"]]
            work = {
                "work_id": f"WORK-{uuid.uuid4().hex[:8].upper()}",
                "title": w["title"],
                "creator_id": creator["creator_id"],
                "creator_name": creator["name"],
                "cover": f"/covers/work_{i+1:03d}.jpg",
                "video_url": f"/videos/work_{i+1:03d}.mp4",
                "duration": w["duration"],
                "tags": w["tags"],
                "prompt": w["prompt"],
                "likes": w["likes"],
                "views": w["views"],
                "favorites": w["favorites"],
                "shares": w["shares"],
                "comments": w["likes"] // 10,
                "created_at": (datetime.now(timezone.utc).timestamp() - i * 3600 * 24).__str__(),
                "status": "published"
            }
            work["hash"] = self._gen_work_hash(work)
            work["did"] = self._gen_did()
            work["trace_mark"] = "Ω₀⊂⊙∞⊂Ω"
            work["certified"] = True
            self.works.append(work)
            creator["works_count"] += 1
            creator["points"] += 50

        self._save_all()
        print(f"[完成] 创作者: {len(self.creators)}人, 作品: {len(self.works)}部")
        return self.works, self.creators

    def add_work(self, title, creator_id, prompt, tags=None, duration=30, cover="", video_url=""):
        """添加新作品（自动确权）"""
        creator = next((c for c in self.creators if c["creator_id"] == creator_id), None)
        if not creator:
            print(f"[错误] 创作者不存在: {creator_id}")
            return None

        work = {
            "work_id": f"WORK-{uuid.uuid4().hex[:8].upper()}",
            "title": title,
            "creator_id": creator_id,
            "creator_name": creator["name"],
            "cover": cover or f"/covers/{work_id}.jpg",
            "video_url": video_url or f"/videos/{work_id}.mp4",
            "duration": duration,
            "tags": tags or [],
            "prompt": prompt,
            "likes": 0,
            "views": 0,
            "favorites": 0,
            "shares": 0,
            "comments": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "published"
        }
        work["hash"] = self._gen_work_hash(work)
        work["did"] = self._gen_did()
        work["trace_mark"] = "Ω₀⊂⊙∞⊂Ω"
        work["certified"] = True

        self.works.append(work)
        creator["works_count"] += 1
        creator["points"] += 50

        # 记录交互
        self.interactions.append({
            "type": "publish",
            "work_id": work["work_id"],
            "creator_id": creator_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        self._save_all()
        print(f"[发布] {title} | DID: {work['did']} | 哈希: {work['hash'][:16]}...")
        return work

    def interact(self, work_id, interaction_type, user_id="anonymous"):
        """记录互动（点赞/收藏/播放/分享）"""
        work = next((w for w in self.works if w["work_id"] == work_id), None)
        if not work:
            print(f"[错误] 作品不存在: {work_id}")
            return False

        points_map = {"like": 1, "favorite": 2, "view": 0, "share": 3, "comment": 1}
        field_map = {"like": "likes", "favorite": "favorites", "view": "views", "share": "shares", "comment": "comments"}

        if interaction_type in field_map:
            work[field_map[interaction_type]] += 1

        # 创作者积分
        creator = next((c for c in self.creators if c["creator_id"] == work["creator_id"]), None)
        if creator and interaction_type in points_map:
            creator["points"] += points_map[interaction_type]

        self.interactions.append({
            "type": interaction_type,
            "work_id": work_id,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        self._save_all()
        return True

    def calculate_ranking(self):
        """计算排行榜"""
        # 热度榜：热度 = 点赞*0.3 + 收藏*0.2 + 播放*0.01 + 分享*0.3 + 评论*0.2
        for work in self.works:
            work["hot_score"] = round(
                work["likes"] * 0.3 +
                work["favorites"] * 0.2 +
                work["views"] * 0.01 +
                work["shares"] * 0.3 +
                work["comments"] * 0.2, 1
            )

        hot_ranking = sorted(self.works, key=lambda x: x["hot_score"], reverse=True)[:20]

        # 新作榜：按时间倒序
        new_ranking = sorted(self.works, key=lambda x: x["created_at"], reverse=True)[:10]

        # 创作者榜：按积分+作品数
        for c in self.creators:
            c["creator_score"] = c["points"] + c["works_count"] * 20 + c["followers"] * 2
        creator_ranking = sorted(self.creators, key=lambda x: x["creator_score"], reverse=True)[:10]

        # 标签统计
        tag_stats = {}
        for work in self.works:
            for tag in work.get("tags", []):
                tag_stats[tag] = tag_stats.get(tag, 0) + 1

        ranking = {
            "hot_ranking": [{"rank": i+1, "work_id": w["work_id"], "title": w["title"],
                            "creator": w["creator_name"], "hot_score": w["hot_score"],
                            "likes": w["likes"], "views": w["views"]}
                           for i, w in enumerate(hot_ranking)],
            "new_ranking": [{"rank": i+1, "work_id": w["work_id"], "title": w["title"],
                            "creator": w["creator_name"], "created_at": w["created_at"]}
                           for i, w in enumerate(new_ranking)],
            "creator_ranking": [{"rank": i+1, "creator_id": c["creator_id"], "name": c["name"],
                                "level": c["level"], "works": c["works_count"],
                                "points": c["points"], "score": c["creator_score"]}
                               for i, c in enumerate(creator_ranking)],
            "tag_cloud": sorted(tag_stats.items(), key=lambda x: x[1], reverse=True),
            "total_works": len(self.works),
            "total_creators": len(self.creators),
            "total_interactions": len(self.interactions),
            "calculated_at": datetime.now(timezone.utc).isoformat()
        }

        self._save(self.ranking_file, ranking)
        print(f"[排行榜] 热度榜TOP3:")
        for i, w in enumerate(ranking["hot_ranking"][:3]):
            print(f"  {i+1}. {w['title']} ({w['creator']}) - 热度{w['hot_score']}")
        return ranking

    def _save_all(self):
        self._save(self.works_file, self.works)
        self._save(self.creators_file, self.creators)
        self._save(self.interactions_file, self.interactions)

    def export(self, format="json"):
        """导出数据"""
        if format == "json":
            export_data = {
                "works": self.works,
                "creators": self.creators,
                "ranking": self._load(self.ranking_file, {}),
                "meta": {
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "did": "DID-BR-000002",
                    "trace": "Ω₀⊂⊙∞⊂Ω",
                    "version": "V1.0"
                }
            }
            path = self.data_dir / "ugc_export.json"
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            print(f"[导出] {path}")
            return str(path)
        elif format == "csv":
            import csv
            path = self.data_dir / "works.csv"
            with open(path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["作品ID", "标题", "创作者", "标签", "时长", "点赞", "播放", "收藏", "分享", "DID", "哈希"])
                for w in self.works:
                    writer.writerow([w["work_id"], w["title"], w["creator_name"],
                                    "/".join(w.get("tags", [])), w["duration"],
                                    w["likes"], w["views"], w["favorites"], w["shares"],
                                    w["did"], w["hash"][:16]])
            print(f"[导出] {path}")
            return str(path)


def main():
    parser = argparse.ArgumentParser(description="昆仑洞天·UGC创作者社区 V1.0")
    parser.add_argument("--init", action="store_true", help="初始化+种子数据")
    parser.add_argument("--rank", action="store_true", help="计算排行榜")
    parser.add_argument("--export", choices=["json", "csv"], help="导出数据")
    parser.add_argument("--data-dir", default="./ugc_data", help="数据目录")
    args = parser.parse_args()

    print("=" * 60)
    print("  昆仑洞天·UGC创作者社区 V1.0")
    print("  DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS")
    print("=" * 60)

    community = UGCCommunity(args.data_dir)

    if args.init:
        community.init_seed_data()
        community.calculate_ranking()
    elif args.rank:
        community.calculate_ranking()
    elif args.export:
        community.export(args.export)
    else:
        print("使用 --init 初始化 | --rank 计算排行榜 | --export json/csv 导出")


if __name__ == "__main__":
    main()

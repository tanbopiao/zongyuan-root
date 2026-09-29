#!/usr/bin/env python3
"""
昆仑洞天·商业化计费与创作者分成系统 V1.0
P4-3 生态闭环核心
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS

会员体系 + 作品付费 + 打赏系统 + 收益结算 + 创作者分成 + 积分兑换。
"""

import json
import hashlib
import time
import uuid
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime, timezone, timedelta


class MembershipTier(Enum):
    FREE = "free"           # 免费
    PRO = "pro"             # 专业版
    ENTERPRISE = "enterprise"  # 企业版


class TransactionType(Enum):
    MEMBERSHIP = "membership"     # 会员购买
    WORK_PURCHASE = "work_purchase"  # 作品购买
    WORK_RENT = "work_rent"       # 作品租赁
    TIP = "tip"                   # 打赏
    POINTS_REDEEM = "points_redeem"  # 积分兑换
    WITHDRAWAL = "withdrawal"     # 提现
    PLATFORM_FEE = "platform_fee"  # 平台手续费


class TransactionStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass
class Membership:
    """会员配置"""
    tier: MembershipTier
    name: str
    price_monthly: float
    price_yearly: float
    features: List[str]
    video_generations_monthly: int
    image_generations_monthly: int
    priority_support: bool = False


@dataclass
class Creator:
    """创作者账户"""
    creator_id: str
    name: str
    avatar: str = ""
    tier: str = "Lv1"
    total_earnings: float = 0.0
    available_balance: float = 0.0
    pending_balance: float = 0.0
    total_works: int = 0
    total_plays: int = 0
    total_likes: int = 0
    fans_count: int = 0
    join_date: str = ""
    bank_account: str = ""  # 脱敏存储
    withdrawal_history: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Work:
    """作品"""
    work_id: str
    title: str
    creator_id: str
    price: float = 0.0  # 0=免费
    rent_price: float = 0.0
    is_paid: bool = False
    total_revenue: float = 0.0
    total_purchases: int = 0
    total_tips: float = 0.0
    creator_share: float = 0.7  # 创作者分成比例70%

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Transaction:
    """交易记录"""
    transaction_id: str
    type: TransactionType
    user_id: str
    creator_id: Optional[str] = None
    work_id: Optional[str] = None
    amount: float = 0.0
    platform_fee: float = 0.0
    creator_share: float = 0.0
    status: TransactionStatus = TransactionStatus.PENDING
    description: str = ""
    created_at: str = ""
    completed_at: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['type'] = self.type.value
        d['status'] = self.status.value
        return d


class BillingSystem:
    """商业化计费系统主类"""

    def __init__(self, data_dir: str = "./billing_data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.memberships = self._init_memberships()
        self.creators: Dict[str, Creator] = {}
        self.works: Dict[str, Work] = {}
        self.transactions: List[Transaction] = []
        self.platform_revenue = 0.0
        self._init_demo_data()

    def _init_memberships(self) -> Dict[MembershipTier, Membership]:
        """初始化会员配置"""
        return {
            MembershipTier.FREE: Membership(
                tier=MembershipTier.FREE, name="免费版",
                price_monthly=0, price_yearly=0,
                features=["基础作品浏览", "每日3次视频生成", "社区互动", "积分获取"],
                video_generations_monthly=90, image_generations_monthly=300
            ),
            MembershipTier.PRO: Membership(
                tier=MembershipTier.PRO, name="专业版",
                price_monthly=99, price_yearly=999,
                features=["全部作品浏览", "每日30次视频生成", "高清无水印", "优先算力调度", "专属客服", "创作者分成"],
                video_generations_monthly=900, image_generations_monthly=3000,
                priority_support=True
            ),
            MembershipTier.ENTERPRISE: Membership(
                tier=MembershipTier.ENTERPRISE, name="企业版",
                price_monthly=999, price_yearly=9999,
                features=["全部功能", "无限视频生成", "API接入", "私有部署", "专属团队", "SLA保障", "定制开发"],
                video_generations_monthly=99999, image_generations_monthly=99999,
                priority_support=True
            ),
        }

    def _init_demo_data(self):
        """初始化演示数据"""
        demo_creators = [
            Creator("creator_001", "玄汐阁主", tier="Lv5", total_earnings=12580.50,
                   available_balance=3200.00, pending_balance=580.50, total_works=24,
                   total_plays=156000, total_likes=45000, fans_count=8900,
                   join_date="2026-01-15"),
            Creator("creator_002", "幕城Sheen", tier="Lv4", total_earnings=8920.30,
                   available_balance=2100.00, pending_balance=420.30, total_works=18,
                   total_plays=98000, total_likes=32000, fans_count=5600,
                   join_date="2026-02-20"),
            Creator("creator_003", "拂屉", tier="Lv3", total_earnings=5640.00,
                   available_balance=1500.00, pending_balance=240.00, total_works=12,
                   total_plays=67000, total_likes=21000, fans_count=3400,
                   join_date="2026-03-10"),
            Creator("creator_004", "烛龙守夜人", tier="Lv3", total_earnings=4280.80,
                   available_balance=1100.00, pending_balance=180.80, total_works=15,
                   total_plays=52000, total_likes=18000, fans_count=2800,
                   join_date="2026-03-25"),
            Creator("creator_005", "青鸾画师", tier="Lv2", total_earnings=2150.00,
                   available_balance=600.00, pending_balance=150.00, total_works=8,
                   total_plays=28000, total_likes=9500, fans_count=1500,
                   join_date="2026-05-01"),
        ]
        for c in demo_creators:
            self.creators[c.creator_id] = c

        demo_works = [
            Work("work_001", "玄女降临", "creator_001", price=9.9, rent_price=2.9,
                is_paid=True, total_revenue=3560.00, total_purchases=280, total_tips=580.00),
            Work("work_002", "神兵斩妖", "creator_001", price=9.9, rent_price=2.9,
                is_paid=True, total_revenue=2890.00, total_purchases=220, total_tips=420.00),
            Work("work_003", "无间狱", "creator_002", price=12.9, rent_price=3.9,
                is_paid=True, total_revenue=4120.00, total_purchases=310, total_tips=680.00),
            Work("work_004", "魂印", "creator_002", price=0, is_paid=False,
                total_revenue=890.00, total_purchases=0, total_tips=890.00),
            Work("work_005", "长安异闻录", "creator_003", price=6.9, rent_price=1.9,
                is_paid=True, total_revenue=1850.00, total_purchases=180, total_tips=320.00),
            Work("work_006", "中式天宫", "creator_004", price=0, is_paid=False,
                total_revenue=560.00, total_purchases=0, total_tips=560.00),
        ]
        for w in demo_works:
            self.works[w.work_id] = w

    def purchase_membership(self, user_id: str, tier: MembershipTier,
                           billing_cycle: str = "monthly") -> Transaction:
        """购买会员"""
        membership = self.memberships[tier]
        amount = membership.price_monthly if billing_cycle == "monthly" else membership.price_yearly
        tx = Transaction(
            transaction_id=f"tx_{uuid.uuid4().hex[:12]}",
            type=TransactionType.MEMBERSHIP,
            user_id=user_id,
            amount=amount,
            platform_fee=0,
            creator_share=0,
            status=TransactionStatus.COMPLETED,
            description=f"购买{membership.name}（{'月付' if billing_cycle=='monthly' else '年付'}）",
            created_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat()
        )
        self.transactions.append(tx)
        self.platform_revenue += amount
        return tx

    def purchase_work(self, user_id: str, work_id: str) -> Optional[Transaction]:
        """购买作品"""
        work = self.works.get(work_id)
        if not work or not work.is_paid:
            return None
        creator = self.creators.get(work.creator_id)
        platform_fee = round(work.price * (1 - work.creator_share), 2)
        creator_amount = round(work.price * work.creator_share, 2)

        tx = Transaction(
            transaction_id=f"tx_{uuid.uuid4().hex[:12]}",
            type=TransactionType.WORK_PURCHASE,
            user_id=user_id,
            creator_id=work.creator_id,
            work_id=work_id,
            amount=work.price,
            platform_fee=platform_fee,
            creator_share=creator_amount,
            status=TransactionStatus.COMPLETED,
            description=f"购买作品《{work.title}》",
            created_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat()
        )
        self.transactions.append(tx)
        work.total_revenue += work.price
        work.total_purchases += 1
        self.platform_revenue += platform_fee
        if creator:
            creator.pending_balance += creator_amount
            creator.total_earnings += creator_amount
        return tx

    def send_tip(self, user_id: str, creator_id: str, work_id: str,
                 amount: float) -> Optional[Transaction]:
        """打赏创作者"""
        creator = self.creators.get(creator_id)
        work = self.works.get(work_id)
        if not creator:
            return None
        platform_fee = round(amount * 0.1, 2)  # 平台抽成10%
        creator_amount = round(amount * 0.9, 2)

        tx = Transaction(
            transaction_id=f"tx_{uuid.uuid4().hex[:12]}",
            type=TransactionType.TIP,
            user_id=user_id,
            creator_id=creator_id,
            work_id=work_id,
            amount=amount,
            platform_fee=platform_fee,
            creator_share=creator_amount,
            status=TransactionStatus.COMPLETED,
            description=f"打赏创作者{creator.name} - 《{work.title if work else '未知作品'}》",
            created_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat()
        )
        self.transactions.append(tx)
        creator.pending_balance += creator_amount
        creator.total_earnings += creator_amount
        if work:
            work.total_tips += amount
        self.platform_revenue += platform_fee
        return tx

    def request_withdrawal(self, creator_id: str, amount: float) -> Optional[Transaction]:
        """创作者提现申请"""
        creator = self.creators.get(creator_id)
        if not creator or creator.available_balance < amount:
            return None
        tx = Transaction(
            transaction_id=f"tx_{uuid.uuid4().hex[:12]}",
            type=TransactionType.WITHDRAWAL,
            user_id=creator_id,
            creator_id=creator_id,
            amount=amount,
            status=TransactionStatus.PENDING,
            description=f"创作者提现申请 - ¥{amount}",
            created_at=datetime.now(timezone.utc).isoformat()
        )
        self.transactions.append(tx)
        creator.available_balance -= amount
        creator.withdrawal_history.append({
            "transaction_id": tx.transaction_id,
            "amount": amount,
            "status": "pending",
            "created_at": tx.created_at
        })
        return tx

    def settle_pending(self, creator_id: str):
        """结算待结算收益（每月结算）"""
        creator = self.creators.get(creator_id)
        if not creator:
            return
        creator.available_balance += creator.pending_balance
        creator.pending_balance = 0.0

    def get_creator_earnings(self, creator_id: str) -> Dict:
        """获取创作者收益统计"""
        creator = self.creators.get(creator_id)
        if not creator:
            return {}
        creator_works = [w for w in self.works.values() if w.creator_id == creator_id]
        return {
            "creator_id": creator.creator_id,
            "name": creator.name,
            "tier": creator.tier,
            "total_earnings": creator.total_earnings,
            "available_balance": creator.available_balance,
            "pending_balance": creator.pending_balance,
            "total_works": creator.total_works,
            "total_plays": creator.total_plays,
            "total_likes": creator.total_likes,
            "fans_count": creator.fans_count,
            "works_revenue": {w.title: w.total_revenue for w in creator_works},
            "works_tips": {w.title: w.total_tips for w in creator_works},
        }

    def get_platform_stats(self) -> Dict:
        """获取平台统计"""
        total_creator_earnings = sum(c.total_earnings for c in self.creators.values())
        total_work_revenue = sum(w.total_revenue for w in self.works.values())
        paid_works = len([w for w in self.works.values() if w.is_paid])
        return {
            "total_creators": len(self.creators),
            "total_works": len(self.works),
            "paid_works": paid_works,
            "free_works": len(self.works) - paid_works,
            "platform_revenue": round(self.platform_revenue, 2),
            "total_creator_earnings": round(total_creator_earnings, 2),
            "total_work_revenue": round(total_work_revenue, 2),
            "total_transactions": len(self.transactions),
            "membership_tiers": {t.value: m.name for t, m in self.memberships.items()},
            "creator_share_rate": "70%",
            "platform_fee_rate": "30%（作品）/ 10%（打赏）",
        }

    def get_leaderboard(self, limit: int = 5) -> List[Dict]:
        """创作者收益排行榜"""
        sorted_creators = sorted(self.creators.values(),
                                key=lambda c: c.total_earnings, reverse=True)
        return [{"rank": i+1, "name": c.name, "tier": c.tier,
                 "earnings": c.total_earnings, "works": c.total_works,
                 "fans": c.fans_count} for i, c in enumerate(sorted_creators[:limit])]

    def save_report(self, filepath: Optional[str] = None) -> str:
        """保存报告"""
        report = {
            "report_id": f"BILL-RPT-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "did": "DID-BR-000002",
            "trace_chain": "Ω₀⊂⊙∞⊂Ω",
            "platform_stats": self.get_platform_stats(),
            "creator_leaderboard": self.get_leaderboard(),
            "recent_transactions": [t.to_dict() for t in self.transactions[-10:]],
        }
        if filepath is None:
            filepath = os.path.join(self.data_dir, f"report_{int(time.time())}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return filepath


# ============ CLI ============
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="昆仑洞天·商业化计费与创作者分成系统")
    parser.add_argument("--demo", action="store_true", help="运行演示")
    parser.add_argument("--stats", action="store_true", help="查看平台统计")
    parser.add_argument("--leaderboard", action="store_true", help="创作者排行榜")
    parser.add_argument("--creator", type=str, help="查看创作者收益")
    parser.add_argument("--report", action="store_true", help="生成报告")
    parser.add_argument("--data-dir", type=str, default="./billing_data")
    args = parser.parse_args()

    print("=" * 60)
    print("  昆仑洞天·商业化计费与创作者分成系统 V1.0")
    print("  DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS")
    print("=" * 60)

    system = BillingSystem(data_dir=args.data_dir)

    if args.demo:
        print("\n[演示] 模拟交易...")
        # 购买会员
        tx1 = system.purchase_membership("user_001", MembershipTier.PRO, "monthly")
        print(f"  ✅ 会员购买: ¥{tx1.amount} - {tx1.description}")
        # 购买作品
        tx2 = system.purchase_work("user_001", "work_001")
        print(f"  ✅ 作品购买: ¥{tx2.amount} - 创作者分成¥{tx2.creator_share} 平台费¥{tx2.platform_fee}")
        # 打赏
        tx3 = system.send_tip("user_002", "creator_001", "work_001", 50.0)
        print(f"  ✅ 打赏: ¥{tx3.amount} - 创作者分成¥{tx3.creator_share} 平台费¥{tx3.platform_fee}")
        # 结算
        system.settle_pending("creator_001")
        creator = system.creators["creator_001"]
        print(f"  ✅ 结算完成: {creator.name} 可用余额¥{creator.available_balance}")

    elif args.stats:
        print(f"\n[平台统计] {json.dumps(system.get_platform_stats(), ensure_ascii=False, indent=2)}")

    elif args.leaderboard:
        print("\n[创作者收益排行榜 TOP5]")
        for c in system.get_leaderboard():
            print(f"  #{c['rank']} {c['name']:12s} | Lv{c['tier']:3s} | 收益¥{c['earnings']:>10.2f} | 作品{c['works']} | 粉丝{c['fans']}")

    elif args.creator:
        earnings = system.get_creator_earnings(args.creator)
        print(f"\n[创作者收益] {json.dumps(earnings, ensure_ascii=False, indent=2)}")

    elif args.report:
        path = system.save_report()
        print(f"\n[报告] 已保存: {path}")

    else:
        parser.print_help()

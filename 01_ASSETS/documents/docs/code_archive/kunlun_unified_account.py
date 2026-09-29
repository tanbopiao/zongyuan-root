#!/usr/bin/env python3
"""
昆仑洞天·统一账号与多端适配系统 V1.0
P4-4 生态闭环核心（P4阶段收官）
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS

统一账号体系 + 多端适配 + SSO单点登录 + 响应式布局 + 设备管理 + 权限体系。
"""

import json
import hashlib
import time
import uuid
import os
import secrets
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Set
from enum import Enum
from datetime import datetime, timezone, timedelta


class UserRole(Enum):
    USER = "user"           # 普通用户
    CREATOR = "creator"     # 创作者
    ADMIN = "admin"         # 管理员


class DeviceType(Enum):
    WEB = "web"
    MOBILE = "mobile"
    MINIPROGRAM = "miniprogram"
    DESKTOP = "desktop"
    TABLET = "tablet"


class PlatformType(Enum):
    IOS = "ios"
    ANDROID = "android"
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    WEB_BROWSER = "web_browser"
    WECHAT = "wechat"


@dataclass
class User:
    """用户账户"""
    user_id: str
    username: str
    email: str
    phone: str = ""
    role: UserRole = UserRole.USER
    avatar: str = ""
    membership_tier: str = "free"
    created_at: str = ""
    last_login_at: str = ""
    status: str = "active"  # active/banned/suspended
    points: int = 0
    total_plays: int = 0
    favorite_works: List[str] = field(default_factory=list)
    preferences: Dict = field(default_factory=dict)
    two_factor_enabled: bool = False

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['role'] = self.role.value
        return d


@dataclass
class Device:
    """登录设备"""
    device_id: str
    user_id: str
    device_type: DeviceType
    platform: PlatformType
    device_name: str
    ip_address: str = ""
    location: str = ""
    last_active: str = ""
    is_current: bool = False
    trusted: bool = False

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['device_type'] = self.device_type.value
        d['platform'] = self.platform.value
        return d


@dataclass
class Session:
    """会话Token"""
    session_id: str
    user_id: str
    device_id: str
    token: str
    refresh_token: str
    created_at: str
    expires_at: str
    is_valid: bool = True

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ResponsiveLayout:
    """响应式布局配置"""
    breakpoint_name: str
    min_width: int
    max_width: int
    columns: int
    font_scale: float
    sidebar_collapsed: bool
    touch_optimized: bool
    description: str


class UnifiedAccountSystem:
    """统一账号与多端适配系统主类"""

    def __init__(self, data_dir: str = "./account_data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.users: Dict[str, User] = {}
        self.devices: Dict[str, Device] = {}
        self.sessions: Dict[str, Session] = {}
        self.layouts = self._init_layouts()
        self._init_demo_data()

    def _init_layouts(self) -> List[ResponsiveLayout]:
        """初始化响应式断点配置"""
        return [
            ResponsiveLayout("mobile", 0, 480, 1, 0.85, True, True, "手机竖屏"),
            ResponsiveLayout("mobile_large", 481, 768, 2, 0.9, True, True, "手机横屏/小平板"),
            ResponsiveLayout("tablet", 769, 1024, 2, 0.95, False, True, "平板"),
            ResponsiveLayout("laptop", 1025, 1440, 3, 1.0, False, False, "笔记本电脑"),
            ResponsiveLayout("desktop", 1441, 1920, 4, 1.0, False, False, "桌面电脑"),
            ResponsiveLayout("wide", 1921, 99999, 5, 1.05, False, False, "超宽屏"),
        ]

    def _init_demo_data(self):
        """初始化演示数据"""
        demo_users = [
            User("user_001", "玄汐阁主", "xuanxi@huodouai.com", role=UserRole.CREATOR,
                 membership_tier="pro", points=12500, total_plays=3200,
                 preferences={"theme":"dark","language":"zh-CN","autoplay":True}),
            User("user_002", "幕城Sheen", "mucheng@huodouai.com", role=UserRole.CREATOR,
                 membership_tier="pro", points=8900, total_plays=2100,
                 preferences={"theme":"dark","language":"zh-CN","autoplay":False}),
            User("user_003", "普通用户A", "user_a@huodouai.com", role=UserRole.USER,
                 membership_tier="free", points=320, total_plays=150,
                 preferences={"theme":"light","language":"zh-CN","autoplay":True}),
            User("user_004", "拂屉", "futi@huodouai.com", role=UserRole.CREATOR,
                 membership_tier="free", points=5600, total_plays=1800,
                 preferences={"theme":"dark","language":"zh-CN","autoplay":True}),
            User("user_005", "admin", "admin@huodouai.com", role=UserRole.ADMIN,
                 membership_tier="enterprise", points=99999, total_plays=5000,
                 preferences={"theme":"dark","language":"zh-CN","autoplay":False}),
        ]
        for u in demo_users:
            u.created_at = "2026-01-15T00:00:00Z"
            u.last_login_at = datetime.now(timezone.utc).isoformat()
            self.users[u.user_id] = u

        demo_devices = [
            Device("dev_001", "user_001", DeviceType.WEB, PlatformType.WEB_BROWSER,
                   "Chrome on Windows", "192.168.1.100", "深圳", is_current=True, trusted=True),
            Device("dev_002", "user_001", DeviceType.MOBILE, PlatformType.IOS,
                   "iPhone 15 Pro", "10.0.0.50", "深圳", trusted=True),
            Device("dev_003", "user_001", DeviceType.MINIPROGRAM, PlatformType.WECHAT,
                   "微信小程序", "10.0.0.50", "深圳"),
            Device("dev_004", "user_002", DeviceType.WEB, PlatformType.MACOS,
                   "Safari on MacBook", "192.168.1.101", "北京", is_current=True, trusted=True),
            Device("dev_005", "user_003", DeviceType.MOBILE, PlatformType.ANDROID,
                   "小米14", "10.0.0.51", "上海", is_current=True),
        ]
        for d in demo_devices:
            d.last_active = datetime.now(timezone.utc).isoformat()
            self.devices[d.device_id] = d

    def register_user(self, username: str, email: str, password: str) -> Optional[User]:
        """注册新用户"""
        # 检查重复
        for u in self.users.values():
            if u.email == email or u.username == username:
                return None
        user = User(
            user_id=f"user_{uuid.uuid4().hex[:8]}",
            username=username,
            email=email,
            role=UserRole.USER,
            membership_tier="free",
            created_at=datetime.now(timezone.utc).isoformat(),
            points=100,  # 注册奖励
        )
        self.users[user.user_id] = user
        return user

    def login(self, email: str, password: str, device_type: DeviceType,
              platform: PlatformType, device_name: str, ip: str = "") -> Optional[Dict]:
        """登录（返回会话信息）"""
        user = None
        for u in self.users.values():
            if u.email == email:
                user = u
                break
        if not user:
            return None

        # 创建设备
        device = Device(
            device_id=f"dev_{uuid.uuid4().hex[:8]}",
            user_id=user.user_id,
            device_type=device_type,
            platform=platform,
            device_name=device_name,
            ip_address=ip,
            last_active=datetime.now(timezone.utc).isoformat(),
            is_current=True
        )
        self.devices[device.device_id] = device

        # 创建会话
        now = datetime.now(timezone.utc)
        session = Session(
            session_id=f"sess_{uuid.uuid4().hex[:8]}",
            user_id=user.user_id,
            device_id=device.device_id,
            token=secrets.token_hex(32),
            refresh_token=secrets.token_hex(32),
            created_at=now.isoformat(),
            expires_at=(now + timedelta(hours=24)).isoformat(),
        )
        self.sessions[session.session_id] = session

        user.last_login_at = now.isoformat()

        return {
            "user": user.to_dict(),
            "device": device.to_dict(),
            "session": session.to_dict(),
            "layout": self.get_layout_for_device(device_type).__dict__ if hasattr(self.get_layout_for_device(device_type), '__dict__') else None
        }

    def logout(self, session_id: str) -> bool:
        """登出"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        session.is_valid = False
        return True

    def logout_all_devices(self, user_id: str) -> int:
        """登出所有设备"""
        count = 0
        for s in self.sessions.values():
            if s.user_id == user_id and s.is_valid:
                s.is_valid = False
                count += 1
        return count

    def refresh_token(self, refresh_token: str) -> Optional[Dict]:
        """刷新Token"""
        for s in self.sessions.values():
            if s.refresh_token == refresh_token and s.is_valid:
                now = datetime.now(timezone.utc)
                s.token = secrets.token_hex(32)
                s.refresh_token = secrets.token_hex(32)
                s.created_at = now.isoformat()
                s.expires_at = (now + timedelta(hours=24)).isoformat()
                return {"token": s.token, "refresh_token": s.refresh_token, "expires_at": s.expires_at}
        return None

    def get_user_devices(self, user_id: str) -> List[Device]:
        """获取用户所有登录设备"""
        return [d for d in self.devices.values() if d.user_id == user_id]

    def revoke_device(self, device_id: str) -> bool:
        """远程下线设备"""
        device = self.devices.get(device_id)
        if not device:
            return False
        # 使该设备的所有会话失效
        for s in self.sessions.values():
            if s.device_id == device_id:
                s.is_valid = False
        return True

    def get_layout_for_device(self, device_type: DeviceType) -> ResponsiveLayout:
        """根据设备类型获取推荐布局"""
        if device_type == DeviceType.MOBILE:
            return self.layouts[0]  # mobile
        elif device_type == DeviceType.TABLET:
            return self.layouts[2]  # tablet
        elif device_type == DeviceType.MINIPROGRAM:
            return self.layouts[1]  # mobile_large
        else:
            return self.layouts[3]  # laptop

    def get_layout_for_width(self, width: int) -> ResponsiveLayout:
        """根据屏幕宽度获取布局"""
        for layout in self.layouts:
            if layout.min_width <= width <= layout.max_width:
                return layout
        return self.layouts[3]

    def sync_preferences(self, user_id: str, preferences: Dict) -> bool:
        """同步用户偏好（跨端）"""
        user = self.users.get(user_id)
        if not user:
            return False
        user.preferences.update(preferences)
        return True

    def upgrade_role(self, user_id: str, new_role: UserRole) -> bool:
        """升级用户角色"""
        user = self.users.get(user_id)
        if not user:
            return False
        user.role = new_role
        return True

    def get_stats(self) -> Dict:
        """获取系统统计"""
        role_counts = {r.value: 0 for r in UserRole}
        device_counts = {d.value: 0 for d in DeviceType}
        for u in self.users.values():
            role_counts[u.role.value] += 1
        for d in self.devices.values():
            device_counts[d.device_type.value] += 1
        active_sessions = len([s for s in self.sessions.values() if s.is_valid])
        return {
            "total_users": len(self.users),
            "role_distribution": role_counts,
            "total_devices": len(self.devices),
            "device_distribution": device_counts,
            "active_sessions": active_sessions,
            "supported_platforms": [p.value for p in PlatformType],
            "responsive_breakpoints": len(self.layouts),
        }

    def save_report(self, filepath: Optional[str] = None) -> str:
        """保存报告"""
        report = {
            "report_id": f"ACCT-RPT-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "did": "DID-BR-000002",
            "trace_chain": "Ω₀⊂⊙∞⊂Ω",
            "stats": self.get_stats(),
            "responsive_layouts": [asdict(l) for l in self.layouts],
            "users": [u.to_dict() for u in list(self.users.values())[:5]],
        }
        if filepath is None:
            filepath = os.path.join(self.data_dir, f"report_{int(time.time())}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return filepath


# ============ CLI ============
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="昆仑洞天·统一账号与多端适配系统")
    parser.add_argument("--demo", action="store_true", help="运行演示")
    parser.add_argument("--stats", action="store_true", help="查看统计")
    parser.add_argument("--layouts", action="store_true", help="查看响应式布局")
    parser.add_argument("--devices", type=str, help="查看用户设备列表")
    parser.add_argument("--report", action="store_true", help="生成报告")
    parser.add_argument("--data-dir", type=str, default="./account_data")
    args = parser.parse_args()

    print("=" * 60)
    print("  昆仑洞天·统一账号与多端适配系统 V1.0")
    print("  DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 火斗云智AIOS")
    print("=" * 60)

    system = UnifiedAccountSystem(data_dir=args.data_dir)

    if args.demo:
        print("\n[演示] 用户登录（Web端）...")
        result = system.login("xuanxi@huodouai.com", "password",
                            DeviceType.WEB, PlatformType.WEB_BROWSER,
                            "Chrome on Windows", "192.168.1.100")
        if result:
            print(f"  ✅ 登录成功: {result['user']['username']}")
            print(f"  Token: {result['session']['token'][:16]}...")
            print(f"  推荐布局: {result['layout']['breakpoint_name'] if result['layout'] else 'N/A'}")

        print("\n[演示] 用户登录（移动端）...")
        result2 = system.login("xuanxi@huodouai.com", "password",
                             DeviceType.MOBILE, PlatformType.IOS,
                             "iPhone 15 Pro", "10.0.0.50")
        if result2:
            print(f"  ✅ 登录成功: {result2['user']['username']}")
            print(f"  推荐布局: {result2['layout']['breakpoint_name'] if result2['layout'] else 'N/A'}")

        print("\n[演示] 同步用户偏好...")
        system.sync_preferences("user_001", {"theme":"dark","language":"zh-CN","autoplay":True})
        print(f"  ✅ 偏好已同步")

        print("\n[演示] 查看用户设备...")
        devices = system.get_user_devices("user_001")
        for d in devices:
            print(f"  - {d.device_name} ({d.device_type.value}) {'[当前]' if d.is_current else ''}")

    elif args.stats:
        print(f"\n[统计] {json.dumps(system.get_stats(), ensure_ascii=False, indent=2)}")

    elif args.layouts:
        print("\n[响应式布局断点]")
        for l in system.layouts:
            print(f"  {l.breakpoint_name:15s} | {l.min_width:>5d}-{l.max_width:<6d}px | {l.columns}列 | 字体×{l.font_scale} | {l.description}")

    elif args.devices:
        devices = system.get_user_devices(args.devices)
        print(f"\n[用户设备列表] {len(devices)}个设备")
        for d in devices:
            print(f"  - {d.device_name} ({d.device_type.value}/{d.platform.value}) IP:{d.ip_address} {'[当前]' if d.is_current else ''}")

    elif args.report:
        path = system.save_report()
        print(f"\n[报告] 已保存: {path}")

    else:
        parser.print_help()

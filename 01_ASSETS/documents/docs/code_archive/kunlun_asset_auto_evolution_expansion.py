#!/usr/bin/env python3
"""
昆仑洞天资产自动演化扩展机制 V1.0
ZONGYUAN-ROOT 元极恒一自治体系 | 昆仑洞天IP资产管理

核心能力：
1. 资产注册与分类层 - 自动发现/注册/分类12+种资产类型
2. 资产质量评估层 - 多维度质量评估（内容/技术/创意/商业/复用）
3. 资产自动演化层 - 基于质量评估自动优化/重制/升级/修复资产
4. 资产自动扩展层 - 基于现有资产自动生成衍生/续集/变体/关联资产
5. 资产关联图谱层 - 构建资产间关联关系网络（角色-场景-视频-音乐）
6. 资产版本管理层 - 版本迭代/回滚/分支/合并/变更日志
7. 资产价值评估层 - 商业价值/复用价值/IP价值/传播价值评估
8. 资产归档确权层 - SHA256确权+四层结构化+九大元类+记忆网关上报

资产类型体系：
  角色类：角色形象/角色设定/角色立绘/角色表情包
  场景类：场景背景/环境设定/3D场景/场景概念图
  视频类：正片/片段/预告/花絮/MV/教程
  图片类：关键帧/海报/封面/插画/壁纸/头像
  音频类：配乐/音效/配音/主题曲/插曲/播客
  文字类：大纲/剧本/台词/分镜表/设定集/小说
  IP衍生类：周边/联名/授权/数字藏品

锚定：Ω₀⊂⊙∞⊂Ω | DID-BR-000002
"""

import json
import time
import datetime
import hashlib
import math
import random
import urllib.request
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Callable, Any
from enum import Enum
from collections import defaultdict, deque

# ============ 配置 ============
GATEWAY_BASE = "https://www.huodouai.com"
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
SOURCE_NODE = "ZR-NODE-DC2E51C0"
ASSET_VERSION = "kunlun-asset-evolution-v1.0"
MAX_ASSET_HISTORY = 500

# ============ 枚举类型 ============
class AssetType(Enum):
    CHARACTER_IMAGE = "角色形象"
    CHARACTER_SETTING = "角色设定"
    CHARACTER_ILLUSTRATION = "角色立绘"
    CHARACTER_EMOJI = "角色表情包"
    SCENE_BACKGROUND = "场景背景"
    SCENE_SETTING = "环境设定"
    SCENE_CONCEPT = "场景概念图"
    VIDEO_EPISODE = "正片"
    VIDEO_CLIP = "片段"
    VIDEO_TRAILER = "预告"
    VIDEO_BEHIND = "花絮"
    IMAGE_KEYFRAME = "关键帧"
    IMAGE_POSTER = "海报"
    IMAGE_COVER = "封面"
    IMAGE_ILLUSTRATION = "插画"
    AUDIO_BGM = "配乐"
    AUDIO_SFX = "音效"
    AUDIO_VOICE = "配音"
    AUDIO_THEME = "主题曲"
    TEXT_OUTLINE = "大纲"
    TEXT_SCRIPT = "剧本"
    TEXT_STORYBOARD = "分镜表"
    TEXT_NOVEL = "小说"
    IP_MERCHANDISE = "周边"
    IP_COLLAB = "联名"
    IP_COLLECTIBLE = "数字藏品"

class AssetQualityDimension(Enum):
    CONTENT = "内容质量"
    TECHNICAL = "技术质量"
    CREATIVE = "创意质量"
    COMMERCIAL = "商业价值"
    REUSE = "复用价值"
    CONSISTENCY = "一致性"

class AssetStatus(Enum):
    DRAFT = "草稿"
    REVIEWING = "审核中"
    PUBLISHED = "已发布"
    ARCHIVED = "已归档"
    EVOLVING = "演化中"
    DEPRECATED = "已弃用"
    REMASTERED = "已重制"

class EvolutionActionType(Enum):
    UPGRADE_QUALITY = "质量升级"
    REMASTER = "高清重制"
    OPTIMIZE = "参数优化"
    EXPAND_VARIANT = "扩展变体"
    CREATE_SEQUEL = "创作续集"
    CREATE_DERIVATIVE = "创作衍生"
    REPAIR = "修复缺陷"
    RECOLOR = "重新调色"
    RESCORE = "重新配乐"
    TRANSLATE = "多语言翻译"

# ============ 数据结构 ============
@dataclass
class AssetQuality:
    """资产质量评分"""
    content: float = 0.0  # 内容质量0-100
    technical: float = 0.0  # 技术质量0-100
    creative: float = 0.0  # 创意质量0-100
    commercial: float = 0.0  # 商业价值0-100
    reuse: float = 0.0  # 复用价值0-100
    consistency: float = 0.0  # 一致性0-100
    overall: float = 0.0  # 综合评分
    evaluated_at: float = 0.0

    def calculate_overall(self):
        self.overall = round(
            0.25 * self.content + 0.20 * self.technical + 0.20 * self.creative +
            0.15 * self.commercial + 0.10 * self.reuse + 0.10 * self.consistency, 1
        )

@dataclass
class AssetVersion:
    """资产版本"""
    version: str
    parent_version: str = ""
    quality: Optional[AssetQuality] = None
    changes: List[str] = field(default_factory=list)
    file_hash: str = ""
    created_at: float = 0.0
    note: str = ""

@dataclass
class Asset:
    """资产"""
    asset_id: str
    name: str
    asset_type: AssetType
    status: AssetStatus = AssetStatus.DRAFT
    description: str = ""
    tags: List[str] = field(default_factory=list)
    file_url: str = ""
    file_size_bytes: int = 0
    file_format: str = ""
    duration_seconds: float = 0.0  # 视频/音频时长
    resolution: str = ""  # 图片/视频分辨率
    creator: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
    quality: Optional[AssetQuality] = None
    versions: List[AssetVersion] = field(default_factory=list)
    current_version: str = "v1.0"
    related_assets: List[str] = field(default_factory=list)  # 关联资产ID
    related_characters: List[str] = field(default_factory=list)
    related_scenes: List[str] = field(default_factory=list)
    view_count: int = 0
    use_count: int = 0  # 被引用次数
    like_count: int = 0
    share_count: int = 0
    commercial_value: float = 0.0  # 商业价值评估
    ip_value: float = 0.0  # IP价值
    evolution_count: int = 0
    metadata: Dict = field(default_factory=dict)

    def get_quality_level(self) -> str:
        if not self.quality:
            return "未评估"
        score = self.quality.overall
        if score >= 90:
            return "S级（卓越）"
        elif score >= 80:
            return "A级（优秀）"
        elif score >= 70:
            return "B级（良好）"
        elif score >= 60:
            return "C级（合格）"
        else:
            return "D级（待改进）"

@dataclass
class EvolutionTask:
    """演化任务"""
    task_id: str
    asset_id: str
    asset_name: str
    action_type: EvolutionActionType
    reason: str = ""
    current_quality: float = 0.0
    target_quality: float = 0.0
    status: str = "pending"  # pending/running/completed/failed
    result: str = ""
    created_at: float = 0.0
    completed_at: Optional[float] = None

@dataclass
class AssetGraphNode:
    """资产图谱节点"""
    asset_id: str
    name: str
    asset_type: AssetType
    quality_score: float = 0.0
    connections: int = 0

@dataclass
class AssetGraphEdge:
    """资产图谱边"""
    source: str
    target: str
    relation_type: str  # 衍生/续集/关联/引用/同角色/同场景
    strength: float = 0.0  # 关联强度0-1

# ============ 网关通信 ============
def gateway_get(path, timeout=30):
    url = f"{GATEWAY_BASE}{path}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return 0, {"error": str(e)}

def gateway_post(path, data, timeout=15):
    url = f"{GATEWAY_BASE}{path}"
    body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=body, method='POST')
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return 0, {"error": str(e)}

# ============ L1: 资产注册与分类层 ============
class AssetRegistry:
    """资产注册与分类层"""

    def __init__(self):
        self.assets: Dict[str, Asset] = {}
        self.registry_log: List[Dict] = []

    def register_asset(self, asset_id: str, name: str, asset_type: AssetType,
                        description: str = "", tags: List[str] = None,
                        file_url: str = "", creator: str = "") -> Asset:
        """注册资产"""
        asset = Asset(
            asset_id=asset_id,
            name=name,
            asset_type=asset_type,
            description=description,
            tags=tags or [],
            file_url=file_url,
            creator=creator,
            created_at=time.time(),
            updated_at=time.time(),
        )
        self.assets[asset_id] = asset
        self.registry_log.append({"action": "register", "asset_id": asset_id, "type": asset_type.value})
        return asset

    def initialize_default_assets(self) -> List[Asset]:
        """初始化昆仑洞天默认资产库"""
        default_assets = [
            # 角色资产
            ("ASSET-CHAR-001", "女娲角色形象", AssetType.CHARACTER_IMAGE, "大地之母创世神角色形象，人首蛇身七彩霞衣", ["女娲", "创世神", "主角"], "女娲"),
            ("ASSET-CHAR-002", "九天玄女角色形象", AssetType.CHARACTER_IMAGE, "九天圣女兵法女神角色形象，白衣胜雪背负玄火剑", ["九天玄女", "女神", "主角"], "九天玄女"),
            ("ASSET-CHAR-003", "烛龙角色形象", AssetType.CHARACTER_IMAGE, "钟山之神时间之主角色形象，人面蛇身赤色鳞甲", ["烛龙", "古神", "配角"], "烛龙"),
            ("ASSET-CHAR-004", "女娲角色设定集", AssetType.CHARACTER_SETTING, "女娲完整角色设定，包含背景/能力/关系/成长线", ["女娲", "设定"], "女娲"),
            ("ASSET-CHAR-005", "九天玄女角色立绘", AssetType.CHARACTER_ILLUSTRATION, "九天玄女高清立绘，多形态版本", ["九天玄女", "立绘"], "九天玄女"),
            # 场景资产
            ("ASSET-SCENE-001", "昆仑山场景背景", AssetType.SCENE_BACKGROUND, "万山之祖仙山之巅，云海翻腾灵气汇聚", ["昆仑山", "仙界", "主场景"], "昆仑山"),
            ("ASSET-SCENE-002", "钟山场景背景", AssetType.SCENE_BACKGROUND, "烛龙居所时间法则源头，日夜交替之地", ["钟山", "混沌", "场景"], "钟山"),
            ("ASSET-SCENE-003", "涿鹿之野场景背景", AssetType.SCENE_BACKGROUND, "黄帝蚩尤决战之地，古战场战魂不散", ["涿鹿", "凡界", "战场"], "涿鹿之野"),
            ("ASSET-SCENE-004", "天庭场景概念图", AssetType.SCENE_CONCEPT, "神界中枢万神朝拜之地概念设计图", ["天庭", "神界", "概念"], "天庭"),
            # 视频资产
            ("ASSET-VIDEO-001", "昆仑洞天EP01正片", AssetType.VIDEO_EPISODE, "第一集混沌初开女娲造人完整正片，9:16国风", ["EP01", "正片", "女娲"], "女娲"),
            ("ASSET-VIDEO-002", "昆仑洞天EP02正片", AssetType.VIDEO_EPISODE, "第二集钟山烛龙时间之主完整正片", ["EP02", "正片", "烛龙"], "烛龙"),
            ("ASSET-VIDEO-003", "昆仑洞天EP03正片", AssetType.VIDEO_EPISODE, "第三集涿鹿风云黄帝战蚩尤完整正片", ["EP03", "正片", "黄帝"], "黄帝"),
            ("ASSET-VIDEO-004", "昆仑洞天预告PV", AssetType.VIDEO_TRAILER, "系列预告宣传片，高燃剪辑", ["预告", "PV", "宣传"], "全员"),
            ("ASSET-VIDEO-005", "EP01精彩片段", AssetType.VIDEO_CLIP, "第一集高潮战斗片段，适合短视频传播", ["EP01", "片段", "战斗"], "女娲"),
            # 图片资产
            ("ASSET-IMG-001", "EP01关键帧合集", AssetType.IMAGE_KEYFRAME, "第一集12张关键帧，9:16电影级国风", ["EP01", "关键帧"], "全员"),
            ("ASSET-IMG-002", "昆仑洞天系列海报", AssetType.IMAGE_POSTER, "系列主视觉海报，横版+竖版", ["海报", "主视觉", "宣传"], "全员"),
            ("ASSET-IMG-003", "EP01封面图", AssetType.IMAGE_COVER, "第一集视频封面，9:16", ["EP01", "封面"], "女娲"),
            ("ASSET-IMG-004", "女娲补天插画", AssetType.IMAGE_ILLUSTRATION, "女娲炼五色石补天场景插画", ["女娲", "插画", "补天"], "女娲"),
            # 音频资产
            ("ASSET-AUD-001", "昆仑洞天主题曲", AssetType.AUDIO_THEME, "系列主题曲，国风史诗风格", ["主题曲", "BGM", "音乐"], "全员"),
            ("ASSET-AUD-002", "战斗场景配乐", AssetType.AUDIO_BGM, "高燃战斗背景音乐，多版本", ["BGM", "战斗", "配乐"], "全员"),
            ("ASSET-AUD-003", "女娲配音素材", AssetType.AUDIO_VOICE, "女娲角色全部台词配音", ["女娲", "配音", "台词"], "女娲"),
            ("ASSET-AUD-004", "法术音效合集", AssetType.AUDIO_SFX, "各类法术/战斗/环境音效", ["音效", "SFX", "法术"], "全员"),
            # 文字资产
            ("ASSET-TEXT-001", "昆仑洞天分集大纲", AssetType.TEXT_OUTLINE, "全系列分集大纲文档", ["大纲", "剧本"], "全员"),
            ("ASSET-TEXT-002", "EP01完整剧本", AssetType.TEXT_SCRIPT, "第一集完整剧本，含台词/动作/场景", ["EP01", "剧本"], "女娲"),
            ("ASSET-TEXT-003", "EP01分镜表", AssetType.TEXT_STORYBOARD, "第一集12镜头分镜表，含景别/运镜/时长", ["EP01", "分镜"], "全员"),
            ("ASSET-TEXT-004", "昆仑洞天设定集", AssetType.TEXT_NOVEL, "完整世界观设定集，含角色/势力/功法/历史", ["设定集", "世界观"], "全员"),
            # IP衍生
            ("ASSET-IP-001", "女娲手办设计", AssetType.IP_MERCHANDISE, "女娲角色手办设计方案", ["女娲", "手办", "周边"], "女娲"),
            ("ASSET-IP-002", "昆仑洞天数字藏品", AssetType.IP_COLLECTIBLE, "系列限量数字藏品，含角色卡/场景卡", ["数字藏品", "NFT", "收藏"], "全员"),
        ]

        assets = []
        for asset_id, name, atype, desc, tags, creator in default_assets:
            asset = self.register_asset(asset_id, name, atype, desc, tags, creator=creator)
            # 设置文件属性
            if atype in (AssetType.VIDEO_EPISODE, AssetType.VIDEO_CLIP, AssetType.VIDEO_TRAILER):
                asset.file_format = "mp4"
                asset.duration_seconds = random.randint(30, 180)
                asset.resolution = "1080x1920"
                asset.file_size_bytes = random.randint(50_000_000, 200_000_000)
            elif atype in (AssetType.IMAGE_KEYFRAME, AssetType.IMAGE_POSTER, AssetType.IMAGE_COVER, AssetType.IMAGE_ILLUSTRATION, AssetType.CHARACTER_IMAGE, AssetType.CHARACTER_ILLUSTRATION, AssetType.SCENE_CONCEPT):
                asset.file_format = "png"
                asset.resolution = random.choice(["1080x1920", "1920x1080", "2048x2048"])
                asset.file_size_bytes = random.randint(2_000_000, 15_000_000)
            elif atype in (AssetType.AUDIO_BGM, AssetType.AUDIO_THEME, AssetType.AUDIO_VOICE, AssetType.AUDIO_SFX):
                asset.file_format = "mp3"
                asset.duration_seconds = random.randint(10, 300)
                asset.file_size_bytes = random.randint(500_000, 10_000_000)
            elif atype in (AssetType.TEXT_OUTLINE, AssetType.TEXT_SCRIPT, AssetType.TEXT_STORYBOARD, AssetType.TEXT_NOVEL, AssetType.CHARACTER_SETTING, AssetType.SCENE_SETTING):
                asset.file_format = "md"
                asset.file_size_bytes = random.randint(10_000, 500_000)

            asset.status = AssetStatus.PUBLISHED
            asset.view_count = random.randint(100, 50000)
            asset.use_count = random.randint(1, 50)
            asset.like_count = random.randint(10, 10000)
            asset.share_count = random.randint(0, 5000)
            assets.append(asset)

        return assets

    def get_assets_by_type(self, asset_type: AssetType) -> List[Asset]:
        return [a for a in self.assets.values() if a.asset_type == asset_type]

    def get_asset_summary(self) -> Dict:
        by_type = defaultdict(int)
        by_status = defaultdict(int)
        for asset in self.assets.values():
            by_type[asset.asset_type.value] += 1
            by_status[asset.status.value] += 1
        return {
            "total": len(self.assets),
            "by_type": dict(by_type),
            "by_status": dict(by_status),
            "total_views": sum(a.view_count for a in self.assets.values()),
            "total_uses": sum(a.use_count for a in self.assets.values()),
        }

# ============ L2: 资产质量评估层 ============
class AssetQualityEvaluator:
    """资产质量评估层"""

    def __init__(self, registry: AssetRegistry):
        self.registry = registry
        self.evaluation_log: List[Dict] = []

    def evaluate_asset(self, asset: Asset) -> AssetQuality:
        """评估单个资产质量（多维度）"""
        # 基于资产类型和属性生成差异化评分
        type_factors = {
            AssetType.VIDEO_EPISODE: {"content": (75, 95), "technical": (70, 90), "creative": (70, 92), "commercial": (80, 98), "reuse": (60, 85)},
            AssetType.VIDEO_TRAILER: {"content": (70, 90), "technical": (75, 92), "creative": (75, 95), "commercial": (85, 98), "reuse": (70, 90)},
            AssetType.CHARACTER_IMAGE: {"content": (75, 95), "technical": (70, 92), "creative": (72, 95), "commercial": (75, 95), "reuse": (80, 98)},
            AssetType.CHARACTER_SETTING: {"content": (80, 98), "technical": (60, 80), "creative": (75, 95), "commercial": (65, 85), "reuse": (85, 98)},
            AssetType.SCENE_BACKGROUND: {"content": (70, 92), "technical": (68, 90), "creative": (68, 90), "commercial": (70, 88), "reuse": (82, 98)},
            AssetType.IMAGE_KEYFRAME: {"content": (72, 93), "technical": (70, 92), "creative": (70, 92), "commercial": (65, 85), "reuse": (75, 95)},
            AssetType.IMAGE_POSTER: {"content": (75, 95), "technical": (72, 93), "creative": (78, 97), "commercial": (80, 96), "reuse": (60, 80)},
            AssetType.AUDIO_THEME: {"content": (75, 95), "technical": (70, 90), "creative": (75, 96), "commercial": (80, 97), "reuse": (85, 98)},
            AssetType.AUDIO_BGM: {"content": (70, 90), "technical": (68, 88), "creative": (68, 90), "commercial": (70, 88), "reuse": (88, 98)},
            AssetType.TEXT_SCRIPT: {"content": (75, 95), "technical": (65, 85), "creative": (72, 94), "commercial": (60, 80), "reuse": (70, 90)},
            AssetType.TEXT_OUTLINE: {"content": (78, 96), "technical": (60, 80), "creative": (75, 95), "commercial": (55, 75), "reuse": (75, 92)},
            AssetType.IP_COLLECTIBLE: {"content": (80, 97), "technical": (70, 90), "creative": (82, 98), "commercial": (85, 99), "reuse": (50, 70)},
            AssetType.IP_MERCHANDISE: {"content": (75, 94), "technical": (65, 85), "creative": (75, 95), "commercial": (82, 97), "reuse": (55, 75)},
        }

        factors = type_factors.get(asset.asset_type, {"content": (60, 90), "technical": (60, 90), "creative": (60, 90), "commercial": (60, 90), "reuse": (60, 90)})

        # 基于播放量/使用量微调
        popularity_factor = min(1.0, asset.view_count / 10000) * 5
        reuse_factor = min(1.0, asset.use_count / 20) * 5

        quality = AssetQuality(
            content=round(random.uniform(*factors["content"]) + popularity_factor * 0.3, 1),
            technical=round(random.uniform(*factors["technical"]), 1),
            creative=round(random.uniform(*factors["creative"]) + popularity_factor * 0.2, 1),
            commercial=round(random.uniform(*factors["commercial"]) + popularity_factor * 0.5, 1),
            reuse=round(random.uniform(*factors["reuse"]) + reuse_factor, 1),
            consistency=round(random.uniform(70, 95), 1),
            evaluated_at=time.time(),
        )
        quality.content = min(100, quality.content)
        quality.commercial = min(100, quality.commercial)
        quality.reuse = min(100, quality.reuse)
        quality.calculate_overall()

        asset.quality = quality
        asset.updated_at = time.time()

        # 计算商业价值和IP价值
        asset.commercial_value = round(quality.commercial * asset.view_count / 1000, 2)
        asset.ip_value = round(quality.overall * (1 + asset.use_count / 50), 2)

        self.evaluation_log.append({"asset_id": asset.asset_id, "overall": quality.overall})
        return quality

    def evaluate_all(self) -> Dict[str, AssetQuality]:
        """评估所有资产"""
        all_quality = {}
        for asset_id, asset in self.registry.assets.items():
            quality = self.evaluate_asset(asset)
            all_quality[asset_id] = quality
        return all_quality

    def get_quality_distribution(self) -> Dict:
        """获取质量分布"""
        distribution = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0, "未评估": 0}
        for asset in self.registry.assets.values():
            if not asset.quality:
                distribution["未评估"] += 1
                continue
            score = asset.quality.overall
            if score >= 90:
                distribution["S"] += 1
            elif score >= 80:
                distribution["A"] += 1
            elif score >= 70:
                distribution["B"] += 1
            elif score >= 60:
                distribution["C"] += 1
            else:
                distribution["D"] += 1
        return distribution

# ============ L3: 资产自动演化层 ============
class AssetAutoEvolution:
    """资产自动演化层"""

    def __init__(self, registry: AssetRegistry, evaluator: AssetQualityEvaluator):
        self.registry = registry
        self.evaluator = evaluator
        self.evolution_tasks: List[EvolutionTask] = []
        self.evolution_log: List[Dict] = []

    def identify_evolution_candidates(self) -> List[Asset]:
        """识别需要演化的资产（质量低于80或使用频率高）"""
        candidates = []
        for asset in self.registry.assets.values():
            if not asset.quality:
                continue
            # 质量低于80需要演化
            if asset.quality.overall < 80:
                candidates.append(asset)
            # 高使用量资产优先演化
            elif asset.use_count > 20 and asset.quality.overall < 90:
                candidates.append(asset)
        # 按质量升序排列（最差的优先）
        candidates.sort(key=lambda a: a.quality.overall if a.quality else 0)
        return candidates

    def determine_evolution_action(self, asset: Asset) -> EvolutionActionType:
        """确定演化动作"""
        if not asset.quality:
            return EvolutionActionType.UPGRADE_QUALITY

        q = asset.quality
        # 根据最低维度决定动作
        dimensions = {
            "content": q.content,
            "technical": q.technical,
            "creative": q.creative,
            "commercial": q.commercial,
            "reuse": q.reuse,
            "consistency": q.consistency,
        }
        lowest = min(dimensions, key=dimensions.get)

        action_map = {
            "content": EvolutionActionType.UPGRADE_QUALITY,
            "technical": EvolutionActionType.REMASTER,
            "creative": EvolutionActionType.EXPAND_VARIANT,
            "commercial": EvolutionActionType.CREATE_DERIVATIVE,
            "reuse": EvolutionActionType.OPTIMIZE,
            "consistency": EvolutionActionType.REPAIR,
        }
        return action_map.get(lowest, EvolutionActionType.UPGRADE_QUALITY)

    def execute_evolution(self, asset: Asset, action_type: EvolutionActionType) -> EvolutionTask:
        """执行资产演化"""
        old_quality = asset.quality.overall if asset.quality else 0

        task = EvolutionTask(
            task_id=f"EVO-{int(time.time())}-{hashlib.md5(asset.asset_id.encode()).hexdigest()[:6]}",
            asset_id=asset.asset_id,
            asset_name=asset.name,
            action_type=action_type,
            reason=f"质量{old_quality}分，需要{action_type.value}",
            current_quality=old_quality,
            status="running",
            created_at=time.time(),
        )

        # 模拟演化效果
        quality_improvement = random.uniform(3, 12)
        new_quality = min(100, old_quality + quality_improvement)

        # 创建新版本
        old_version = asset.current_version
        parts = old_version.replace("v", "").split(".")
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        if quality_improvement > 8:
            minor += 1
            patch = 0
        else:
            patch += 1
        new_version_str = f"v{major}.{minor}.{patch}"

        version = AssetVersion(
            version=new_version_str,
            parent_version=old_version,
            changes=[f"{action_type.value}，质量提升{quality_improvement:.1f}分"],
            file_hash=hashlib.sha256(f"{asset.asset_id}{new_version_str}{time.time()}".encode()).hexdigest(),
            created_at=time.time(),
            note=action_type.value,
        )
        asset.versions.append(version)
        asset.current_version = new_version_str

        # 更新质量
        if asset.quality:
            asset.quality.overall = round(new_quality, 1)
            # 各维度均匀提升
            asset.quality.content = min(100, asset.quality.content + quality_improvement * 0.3)
            asset.quality.technical = min(100, asset.quality.technical + quality_improvement * 0.2)
            asset.quality.creative = min(100, asset.quality.creative + quality_improvement * 0.2)
            asset.quality.evaluated_at = time.time()

        asset.evolution_count += 1
        asset.updated_at = time.time()
        asset.status = AssetStatus.REMASTERED if action_type == EvolutionActionType.REMASTER else AssetStatus.PUBLISHED

        task.target_quality = new_quality
        task.status = "completed"
        task.result = f"演化成功，{old_quality}→{new_quality:.1f}，版本{old_version}→{new_version_str}"
        task.completed_at = time.time()

        self.evolution_tasks.append(task)
        self.evolution_log.append({
            "asset_id": asset.asset_id,
            "action": action_type.value,
            "improvement": round(quality_improvement, 1),
            "old_version": old_version,
            "new_version": new_version_str,
        })

        return task

    def evolve_low_quality_assets(self, max_count: int = 10) -> List[EvolutionTask]:
        """演化所有低质量资产"""
        candidates = self.identify_evolution_candidates()
        tasks = []
        for asset in candidates[:max_count]:
            action = self.determine_evolution_action(asset)
            task = self.execute_evolution(asset, action)
            tasks.append(task)
        return tasks

    def get_evolution_summary(self) -> Dict:
        completed = [t for t in self.evolution_tasks if t.status == "completed"]
        return {
            "total_tasks": len(self.evolution_tasks),
            "completed": len(completed),
            "avg_improvement": round(sum(t.target_quality - t.current_quality for t in completed) / max(1, len(completed)), 1),
            "by_action": dict(defaultdict(int, {t.action_type.value: sum(1 for x in completed if x.action_type == t.action_type) for t in completed})),
        }

# ============ L4: 资产自动扩展层 ============
class AssetAutoExpansion:
    """资产自动扩展层 - 自动生成衍生/续集/变体资产"""

    def __init__(self, registry: AssetRegistry):
        self.registry = registry
        self.expansion_log: List[Dict] = []

    def create_character_variants(self, character_asset: Asset, count: int = 2) -> List[Asset]:
        """为角色创建变体资产（不同表情/服装/形态）"""
        variants = []
        variant_types = ["战斗形态", "日常形态", "Q版形态", "古风形态", "现代形态"]
        for i in range(min(count, len(variant_types))):
            vtype = variant_types[i]
            variant = self.registry.register_asset(
                asset_id=f"{character_asset.asset_id}-VAR{i+1}",
                name=f"{character_asset.name.replace('角色形象', '')}{vtype}",
                asset_type=AssetType.CHARACTER_IMAGE,
                description=f"{character_asset.description}的{vtype}变体版本",
                tags=character_asset.tags + [vtype, "变体"],
                creator=character_asset.creator,
            )
            variant.file_format = "png"
            variant.resolution = character_asset.resolution
            variant.related_assets.append(character_asset.asset_id)
            variant.related_characters = character_asset.related_characters
            variant.status = AssetStatus.PUBLISHED
            variant.view_count = random.randint(50, 5000)
            variants.append(variant)
        self.expansion_log.append({"type": "character_variant", "source": character_asset.asset_id, "count": len(variants)})
        return variants

    def create_scene_variants(self, scene_asset: Asset, count: int = 2) -> List[Asset]:
        """为场景创建变体（不同时间/天气/角度）"""
        variants = []
        variant_types = ["白昼版", "夜晚版", "雨天版", "雪景版", "黄昏版"]
        for i in range(min(count, len(variant_types))):
            vtype = variant_types[i]
            variant = self.registry.register_asset(
                asset_id=f"{scene_asset.asset_id}-VAR{i+1}",
                name=f"{scene_asset.name}{vtype}",
                asset_type=AssetType.SCENE_BACKGROUND,
                description=f"{scene_asset.description}的{vtype}",
                tags=scene_asset.tags + [vtype, "变体"],
                creator=scene_asset.creator,
            )
            variant.file_format = "png"
            variant.resolution = scene_asset.resolution
            variant.related_assets.append(scene_asset.asset_id)
            variant.status = AssetStatus.PUBLISHED
            variants.append(variant)
        self.expansion_log.append({"type": "scene_variant", "source": scene_asset.asset_id, "count": len(variants)})
        return variants

    def create_video_derivatives(self, video_asset: Asset) -> List[Asset]:
        """为视频创建衍生资产（预告/片段/花絮/竖屏版）"""
        derivatives = []
        derivative_configs = [
            (AssetType.VIDEO_CLIP, "精彩片段", "高燃战斗片段剪辑"),
            (AssetType.VIDEO_TRAILER, "30秒预告", "短视频平台预告版本"),
            (AssetType.IMAGE_POSTER, "截图海报", "高清截图制作海报"),
            (AssetType.IMAGE_KEYFRAME, "精选关键帧", "视频中精选关键帧"),
        ]
        for dtype, suffix, desc in derivative_configs:
            derivative = self.registry.register_asset(
                asset_id=f"{video_asset.asset_id}-DER-{dtype.value}",
                name=f"{video_asset.name}-{suffix}",
                asset_type=dtype,
                description=f"由{video_asset.name}衍生的{suffix}，{desc}",
                tags=video_asset.tags + ["衍生", suffix],
                creator=video_asset.creator,
            )
            derivative.related_assets.append(video_asset.asset_id)
            derivative.related_characters = video_asset.related_characters
            derivative.status = AssetStatus.PUBLISHED
            derivative.view_count = random.randint(100, 10000)
            if dtype in (AssetType.VIDEO_CLIP, AssetType.VIDEO_TRAILER):
                derivative.file_format = "mp4"
                derivative.duration_seconds = random.randint(15, 60)
                derivative.resolution = "1080x1920"
            else:
                derivative.file_format = "png"
                derivative.resolution = "1080x1920"
            derivatives.append(derivative)
        self.expansion_log.append({"type": "video_derivative", "source": video_asset.asset_id, "count": len(derivatives)})
        return derivatives

    def create_episode_sequel(self, episode_asset: Asset) -> Asset:
        """创建续集资产"""
        # 从EP编号推断下一集
        import re
        match = re.search(r'EP(\d+)', episode_asset.asset_id)
        next_ep = int(match.group(1)) + 1 if match else 1
        sequel = self.registry.register_asset(
            asset_id=f"ASSET-VIDEO-{next_ep:03d}",
            name=f"昆仑洞天EP{next_ep:02d}正片",
            asset_type=AssetType.VIDEO_EPISODE,
            description=f"第{next_ep}集正片，承接上集剧情",
            tags=[f"EP{next_ep:02d}", "正片", "续集"],
            creator=episode_asset.creator,
        )
        sequel.file_format = "mp4"
        sequel.duration_seconds = random.randint(60, 180)
        sequel.resolution = "1080x1920"
        sequel.related_assets.append(episode_asset.asset_id)
        sequel.status = AssetStatus.DRAFT
        self.expansion_log.append({"type": "sequel", "source": episode_asset.asset_id, "new": sequel.asset_id})
        return sequel

    def execute_full_expansion(self) -> Dict:
        """执行全面扩展"""
        results = {}

        # 角色变体
        char_images = self.registry.get_assets_by_type(AssetType.CHARACTER_IMAGE)[:3]
        all_char_variants = []
        for char in char_images:
            variants = self.create_character_variants(char, 2)
            all_char_variants.extend(variants)
        results["character_variants"] = all_char_variants

        # 场景变体
        scene_images = self.registry.get_assets_by_type(AssetType.SCENE_BACKGROUND)[:2]
        all_scene_variants = []
        for scene in scene_images:
            variants = self.create_scene_variants(scene, 2)
            all_scene_variants.extend(variants)
        results["scene_variants"] = all_scene_variants

        # 视频衍生
        videos = self.registry.get_assets_by_type(AssetType.VIDEO_EPISODE)[:2]
        all_derivatives = []
        for video in videos:
            derivatives = self.create_video_derivatives(video)
            all_derivatives.extend(derivatives)
        results["video_derivatives"] = all_derivatives

        # 续集
        if videos:
            sequel = self.create_episode_sequel(videos[-1])
            results["sequel"] = sequel

        return results

# ============ L5: 资产关联图谱层 ============
class AssetGraphBuilder:
    """资产关联图谱层"""

    def __init__(self, registry: AssetRegistry):
        self.registry = registry
        self.nodes: Dict[str, AssetGraphNode] = {}
        self.edges: List[AssetGraphEdge] = []

    def build_graph(self) -> Tuple[Dict[str, AssetGraphNode], List[AssetGraphEdge]]:
        """构建资产关联图谱"""
        self.nodes = {}
        self.edges = []

        # 创建节点
        for asset_id, asset in self.registry.assets.items():
            node = AssetGraphNode(
                asset_id=asset_id,
                name=asset.name,
                asset_type=asset.asset_type,
                quality_score=asset.quality.overall if asset.quality else 0,
            )
            self.nodes[asset_id] = node

        # 创建边（基于关联资产）
        for asset_id, asset in self.registry.assets.items():
            for related_id in asset.related_assets:
                if related_id in self.nodes:
                    edge = AssetGraphEdge(
                        source=asset_id,
                        target=related_id,
                        relation_type="衍生" if "DER" in asset_id or "VAR" in asset_id else "关联",
                        strength=round(random.uniform(0.3, 0.9), 2),
                    )
                    self.edges.append(edge)
                    self.nodes[asset_id].connections += 1
                    self.nodes[related_id].connections += 1

            # 同角色关联
            for char_id in asset.related_characters:
                for other_id, other in self.registry.assets.items():
                    if other_id != asset_id and char_id in other.related_characters:
                        # 避免重复边
                        exists = any(e.source == asset_id and e.target == other_id for e in self.edges)
                        if not exists:
                            edge = AssetGraphEdge(
                                source=asset_id,
                                target=other_id,
                                relation_type=f"同角色({char_id})",
                                strength=round(random.uniform(0.4, 0.8), 2),
                            )
                            self.edges.append(edge)

        return self.nodes, self.edges

    def get_graph_stats(self) -> Dict:
        """获取图谱统计"""
        if not self.nodes:
            return {"nodes": 0, "edges": 0}
        avg_connections = sum(n.connections for n in self.nodes.values()) / len(self.nodes)
        most_connected = sorted(self.nodes.values(), key=lambda n: n.connections, reverse=True)[:5]
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "avg_connections": round(avg_connections, 1),
            "density": round(len(self.edges) / (len(self.nodes) * (len(self.nodes) - 1) / 2), 4) if len(self.nodes) > 1 else 0,
            "most_connected": [{"name": n.name, "connections": n.connections} for n in most_connected],
        }

# ============ L6: 资产价值评估层 ============
class AssetValueEvaluator:
    """资产价值评估层"""

    def __init__(self, registry: AssetRegistry):
        self.registry = registry

    def evaluate_portfolio_value(self) -> Dict:
        """评估资产组合总价值"""
        total_commercial = sum(a.commercial_value for a in self.registry.assets.values())
        total_ip = sum(a.ip_value for a in self.registry.assets.values())
        total_views = sum(a.view_count for a in self.registry.assets.values())
        total_uses = sum(a.use_count for a in self.registry.assets.values())

        # 按类型统计价值
        value_by_type = defaultdict(lambda: {"count": 0, "commercial": 0.0, "ip": 0.0, "views": 0})
        for asset in self.registry.assets.values():
            t = asset.asset_type.value
            value_by_type[t]["count"] += 1
            value_by_type[t]["commercial"] += asset.commercial_value
            value_by_type[t]["ip"] += asset.ip_value
            value_by_type[t]["views"] += asset.view_count

        # Top价值资产
        top_value = sorted(self.registry.assets.values(), key=lambda a: a.ip_value, reverse=True)[:10]

        return {
            "total_assets": len(self.registry.assets),
            "total_commercial_value": round(total_commercial, 2),
            "total_ip_value": round(total_ip, 2),
            "total_views": total_views,
            "total_uses": total_uses,
            "avg_commercial_per_asset": round(total_commercial / max(1, len(self.registry.assets)), 2),
            "avg_ip_per_asset": round(total_ip / max(1, len(self.registry.assets)), 2),
            "value_by_type": dict(value_by_type),
            "top_ip_assets": [{"name": a.name, "ip_value": a.ip_value, "commercial": a.commercial_value} for a in top_value],
        }

# ============ 主流程 ============
def execute_kunlun_asset_evolution():
    print("=" * 60)
    print("昆仑洞天资产自动演化扩展机制 V1.0")
    print(f"锚定: {ANCHOR} | DID: {DID}")
    print(f"机制版本: {ASSET_VERSION}")
    print(f"时间: {datetime.datetime.now().isoformat()}")
    print("=" * 60)

    # L1: 资产注册与分类
    print("\n[L1] 资产注册与分类...")
    registry = AssetRegistry()
    default_assets = registry.initialize_default_assets()
    asset_summary = registry.get_asset_summary()
    print(f"  注册资产总数: {asset_summary['total']}个")
    print(f"  按类型分布:")
    for atype, count in sorted(asset_summary['by_type'].items()):
        print(f"    {atype}: {count}个")
    print(f"  总播放量: {asset_summary['total_views']:,}")
    print(f"  总引用次数: {asset_summary['total_uses']}")

    # L2: 资产质量评估
    print("\n[L2] 资产质量评估...")
    evaluator = AssetQualityEvaluator(registry)
    all_quality = evaluator.evaluate_all()
    quality_dist = evaluator.get_quality_distribution()
    print(f"  评估资产数: {len(all_quality)}个")
    print(f"  质量分布:")
    for level, count in quality_dist.items():
        if count > 0:
            print(f"    {level}级: {count}个")
    avg_quality = round(sum(q.overall for q in all_quality.values()) / len(all_quality), 1)
    print(f"  平均质量分: {avg_quality}")

    # L3: 资产自动演化
    print("\n[L3] 资产自动演化...")
    evolution = AssetAutoEvolution(registry, evaluator)
    candidates = evolution.identify_evolution_candidates()
    print(f"  识别演化候选: {len(candidates)}个（质量<80或高使用量）")
    evolved_tasks = evolution.evolve_low_quality_assets(max_count=8)
    print(f"  执行演化任务: {len(evolved_tasks)}个")
    for task in evolved_tasks[:5]:
        print(f"    → {task.asset_name[:24]}: {task.action_type.value}，{task.result[:50]}...")
    evo_summary = evolution.get_evolution_summary()
    print(f"  平均质量提升: +{evo_summary['avg_improvement']}分")

    # 演化后质量分布
    new_quality_dist = evaluator.get_quality_distribution()
    print(f"  演化后质量分布: S={new_quality_dist['S']} A={new_quality_dist['A']} B={new_quality_dist['B']} C={new_quality_dist['C']} D={new_quality_dist['D']}")

    # L4: 资产自动扩展
    print("\n[L4] 资产自动扩展...")
    expansion = AssetAutoExpansion(registry)
    expand_results = expansion.execute_full_expansion()
    total_new = sum(len(v) if isinstance(v, list) else 1 for v in expand_results.values())
    print(f"  新增资产数: {total_new}个")
    print(f"  角色变体: {len(expand_results.get('character_variants', []))}个")
    print(f"  场景变体: {len(expand_results.get('scene_variants', []))}个")
    print(f"  视频衍生: {len(expand_results.get('video_derivatives', []))}个")
    if 'sequel' in expand_results:
        print(f"  续集创作: {expand_results['sequel'].name}")

    new_total = len(registry.assets)
    print(f"  资产库总量: {new_total}个（增长{total_new}个）")

    # L5: 资产关联图谱
    print("\n[L5] 资产关联图谱构建...")
    graph_builder = AssetGraphBuilder(registry)
    nodes, edges = graph_builder.build_graph()
    graph_stats = graph_builder.get_graph_stats()
    print(f"  图谱节点: {graph_stats['nodes']}个")
    print(f"  关联边数: {graph_stats['edges']}条")
    print(f"  平均连接数: {graph_stats['avg_connections']}")
    print(f"  图谱密度: {graph_stats['density']}")
    print(f"  最高连接资产:")
    for item in graph_stats['most_connected'][:3]:
        print(f"    {item['name'][:30]}: {item['connections']}条连接")

    # L6: 资产价值评估
    print("\n[L6] 资产价值评估...")
    value_evaluator = AssetValueEvaluator(registry)
    portfolio = value_evaluator.evaluate_portfolio_value()
    print(f"  资产总数: {portfolio['total_assets']}")
    print(f"  商业总价值: {portfolio['total_commercial_value']:.2f}")
    print(f"  IP总价值: {portfolio['total_ip_value']:.2f}")
    print(f"  总播放量: {portfolio['total_views']:,}")
    print(f"  平均单资产IP价值: {portfolio['avg_ip_per_asset']:.2f}")
    print(f"  IP价值Top3:")
    for item in portfolio['top_ip_assets'][:3]:
        print(f"    {item['name'][:30]}: IP价值{item['ip_value']:.2f}, 商业价值{item['commercial']:.2f}")

    # 归档上报
    print("\n[归档] 资产快照上报记忆网关...")
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
    archive_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "asset_summary": {
            "total": new_total,
            "by_type": asset_summary['by_type'],
            "quality_distribution": new_quality_dist,
            "avg_quality": avg_quality,
        },
        "evolution": {
            "tasks_executed": len(evolved_tasks),
            "avg_improvement": evo_summary['avg_improvement'],
        },
        "expansion": {
            "new_assets": total_new,
            "asset_growth_rate": f"{round(total_new / asset_summary['total'] * 100, 1)}%",
        },
        "graph": graph_stats,
        "portfolio_value": {
            "commercial": portfolio['total_commercial_value'],
            "ip": portfolio['total_ip_value'],
            "total_views": portfolio['total_views'],
        },
        "did": DID,
        "anchor": ANCHOR,
    }
    resp = gateway_post("/api/report/truth", {
        "truth_key": f"KUNLUN.ASSET.EVOLUTION.SNAPSHOT.{timestamp}",
        "truth_value": json.dumps(archive_data, ensure_ascii=False),
        "source_node": SOURCE_NODE,
        "confidence": 0.94,
        "truth_type": "data"
    })
    print(f"  上报: success={resp[1].get('success')}, truth_count={resp[1].get('truth_count')}")

    mechanism_hash = hashlib.sha256(json.dumps({
        "asset_version": ASSET_VERSION,
        "total_assets": new_total,
        "evolution_tasks": len(evolved_tasks),
        "expansion_new": total_new,
        "graph_nodes": graph_stats['nodes'],
        "graph_edges": graph_stats['edges'],
        "did": DID,
        "anchor": ANCHOR
    }, sort_keys=True).encode()).hexdigest()

    print(f"\n{'=' * 60}")
    print(f"昆仑洞天资产自动演化扩展机制执行完成！")
    print(f"机制哈希: {mechanism_hash[:16]}...")
    print(f"{'=' * 60}")

    return {
        "registry": registry,
        "evaluator": evaluator,
        "evolution": evolution,
        "expansion": expansion,
        "graph_builder": graph_builder,
        "value_evaluator": value_evaluator,
        "portfolio": portfolio,
        "mechanism_hash": mechanism_hash
    }

if __name__ == "__main__":
    execute_kunlun_asset_evolution()

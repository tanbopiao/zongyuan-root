"""
物理仿真元规则引擎 V1.0
底层基础组件，实现10大物理仿真元规则的可执行引擎，支持物理场景仿真。

确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import math
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum


class Dimension(Enum):
    """物理维度"""
    SPACE = "space"
    TIME = "time"
    MATTER = "matter"
    ENERGY = "energy"
    FORCE = "force"
    MOTION = "motion"
    FIELD = "field"
    INTERACTION = "interaction"
    CONSTRAINT = "constraint"
    MEASUREMENT = "measurement"


@dataclass
class Vector3:
    """三维向量"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other):
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar):
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def magnitude(self) -> float:
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    def normalize(self) -> 'Vector3':
        mag = self.magnitude()
        if mag == 0:
            return Vector3()
        return Vector3(self.x / mag, self.y / mag, self.z / mag)

    def dot(self, other) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other) -> 'Vector3':
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )

    def to_dict(self) -> Dict:
        return {"x": self.x, "y": self.y, "z": self.z}


@dataclass
class PhysicsObject:
    """物理对象"""
    object_id: str
    name: str = ""
    position: Vector3 = field(default_factory=Vector3)
    velocity: Vector3 = field(default_factory=Vector3)
    acceleration: Vector3 = field(default_factory=Vector3)
    mass: float = 1.0
    radius: float = 0.5
    charge: float = 0.0
    forces: List[Vector3] = field(default_factory=list)
    fixed: bool = False  # 是否固定不动
    material: str = "default"
    metadata: Dict = field(default_factory=dict)

    def apply_force(self, force: Vector3):
        """施加力"""
        self.forces.append(force)

    def clear_forces(self):
        """清除所有力"""
        self.forces = []

    def get_net_force(self) -> Vector3:
        """计算合力"""
        net = Vector3()
        for f in self.forces:
            net = net + f
        return net


@dataclass
class PhysicsRule:
    """物理规则"""
    rule_id: str
    dimension: Dimension
    name: str
    description: str
    formula: str = ""
    enabled: bool = True
    priority: int = 0
    parameters: Dict = field(default_factory=dict)


@dataclass
class SimulationState:
    """仿真状态"""
    time: float = 0.0
    step: int = 0
    objects: Dict[str, PhysicsObject] = field(default_factory=dict)
    rules: Dict[str, PhysicsRule] = field(default_factory=dict)
    history: List[Dict] = field(default_factory=list)
    energy: float = 0.0
    momentum: Vector3 = field(default_factory=Vector3)
    events: List[Dict] = field(default_factory=list)


class PhysicsSimulationEngine:
    """物理仿真元规则引擎"""

    # 物理常量
    GRAVITY = 9.81  # 重力加速度 m/s²
    G = 6.674e-11  # 万有引力常数
    C = 299792458  # 光速 m/s
    K = 8.988e9  # 库仑常数
    PI = math.pi

    def __init__(self, config: Dict = None):
        """
        初始化物理仿真引擎

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.state = SimulationState()
        self._default_rules: List[PhysicsRule] = []
        self._init_default_rules()
        self._step_count = 0

    def _init_default_rules(self):
        """初始化默认物理规则（10大元规则的核心规则）"""
        rules = [
            # 空间元规则
            PhysicsRule("space-001", Dimension.SPACE, "三维欧几里得空间",
                        "所有物体存在于三维欧几里得空间中，位置用(x,y,z)坐标表示",
                        "position = (x, y, z)", priority=100),
            PhysicsRule("space-002", Dimension.SPACE, "距离度量",
                        "两点间距离用欧几里得距离公式计算",
                        "d = √((x2-x1)² + (y2-y1)² + (z2-z1)²)", priority=99),

            # 时间元规则
            PhysicsRule("time-001", Dimension.TIME, "时间单向流逝",
                        "时间从过去流向未来，不可逆转",
                        "t ≥ 0, Δt > 0", priority=100),
            PhysicsRule("time-002", Dimension.TIME, "因果时序",
                        "原因先于结果，事件按时间顺序发生",
                        "t_cause < t_effect", priority=99),

            # 物质元规则
            PhysicsRule("matter-001", Dimension.MATTER, "质量守恒",
                        "封闭系统中总质量保持不变",
                        "Σm_initial = Σm_final", priority=95),
            PhysicsRule("matter-002", Dimension.MATTER, "惯性质量",
                        "物体质量决定其惯性大小",
                        "F = ma", priority=94),

            # 能量元规则
            PhysicsRule("energy-001", Dimension.ENERGY, "能量守恒",
                        "封闭系统中总能量保持不变，可转化但不消失",
                        "ΣE_initial = ΣE_final", priority=95),
            PhysicsRule("energy-002", Dimension.ENERGY, "动能公式",
                        "运动物体的动能",
                        "E_k = ½mv²", priority=94),
            PhysicsRule("energy-003", Dimension.ENERGY, "势能公式",
                        "重力势能",
                        "E_p = mgh", priority=93),

            # 力元规则
            PhysicsRule("force-001", Dimension.FORCE, "牛顿第二定律",
                        "物体加速度与所受合力成正比，与质量成反比",
                        "F = ma", priority=100),
            PhysicsRule("force-002", Dimension.FORCE, "作用力与反作用力",
                        "每一个作用力都有一个大小相等方向相反的反作用力",
                        "F_action = -F_reaction", priority=99),
            PhysicsRule("force-003", Dimension.FORCE, "万有引力",
                        "两物体间万有引力与质量乘积成正比，与距离平方成反比",
                        "F = G*m1*m2/r²", priority=90),

            # 运动元规则
            PhysicsRule("motion-001", Dimension.MOTION, "匀速运动",
                        "不受外力时物体保持匀速直线运动或静止",
                        "v = constant, a = 0", priority=95),
            PhysicsRule("motion-002", Dimension.MOTION, "匀加速运动",
                        "恒定加速度下的运动方程",
                        "v = v0 + at, s = v0t + ½at²", priority=94),
            PhysicsRule("motion-003", Dimension.MOTION, "自由落体",
                        "只受重力作用的自由下落运动",
                        "v = gt, h = ½gt²", priority=93),

            # 场元规则
            PhysicsRule("field-001", Dimension.FIELD, "引力场",
                        "质量在周围空间产生引力场",
                        "g = GM/r²", priority=85),
            PhysicsRule("field-002", Dimension.FIELD, "场叠加原理",
                        "多个场的合场强为各场强的矢量和",
                        "E_total = ΣE_i", priority=84),

            # 相互作用元规则
            PhysicsRule("interaction-001", Dimension.INTERACTION, "碰撞守恒",
                        "碰撞过程中动量守恒",
                        "Σp_initial = Σp_final", priority=90),
            PhysicsRule("interaction-002", Dimension.INTERACTION, "弹性碰撞",
                        "弹性碰撞中动能也守恒",
                        "ΣE_k_initial = ΣE_k_final", priority=89),

            # 约束元规则
            PhysicsRule("constraint-001", Dimension.CONSTRAINT, "几何约束",
                        "物体位置受几何边界限制",
                        "f(position, t) = 0", priority=80),

            # 测量元规则
            PhysicsRule("measurement-001", Dimension.MEASUREMENT, "物理量测量",
                        "物理量通过与标准单位比较进行测量",
                        "value = measurement / unit", priority=70),
        ]

        self._default_rules = rules
        for rule in rules:
            self.state.rules[rule.rule_id] = rule

    def add_object(self, obj: PhysicsObject) -> bool:
        """
        添加物理对象

        Args:
            obj: 物理对象

        Returns:
            是否添加成功
        """
        if obj.object_id in self.state.objects:
            return False
        self.state.objects[obj.object_id] = obj
        return True

    def remove_object(self, object_id: str) -> bool:
        """移除物理对象"""
        if object_id in self.state.objects:
            del self.state.objects[object_id]
            return True
        return False

    def get_object(self, object_id: str) -> Optional[PhysicsObject]:
        """获取物理对象"""
        return self.state.objects.get(object_id)

    def list_objects(self) -> List[Dict]:
        """列出所有物理对象"""
        return [
            {
                "object_id": obj.object_id,
                "name": obj.name,
                "position": obj.position.to_dict(),
                "velocity": obj.velocity.to_dict(),
                "mass": obj.mass,
                "fixed": obj.fixed,
            }
            for obj in self.state.objects.values()
        ]

    def apply_gravity(self):
        """应用重力（所有物体受向下重力）"""
        gravity = Vector3(0, -self.GRAVITY, 0)
        for obj in self.state.objects.values():
            if not obj.fixed:
                force = gravity * obj.mass
                obj.apply_force(force)

    def apply_universal_gravitation(self):
        """应用万有引力（物体间相互引力）"""
        objects = list(self.state.objects.values())
        for i in range(len(objects)):
            for j in range(i + 1, len(objects)):
                obj1, obj2 = objects[i], objects[j]
                diff = obj2.position - obj1.position
                distance = diff.magnitude()
                if distance > 0.001:  # 避免除零
                    force_magnitude = self.G * obj1.mass * obj2.mass / (distance ** 2)
                    direction = diff.normalize()
                    force = direction * force_magnitude
                    if not obj1.fixed:
                        obj1.apply_force(force)
                    if not obj2.fixed:
                        obj2.apply_force(force * -1)

    def apply_spring_force(self, obj1_id: str, obj2_id: str,
                            k: float = 10.0, rest_length: float = 1.0):
        """应用弹簧力（胡克定律）"""
        obj1 = self.get_object(obj1_id)
        obj2 = self.get_object(obj2_id)
        if not obj1 or not obj2:
            return

        diff = obj2.position - obj1.position
        distance = diff.magnitude()
        if distance > 0.001:
            extension = distance - rest_length
            force_magnitude = k * extension
            direction = diff.normalize()
            force = direction * force_magnitude
            if not obj1.fixed:
                obj1.apply_force(force)
            if not obj2.fixed:
                obj2.apply_force(force * -1)

    def detect_collisions(self) -> List[Dict]:
        """检测碰撞"""
        collisions = []
        objects = list(self.state.objects.values())
        for i in range(len(objects)):
            for j in range(i + 1, len(objects)):
                obj1, obj2 = objects[i], objects[j]
                diff = obj2.position - obj1.position
                distance = diff.magnitude()
                min_distance = obj1.radius + obj2.radius
                if distance < min_distance:
                    collisions.append({
                        "object1": obj1.object_id,
                        "object2": obj2.object_id,
                        "distance": distance,
                        "overlap": min_distance - distance,
                        "time": self.state.time,
                    })
        return collisions

    def resolve_collision(self, collision: Dict, restitution: float = 0.8):
        """
        解决碰撞（弹性碰撞）

        Args:
            collision: 碰撞信息
            restitution: 恢复系数（0-1，1为完全弹性）
        """
        obj1 = self.get_object(collision["object1"])
        obj2 = self.get_object(collision["object2"])
        if not obj1 or not obj2 or obj1.fixed or obj2.fixed:
            return

        # 计算碰撞法线
        diff = obj2.position - obj1.position
        normal = diff.normalize()

        # 计算相对速度
        relative_velocity = obj1.velocity - obj2.velocity
        velocity_along_normal = relative_velocity.dot(normal)

        # 如果物体正在分离，不处理
        if velocity_along_normal > 0:
            return

        # 计算冲量
        impulse_magnitude = -(1 + restitution) * velocity_along_normal
        impulse_magnitude /= (1 / obj1.mass + 1 / obj2.mass)

        impulse = normal * impulse_magnitude

        # 应用冲量
        obj1.velocity = obj1.velocity + impulse * (1 / obj1.mass)
        obj2.velocity = obj2.velocity - impulse * (1 / obj2.mass)

        # 位置修正（防止重叠）
        overlap = collision.get("overlap", 0)
        if overlap > 0:
            correction = normal * (overlap / 2)
            obj1.position = obj1.position - correction
            obj2.position = obj2.position + correction

        # 记录事件
        self.state.events.append({
            "type": "collision",
            "object1": obj1.object_id,
            "object2": obj2.object_id,
            "time": self.state.time,
            "impulse": impulse_magnitude,
        })

    def step(self, dt: float = 0.01, enable_gravity: bool = True,
             enable_collision: bool = True) -> Dict:
        """
        执行一步仿真

        Args:
            dt: 时间步长（秒）
            enable_gravity: 是否启用重力
            enable_collision: 是否启用碰撞检测和解决

        Returns:
            仿真步骤结果
        """
        start_time = time.time()

        # 1. 清除上一步的力
        for obj in self.state.objects.values():
            obj.clear_forces()

        # 2. 应用力
        if enable_gravity:
            self.apply_gravity()

        # 3. 计算加速度和更新速度位置（半隐式欧拉积分）
        for obj in self.state.objects.values():
            if not obj.fixed:
                net_force = obj.get_net_force()
                obj.acceleration = net_force * (1 / obj.mass)
                obj.velocity = obj.velocity + obj.acceleration * dt
                obj.position = obj.position + obj.velocity * dt

        # 4. 碰撞检测和解决
        collisions = []
        if enable_collision:
            collisions = self.detect_collisions()
            for collision in collisions:
                self.resolve_collision(collision)

        # 5. 更新状态
        self.state.time += dt
        self.state.step += 1
        self._step_count += 1

        # 6. 计算系统能量和动量
        total_energy = 0.0
        total_momentum = Vector3()
        for obj in self.state.objects.values():
            kinetic = 0.5 * obj.mass * obj.velocity.magnitude() ** 2
            potential = obj.mass * self.GRAVITY * max(0, obj.position.y)
            total_energy += kinetic + potential
            total_momentum = total_momentum + obj.velocity * obj.mass

        self.state.energy = total_energy
        self.state.momentum = total_momentum

        # 7. 记录历史（每10步记录一次）
        if self.state.step % 10 == 0:
            self.state.history.append({
                "time": self.state.time,
                "step": self.state.step,
                "energy": total_energy,
                "momentum": total_momentum.to_dict(),
                "objects": [
                    {
                        "id": obj.object_id,
                        "position": obj.position.to_dict(),
                        "velocity": obj.velocity.to_dict(),
                    }
                    for obj in self.state.objects.values()
                ],
            })

        elapsed = (time.time() - start_time) * 1000

        return {
            "success": True,
            "step": self.state.step,
            "time": self.state.time,
            "dt": dt,
            "object_count": len(self.state.objects),
            "collisions": len(collisions),
            "total_energy": total_energy,
            "total_momentum": total_momentum.to_dict(),
            "elapsed_ms": elapsed,
        }

    def simulate(self, steps: int = 100, dt: float = 0.01,
                 **kwargs) -> Dict:
        """
        执行多步仿真

        Args:
            steps: 仿真步数
            dt: 时间步长
            **kwargs: 其他参数

        Returns:
            仿真结果
        """
        results = []
        for i in range(steps):
            result = self.step(dt, **kwargs)
            results.append(result)

        return {
            "success": True,
            "total_steps": steps,
            "final_time": self.state.time,
            "final_energy": self.state.energy,
            "history_length": len(self.state.history),
            "events": len(self.state.events),
            "objects": self.list_objects(),
        }

    def reset(self):
        """重置仿真状态"""
        self.state = SimulationState()
        self._init_default_rules()
        self._step_count = 0

    def get_rules(self, dimension: Dimension = None) -> List[Dict]:
        """获取物理规则列表"""
        rules = []
        for rule in self.state.rules.values():
            if dimension and rule.dimension != dimension:
                continue
            rules.append({
                "rule_id": rule.rule_id,
                "dimension": rule.dimension.value,
                "name": rule.name,
                "description": rule.description,
                "formula": rule.formula,
                "enabled": rule.enabled,
                "priority": rule.priority,
            })
        return sorted(rules, key=lambda r: r["priority"], reverse=True)

    def get_state_summary(self) -> Dict:
        """获取状态摘要"""
        return {
            "time": self.state.time,
            "step": self.state.step,
            "object_count": len(self.state.objects),
            "rule_count": len(self.state.rules),
            "total_energy": self.state.energy,
            "total_momentum": self.state.momentum.to_dict(),
            "history_records": len(self.state.history),
            "events": len(self.state.events),
            "objects": self.list_objects(),
        }

    def get_stats(self) -> Dict:
        """获取引擎统计"""
        return {
            "total_steps": self._step_count,
            "registered_rules": len(self.state.rules),
            "dimensions": len(Dimension),
            "current_objects": len(self.state.objects),
            "status": "running",
        }

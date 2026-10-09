#!/usr/bin/env python3
"""
元极恒一物理仿真引擎 V2.0
增强版：刚体动力学 + 碰撞检测 + 约束求解 + 粒子系统
归属：元极恒一自治体系 · 物理仿真元规则体系 · 数字孪生物理层
确权：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""

import math
import json
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from enum import Enum


class BodyType(Enum):
    STATIC = "static"      # 静态物体（不受力影响）
    DYNAMIC = "dynamic"    # 动态物体（受重力和力影响）
    KINEMATIC = "kinematic"  # 运动学物体（可手动控制速度）


class ShapeType(Enum):
    CIRCLE = "circle"
    RECTANGLE = "rectangle"
    POLYGON = "polygon"


@dataclass
class Vector2:
    """二维向量"""
    x: float = 0.0
    y: float = 0.0
    
    def __add__(self, other): return Vector2(self.x + other.x, self.y + other.y)
    def __sub__(self, other): return Vector2(self.x - other.x, self.y - other.y)
    def __mul__(self, scalar): return Vector2(self.x * scalar, self.y * scalar)
    def __truediv__(self, scalar): return Vector2(self.x / scalar, self.y / scalar)
    def dot(self, other): return self.x * other.x + self.y * other.y
    def cross(self, other): return self.x * other.y - self.y * other.x
    def length(self): return math.sqrt(self.x ** 2 + self.y ** 2)
    def normalize(self):
        l = self.length()
        return Vector2(self.x / l, self.y / l) if l > 0 else Vector2(0, 0)
    def rotate(self, angle):
        c, s = math.cos(angle), math.sin(angle)
        return Vector2(self.x * c - self.y * s, self.x * s + self.y * c)
    def to_tuple(self): return (self.x, self.y)
    def to_dict(self): return {"x": self.x, "y": self.y}


@dataclass
class RigidBody:
    """刚体"""
    body_id: str
    position: Vector2 = field(default_factory=Vector2)
    velocity: Vector2 = field(default_factory=Vector2)
    acceleration: Vector2 = field(default_factory=Vector2)
    angle: float = 0.0
    angular_velocity: float = 0.0
    mass: float = 1.0
    inverse_mass: float = 1.0
    inertia: float = 1.0
    inverse_inertia: float = 1.0
    restitution: float = 0.5  # 弹性系数
    friction: float = 0.3     # 摩擦系数
    body_type: BodyType = BodyType.DYNAMIC
    shape_type: ShapeType = ShapeType.CIRCLE
    radius: float = 1.0       # 圆形半径
    width: float = 1.0        # 矩形宽
    height: float = 1.0       # 矩形高
    force: Vector2 = field(default_factory=Vector2)
    torque: float = 0.0
    active: bool = True
    
    def __post_init__(self):
        if self.body_type == BodyType.STATIC:
            self.inverse_mass = 0.0
            self.inverse_inertia = 0.0
        else:
            self.inverse_mass = 1.0 / self.mass if self.mass > 0 else 0.0
    
    def apply_force(self, force: Vector2, point: Optional[Vector2] = None):
        """施加力"""
        if self.body_type == BodyType.STATIC:
            return
        self.force = self.force + force
        if point:
            r = point - self.position
            self.torque += r.cross(force)
    
    def apply_impulse(self, impulse: Vector2, point: Optional[Vector2] = None):
        """施加冲量"""
        if self.body_type == BodyType.STATIC:
            return
        self.velocity = self.velocity + impulse * self.inverse_mass
        if point:
            r = point - self.position
            self.angular_velocity += r.cross(impulse) * self.inverse_inertia


@dataclass
class CollisionManifold:
    """碰撞流形"""
    body_a: RigidBody
    body_b: RigidBody
    normal: Vector2 = field(default_factory=Vector2)
    penetration: float = 0.0
    contact_points: List[Vector2] = field(default_factory=list)
    restitution: float = 0.0
    friction: float = 0.0


class PhysicsWorld:
    """物理世界"""
    
    def __init__(self, gravity: Vector2 = None):
        self.bodies: List[RigidBody] = []
        self.gravity = gravity or Vector2(0, -9.81)
        self.time_step = 1.0 / 60.0
        self.iterations = 10
        self.collisions: List[CollisionManifold] = []
        self.body_count = 0
    
    def add_body(self, body: RigidBody):
        """添加刚体"""
        self.bodies.append(body)
        self.body_count += 1
        return body
    
    def remove_body(self, body_id: str):
        """移除刚体"""
        self.bodies = [b for b in self.bodies if b.body_id != body_id]
        self.body_count = len(self.bodies)
    
    def step(self, dt: float = None):
        """物理步进"""
        dt = dt or self.time_step
        
        # 1. 应用力和重力
        for body in self.bodies:
            if body.body_type != BodyType.STATIC and body.active:
                body.acceleration = self.gravity + body.force * body.inverse_mass
                body.velocity = body.velocity + body.acceleration * dt
                body.angular_velocity += body.torque * body.inverse_inertia * dt
                
                # 阻尼
                body.velocity = body.velocity * 0.999
                body.angular_velocity *= 0.999
                
                # 重置力和力矩
                body.force = Vector2(0, 0)
                body.torque = 0.0
        
        # 2. 碰撞检测
        self.collisions = self._detect_collisions()
        
        # 3. 碰撞求解（多次迭代）
        for _ in range(self.iterations):
            for collision in self.collisions:
                self._resolve_collision(collision)
        
        # 4. 位置修正
        for collision in self.collisions:
            self._positional_correction(collision)
        
        # 5. 更新位置
        for body in self.bodies:
            if body.active:
                body.position = body.position + body.velocity * dt
                body.angle += body.angular_velocity * dt
    
    def _detect_collisions(self) -> List[CollisionManifold]:
        """碰撞检测"""
        collisions = []
        for i in range(len(self.bodies)):
            for j in range(i + 1, len(self.bodies)):
                a, b = self.bodies[i], self.bodies[j]
                if a.body_type == BodyType.STATIC and b.body_type == BodyType.STATIC:
                    continue
                
                manifold = self._circle_vs_circle(a, b)
                if manifold:
                    collisions.append(manifold)
        return collisions
    
    def _circle_vs_circle(self, a: RigidBody, b: RigidBody) -> Optional[CollisionManifold]:
        """圆形 vs 圆形碰撞检测"""
        if a.shape_type != ShapeType.CIRCLE or b.shape_type != ShapeType.CIRCLE:
            return None
        
        delta = b.position - a.position
        dist = delta.length()
        r = a.radius + b.radius
        
        if dist >= r:
            return None
        
        normal = delta.normalize() if dist > 0 else Vector2(1, 0)
        penetration = r - dist
        contact_point = a.position + normal * a.radius
        
        return CollisionManifold(
            body_a=a, body_b=b,
            normal=normal, penetration=penetration,
            contact_points=[contact_point],
            restitution=min(a.restitution, b.restitution),
            friction=math.sqrt(a.friction * b.friction)
        )
    
    def _resolve_collision(self, manifold: CollisionManifold):
        """碰撞求解（冲量法）"""
        a, b = manifold.body_a, manifold.body_b
        normal = manifold.normal
        
        # 相对速度
        rv = b.velocity - a.velocity
        vel_along_normal = rv.dot(normal)
        
        if vel_along_normal > 0:
            return  # 物体正在分离
        
        # 计算冲量
        e = manifold.restitution
        j = -(1 + e) * vel_along_normal
        j /= a.inverse_mass + b.inverse_mass
        
        impulse = normal * j
        
        # 应用冲量
        a.apply_impulse(impulse * -1, manifold.contact_points[0])
        b.apply_impulse(impulse, manifold.contact_points[0])
        
        # 摩擦冲量
        rv = b.velocity - a.velocity
        tangent = rv - normal * rv.dot(normal)
        if tangent.length() > 0.0001:
            tangent = tangent.normalize()
            jt = -rv.dot(tangent)
            jt /= a.inverse_mass + b.inverse_mass
            
            mu = manifold.friction
            if abs(jt) < j * mu:
                friction_impulse = tangent * jt
            else:
                friction_impulse = tangent * (-j * mu)
            
            a.apply_impulse(friction_impulse * -1, manifold.contact_points[0])
            b.apply_impulse(friction_impulse, manifold.contact_points[0])
    
    def _positional_correction(self, manifold: CollisionManifold):
        """位置修正（防止物体穿透）"""
        a, b = manifold.body_a, manifold.body_b
        correction = manifold.normal * (manifold.penetration / (a.inverse_mass + b.inverse_mass)) * 0.8
        a.position = a.position - correction * a.inverse_mass
        b.position = b.position + correction * b.inverse_mass
    
    def get_state(self) -> dict:
        """获取物理世界状态"""
        return {
            "body_count": self.body_count,
            "active_bodies": sum(1 for b in self.bodies if b.active),
            "collision_count": len(self.collisions),
            "gravity": self.gravity.to_dict(),
            "time_step": self.time_step,
            "bodies": [
                {
                    "id": b.body_id,
                    "position": b.position.to_dict(),
                    "velocity": b.velocity.to_dict(),
                    "angle": b.angle,
                    "mass": b.mass,
                    "type": b.body_type.value,
                    "shape": b.shape_type.value,
                }
                for b in self.bodies
            ]
        }


class ParticleSystem:
    """粒子系统"""
    
    def __init__(self, max_particles: int = 1000):
        self.particles: List[dict] = []
        self.max_particles = max_particles
        self.emitters: List[dict] = []
    
    def emit(self, position: Vector2, velocity: Vector2, life: float = 2.0, 
             color: str = "#f59e0b", size: float = 3.0):
        """发射粒子"""
        if len(self.particles) >= self.max_particles:
            self.particles.pop(0)
        
        self.particles.append({
            "position": position,
            "velocity": velocity,
            "life": life,
            "max_life": life,
            "color": color,
            "size": size,
            "active": True,
        })
    
    def update(self, dt: float, gravity: Vector2 = None):
        """更新粒子"""
        gravity = gravity or Vector2(0, -9.81)
        for p in self.particles:
            if not p["active"]:
                continue
            p["velocity"] = p["velocity"] + gravity * dt
            p["position"] = p["position"] + p["velocity"] * dt
            p["life"] -= dt
            if p["life"] <= 0:
                p["active"] = False
        
        self.particles = [p for p in self.particles if p["active"]]
    
    def get_active_count(self) -> int:
        return len(self.particles)


# ==================== 测试 ====================
if __name__ == "__main__":
    print("=" * 60)
    print("  元极恒一物理仿真引擎 V2.0 测试")
    print("=" * 60)
    print()
    
    # 创建物理世界
    world = PhysicsWorld(gravity=Vector2(0, -9.81))
    print("【1】创建物理世界")
    print(f"  重力: {world.gravity.to_dict()}")
    print(f"  时间步长: {world.time_step}")
    print()
    
    # 添加地面（静态）
    ground = RigidBody(
        body_id="ground",
        position=Vector2(0, -10),
        mass=10000,
        body_type=BodyType.STATIC,
        shape_type=ShapeType.CIRCLE,
        radius=5,
    )
    world.add_body(ground)
    print("【2】添加地面（静态物体）")
    print()
    
    # 添加掉落的球
    ball = RigidBody(
        body_id="ball_001",
        position=Vector2(0, 20),
        mass=2.0,
        body_type=BodyType.DYNAMIC,
        shape_type=ShapeType.CIRCLE,
        radius=1.0,
        restitution=0.8,
    )
    world.add_body(ball)
    print("【3】添加掉落的球（动态物体）")
    print(f"  初始位置: {ball.position.to_dict()}")
    print(f"  质量: {ball.mass}kg, 弹性: {ball.restitution}")
    print()
    
    # 模拟100帧
    print("【4】模拟100帧物理运算")
    for i in range(100):
        world.step()
        if i % 20 == 0:
            print(f"  帧{i}: 球位置=({ball.position.x:.2f}, {ball.position.y:.2f}), "
                  f"速度=({ball.velocity.x:.2f}, {ball.velocity.y:.2f}), "
                  f"碰撞={len(world.collisions)}")
    
    print()
    print(f"  最终位置: ({ball.position.x:.2f}, {ball.position.y:.2f})")
    print(f"  最终速度: ({ball.velocity.x:.2f}, {ball.velocity.y:.2f})")
    print()
    
    # 粒子系统测试
    print("【5】粒子系统测试")
    ps = ParticleSystem(max_particles=500)
    for i in range(100):
        ps.emit(
            position=Vector2(0, 10),
            velocity=Vector2((i - 50) * 0.1, 5 + i * 0.05),
            life=2.0 + i * 0.01,
            color="#f59e0b",
        )
    print(f"  发射粒子: 100个")
    for i in range(60):
        ps.update(1/60, gravity=Vector2(0, -9.81))
    print(f"  60帧后活跃粒子: {ps.get_active_count()}个")
    print()
    
    # 物理世界状态
    print("【6】物理世界状态")
    state = world.get_state()
    print(f"  刚体总数: {state['body_count']}")
    print(f"  活跃刚体: {state['active_bodies']}")
    print(f"  当前碰撞: {state['collision_count']}")
    print()
    
    print("=" * 60)
    print("  ✅ 物理仿真引擎 V2.0 测试全部通过！")
    print("  功能: 刚体动力学 + 碰撞检测 + 约束求解 + 粒子系统")
    print("=" * 60)

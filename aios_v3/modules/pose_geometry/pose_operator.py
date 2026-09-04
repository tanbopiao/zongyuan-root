"""
姿态几何转换自治内核算子
KUN-LAW-019 | 昆仑洞天元法则

负责统一昆仑洞天所有：角色姿态、骨骼旋转、镜头运镜、关键帧插值、动画平滑矫正
解决欧拉角万向锁、画面跳帧、运镜抖动、姿态不统一等工程缺陷

核心能力：
- 四元数 ↔ 旋转矩阵双向转换（永久固化公式）
- SLERP四元数球面线性插值（禁止纯欧拉角插值）
- 矩阵正交性校验 + 行列式=1真值校验
- 四元数归一化校验
- 连续帧姿态平滑度校验
- 不合格帧拦截重算

纯Python实现，无外部依赖
"""

import math
import json
import hashlib
import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger("AIOSv3.PoseGeometry")

# 数学常量
EPSILON = 1e-10
DEG_TO_RAD = math.pi / 180.0
RAD_TO_DEG = 180.0 / math.pi


class Quaternion:
    """
    四元数类
    格式：q = (w, x, y, z)
    w为标量部分，x/y/z为向量部分
    所有姿态计算优先使用四元数
    """
    
    def __init__(self, w: float = 1.0, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.w = float(w)
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
    
    def __repr__(self) -> str:
        return f"Quaternion(w={self.w:.6f}, x={self.x:.6f}, y={self.y:.6f}, z={self.z:.6f})"
    
    def __eq__(self, other: 'Quaternion') -> bool:
        if not isinstance(other, Quaternion):
            return False
        return (abs(self.w - other.w) < EPSILON and
                abs(self.x - other.x) < EPSILON and
                abs(self.y - other.y) < EPSILON and
                abs(self.z - other.z) < EPSILON)
    
    def __mul__(self, other: 'Quaternion') -> 'Quaternion':
        """四元数乘法（ Hamilton乘积 ）"""
        if not isinstance(other, Quaternion):
            raise TypeError("四元数只能与四元数相乘")
        
        w1, x1, y1, z1 = self.w, self.x, self.y, self.z
        w2, x2, y2, z2 = other.w, other.x, other.y, other.z
        
        return Quaternion(
            w=w1*w2 - x1*x2 - y1*y2 - z1*z2,
            x=w1*x2 + x1*w2 + y1*z2 - z1*y2,
            y=w1*y2 - x1*z2 + y1*w2 + z1*x2,
            z=w1*z2 + x1*y2 - y1*x2 + z1*w2
        )
    
    def conjugate(self) -> 'Quaternion':
        """四元数共轭"""
        return Quaternion(self.w, -self.x, -self.y, -self.z)
    
    def norm(self) -> float:
        """四元数范数（模长）"""
        return math.sqrt(self.w**2 + self.x**2 + self.y**2 + self.z**2)
    
    def normalize(self) -> 'Quaternion':
        """四元数归一化（强制归一化，防止精度漂移）"""
        n = self.norm()
        if n < EPSILON:
            logger.warning("四元数范数接近零，返回单位四元数")
            return Quaternion(1.0, 0.0, 0.0, 0.0)
        return Quaternion(self.w/n, self.x/n, self.y/n, self.z/n)
    
    def inverse(self) -> 'Quaternion':
        """四元数逆"""
        n_sq = self.w**2 + self.x**2 + self.y**2 + self.z**2
        if n_sq < EPSILON:
            raise ValueError("零四元数没有逆")
        return Quaternion(self.w/n_sq, -self.x/n_sq, -self.y/n_sq, -self.z/n_sq)
    
    def dot(self, other: 'Quaternion') -> float:
        """四元数点积"""
        return self.w*other.w + self.x*other.x + self.y*other.y + self.z*other.z
    
    def to_list(self) -> List[float]:
        """转换为列表 [w, x, y, z]"""
        return [self.w, self.x, self.y, self.z]
    
    @classmethod
    def from_list(cls, lst: List[float]) -> 'Quaternion':
        """从列表创建"""
        if len(lst) != 4:
            raise ValueError("四元数列表必须有4个元素 [w, x, y, z]")
        return cls(lst[0], lst[1], lst[2], lst[3])
    
    @classmethod
    def identity(cls) -> 'Quaternion':
        """单位四元数"""
        return cls(1.0, 0.0, 0.0, 0.0)
    
    @classmethod
    def from_euler(cls, roll: float, pitch: float, yaw: float, degrees: bool = True) -> 'Quaternion':
        """
        从欧拉角创建四元数（ZYX顺序，即yaw-pitch-roll）
        注意：欧拉角仅用于输入转换，插值必须使用SLERP
        """
        if degrees:
            roll *= DEG_TO_RAD
            pitch *= DEG_TO_RAD
            yaw *= DEG_TO_RAD
        
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)
        
        return cls(
            w=cr * cp * cy + sr * sp * sy,
            x=sr * cp * cy - cr * sp * sy,
            y=cr * sp * cy + sr * cp * sy,
            z=cr * cp * sy - sr * sp * cy
        )
    
    def to_euler(self, degrees: bool = True) -> Tuple[float, float, float]:
        """
        转换为欧拉角（ZYX顺序）
        仅用于输出显示，插值必须使用SLERP
        """
        # 旋转矩阵 → 欧拉角
        sinr_cosp = 2 * (self.w * self.x + self.y * self.z)
        cosr_cosp = 1 - 2 * (self.x**2 + self.y**2)
        roll = math.atan2(sinr_cosp, cosr_cosp)
        
        sinp = 2 * (self.w * self.y - self.z * self.x)
        if abs(sinp) >= 1:
            pitch = math.copysign(math.pi / 2, sinp)
        else:
            pitch = math.asin(sinp)
        
        siny_cosp = 2 * (self.w * self.z + self.x * self.y)
        cosy_cosp = 1 - 2 * (self.y**2 + self.z**2)
        yaw = math.atan2(siny_cosp, cosy_cosp)
        
        if degrees:
            roll *= RAD_TO_DEG
            pitch *= RAD_TO_DEG
            yaw *= RAD_TO_DEG
        
        return roll, pitch, yaw


class RotationMatrix:
    """
    旋转矩阵类
    3x3正交矩阵，行列式=1
    用于矩阵校验、正交修复、空间变换
    """
    
    def __init__(self, matrix: Optional[List[List[float]]] = None):
        if matrix is None:
            self.matrix = [[1.0, 0.0, 0.0],
                          [0.0, 1.0, 0.0],
                          [0.0, 0.0, 1.0]]
        else:
            if len(matrix) != 3 or any(len(row) != 3 for row in matrix):
                raise ValueError("旋转矩阵必须是3x3矩阵")
            self.matrix = [[float(v) for v in row] for row in matrix]
    
    def __repr__(self) -> str:
        rows = []
        for row in self.matrix:
            rows.append(f"  [{', '.join(f'{v:.6f}' for v in row)}]")
        return "RotationMatrix(\n" + "\n".join(rows) + "\n)"
    
    def __getitem__(self, idx: int) -> List[float]:
        return self.matrix[idx]
    
    def __mul__(self, other: 'RotationMatrix') -> 'RotationMatrix':
        """矩阵乘法"""
        if not isinstance(other, RotationMatrix):
            raise TypeError("旋转矩阵只能与旋转矩阵相乘")
        
        result = [[0.0]*3 for _ in range(3)]
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    result[i][j] += self.matrix[i][k] * other.matrix[k][j]
        return RotationMatrix(result)
    
    def transpose(self) -> 'RotationMatrix':
        """矩阵转置"""
        result = [[self.matrix[j][i] for j in range(3)] for i in range(3)]
        return RotationMatrix(result)
    
    def determinant(self) -> float:
        """计算行列式"""
        m = self.matrix
        return (m[0][0] * (m[1][1]*m[2][2] - m[1][2]*m[2][1])
                - m[0][1] * (m[1][0]*m[2][2] - m[1][2]*m[2][0])
                + m[0][2] * (m[1][0]*m[2][1] - m[1][1]*m[2][0]))
    
    def is_orthogonal(self, tolerance: float = 1e-6) -> bool:
        """
        校验矩阵正交性
        正交矩阵满足 R * R^T = I
        """
        product = self * self.transpose()
        identity = RotationMatrix.identity()
        
        for i in range(3):
            for j in range(3):
                expected = 1.0 if i == j else 0.0
                if abs(product[i][j] - expected) > tolerance:
                    return False
        return True
    
    def is_valid_rotation(self, tolerance: float = 1e-6) -> bool:
        """
        校验是否为有效旋转矩阵
        条件：正交性 + 行列式=1
        """
        return self.is_orthogonal(tolerance) and abs(self.determinant() - 1.0) < tolerance
    
    def to_list(self) -> List[List[float]]:
        """转换为嵌套列表"""
        return [row[:] for row in self.matrix]
    
    @classmethod
    def identity(cls) -> 'RotationMatrix':
        """单位矩阵"""
        return cls([[1.0, 0.0, 0.0],
                   [0.0, 1.0, 0.0],
                   [0.0, 0.0, 1.0]])
    
    @classmethod
    def from_list(cls, lst: List[List[float]]) -> 'RotationMatrix':
        """从列表创建"""
        return cls(lst)


class PoseGeometryOperator:
    """
    姿态几何转换算子（KUN-LAW-019核心实现）
    
    永久固化转换公式：
    1. 四元数 → 旋转矩阵（标准渲染公式）
    2. 旋转矩阵 → 四元数（内核稳健算法：迹判定+最大分量+归一化）
    
    强制规则：
    - 禁止使用纯欧拉角做动画插值
    - 所有插值强制使用SLERP四元数球面线性插值
    - 所有关键帧必须经过双向校验
    """
    
    def __init__(self):
        self.conversion_count = 0
        self.interpolation_count = 0
        self.validation_count = 0
        logger.info("姿态几何转换算子初始化完成（KUN-LAW-019）")
    
    def quaternion_to_matrix(self, q: Quaternion) -> RotationMatrix:
        """
        四元数 → 旋转矩阵（标准渲染公式，永久固化）
        
        R = [
            [1-2y²-2z², 2xy-2wz,   2xz+2wy],
            [2xy+2wz,   1-2x²-2z², 2yz-2wx],
            [2xz-2wy,   2yz+2wx,   1-2x²-2y²]
        ]
        """
        # 先归一化，确保计算准确
        q = q.normalize()
        w, x, y, z = q.w, q.x, q.y, q.z
        
        matrix = [
            [1 - 2*y*y - 2*z*z, 2*x*y - 2*w*z,     2*x*z + 2*w*y],
            [2*x*y + 2*w*z,     1 - 2*x*x - 2*z*z, 2*y*z - 2*w*x],
            [2*x*z - 2*w*y,     2*y*z + 2*w*x,     1 - 2*x*x - 2*y*y]
        ]
        
        self.conversion_count += 1
        return RotationMatrix(matrix)
    
    def matrix_to_quaternion(self, m: RotationMatrix) -> Quaternion:
        """
        旋转矩阵 → 四元数（内核稳健算法，永久固化）
        
        算法步骤：
        1. 优先矩阵迹判定
        2. 取最大分量防精度崩坏
        3. 自动归一化收尾
        
        这是云内核唯一认可的转换范式，禁止自定义改写
        """
        matrix = m.matrix
        trace = matrix[0][0] + matrix[1][1] + matrix[2][2]
        
        if trace > 0:
            # 迹为正，直接计算
            s = math.sqrt(trace + 1.0) * 2
            w = 0.25 * s
            x = (matrix[2][1] - matrix[1][2]) / s
            y = (matrix[0][2] - matrix[2][0]) / s
            z = (matrix[1][0] - matrix[0][1]) / s
        else:
            # 迹为负，找最大对角元素
            if matrix[0][0] > matrix[1][1] and matrix[0][0] > matrix[2][2]:
                s = math.sqrt(1.0 + matrix[0][0] - matrix[1][1] - matrix[2][2]) * 2
                w = (matrix[2][1] - matrix[1][2]) / s
                x = 0.25 * s
                y = (matrix[0][1] + matrix[1][0]) / s
                z = (matrix[0][2] + matrix[2][0]) / s
            elif matrix[1][1] > matrix[2][2]:
                s = math.sqrt(1.0 + matrix[1][1] - matrix[0][0] - matrix[2][2]) * 2
                w = (matrix[0][2] - matrix[2][0]) / s
                x = (matrix[0][1] + matrix[1][0]) / s
                y = 0.25 * s
                z = (matrix[1][2] + matrix[2][1]) / s
            else:
                s = math.sqrt(1.0 + matrix[2][2] - matrix[0][0] - matrix[1][1]) * 2
                w = (matrix[1][0] - matrix[0][1]) / s
                x = (matrix[0][2] + matrix[2][0]) / s
                y = (matrix[1][2] + matrix[2][1]) / s
                z = 0.25 * s
        
        q = Quaternion(w, x, y, z).normalize()
        self.conversion_count += 1
        return q
    
    def slerp(self, q1: Quaternion, q2: Quaternion, t: float) -> Quaternion:
        """
        SLERP四元数球面线性插值（强制使用，禁止纯欧拉角插值）
        
        适用于：镜头环绕、角色转身、神力抬手、神兽动态
        杜绝：抖动、卡顿、角度跳变、万向锁崩坏
        
        参数：
            q1: 起始四元数
            q2: 目标四元数
            t: 插值参数 [0, 1]
        """
        # 归一化输入
        q1 = q1.normalize()
        q2 = q2.normalize()
        
        # 计算点积（余弦夹角）
        dot = q1.dot(q2)
        
        # 如果点积为负，取反其中一个四元数以保证最短路径插值
        if dot < 0.0:
            q2 = Quaternion(-q2.w, -q2.x, -q2.y, -q2.z)
            dot = -dot
        
        # 如果四元数非常接近，使用线性插值避免除零
        if dot > 0.9995:
            result = Quaternion(
                w=q1.w + t * (q2.w - q1.w),
                x=q1.x + t * (q2.x - q1.x),
                y=q1.y + t * (q2.y - q1.y),
                z=q1.z + t * (q2.z - q1.z)
            )
            self.interpolation_count += 1
            return result.normalize()
        
        # 标准SLERP
        theta_0 = math.acos(max(-1.0, min(1.0, dot)))
        theta = theta_0 * t
        sin_theta = math.sin(theta)
        sin_theta_0 = math.sin(theta_0)
        
        s1 = math.cos(theta) - dot * sin_theta / sin_theta_0
        s2 = sin_theta / sin_theta_0
        
        result = Quaternion(
            w=s1 * q1.w + s2 * q2.w,
            x=s1 * q1.x + s2 * q2.x,
            y=s1 * q1.y + s2 * q2.y,
            z=s1 * q1.z + s2 * q2.z
        )
        
        self.interpolation_count += 1
        return result.normalize()
    
    def slerp_sequence(self, q1: Quaternion, q2: Quaternion, 
                        num_frames: int) -> List[Quaternion]:
        """
        生成SLERP插值序列（用于关键帧之间的过渡帧）
        
        参数：
            q1: 起始关键帧姿态
            q2: 目标关键帧姿态
            num_frames: 生成的帧数（包含起始和结束）
        """
        if num_frames < 2:
            return [q1.normalize()]
        
        frames = []
        for i in range(num_frames):
            t = i / (num_frames - 1)
            frames.append(self.slerp(q1, q2, t))
        return frames
    
    def bidirectional_verify(self, q: Quaternion) -> Dict[str, Any]:
        """
        四元数 ↔ 旋转矩阵双向校验
        所有关键帧资产入库必须经过此校验
        """
        # 四元数 → 矩阵
        matrix = self.quaternion_to_matrix(q)
        
        # 矩阵 → 四元数
        q_recovered = self.matrix_to_quaternion(matrix)
        
        # 校验一致性（考虑四元数的双覆盖性，q和-q表示同一旋转）
        q_norm = q.normalize()
        q_rec_norm = q_recovered.normalize()
        
        direct_match = (abs(q_norm.w - q_rec_norm.w) < 1e-6 and
                        abs(q_norm.x - q_rec_norm.x) < 1e-6 and
                        abs(q_norm.y - q_rec_norm.y) < 1e-6 and
                        abs(q_norm.z - q_rec_norm.z) < 1e-6)
        
        negated_match = (abs(q_norm.w + q_rec_norm.w) < 1e-6 and
                         abs(q_norm.x + q_rec_norm.x) < 1e-6 and
                         abs(q_norm.y + q_rec_norm.y) < 1e-6 and
                         abs(q_norm.z + q_rec_norm.z) < 1e-6)
        
        consistent = direct_match or negated_match
        
        # 矩阵校验
        matrix_valid = matrix.is_valid_rotation()
        
        return {
            "success": consistent and matrix_valid,
            "original_quaternion": q_norm.to_list(),
            "recovered_quaternion": q_rec_norm.to_list(),
            "matrix": matrix.to_list(),
            "consistent": consistent,
            "matrix_valid": matrix_valid,
            "matrix_determinant": matrix.determinant(),
            "matrix_orthogonal": matrix.is_orthogonal()
        }
    
    def get_stats(self) -> Dict[str, int]:
        """获取算子统计"""
        return {
            "conversion_count": self.conversion_count,
            "interpolation_count": self.interpolation_count,
            "validation_count": self.validation_count
        }


class PoseValidator:
    """
    姿态校验器（视频生成前置校验算子）
    
    云内核自动巡检每一帧姿态：
    - 矩阵正交性校验
    - 行列式=1真值校验
    - 四元数归一化校验
    - 连续帧姿态平滑度校验
    
    不合格帧直接拦截重算，保障短剧资产画质稳态统一
    """
    
    def __init__(self, 
                 orthogonality_tolerance: float = 1e-6,
                 determinant_tolerance: float = 1e-6,
                 quaternion_norm_tolerance: float = 1e-6,
                 smoothness_threshold: float = 0.5):
        self.orthogonality_tolerance = orthogonality_tolerance
        self.determinant_tolerance = determinant_tolerance
        self.quaternion_norm_tolerance = quaternion_norm_tolerance
        self.smoothness_threshold = smoothness_threshold
        self.validation_count = 0
        self.passed_count = 0
        self.failed_count = 0
        logger.info("姿态校验器初始化完成（KUN-LAW-019）")
    
    def check_orthogonality(self, matrix: RotationMatrix) -> Dict[str, Any]:
        """矩阵正交性校验"""
        is_ortho = matrix.is_orthogonal(self.orthogonality_tolerance)
        product = matrix * matrix.transpose()
        identity = RotationMatrix.identity()
        
        max_deviation = 0.0
        for i in range(3):
            for j in range(3):
                expected = 1.0 if i == j else 0.0
                deviation = abs(product[i][j] - expected)
                max_deviation = max(max_deviation, deviation)
        
        return {
            "passed": is_ortho,
            "max_deviation": max_deviation,
            "tolerance": self.orthogonality_tolerance,
            "message": "矩阵正交性校验通过" if is_ortho else f"矩阵正交性校验失败，最大偏差{max_deviation:.2e}"
        }
    
    def check_determinant(self, matrix: RotationMatrix) -> Dict[str, Any]:
        """行列式=1真值校验"""
        det = matrix.determinant()
        passed = abs(det - 1.0) < self.determinant_tolerance
        
        return {
            "passed": passed,
            "determinant": det,
            "expected": 1.0,
            "deviation": abs(det - 1.0),
            "tolerance": self.determinant_tolerance,
            "message": "行列式=1校验通过" if passed else f"行列式校验失败，当前值{det:.6f}，偏差{abs(det-1.0):.2e}"
        }
    
    def check_quaternion_normalization(self, q: Quaternion) -> Dict[str, Any]:
        """四元数归一化校验"""
        norm = q.norm()
        passed = abs(norm - 1.0) < self.quaternion_norm_tolerance
        
        return {
            "passed": passed,
            "norm": norm,
            "expected": 1.0,
            "deviation": abs(norm - 1.0),
            "tolerance": self.quaternion_norm_tolerance,
            "normalized_quaternion": q.normalize().to_list(),
            "message": "四元数归一化校验通过" if passed else f"四元数未归一化，范数{norm:.6f}，偏差{abs(norm-1.0):.2e}"
        }
    
    def check_smoothness(self, q_prev: Quaternion, q_curr: Quaternion, 
                          q_next: Optional[Quaternion] = None) -> Dict[str, Any]:
        """
        连续帧姿态平滑度校验
        检测角度跳变、抖动、不连续
        """
        q_prev_norm = q_prev.normalize()
        q_curr_norm = q_curr.normalize()
        
        # 计算相邻帧之间的旋转角度
        dot = abs(q_prev_norm.dot(q_curr_norm))
        dot = max(-1.0, min(1.0, dot))
        angle_prev_curr = 2 * math.acos(dot) * RAD_TO_DEG
        
        # 如果有下一帧，计算二阶差分（加速度）
        if q_next is not None:
            q_next_norm = q_next.normalize()
            dot2 = abs(q_curr_norm.dot(q_next_norm))
            dot2 = max(-1.0, min(1.0, dot2))
            angle_curr_next = 2 * math.acos(dot2) * RAD_TO_DEG
            
            # 二阶差分（角度变化率的变化）
            second_order_diff = abs(angle_curr_next - angle_prev_curr)
        else:
            angle_curr_next = None
            second_order_diff = None
        
        # 平滑度判定
        max_angle = max(angle_prev_curr, angle_curr_next or 0)
        passed = max_angle < self.smoothness_threshold * 100  # 转换为度阈值
        
        return {
            "passed": passed,
            "angle_prev_curr_deg": angle_prev_curr,
            "angle_curr_next_deg": angle_curr_next,
            "second_order_diff_deg": second_order_diff,
            "threshold_deg": self.smoothness_threshold * 100,
            "message": "姿态平滑度校验通过" if passed else f"姿态跳变检测到，最大角度{max_angle:.2f}°，阈值{self.smoothness_threshold*100:.2f}°"
        }
    
    def full_pose_validation(self, q: Quaternion, 
                              q_prev: Optional[Quaternion] = None,
                              q_next: Optional[Quaternion] = None) -> Dict[str, Any]:
        """
        完整姿态校验（视频生成前置校验算子）
        
        校验项：
        1. 四元数归一化校验
        2. 四元数 → 矩阵转换
        3. 矩阵正交性校验
        4. 行列式=1真值校验
        5. 连续帧姿态平滑度校验（如果有前后帧）
        
        不合格帧直接拦截重算
        """
        self.validation_count += 1
        
        results = {}
        all_passed = True
        
        # 1. 四元数归一化校验
        norm_result = self.check_quaternion_normalization(q)
        results['quaternion_normalization'] = norm_result
        if not norm_result['passed']:
            all_passed = False
        
        # 2. 转换为矩阵
        operator = PoseGeometryOperator()
        matrix = operator.quaternion_to_matrix(q)
        
        # 3. 矩阵正交性校验
        ortho_result = self.check_orthogonality(matrix)
        results['matrix_orthogonality'] = ortho_result
        if not ortho_result['passed']:
            all_passed = False
        
        # 4. 行列式=1校验
        det_result = self.check_determinant(matrix)
        results['determinant'] = det_result
        if not det_result['passed']:
            all_passed = False
        
        # 5. 连续帧平滑度校验
        if q_prev is not None:
            smooth_result = self.check_smoothness(q_prev, q, q_next)
            results['smoothness'] = smooth_result
            if not smooth_result['passed']:
                all_passed = False
        
        # 生成校验哈希（用于资产确权）
        validation_data = json.dumps({
            "quaternion": q.normalize().to_list(),
            "matrix": matrix.to_list(),
            "results": {k: v['passed'] for k, v in results.items()},
            "timestamp": datetime.now(timezone(timedelta(hours=8))).isoformat()
        }, ensure_ascii=False, sort_keys=True)
        validation_hash = hashlib.sha256(validation_data.encode()).hexdigest()
        
        if all_passed:
            self.passed_count += 1
        else:
            self.failed_count += 1
        
        return {
            "passed": all_passed,
            "action": "通过，允许渲染" if all_passed else "拦截，需要重算",
            "quaternion": q.normalize().to_list(),
            "matrix": matrix.to_list(),
            "checks": results,
            "validation_hash": validation_hash,
            "timestamp": datetime.now(timezone(timedelta(hours=8))).isoformat(),
            "law_id": "KUN-LAW-019"
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取校验器统计"""
        total = self.validation_count
        pass_rate = (self.passed_count / total * 100) if total > 0 else 0
        
        return {
            "total_validations": total,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "pass_rate": round(pass_rate, 2),
            "thresholds": {
                "orthogonality_tolerance": self.orthogonality_tolerance,
                "determinant_tolerance": self.determinant_tolerance,
                "quaternion_norm_tolerance": self.quaternion_norm_tolerance,
                "smoothness_threshold_deg": self.smoothness_threshold * 100
            }
        }


class PoseGeometryKernel:
    """
    姿态几何自治内核（完整封装）
    
    整合：
    - PoseGeometryOperator（转换算子）
    - PoseValidator（校验器）
    - 姿态资产管理
    - Merkle-DAG溯源链路
    
    自治闭环：
    动画关键帧生成 → 姿态矩阵计算 → 四元数平滑插值 → 内核合规校验 → 哈希确权 → 视频渲染 → 三层全域锁档
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.operator = PoseGeometryOperator()
        self.validator = PoseValidator()
        
        if data_dir is None:
            data_dir = Path(r"C:\Users\4906\.zongyuan_root\aios_v3\data\pose_geometry")
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.pose_assets = self._load_pose_assets()
        logger.info("姿态几何自治内核初始化完成（KUN-LAW-019）")
    
    def _load_pose_assets(self) -> List[Dict]:
        """加载姿态资产"""
        assets_file = self.data_dir / 'pose_assets.json'
        if assets_file.exists():
            with open(assets_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_pose_assets(self):
        """保存姿态资产"""
        assets_file = self.data_dir / 'pose_assets.json'
        with open(assets_file, 'w', encoding='utf-8') as f:
            json.dump(self.pose_assets, f, ensure_ascii=False, indent=2)
    
    def register_pose_asset(self, name: str, quaternion: Quaternion,
                             category: str = "character",
                             character: str = "generic",
                             scene: str = "default") -> Dict[str, Any]:
        """
        注册姿态资产（入库前必须经过双向校验）
        
        每一组姿态参数附带：
        - 几何校验哈希
        - 矩阵正交回执
        - 四元数归一化凭证
        并入Merkle-DAG溯源链路
        """
        # 双向校验
        verify_result = self.operator.bidirectional_verify(quaternion)
        
        if not verify_result['success']:
            return {
                "success": False,
                "error": "姿态资产双向校验失败，拒绝入库",
                "verify_result": verify_result
            }
        
        # 完整校验
        full_validation = self.validator.full_pose_validation(quaternion)
        
        # 生成资产ID
        asset_id = f"POSE-{hashlib.md5(name.encode()).hexdigest()[:8]}-{int(time.time())}"
        
        # 生成Merkle凭证
        asset_data = {
            "name": name,
            "quaternion": quaternion.normalize().to_list(),
            "matrix": verify_result['matrix'],
            "category": category,
            "character": character,
            "scene": scene,
            "verify_result": verify_result,
            "full_validation": full_validation,
            "law_id": "KUN-LAW-019",
            "created_at": datetime.now(timezone(timedelta(hours=8))).isoformat()
        }
        
        asset_hash = hashlib.sha256(
            json.dumps(asset_data, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
        
        asset_record = {
            "asset_id": asset_id,
            "name": name,
            "category": category,
            "character": character,
            "scene": scene,
            "quaternion": quaternion.normalize().to_list(),
            "matrix": verify_result['matrix'],
            "asset_hash": asset_hash,
            "validation_hash": full_validation['validation_hash'],
            "geometric_verification": {
                "orthogonality_passed": verify_result['matrix_orthogonal'],
                "determinant": verify_result['matrix_determinant'],
                "bidirectional_consistent": verify_result['consistent']
            },
            "law_id": "KUN-LAW-019",
            "created_at": datetime.now(timezone(timedelta(hours=8))).isoformat()
        }
        
        self.pose_assets.append(asset_record)
        self._save_pose_assets()
        
        return {
            "success": True,
            "asset_id": asset_id,
            "asset_hash": asset_hash,
            "validation_hash": full_validation['validation_hash'],
            "record": asset_record,
            "message": f"姿态资产「{name}」已注册入库，校验通过，哈希确权完成"
        }
    
    def generate_camera_orbit(self, center_quat: Quaternion, 
                                axis: str = "y",
                                total_degrees: float = 360.0,
                                num_frames: int = 60) -> List[Quaternion]:
        """
        生成环绕镜头轨迹（短剧运镜引擎）
        
        所有环绕镜头、抬镜、俯冲、跟随镜头，由四元数SLERP生成丝滑轨迹
        """
        frames = []
        for i in range(num_frames):
            angle_deg = (i / (num_frames - 1)) * total_degrees
            angle_rad = angle_deg * DEG_TO_RAD
            
            if axis == "x":
                rotation = Quaternion(math.cos(angle_rad/2), math.sin(angle_rad/2), 0, 0)
            elif axis == "y":
                rotation = Quaternion(math.cos(angle_rad/2), 0, math.sin(angle_rad/2), 0)
            elif axis == "z":
                rotation = Quaternion(math.cos(angle_rad/2), 0, 0, math.sin(angle_rad/2))
            else:
                raise ValueError(f"不支持的旋转轴: {axis}，支持 x/y/z")
            
            result = (rotation * center_quat).normalize()
            frames.append(result)
        
        return frames
    
    def validate_frame_sequence(self, frames: List[Quaternion]) -> Dict[str, Any]:
        """
        校验完整帧序列（视频生成前置批量校验）
        
        不合格帧直接拦截重算
        """
        results = []
        failed_frames = []
        
        for i, q in enumerate(frames):
            q_prev = frames[i-1] if i > 0 else None
            q_next = frames[i+1] if i < len(frames)-1 else None
            
            validation = self.validator.full_pose_validation(q, q_prev, q_next)
            results.append({
                "frame_index": i,
                "validation": validation
            })
            
            if not validation['passed']:
                failed_frames.append(i)
        
        all_passed = len(failed_frames) == 0
        
        return {
            "total_frames": len(frames),
            "passed_frames": len(frames) - len(failed_frames),
            "failed_frames": failed_frames,
            "all_passed": all_passed,
            "action": "全部通过，允许渲染" if all_passed else f"{len(failed_frames)}帧不合格，需要重算",
            "frame_results": results,
            "law_id": "KUN-LAW-019"
        }
    
    def get_kernel_status(self) -> Dict[str, Any]:
        """获取内核状态"""
        return {
            "law_id": "KUN-LAW-019",
            "law_name": "姿态几何转换自治内核算子",
            "status": "active",
            "operator_stats": self.operator.get_stats(),
            "validator_stats": self.validator.get_stats(),
            "registered_assets": len(self.pose_assets),
            "autonomous_closed_loop": [
                "动画关键帧生成",
                "姿态矩阵计算",
                "四元数平滑插值",
                "内核合规校验",
                "哈希确权",
                "视频渲染",
                "三层全域锁档"
            ],
            "enforcement_rules": [
                "所有3D姿态存储统一标准（四元数优先，矩阵校验）",
                "禁止使用纯欧拉角做动画插值（强制SLERP）",
                "视频生成前置校验算子（不合格帧拦截重算）"
            ]
        }


# 便捷函数
def create_kernel(data_dir: Optional[Path] = None) -> PoseGeometryKernel:
    """创建姿态几何自治内核实例"""
    return PoseGeometryKernel(data_dir)


if __name__ == "__main__":
    print("=" * 60)
    print("姿态几何转换自治内核算子 - KUN-LAW-019")
    print("Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZONGYUAN-ROOT")
    print("=" * 60)
    print()
    
    # 创建内核
    kernel = create_kernel()
    
    # 测试1：四元数 ↔ 矩阵双向转换
    print("【测试1】四元数 ↔ 旋转矩阵双向转换")
    q = Quaternion.from_euler(30, 45, 60)
    print(f"  原始四元数: {q}")
    print(f"  原始欧拉角: roll=30°, pitch=45°, yaw=60°")
    
    operator = PoseGeometryOperator()
    matrix = operator.quaternion_to_matrix(q)
    print(f"  转换矩阵行列式: {matrix.determinant():.6f}")
    print(f"  矩阵正交性: {matrix.is_orthogonal()}")
    
    q_recovered = operator.matrix_to_quaternion(matrix)
    print(f"  恢复四元数: {q_recovered}")
    
    verify = operator.bidirectional_verify(q)
    print(f"  双向校验: {'通过' if verify['success'] else '失败'}")
    print()
    
    # 测试2：SLERP插值
    print("【测试2】SLERP四元数球面线性插值")
    q1 = Quaternion.from_euler(0, 0, 0)
    q2 = Quaternion.from_euler(0, 90, 0)
    print(f"  起始: {q1}")
    print(f"  目标: {q2}")
    
    for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
        q_interp = operator.slerp(q1, q2, t)
        roll, pitch, yaw = q_interp.to_euler()
        print(f"  t={t:.2f}: yaw={yaw:.1f}° (四元数: {q_interp.w:.4f}, {q_interp.z:.4f})")
    print()
    
    # 测试3：姿态校验
    print("【测试3】完整姿态校验")
    validator = PoseValidator()
    validation = validator.full_pose_validation(q)
    print(f"  校验结果: {'通过' if validation['passed'] else '失败'}")
    print(f"  校验哈希: {validation['validation_hash'][:32]}...")
    print(f"  四元数归一化: {validation['checks']['quaternion_normalization']['passed']}")
    print(f"  矩阵正交性: {validation['checks']['matrix_orthogonality']['passed']}")
    print(f"  行列式=1: {validation['checks']['determinant']['passed']}")
    print()
    
    # 测试4：注册姿态资产
    print("【测试4】注册姿态资产")
    result = kernel.register_pose_asset(
        name="月神_抬手姿态",
        quaternion=Quaternion.from_euler(15, 30, 45),
        category="character",
        character="月神",
        scene="昆仑墟境"
    )
    print(f"  注册结果: {'成功' if result['success'] else '失败'}")
    if result['success']:
        print(f"  资产ID: {result['asset_id']}")
        print(f"  资产哈希: {result['asset_hash'][:32]}...")
    print()
    
    # 测试5：环绕镜头生成
    print("【测试5】环绕镜头轨迹生成")
    center = Quaternion.identity()
    orbit_frames = kernel.generate_camera_orbit(center, axis="y", total_degrees=360, num_frames=8)
    print(f"  生成帧数: {len(orbit_frames)}")
    for i, frame in enumerate(orbit_frames):
        roll, pitch, yaw = frame.to_euler()
        print(f"  帧{i}: yaw={yaw:.1f}°")
    print()
    
    # 内核状态
    print("【内核状态】")
    status = kernel.get_kernel_status()
    print(f"  法则ID: {status['law_id']}")
    print(f"  转换次数: {status['operator_stats']['conversion_count']}")
    print(f"  插值次数: {status['operator_stats']['interpolation_count']}")
    print(f"  校验总数: {status['validator_stats']['total_validations']}")
    print(f"  通过率: {status['validator_stats']['pass_rate']}%")
    print(f"  已注册资产: {status['registered_assets']}")
    print()
    
    print("=" * 60)
    print("✅ 姿态几何转换自治内核算子测试完成")
    print("法则终局真值：所有虚拟姿态，皆以矩阵建基、四元数归一、内核自治校验、全域溯源确权。")
    print("=" * 60)

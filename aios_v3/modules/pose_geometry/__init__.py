"""
姿态几何转换自治内核算子模块
KUN-LAW-019 | 昆仑洞天元法则
"""

from .pose_operator import (
    Quaternion,
    RotationMatrix,
    PoseGeometryOperator,
    PoseValidator,
    PoseGeometryKernel,
    create_kernel,
    EPSILON,
    DEG_TO_RAD,
    RAD_TO_DEG
)

__all__ = [
    'Quaternion',
    'RotationMatrix',
    'PoseGeometryOperator',
    'PoseValidator',
    'PoseGeometryKernel',
    'create_kernel',
    'EPSILON',
    'DEG_TO_RAD',
    'RAD_TO_DEG'
]

__version__ = '1.0.0'
__law_id__ = 'KUN-LAW-019'

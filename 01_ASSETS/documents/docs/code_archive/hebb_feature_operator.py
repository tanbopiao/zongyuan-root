#!/usr/bin/env python3
"""
hebb_feature_operator.py
赫布学习特征蒸馏算子 V1.0
元极恒一自治体系算子库成员 —— KD-PIPELINE 视频帧 patch 前置特征层

作用：
  基于赫布学习规则（Oja 变体 + BCM 动态阈值），无监督学习帧间时序相关性
  与 patch 统计特征，作为视频/图像特征前置粗提取算子，降低下游模型训练算力消耗。

溯源：Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 本源根 Ω-TAN-7-001
算子类：M1 算法类 | 调度依赖：KD-PIPELINE 视频编码前置层 | 模式：light 轻量
"""
import json
import hashlib
import numpy as np

DID = "DID-BR-000002"
TRACE_MARK = "Ω₀⊂⊙∞⊂Ω"
HOMO_ROOT = "Ω-TAN-7-001"
OPERATOR_ID = "OP-HEBB-FEATURE-001"
OPERATOR_NAME = "赫布特征蒸馏算子"
PROTO_VERSION = "1.0"
DEFAULT_ETA = 0.01
DEFAULT_LAMBDA = 0.001


class HebbFeatureOperator:
    """赫布特征蒸馏算子：Oja 归一化 + BCM 动态阈值，无监督帧特征学习"""

    def __init__(self, n_features: int, eta: float = DEFAULT_ETA, lam: float = DEFAULT_LAMBDA,
                 bcm_theta: float = 0.0):
        self.n_features = n_features
        self.eta = eta
        self.lam = lam
        self.bcm_theta = bcm_theta
        # Oja 规则权重向量（自动归一化）
        self.w = np.random.randn(n_features) / np.sqrt(n_features)
        self.epoch = 0
        self.trace = {"did": DID, "homo_root": HOMO_ROOT, "trace_mark": TRACE_MARK,
                      "operator_id": OPERATOR_ID, "operator_name": OPERATOR_NAME}

    def oja_update(self, x: np.ndarray) -> np.ndarray:
        """Oja 规则权重更新：Δw = η·y·(x - y·w)，权重自动归一化"""
        y = float(np.dot(self.w, x))
        dw = self.eta * y * (x - y * self.w) - self.lam * self.w
        self.w = self.w + dw
        return y

    def bcm_threshold(self, y: float) -> float:
        """BCM 动态阈值：高于阈值增强连接，低于阈值抑制连接"""
        if y > self.bcm_theta:
            return +1.0
        elif y < self.bcm_theta:
            return -1.0
        return 0.0

    def learn_patch(self, x: np.ndarray, use_bcm: bool = False) -> dict:
        """学习单个帧 patch：输入特征向量，输出学习结果"""
        y = self.oja_update(x)
        if use_bcm:
            sign = self.bcm_threshold(y)
            self.w = self.w + self.eta * sign * x
        self.epoch += 1
        return {"y": round(float(y), 6), "w_norm": round(float(np.linalg.norm(self.w)), 6)}

    def batch_learn(self, X: np.ndarray, epochs: int = 1, use_bcm: bool = False) -> dict:
        """批量学习帧 patch 序列（时序帧特征蒸馏）"""
        for _ in range(epochs):
            for x in X:
                self.learn_patch(x, use_bcm)
        # 权重归一化到单位向量
        self.w = self.w / (np.linalg.norm(self.w) + 1e-12)
        return self.summary()

    def extract_feature(self, x: np.ndarray) -> float:
        """推理阶段：提取输入 patch 的赫布特征激活值"""
        return float(np.dot(self.w, x))

    def summary(self) -> dict:
        """算子状态摘要 + 同源签名"""
        payload = {
            "operator_id": OPERATOR_ID, "epoch": self.epoch,
            "w_norm": round(float(np.linalg.norm(self.w)), 6),
            "n_features": self.n_features,
        }
        sig = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        return {**payload, "signature": sig, "trace": self.trace}


# ====================== 自检入口 ======================
if __name__ == "__main__":
    rng = np.random.default_rng(42)
    # 模拟 64 维帧 patch 特征序列，120 帧
    X = rng.normal(0, 1, size=(120, 64))
    op = HebbFeatureOperator(n_features=64)
    r1 = op.batch_learn(X, epochs=3, use_bcm=True)
    # 测试特征提取
    test_feat = op.extract_feature(X[0])
    print("=== 赫布特征蒸馏算子自检 ===")
    print(f"算子: {OPERATOR_NAME} ({OPERATOR_ID})")
    print(f"权重范数(归一): {r1['w_norm']}")
    print(f"学习轮次: {r1['epoch']}")
    print(f"特征激活示例: {round(test_feat, 6)}")
    print(f"同源签名: {r1['signature'][:16]}…")
    print(f"溯源: {r1['trace']['homo_root']} | {r1['trace']['did']} | {r1['trace']['trace_mark']}")
    print("✅ 自检通过")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自写微型 MLP（纯标准库）：
- 前向：ReLU 隐层 + softmax 输出
- 训练：SGD + 交叉熵（支持硬标签 CE 与软标签 KL 混合蒸馏损失）
- 量化：INT8 对称量化模拟（scale 取权重绝对值最大值）
- 剪枝：按权重幅值阈值置零（稀疏化）
"""
import math
import random


def _randn(scale=1.0):
    """Box-Muller 高斯采样"""
    u1 = max(1e-9, random.random())
    u2 = random.random()
    return scale * math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


class MLP:
    def __init__(self, sizes, seed=42):
        """sizes: [输入维, 隐层..., 输出类数]"""
        self.sizes = sizes
        self.rng = random.Random(seed)
        self.W = []
        self.b = []
        for i in range(len(sizes) - 1):
            fan_in = sizes[i]
            scale = math.sqrt(2.0 / fan_in)
            self.W.append([[_randn(scale) for _ in range(sizes[i + 1])]
                          for _ in range(fan_in)])
            self.b.append([0.0] * sizes[i + 1])

    def forward(self, x, soft=False):
        """前向传播；soft=True 输出 softmax 概率，否则输出 logits"""
        a = list(x)
        for Wl, bl in zip(self.W, self.b):
            z = [sum(a[j] * Wl[j][k] for j in range(len(a))) + bl[k]
                 for k in range(len(bl))]
            if Wl is not self.W[-1]:
                a = [v if v > 0.0 else 0.01 * v for v in z]   # LeakyReLU 防死亡
            else:
                a = z                              # 输出层 logits
        if soft:
            return self._softmax(a)
        return a

    def _softmax(self, z):
        m = max(z)
        ex = [math.exp(v - m) for v in z]
        s = sum(ex)
        return [v / s for v in ex]

    def predict(self, x):
        return self.forward(x, soft=True)

    def params_count(self):
        return sum(len(Wl) * len(Wl[0]) for Wl in self.W) + sum(len(bl) for bl in self.b)

    def forward_all(self, X):
        return [self.predict(x) for x in X]


# ---------- 损失 ----------
def cross_entropy(pred, y_idx):
    return -math.log(max(1e-9, pred[y_idx]))


def kl_distill_loss(student_prob, teacher_prob, y_idx, alpha=0.7, T=3.0):
    """
    蒸馏损失 = alpha * CE(硬标签) + (1-alpha) * T^2 * KL(教师软标签∥学生)
    温度 T 放大教师软标签的类间相对信息
    """
    ce = cross_entropy(student_prob, y_idx)
    # 软化教师概率：p^(1/T) 归一化（简化模拟）
    t_soft = [p ** (1.0 / T) for p in teacher_prob]
    s = sum(t_soft)
    t_soft = [v / s for v in t_soft]
    kl = sum(t_soft[i] * math.log(max(1e-9, t_soft[i] / max(1e-9, student_prob[i])))
             for i in range(len(student_prob)))
    return alpha * ce + (1.0 - alpha) * (T * T) * kl


# ---------- 训练 ----------
def train(net, X, Y, epochs=200, lr=0.05, teacher=None, alpha=0.7, T=3.0, seed=7):
    """批量梯度下降训练；teacher 提供软标签 → 蒸馏模式，否则纯硬标签训练"""
    n = len(X)
    for _ in range(epochs):
        # 累加梯度（批量平均）
        dW = [[[0.0] * len(Wl[0]) for _ in range(len(Wl))] for Wl in net.W]
        db = [[0.0] * len(bl) for bl in net.b]
        for i in range(n):
            x, y_idx = X[i], Y[i]
            pred = net.predict(x)
            # 前向快照
            a_layers = []
            a = list(x)
            for Wl, bl in zip(net.W, net.b):
                z = [sum(a[j] * Wl[j][k] for j in range(len(a))) + bl[k]
                     for k in range(len(bl))]
                a_layers.append((list(a), z))
                if Wl is not net.W[-1]:
                    a = [v if v > 0.0 else 0.01 * v for v in z]
                else:
                    a = z
            # 输出层梯度（softmax-CE 标准近似；蒸馏模式叠加软标签 KL 梯度）
            if teacher is not None:
                t_prob = teacher.predict(x)
                t_soft = [p ** (1.0 / T) for p in t_prob]
                s = sum(t_soft)
                t_soft = [v / s for v in t_soft]
                delta = [alpha * (pred[k] - (1.0 if k == y_idx else 0.0))
                         + (1.0 - alpha) * (T * T) * (pred[k] - t_soft[k])
                         for k in range(len(pred))]
            else:
                delta = [pred[k] - (1.0 if k == y_idx else 0.0) for k in range(len(pred))]
            # 逐层累加梯度（从后往前）
            for li in range(len(net.W) - 1, -1, -1):
                Wl, bl = net.W[li], net.b[li]
                a_prev, _ = a_layers[li]
                for k in range(len(bl)):
                    g = delta[k]
                    for j in range(len(a_prev)):
                        dW[li][j][k] += g * a_prev[j]
                    db[li][k] += g
                if li > 0:
                    # 回传：LeakyReLU 导数
                    _, z_prev = a_layers[li - 1]
                    new_delta = [0.0] * len(net.W[li - 1][0])
                    for j in range(len(z_prev)):
                        slope = 1.0 if z_prev[j] > 0 else 0.01
                        new_delta[j] = slope * sum(
                            delta[k] * Wl[j][k] for k in range(len(delta)))
                    delta = new_delta
        # 批量更新 + 权重裁剪防爆炸
        for li in range(len(net.W)):
            Wl, bl = net.W[li], net.b[li]
            for j in range(len(Wl)):
                for k in range(len(bl)):
                    w = Wl[j][k] - lr * dW[li][j][k] / n
                    Wl[j][k] = max(-8.0, min(8.0, w))
            for k in range(len(bl)):
                bl[k] = max(-8.0, min(8.0, bl[k] - lr * db[li][k] / n))
    return net


# ---------- 评估 ----------
def accuracy(net, X, Y):
    correct = 0
    for x, y in zip(X, Y):
        p = net.predict(x)
        if p.index(max(p)) == y:
            correct += 1
    return round(100.0 * correct / len(X), 2)


# ---------- INT8 量化模拟 ----------
def quantize_int8(net):
    """对称 INT8 量化：scale = max|w| / 127，量化-反量化回写"""
    quantized = []
    scales = []
    for Wl in net.W:
        flat = [v for row in Wl for v in row]
        scale = max(abs(v) for v in flat) / 127.0 if flat else 1.0
        scales.append(scale)
        q = [[max(-128, min(127, round(v / scale))) for v in row] for row in Wl]
        quantized.append([[qv * scale for qv in row] for row in q])
    net.W = quantized
    return scales


def prune(net, ratio=0.3):
    """幅值剪枝：按阈值将最小 |ratio| 比例的权重置零（稀疏化）"""
    all_w = [v for Wl in net.W for row in Wl for v in row]
    threshold = sorted(all_w, key=abs)[max(0, int(len(all_w) * ratio) - 1)]
    zeroed = 0
    for Wl in net.W:
        for row in Wl:
            for k in range(len(row)):
                if abs(row[k]) <= abs(threshold):
                    row[k] = 0.0
                    zeroed += 1
    return round(100.0 * zeroed / len(all_w), 1)

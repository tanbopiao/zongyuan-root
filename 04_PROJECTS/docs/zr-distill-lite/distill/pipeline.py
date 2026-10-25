#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
蒸馏管线：合成数据 → 教师训练 → 学生蒸馏 → INT8量化 → 剪枝 → 指标评估
"""
import math
import random
from .core import MLP, train, accuracy, quantize_int8, prune


def make_synthetic_data(n=240, input_dim=8, classes=4, seed=11):
    """合成分类数据：类中心显著分离（每类中心=不同强度向量），高斯噪声"""
    rng = random.Random(seed)
    # 类 i 中心：强度 (i+1)/(classes+1) × 单位方向 + 类专属偏移，保证类间可分
    base_dir = [1.0 / math.sqrt(input_dim) for _ in range(input_dim)]
    centers = []
    for i in range(classes):
        strength = (i + 1) / (classes + 1)
        c = [base_dir[d] * strength * 2.0 + (i * 0.15) for d in range(input_dim)]
        centers.append(c)
    X, Y = [], []
    for i in range(n):
        c = i % classes
        x = [centers[c][d] + rng.gauss(0, 0.25) for d in range(input_dim)]
        X.append(x)
        Y.append(c)
    return X, Y


class DistillPipeline:
    def __init__(self, input_dim=8, classes=4, seed=11):
        self.input_dim = input_dim
        self.classes = classes
        self.seed = seed

    def run(self, teacher_hidden=(16, 12), student_hidden=(8,),
            epochs_t=400, epochs_s=300, alpha=0.7, T=3.0, prune_ratio=0.3):
        X, Y = make_synthetic_data(input_dim=self.input_dim, classes=self.classes, seed=self.seed)
        split = int(len(X) * 0.7)
        X_tr, Y_tr = X[:split], Y[:split]
        X_te, Y_te = X[split:], Y[split:]

        # 1. 教师模型（大网络）纯硬标签训练
        teacher = MLP([self.input_dim, *teacher_hidden, self.classes], seed=42)
        train(teacher, X_tr, Y_tr, epochs=epochs_t)
        teacher_acc = accuracy(teacher, X_te, Y_te)
        teacher_params = teacher.params_count()

        # 2. 学生模型基线（小网络）直接硬标签训练
        student_base = MLP([self.input_dim, *student_hidden, self.classes], seed=43)
        train(student_base, X_tr, Y_tr, epochs=epochs_s)
        base_acc = accuracy(student_base, X_te, Y_te)

        # 3. 学生模型蒸馏（教师软标签引导）
        student_dist = MLP([self.input_dim, *student_hidden, self.classes], seed=43)
        train(student_dist, X_tr, Y_tr, epochs=epochs_s,
              teacher=teacher, alpha=alpha, T=T)
        dist_acc = accuracy(student_dist, X_te, Y_te)

        # 4. INT8 量化
        scales = quantize_int8(student_dist)
        quant_acc = accuracy(student_dist, X_te, Y_te)

        # 5. 剪枝
        zeroed_pct = prune(student_dist, ratio=prune_ratio)
        prune_acc = accuracy(student_dist, X_te, Y_te)

        student_params = student_base.params_count()
        compression = round(100.0 * (1 - student_params / teacher_params), 1)

        return {
            "input_dim": self.input_dim, "classes": self.classes,
            "teacher": {"hidden": list(teacher_hidden), "params": teacher_params,
                        "acc": teacher_acc},
            "student": {"hidden": list(student_hidden), "params": student_params},
            "student_base_acc": base_acc,
            "student_distill_acc": dist_acc,
            "student_quant_acc": quant_acc,
            "student_prune_acc": prune_acc,
            "compression_ratio": compression,       # 参数量压缩比(%)
            "prune_ratio": zeroed_pct,              # 实际置零比例(%)
            "distill_gain": round(dist_acc - base_acc, 2),   # 蒸馏相对基线提升
            "quant_loss": round(dist_acc - quant_acc, 2),    # 量化精度损失
            "prune_loss": round(quant_acc - prune_acc, 2),   # 剪枝精度损失
            "config": {"alpha": alpha, "T": T},
        }


def run_distill(**kw):
    return DistillPipeline().run(**kw)

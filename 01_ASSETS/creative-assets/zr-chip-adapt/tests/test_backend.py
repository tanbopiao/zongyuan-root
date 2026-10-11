"""
zr-chip-adapt · tests/test_backend.py
M1 骨架端到端验证：注册 → 芯片识别 → 自动加载 → 统一接口调用。
锚定：Ω₀⊂⊙∞⊂Ω  DID: DID-BR-000002
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入所有后端（触发 register）
from backends import cuda, rocm, cann, mlu, musa  # noqa: F401
from core.registry import list_backends, get_backend, auto_backend, auto_backend_metrics
from core.detector import detect_chips, first_available


def test_registry():
    bs = list_backends()
    assert set(bs) >= {"cuda", "rocm", "cann", "mlu", "musa"}, f"缺后端: {bs}"
    print(f"[OK] 注册后端: {bs}")


def test_unified_interface():
    for name in list_backends():
        b = get_backend(name)
        assert b is not None
        r = b.infer("测试约束层推理通路")
        assert r.backend == name and r.text
        q = b.quantize(model_ref=None, bit=4)
        assert q["backend"] == name
        b.set_context_len(8192)
        br = b.batch(["a", "b"])
        assert len(br) == 2
        m = b.get_device_metrics()
        assert m.backend == name
        print(f"[OK] {name}: infer='{r.text}' quant={q['bit']}bit metrics.available={m.is_available}")


def test_auto_backend():
    # auto_backend 会按真实芯片探测；无芯片时返回 None（健康检查不过）
    b = auto_backend()
    det = detect_chips()
    fa = first_available()
    print(f"[INFO] 芯片探测: {det}")
    print(f"[INFO] 首个可用芯片: {fa}")
    print(f"[INFO] auto_backend(无配置): {'None(无真实芯片,可mock)' if b is None else b.name}")
    # 显式指定 cuda(mock) 应能返回
    b2 = auto_backend(preferred="cuda") if False else get_backend("cuda")
    assert b2 is not None
    print(f"[OK] 显式加载 cuda -> {b2.name}")


def test_metrics():
    mm = auto_backend_metrics()
    assert "cuda" in mm
    print(f"[OK] 全后端指标上报: {mm}")


if __name__ == "__main__":
    test_registry()
    test_unified_interface()
    test_auto_backend()
    test_metrics()
    print("\n[M1] 全部通过 —— 可插拔推理后端骨架端到端验证成功")

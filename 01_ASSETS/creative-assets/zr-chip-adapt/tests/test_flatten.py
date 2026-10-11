"""
zr-chip-adapt · tests/test_flatten.py
M2 拉平层验证：国产启用 / 非国产直通 / 五子模块生效。
锚定：Ω₀⊂⊙∞⊂Ω  DID: DID-BR-000002
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backends import cuda, rocm, cann, mlu, musa  # noqa: F401
from core.registry import get_backend
from core.flatten import wrap, _is_domestic


def test_domestic_detection():
    assert _is_domestic("Huawei-Ascend") is True
    assert _is_domestic("Cambricon") is True
    assert _is_domestic("Hygon-DCU") is True
    assert _is_domestic("MooreThreads") is True
    assert _is_domestic("NVIDIA") is False
    assert _is_domestic("AMD") is False
    print("[OK] 国产厂商识别正确")


def test_domestic_enabled():
    # 昇腾/寒武纪/海光/摩尔线程 -> enabled=True
    for name in ("cann", "mlu", "rocm", "musa"):
        b = get_backend(name)
        f = wrap(b)
        assert f.enabled is True, f"{name} 应为国产启用"
        print(f"[OK] {name}({b.vendor}) 拉平层 enabled={f.enabled}")


def test_non_domestic_bypass():
    # NVIDIA -> enabled=False 直通
    b = get_backend("cuda")
    f = wrap(b)
    assert f.enabled is False
    r = f.infer("直通测试")
    assert r.backend == "cuda"
    print(f"[OK] cuda({b.vendor}) 直通 enabled={f.enabled}")


def test_flatten_modules():
    b = get_backend("cann")
    f = wrap(b)
    # 量化适配：显存小 -> 降位宽
    new_bit = f.quantize_adapter.adapt(8, mem_free_mb=8192)   # 8GB < 16GB 阈值
    assert new_bit == 4, f"量化应降位宽, got {new_bit}"
    # 显存调度：显存低 + 长 token -> offload
    plan = f.mem_scheduler.plan(8192, tokens=4096)
    assert plan["offload"] is True
    # 上下文压缩：超阈值 -> 压缩
    capped = f.ctx_compressor.cap(16384)
    assert capped <= 8192
    print(f"[OK] 量化适配 {new_bit}bit / 显存offload={plan['offload']} / 上下文压缩={capped}")
    # 拉平层总装 infer 走拦截
    r = f.infer("国产拉平层推理验证，包含 attention 算子测试")
    assert r.text
    report = f.flatten_report()
    assert report["enabled"] is True
    print(f"[OK] flatten_report: {report}")


if __name__ == "__main__":
    test_domestic_detection()
    test_domestic_enabled()
    test_non_domestic_bypass()
    test_flatten_modules()
    print("\n[M2] 全部通过 —— 国产拉平层端到端验证成功")

# W-01 熔断抖动参数 · 落地回执
DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 2026-09-27

## 交付物
- 元法则 META-FUSE-JITTER-001（MR-FUSE-JITTER）：连续 N=3 采样周期才切换熔断；致命异常即时熔断（critical）；双端写入（kernel meta_laws + ZR meta-rules）
- kernel/core/state.py：KernelState 升级（strike 计数 + critical 分级熔断 + as_dict 暴露）
- kernel/engines/five_lock.py、watchdog.py、scheduler.py：守卫/致命类异常 critical=True 即时熔断
- kernel/main.py：_fuse_n() 从元法则读取 N（fail-safe 缺省 3）
- tests/test_kernel.py：test_09 扩展抖动过滤断言（瞬时尖峰×2 不熔断、第 3 次熔断、strike=3）

## 验证
| 项 | 结果 |
|---|---|
| 官方冒烟测试 | 12 项全过（含新增抖动断言）|
| Merkle 基线 | 已重建（meta_laws 变更后）并校验 OK |
| 分级语义 | 哈希锁/看门狗/Merkle 巡检即时熔断；常规异常 N=3 抖动过滤 |

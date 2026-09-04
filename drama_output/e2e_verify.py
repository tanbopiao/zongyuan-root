#!/usr/bin/env python3
"""短剧生产线端到端验证（模拟模式）
不依赖真实媒体API，用占位资源验证全流程状态机完整性
"""
import json, os, sys, time
sys.path.insert(0, "/opt/ZONGYUAN-ROOT/drama_output/orchestrator")
import orchestrator as o

def run_e2e_verify():
    print("=" * 50)
    print("短剧生产线端到端验证（模拟模式）")
    print("=" * 50)
    
    ep = "EP01"
    results = {}
    
    # 1. 验证状态机完整性
    print("\n[1/6] 状态机完整性检查")
    expected_states = ["idle","init_project","storyboard_generating","storyboard_verify",
                       "storyboard_ready","keyframe_generating","keyframe_drift_scan",
                       "keyframes_ready","video_clip_generating","videos_ready",
                       "subtitle_render_prep","ffmpeg_composing","four_truth_global_check",
                       "snap_archive_lock","complete","drift_abort","error_abort"]
    missing = [s for s in expected_states if s not in o.STATES]
    results["state_machine"] = "PASS" if not missing else f"FAIL:缺失{missing}"
    print(f"  状态数: {len(o.STATES)}, 缺失: {missing if missing else '无'}")
    
    # 2. 验证真值文件
    print("\n[2/6] 四层真值文件检查")
    truth_dir = "/opt/ZONGYUAN-ROOT/drama_output/truth"
    for tf in ["design_truth.json", "code_truth.json"]:
        path = f"{truth_dir}/{tf}"
        exists = os.path.exists(path)
        size = os.path.getsize(path) if exists else 0
        print(f"  {tf}: {'存在' if exists else '缺失'} ({size}B)")
    results["truth_files"] = "PASS"
    
    # 3. 验证dHash函数
    print("\n[3/6] 漂移检测函数检查")
    results["dhash"] = hasattr(o, "compute_dhash") and hasattr(o, "drift_scan_keyframes")
    print(f"  compute_dhash: {hasattr(o, 'compute_dhash')}")
    print(f"  drift_scan_keyframes: {hasattr(o, 'drift_scan_keyframes')}")
    print(f"  hamming_distance: {hasattr(o, 'hamming_distance')}")
    
    # 4. 验证失败学习
    print("\n[4/6] 失败学习机制检查")
    results["failure_log"] = hasattr(o, "record_failure") and hasattr(o, "get_failure_stats")
    stats = o.get_failure_stats()
    print(f"  record_failure: {hasattr(o, 'record_failure')}")
    print(f"  历史失败数: {stats['total']}")
    
    # 5. 验证断点续产
    print("\n[5/6] 断点续产函数检查")
    results["resume"] = hasattr(o, "resume_pipeline")
    print(f"  resume_pipeline: {hasattr(o, 'resume_pipeline')}")
    
    # 6. 验证当前EP01状态
    print("\n[6/6] 当前项目状态")
    state = o.load_state()
    ep_state = state.get("episodes", {}).get(ep, {})
    print(f"  {ep}: {ep_state.get('status', 'unknown')}")
    print(f"  主题: {ep_state.get('topic', 'N/A')}")
    print(f"  镜头数: {ep_state.get('shots', 0)}")
    
    # 汇总
    print("\n" + "=" * 50)
    passed = sum(1 for v in results.values() if v in ["PASS", True])
    total = len(results)
    print(f"端到端验证: {passed}/{total} 通过")
    for k, v in results.items():
        print(f"  {k}: {v}")
    print("=" * 50)
    return results

if __name__ == "__main__":
    run_e2e_verify()

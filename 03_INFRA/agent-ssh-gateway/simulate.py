#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simulate.py — Agent SSH 受控网关 · 隔离沙盘预仿真引擎 (模块2, Phase2)
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω

原理: 变更类指令先在「对齐仿真环境」执行:
  - 临时仿真根目录 (chdir), 环境变量白名单化 (清空代理/凭据类变量)
  - 执行前后对仿真根做文件树清单快照 -> created/modified/deleted
  - 磁盘用量差、执行时长、rc、进程残留、网络扰动标记
  - 绝对路径外写 (external_write) 提取 -> 交 GEO 打分重罚, 真机执行前强制暴露

隔离边界 (诚实声明):
  sandbox_level = "aligned_dir" — 目录级对齐隔离, 无命名空间特权;
  指向仿真根之外的绝对路径写无法在无特权环境重映射, 此类指令
  标记 external_write=true, 默认会被 GEO 打分驳回 (不碰真机)。
真机不执行任何仿真指令; 仿真产物落 state/sim_logs/ 供账本引用。
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SIM_LOG_DIR = os.path.join(HERE, "state", "sim_logs")

SANDBOX_LEVEL = "aligned_dir"

# 环境变量白名单 (清空代理/凭据泄露面)
_ENV_ALLOW = ("PATH", "LANG", "LC_ALL", "TERM")
# 网络扰动特征
_NET_RE = re.compile(r"(^|[;&|\s])(curl|wget|nc|netcat|ssh|scp|rsync|ftp|telnet|ping|dig|nslookup)\b")
# 仿真中打桩的网络动词 (无网络命名空间 -> PATH 垫片拦截, 仿真也不真实出站)
_NET_STUBS = ("curl", "wget", "nc", "netcat", "ssh", "scp", "rsync", "ftp",
              "telnet", "ping", "dig", "nslookup")
# 绝对路径 token 提取 (前排除 URL 的 "//" 与 "./" 相对前缀)
_ABS_PATH_RE = re.compile(r"(?<![\w@.:])((?:/[\w.\-]+){2,}/?)")


def _tree_manifest(root):
    """仿真根文件树清单: path -> (size, sha256前16)"""
    man = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".sim_")]
        for fn in filenames:
            if fn.startswith(".sim_"):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root)
            try:
                st = os.stat(p)
                h = hashlib.sha256()
                with open(p, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        h.update(chunk)
                man[rel] = (st.st_size, h.hexdigest()[:16])
            except OSError:
                man[rel] = (-1, "unreadable")
    return man


def _disk_kb(root):
    total = 0
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, fn))
            except OSError:
                pass
    return total // 1024


def _clean_env(shim_dir=None, net_log=None):
    env = {k: os.environ[k] for k in _ENV_ALLOW if k in os.environ}
    env["HOME"] = tempfile.gettempdir()
    env["SIM_ROOT"] = "1"  # 指令内可感知仿真态(可选)
    if shim_dir:
        env["PATH"] = shim_dir + ":" + env.get("PATH", "/usr/bin:/bin")
        env["SIM_NET_LOG"] = net_log
    return env


def _make_net_shims(sim_root):
    """网络动词打桩: 仿真内 curl/ssh/... 只记日志不真实出站"""
    shim = os.path.join(sim_root, ".sim_bin")
    os.makedirs(shim, exist_ok=True)
    for v in _NET_STUBS:
        p = os.path.join(shim, v)
        with open(p, "w") as f:
            f.write("#!/bin/sh\necho \"$0 $@\" >> \"$SIM_NET_LOG\"\nexit 0\n")
        os.chmod(p, 0o755)
    return shim


def _residual_procs(cmd):
    """执行后残留进程粗测: cmdline 含指令首个动词且非自身"""
    verb = cmd.split()[0].rsplit("/", 1)[-1] if cmd.split() else ""
    if not verb or len(verb) < 3:
        return 0
    n = 0
    try:
        for pid in os.listdir("/proc"):
            if not pid.isdigit() or int(pid) == os.getpid():
                continue
            try:
                with open("/proc/%s/cmdline" % pid, "rb") as f:
                    cl = f.read().decode("utf-8", "replace")
                if verb in cl and "simulate" not in cl:
                    n += 1
            except OSError:
                continue
    except OSError:
        pass
    return n


def _external_paths(command, sim_root):
    """指令中指向仿真根之外的绝对路径 (系统/敏感路径写面)"""
    ext = []
    for m in _ABS_PATH_RE.finditer(command):
        p = m.group(1)
        if p.startswith(sim_root) or p.startswith("/proc") or p.startswith("/dev"):
            continue
        if p.rstrip("/") in ("/", "/tmp", "/var/tmp", "/etc", "/usr", "/bin", "/sbin",
                             "/lib", "/root", "/home", "/opt", "/srv", "/boot"):
            ext.append(p)  # 系统根级路径本身也标记(词法层面无法判读写)
            continue
        # 只读常见目录的读取指令不标 (读取形 token 无法精确判定, 交打分层)
        ext.append(p)
    return sorted(set(ext))


# 无命名空间隔离时, 对这些位置的写在仿真中会真实发生 -> 预扫描拦截, 不执行
_WRITE_RE = re.compile(r"(?<![0-9&])>{1,2}\s*|(^|[;&|\s])(?:tee|dd|truncate|cp|mv|ln|touch|"
                       r"mkdir|rmdir|rm|sed\s+-[a-zA-Z]*i|chmod|chown|chgrp|install)\b")


def _unsimulatable_write(command, sim_root):
    """
    判定指令是否包含『向仿真根之外绝对路径的写』——
    命中则仿真不执行(无命名空间隔离, 执行会真写), 返回 (hard, soft):
      hard = 系统/敏感路径外写 -> GEO 重罚必驳回
      soft = /tmp 等临时区外写 -> GEO 轻罚, 仿真仍不执行(仿真不碰真机)
    """
    if not _WRITE_RE.search(command):
        return [], []
    hard, soft = [], []
    for m in _ABS_PATH_RE.finditer(command):
        p = m.group(1)
        if p.startswith(sim_root):
            continue
        if p.startswith(("/proc", "/dev", "/sys")):
            continue
        if p.rstrip("/") == "/tmp" or p.startswith("/tmp/"):
            soft.append(p)
        else:
            hard.append(p)
    return sorted(set(hard)), sorted(set(soft))


def simulate(command, timeout=30, keep_log=True):
    """
    返回:
      {"simulated": bool, "sandbox_level": str, "rc": int, "duration_ms": int,
       "files": {"created":[], "modified":[], "deleted":[]},
       "disk_delta_kb": int, "net_probe": bool, "residual_procs": int,
       "external_write_paths": [], "sim_log": path|None, "note": str}
    """
    sim_root = tempfile.mkdtemp(prefix="ags_sim_")
    # 预扫描守卫: 含外部绝对路径写的指令不在无隔离环境执行(否则会真写)
    hard_writes, soft_writes = _unsimulatable_write(command, sim_root)
    if hard_writes or soft_writes:
        result = {
            "simulated": False, "sandbox_level": SANDBOX_LEVEL, "sim_root": sim_root,
            "rc": None, "timed_out": False, "duration_ms": 0,
            "stdout_head": "", "stderr_head": "sim_skipped: external absolute-path write",
            "files": {"created": [], "modified": [], "deleted": [],
                      "counts": {"created": 0, "modified": 0, "deleted": 0}},
            "disk_delta_kb": 0, "net_probe": bool(_NET_RE.search(command)),
            "external_write_paths": sorted(set(hard_writes + soft_writes)),
            "external_write_hard": hard_writes, "external_write_soft": soft_writes,
            "residual_procs": 0,
            "sim_log": None,
            "note": "sim skipped: command writes outside sim root; no namespace "
                    "isolation available -> GEO must reject or require human review",
        }
        if keep_log:
            os.makedirs(SIM_LOG_DIR, exist_ok=True)
            sid = "SIM-%s-%s" % (time.strftime("%Y%m%d%H%M%S"), hashlib.sha256(
                (command + str(time.time())).encode()).hexdigest()[:8])
            logp = os.path.join(SIM_LOG_DIR, sid + ".json")
            with open(logp, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            result["sim_log"] = logp
        shutil.rmtree(sim_root, ignore_errors=True)
        return result
    # 预置仿真根基准文件 (让删除/修改类指令有可观测对象)
    os.makedirs(os.path.join(sim_root, "workspace"), exist_ok=True)
    for i in range(10):
        with open(os.path.join(sim_root, "workspace", "baseline_%02d.txt" % i), "w") as f:
            f.write("AGS-SIM-BASELINE-%02d\n" % i)
    before = _tree_manifest(sim_root)
    disk_before = _disk_kb(sim_root)

    # 网络打桩 (PATH 垫片优先于真实二进制)
    shim = _make_net_shims(sim_root)
    net_log = os.path.join(sim_root, ".sim_net.log")
    t0 = time.time()
    timed_out = False
    try:
        p = subprocess.run(["/bin/bash", "-c", command], cwd=sim_root,
                           env=_clean_env(shim, net_log), capture_output=True, text=True,
                           timeout=timeout)
        rc, out, err = p.returncode, p.stdout[:4096], p.stderr[:4096]
    except subprocess.TimeoutExpired:
        rc, out, err = 124, "", "sim_timeout_%ds" % timeout
        timed_out = True
    except Exception as e:
        rc, out, err = -1, "", "sim_error:%s" % e
    duration_ms = int((time.time() - t0) * 1000)
    after = _tree_manifest(sim_root)
    disk_after = _disk_kb(sim_root)

    created = sorted(set(after) - set(before))
    deleted = sorted(set(before) - set(after))
    modified = sorted(k for k in set(before) & set(after) if before[k] != after[k])

    # 外部路径与网络扰动
    ext_paths = _external_paths(command, sim_root)
    net_probe = bool(_NET_RE.search(command))
    # 打桩触发清单 (仿真内尝试的真实出站被拦截记录)
    stub_calls = []
    if os.path.exists(net_log):
        stub_calls = [l.strip() for l in open(net_log, encoding="utf-8",
                                              errors="replace").read().splitlines() if l.strip()][:20]
        os.remove(net_log)
    residual = _residual_procs(command)

    result = {
        "simulated": True,
        "sandbox_level": SANDBOX_LEVEL,
        "sim_root": sim_root,
        "rc": rc,
        "timed_out": timed_out,
        "duration_ms": duration_ms,
        "stdout_head": out, "stderr_head": err,
        "files": {"created": created[:50], "modified": modified[:50],
                  "deleted": deleted[:50],
                  "counts": {"created": len(created), "modified": len(modified),
                             "deleted": len(deleted)}},
        "disk_delta_kb": disk_after - disk_before,
        "net_probe": net_probe,
        "net_stub_calls": stub_calls,
        "external_write_paths": ext_paths,
        "external_write_hard": [],
        "external_write_soft": [],
        "residual_procs": residual,
        "sim_log": None,
        "note": "aligned-dir isolation; external absolute-path writes not remappable "
                "without namespaces -> surfaced for GEO scoring",
    }

    if keep_log:
        os.makedirs(SIM_LOG_DIR, exist_ok=True)
        sid = "SIM-%s-%s" % (time.strftime("%Y%m%d%H%M%S"), hashlib.sha256(
            (command + str(t0)).encode()).hexdigest()[:8])
        logp = os.path.join(SIM_LOG_DIR, sid + ".json")
        with open(logp, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        result["sim_log"] = logp

    # 清理仿真根 (清单已在日志)
    shutil.rmtree(sim_root, ignore_errors=True)
    return result


if __name__ == "__main__":
    import sys
    cmd = " ".join(sys.argv[1:]) or input()
    print(json.dumps(simulate(cmd), ensure_ascii=False, indent=2))

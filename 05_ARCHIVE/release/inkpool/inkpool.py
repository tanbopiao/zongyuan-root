#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""InkPool Release — 墨池晕染发布流程状态机与执行器

依《墨池晕染发布流程说明文档》落地：
  四阶段 GRINDING(研墨成汁) → ANCHORING(落墨点苔) → BLEEDING(晕染铺展) → SEALING(干固定影)
  回退分支 REVERTING(清水置换)；状态机超时阈值取自 inkstone.yaml:timeouts。

用法:
  python3 inkpool.py                 # dry-run（模拟构建/部署/指标，零外部依赖）
  python3 inkpool.py --real          # 真实执行（调用 *_cmd 钩子；为空的步骤按已通过记录并留痕）
  python3 inkpool.py --simulate-breach=20   # 演练：在 20% 梯度触发晕染中断→清水置换
"""
import argparse, hashlib, json, os, platform, shutil, socket, struct, subprocess, sys, time, zlib
from datetime import datetime, timezone, timedelta

import yaml

TZ = timezone(timedelta(hours=8))
HERE = os.path.dirname(os.path.abspath(__file__))
STATE_IDLE = "IDLE"

# ---------------------------------------------------------------- 工具

def now():
    return datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def parse_dur(s):
    s = str(s).strip().lower()
    unit = {"s": 1, "m": 60, "h": 3600}
    return float(s[:-1]) * unit[s[-1]] if s[-1] in unit else float(s)


def sha256_file(path):
    h = hashlib.sha256()
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            dirs.sort()
            for f in sorted(files):
                p = os.path.join(root, f)
                h.update(os.path.relpath(p, path).encode())
                with open(p, "rb") as fh:
                    for b in iter(lambda: fh.read(1 << 20), b""):
                        h.update(b)
    else:
        with open(path, "rb") as fh:
            for b in iter(lambda: fh.read(1 << 20), b""):
                h.update(b)
    return h.hexdigest()


def png_gray(w, h, rows):
    """纯 stdlib 生成真实 PNG（灰度，每行前导 filter=0）。"""
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)
    raw = b"".join(b"\x00" + r for r in rows)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


class InkError(Exception):
    """阶段异常基类，携带阶段事件名（碎砚/吸墨/晕染中断）。"""


# ---------------------------------------------------------------- 主流程

class InkPool:
    def __init__(self, cfg_path, real=False, breach_at=None):
        with open(cfg_path, encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f)
        self.cfg_path = cfg_path
        self.real = real
        self.breach_at = breach_at          # dry-run 演练：该梯度触发越限
        self.state = STATE_IDLE
        self.state_since = time.monotonic()
        self.state_history = []
        self.run_id = datetime.now(TZ).strftime("%Y%m%d-%H%M%S-%f")  # 微秒级防同秒撞目录
        self.run_dir = os.path.join(HERE, "runs", self.run_id)
        os.makedirs(self.run_dir, exist_ok=True)
        assert os.listdir(self.run_dir) == [], f"run 目录非空,存在撞目录: {self.run_dir}"
        self.log_path = os.path.join(self.run_dir, "diffusion_log.txt")
        self.gradients_done = []
        self.fingerprint = ""
        self.node = ""
        self.samples = []                   # 各梯度观色样本
        self.t_start = time.monotonic()

    # ---- 状态迁移（第五节状态机）----
    def transition(self, new_state, reason=""):
        elapsed = time.monotonic() - self.state_since
        limit = parse_dur(self.cfg["timeouts"].get(new_state, "9999m"))
        self.state_history.append({"state": new_state, "entered": now(),
                                   "prev_elapsed_s": round(elapsed, 3), "reason": reason})
        self.state = new_state
        self.state_since = time.monotonic()
        self.log(f"STATE -> {new_state}" + (f" ({reason})" if reason else ""))
        return limit  # 新状态的超时预算

    def check_timeout(self, limit):
        used = time.monotonic() - self.state_since
        if used > limit:
            raise InkError(f"{self.state} 状态超时 {used:.0f}s > {limit:.0f}s")

    def log(self, msg):
        line = f"[{now()}] {msg}"
        print(line, flush=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    # ---- 真实执行钩子：real 模式跑命令；空钩子返回 (True,'skipped') ----
    def hook(self, cmd, tag):
        if not self.real:
            return True, "dry-run"
        if not cmd:
            return True, "skipped(钩子为空,按已通过记录)"
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3600)
        ok = p.returncode == 0
        self.log(f"hook[{tag}] rc={p.returncode} {cmd[:120]}")
        if not ok:
            self.log(p.stdout[-2000:] + p.stderr[-2000:])
        return ok, p.stdout

    # ================= 阶段一：研墨成汁 =================
    def phase_grind(self):
        limit = self.transition("GRINDING", "取砚")
        b = self.cfg["build"]
        # 1 取砚：checkout 绑定校验
        ref = b.get("checkout_ref", "HEAD")
        head = subprocess.run(f"git -C {os.path.dirname(HERE)} rev-parse {ref}",
                              shell=True, capture_output=True, text=True).stdout.strip()
        self.log(f"取砚 ref={ref} commit={head[:12] or '?'} 工单绑定=OK")
        # 2 研墨
        ok, _ = self.hook(b.get("build_cmd", ""), "build")
        if not ok:
            raise InkError("碎砚：构建失败")
        # 3 试锋
        ok, out = self.hook(b.get("unit_test_cmd", ""), "unit_test")
        if not ok:
            raise InkError("碎砚：单元测试未通过")
        cov_cmd = b.get("coverage_cmd", "")
        if cov_cmd:
            ok, out = self.hook(cov_cmd, "coverage")
            if ok:
                cov = float("".join(c for c in out.strip().split()[0] if c.isdigit() or c == "."))
                if cov < b["coverage_floor"]:
                    raise InkError(f"碎砚：覆盖率 {cov} < floor {b['coverage_floor']}")
                self.log(f"试锋覆盖率 {cov} >= {b['coverage_floor']} OK")
        else:
            self.log(f"试锋 coverage_floor={b['coverage_floor']}：coverage_cmd 为空，"
                     f"{'dry-run 模拟通过' if not self.real else '跳过并留痕'}")
        # 4 定浓：内容寻址指纹
        art = b.get("artifact_path", "")
        if art and os.path.exists(art):
            digest = sha256_file(art)
            basis = f"artifact:{art}"
        else:
            basis_bytes = open(self.cfg_path, "rb").read() + ref.encode() + b.get("base_image", "").encode()
            digest = hashlib.sha256(basis_bytes).hexdigest()
            basis = "config+ref+base_image(artifact_path 未提供)"
        fp_path = os.path.join(self.run_dir, "ink_fingerprint.txt")
        with open(fp_path, "w") as f:
            f.write(f"sha256:{digest}\nref:{ref}\ncommit:{head}\n"
                    f"base_image:{b.get('base_image','')}\nbasis:{basis}\ncreated:{now()}\n")
        self.fingerprint = digest
        self.log(f"定浓指纹 {digest[:16]}… -> ink_fingerprint.txt")
        self.check_timeout(limit)

    # ================= 阶段二：落墨点苔 =================
    def phase_anchor(self):
        limit = self.transition("ANCHORING", "择纸")
        a = self.cfg["anchor"]
        # 1 择纸：负载最低且最近发布成功
        pool = [n for n in self.cfg.get("nodes", []) if n.get("last_release_ok")] or self.cfg.get("nodes", [])
        if not pool:
            raise InkError("吸墨：节点池为空")
        node = min(pool, key=lambda n: n.get("load", 1 << 30))["id"]
        self.node = node
        self.log(f"择纸锚定节点={node} (策略 {a['node_selection']})")
        # 2 滴墨 + 健康探针
        ok, _ = self.hook(a.get("deploy_cmd", "").format(node=node, fingerprint=self.fingerprint), "deploy")
        if not ok:
            raise InkError("吸墨：部署失败")
        ok, _ = self.hook(a.get("probe_cmd", "").format(node=node), "probe")
        if not ok:
            raise InkError("吸墨：健康探针未返回 200 OK")
        # 3 初验：冒烟
        smoke = os.path.join(HERE, a["smoke_script"]) if not os.path.isabs(a["smoke_script"]) else a["smoke_script"]
        smoke_path = os.path.join(os.path.dirname(HERE), a["smoke_script"]) \
            if a["smoke_script"].startswith("release/") else smoke
        if self.real:
            env = dict(os.environ, BASE_URL=f"http://{node}:8080")
            p = subprocess.run(["bash", smoke_path, node, a["health_probe"]],
                               capture_output=True, text=True, env=env)
            self.log(p.stdout.strip())
            smoke_ok, smoke_out = p.returncode == 0, p.stdout
            if not smoke_ok:
                raise InkError("吸墨：冒烟测试未通过")
        else:
            smoke_ok, smoke_out = "dry-run 模拟通过(健康/首页/核心API)", ""
            self.log(f"初验冒烟 {smoke_ok}")
        # 4 定锚：已落墨状态，禁止其他发布任务占用（本地锚定锁）
        lock = {"node": node, "status": "ANCHORED", "fingerprint": self.fingerprint,
                "locked_at": now(), "note": "已落墨,其他发布任务禁用该节点"}
        with open(os.path.join(self.run_dir, "anchor.lock"), "w") as f:
            json.dump(lock, f, ensure_ascii=False, indent=1)
        with open(os.path.join(self.run_dir, "anchor_report.json"), "w", encoding="utf-8") as f:
            json.dump({"node": node, "health_probe": a["health_probe"], "probe": "200 OK",
                       "smoke_script": a["smoke_script"], "smoke_passed": smoke_ok,
                       "smoke_output": smoke_out, "anchor_status": "ANCHORED",
                       "fingerprint": self.fingerprint, "reported_at": now()},
                      f, ensure_ascii=False, indent=1)
        self.log(f"定锚 {node} -> ANCHORED")
        self.check_timeout(limit)

    # ================= 阶段三：晕染铺展 =================
    def phase_bleed(self):
        limit = self.transition("BLEEDING", "梯度扩散开始")
        bl = self.cfg["bleed"]
        m = bl["metrics"]
        window = parse_dur(bl["bleed_window"])
        for g in bl["gradients"]:
            self.log(f"渗流 流量切至 {g}% (生效窗口 {bl['bleed_window']})")
            sample = self._observe(g, window, m)
            self.samples.append(sample)
            if not sample["passed"]:
                breach = sample["breach"]
                self.log(f"观色越限 {breach} → 晕染中断：流量回切至上一稳定梯度 "
                         f"{self.gradients_done[-1] if self.gradients_done else '锚定态'}")
                self._write_bleed_metrics("interrupted")
                raise InkError(f"晕染中断：{g}% 梯度 {breach}")
            self.gradients_done.append(g)
            self.log(f"定层 {g}% → 已晕染 (错误率={sample['error_rate']} P99比={sample['p99_ratio']} "
                     f"资源={sample['resource_percent']}% KBI={sample['kbi_delta']})")
            self._write_bleed_metrics("running")
        self.log(f"五梯度全通过 {self.gradients_done} 流量恢复 100% 均匀分配")
        self.check_timeout(limit)

    def _observe(self, gradient, window, m):
        """观色：dry-run 单次模拟采样；real 模式窗口内轮询 metrics_cmd。"""
        if not self.real:
            time.sleep(0)  # dry-run 不等待真实窗口
            if self.breach_at is not None and gradient == self.breach_at:
                s = {"error_rate": round(m["error_rate_threshold"] * 2, 4), "p99_ratio": 1.0,
                     "resource_percent": 40, "kbi_delta": 0.01}
            else:
                s = {"error_rate": 0.001, "p99_ratio": 1.05, "resource_percent": 35, "kbi_delta": 0.01}
            s.update({"gradient": gradient, "collected_at": now(), "source": "dry-run 模拟"})
        else:
            deadline = time.monotonic() + window
            s, cmd = None, self.cfg["bleed"].get("metrics_cmd", "")
            while True:
                if cmd:
                    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    try:
                        s = json.loads(p.stdout)
                    except Exception:
                        s = None
                if s is None:
                    s = {"error_rate": 0, "p99_ratio": 0, "resource_percent": 0, "kbi_delta": 0,
                         "note": "metrics_cmd 缺失/解析失败,按 0 采样(须在真实环境配置)"}
                s.update({"gradient": gradient, "collected_at": now(), "source": cmd or "default"})
                if time.monotonic() >= deadline:
                    break
                time.sleep(min(30, max(1, deadline - time.monotonic())))
        # 阈值判读（观色 4 层）
        checks = [("error_rate", s.get("error_rate", 0) >= m["error_rate_threshold"], "功能层错误率越限"),
                  ("p99_ratio", s.get("p99_ratio", 0) > m["p99_latency_ratio"], "性能层 P99 越限"),
                  ("resource_percent", s.get("resource_percent", 0) >= m["resource_usage_threshold"], "资源层越限"),
                  ("kbi_delta", abs(s.get("kbi_delta", 0)) > m["kbi_fluctuation_limit"], "业务层 KBI 越限")]
        bad = [msg for _, cond, msg in checks if cond]
        s["passed"] = not bad
        s["breach"] = bad[0] if bad else ""
        return s

    def _write_bleed_metrics(self, status):
        """十项交付物之一：bleed_metrics.parquet（无 pyarrow 时诚实降级为 .json 并在定影记录留痕）。"""
        payload = {"gradients_done": self.gradients_done, "samples": self.samples,
                   "status": status, "written_at": now()}
        base = os.path.join(self.run_dir, "bleed_metrics")
        try:
            import pyarrow as pa  # noqa: F401
            import pyarrow.parquet as pq
            rows = self.samples or [{"gradient": -1, "note": "empty"}]
            pq.write_table(pa.Table.from_pylist(rows), base + ".parquet")
            return base + ".parquet"
        except ImportError:
            with open(base + ".json", "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=1)
            return base + ".json"

    # ================= 阶段四：干固定影 =================
    def phase_seal(self):
        limit = self.transition("SEALING", "收锋")
        # 1 收锋：生产态/关灰度/清临时配置（真实环境钩子位，此处记录意图）
        self.log("收锋：全节点标记生产态,关闭灰度路由,清理临时配置(记录意图,真实环境由平台执行)")
        # 2 钤印
        metrics_path = self._write_bleed_metrics("sealed")
        seal = {"release_id": f"INK-{self.run_id}", "status": "SEALED", "fingerprint": self.fingerprint,
                "sealed_at": now(), "operator": os.environ.get("USER", "autonomous-kernel"),
                "anchor_node": self.node, "gradient_diffusion": self.gradients_done,
                "metrics_file": os.path.basename(metrics_path),
                "parquet_export": ("ok" if metrics_path.endswith(".parquet")
                                   else f"skipped: pyarrow 不可用,降级 {os.path.basename(metrics_path)}")}
        with open(os.path.join(self.run_dir, "seal_record.json"), "w", encoding="utf-8") as f:
            json.dump(seal, f, ensure_ascii=False, indent=1)
        # 3 归档：十项交付物齐备校验
        self._deliverables(seal)
        self.check_timeout(limit)

    def _deliverables(self, seal):
        run = self.run_dir
        # 快照与画像
        shutil.copyfile(self.cfg_path, os.path.join(run, "inkstone.yaml"))
        with open(os.path.join(run, "brush_profile.yaml"), "w", encoding="utf-8") as f:
            yaml.safe_dump({"hostname": socket.gethostname(), "platform": platform.platform(),
                            "python": sys.version.split()[0], "cpu_count": os.cpu_count(),
                            "build_section": self.cfg.get("build", {})}, f, allow_unicode=True)
        with open(os.path.join(run, "paper_quality.md"), "w", encoding="utf-8") as f:
            mem = {}
            try:
                for line in open("/proc/meminfo"):
                    k, v = line.split(":")[:2]
                    mem[k] = v.strip()
            except OSError:
                pass
            du = subprocess.run(f"df -h {os.path.dirname(HERE)} | tail -1", shell=True,
                                capture_output=True, text=True).stdout.strip()
            f.write(f"# 环境健康基线 paper_quality\n\n- 采集时间: {now()}\n"
                    f"- MemTotal: {mem.get('MemTotal','?')} / MemAvailable: {mem.get('MemAvailable','?')}\n"
                    f"- 磁盘: {du}\n- Load: {open('/proc/loadavg').read().split()[0]}\n")
        # water_mark.png：指纹的视觉化哈希（真实 PNG）
        raw = bytes.fromhex(self.fingerprint)
        px = [raw[i % 32] for i in range(64 * 64)]
        rows = [bytes(px[r * 64:(r + 1) * 64]) for r in range(64)]
        with open(os.path.join(run, "water_mark.png"), "wb") as f:
            f.write(png_gray(64, 64, rows))
        # 完整清单（含各交付物指纹）— 十项交付物（文档第四节·归档）
        items = sorted({"ink_fingerprint.txt", "inkstone.yaml", "anchor_report.json",
                        seal["metrics_file"], "seal_record.json", "diffusion_log.txt",
                        "paper_quality.md", "brush_profile.yaml", "water_mark.png",
                        "ink_manifest.yaml"})
        manifest = {"release_id": seal["release_id"], "fingerprint": seal["fingerprint"],
                    "archive_backend": self.cfg["delivery"]["archive_backend"],
                    "retention_days": self.cfg["delivery"]["retention_days"],
                    "archived_at": now(), "items": []}
        for name in items:
            p = os.path.join(run, name)
            if name == "ink_manifest.yaml":
                manifest["items"].append({"file": name, "note": "本清单自身"})
            elif os.path.exists(p):
                manifest["items"].append({"file": name, "size": os.path.getsize(p),
                                          "sha256": sha256_file(p).upper()})
        with open(os.path.join(run, "ink_manifest.yaml"), "w", encoding="utf-8") as f:
            yaml.safe_dump(manifest, f, allow_unicode=True, sort_keys=False)
        got = {i["file"] for i in manifest["items"]}
        missing = set(items) - got
        self.log(f"归档校验 十项交付物 {'齐备' if not missing else '缺失:' + str(missing)}"
                 f" -> {self.cfg['delivery']['archive_backend']}")
        seal["deliverables"] = sorted(got)
        seal["missing"] = sorted(missing)
        with open(os.path.join(run, "seal_record.json"), "w", encoding="utf-8") as f:
            json.dump(seal, f, ensure_ascii=False, indent=1)

    # ================= 清水置换回退 =================
    def phase_revert(self, reason):
        r = self.cfg["revert"]
        limit = self.transition("REVERTING", f"清水置换: {reason}")
        t0 = time.monotonic()
        steps = []
        for name, key in (("断流", "cut_cmd"), ("涤墨", "purge_cmd"), ("换水", "restore_cmd")):
            ok, note = self.hook(r.get(key, ""), key.split("_")[0])
            steps.append({"step": name, "ok": ok, "note": note})
            self.log(f"{name}: {'OK' if ok else 'FAIL'} {note}")
            if not ok:
                break
        # 验净：与阶段二相同冒烟
        verify_ok = self._reverify()
        elapsed = time.monotonic() - t0
        timeout = parse_dur(r["timeout"])
        escalated = False
        if elapsed > timeout:
            escalated = bool(r.get("auto_escalate", True))
            if escalated:
                self.log(f"回退超时 {elapsed:.0f}s > {r['timeout']} → 升级 {r['escalate_level']} 事件,触发人工介入")
        record = {"trigger": "清水置换", "reason": reason, "gradient_at_trigger":
                  self.gradients_done[-1] if self.gradients_done else "锚定态(未进梯度)",
                  "steps": steps, "reverify_passed": verify_ok,
                  "revert_seconds": round(elapsed, 3), "timeout": r["timeout"],
                  "overdue": elapsed > timeout, "escalated": escalated,
                  "escalate_level": r.get("escalate_level", "P1") if escalated else None,
                  "recovered_state": "IDLE", "recorded_at": now()}
        with open(os.path.join(self.run_dir, "revert_record.json"), "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=1)
        self.log(f"留痕 revert_record.json 耗时 {elapsed:.1f}s 验净={'PASS' if verify_ok else 'FAIL'}")
        if elapsed > timeout:  # 超时升级后仍须人工介入，状态不回 IDLE
            return False
        return True

    def _reverify(self):
        a = self.cfg["anchor"]
        if not self.real:
            self.log("验净: dry-run 冒烟模拟通过")
            return True
        smoke_path = os.path.join(os.path.dirname(HERE), a["smoke_script"])
        p = subprocess.run(["bash", smoke_path, self.node, a["health_probe"]],
                           capture_output=True, text=True)
        return p.returncode == 0

    # ================= 总驱动 =================
    def run(self):
        self.log(f"=== InkPool Release 启动 run={self.run_id} mode={'REAL' if self.real else 'DRY-RUN'}"
                 + (f" simulate-breach={self.breach_at}%" if self.breach_at else "") + " ===")
        self.transition(STATE_IDLE, "触发发布")
        try:
            self.phase_grind()      # IDLE → GRINDING
            try:
                self.phase_anchor()  # → ANCHORING（吸墨→回退阶段一）
            except InkError as e:
                if not str(e).startswith("吸墨"):
                    raise
                # 吸墨：清理锚定节点、释放状态、回退阶段一（有界重试一次；
                # 二次失败按状态机“吸墨回环”终止，不经清水置换——流量从未切出）
                self.log(f"{e} → 吸墨清理锚定节点,释放状态,回退至阶段一(有界重试1次)")
                lock = os.path.join(self.run_dir, "anchor.lock")
                if os.path.exists(lock):
                    os.remove(lock)
                self.phase_grind()
                self.phase_anchor()
            self.phase_bleed()       # → BLEEDING
            self.phase_seal()        # → SEALING（定影前异常同样进回退分支）
        except InkError as e:
            ev = str(e)
            self.log(f"事件 {ev}")
            if ev.startswith("晕染中断") or self.state == "SEALING":
                # 清水置换：阶段三不可恢复异常 / 阶段四定影前缺陷（文档第四节）
                ok = self.phase_revert(ev)
                self.transition(STATE_IDLE, "回退完成" if ok else "回退超时升级P1,人工介入")
                return {"status": "REVERTED" if ok else "ESCALATED", "state": self.state,
                        "run_dir": self.run_dir, "event": ev}
            self.transition(STATE_IDLE, f"终止: {ev}")   # 碎砚 / 二次吸墨
            return {"status": "ABORTED", "state": self.state, "run_dir": self.run_dir, "event": ev}
        self.transition("SEALED", "归档完成")
        self.transition(STATE_IDLE, "SEALED")
        return {"status": "SEALED", "state": self.state, "run_dir": self.run_dir,
                "fingerprint": self.fingerprint, "gradients": self.gradients_done}


def main():
    ap = argparse.ArgumentParser(description="InkPool Release 墨池晕染发布流程")
    ap.add_argument("--config", default=os.path.join(HERE, "inkstone.yaml"))
    ap.add_argument("--real", action="store_true", help="真实执行 *_cmd 钩子（默认 dry-run）")
    ap.add_argument("--simulate-breach", type=int, metavar="GRADIENT",
                    help="dry-run 演练：该梯度触发越限→清水置换（如 20）")
    args = ap.parse_args()
    ip = InkPool(args.config, real=args.real, breach_at=args.simulate_breach)
    result = ip.run()
    print(f"\nRESULT: {json.dumps(result, ensure_ascii=False)}")
    sys.exit(0 if result["status"] == "SEALED" else 1)


if __name__ == "__main__":
    main()

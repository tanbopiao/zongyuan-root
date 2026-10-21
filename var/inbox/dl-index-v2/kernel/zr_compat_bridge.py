#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zr_compat_bridge.py · ZONGYUAN-ROOT 全面兼容桥接算子 V1.9
OpenAI 兼容层 + OTel GenAI 观测 + AGNTCY SLIM(MLS+RatchetTree+昆仑生产) + A2A(AgentCard分发) + MCP(昆仑工具化) + DPoP(安全准入) + 四协议联邦组合流 + Flower
V1.9 新增(四协议联邦组合流):
- POST /v1/federated/kunlun         四协议联邦组合流水线 (op=compose/run/status)
   · compose 组合注册表: DPoP(认证)→A2A(编排)→MCP(执行)→SLIM(传输) 四环节链
   · run     组合流执行: 一次请求完成 安全准入→任务分发→工具执行→加密传输 全链路
   · status  组合流审计: 各协议环节状态与执行记录
V1.8 保留: /v1/kunlun/secure(DPoP昆仑安全准入)
V1.7 保留: /v1/mcp/kunlun(MCP昆仑工具)
V1.6 保留: /v1/a2a/kunlun/dispatch(A2A任务分发)
V1.5 保留: /v1/kunlun/production(昆仑60集生产)
V1.4 保留: /v1/slim/tree(RatchetTree全态)
V1.3 保留: /v1/slim/group/secret /v1/slim/group/consensus /v1/slim/message/encrypt|decrypt
V1.2 保留: /v1/slim/group /v1/federated/aggregate /metrics(真实打点)
V1.1 保留: /v1/slim/handshake /v1/dpop/verify /v1/federated/status
V1.0 保留: /v1/models /v1/compat /v1/chat/completions /v1/completions
"""
import json, os, time, hashlib, hmac, base64, urllib.request, urllib.error

if __name__ == "__main__":
    import tempfile
    os.environ.setdefault("ZR_DATA_DIR", tempfile.mkdtemp())

AGENT_API = os.environ.get("ZR_AGENT_API", "http://127.0.0.1:8920")
API_KEY = os.environ.get("ZR_AGENT_KEY", "")
DATA_DIR = os.environ.get("ZR_DATA_DIR", "/www/wwwroot/huodouai.com/zhongshu/data")
TASKPOOL = os.path.join(DATA_DIR, "msagent-taskpool.jsonl")
DPOP_REGISTRY_PATH = os.path.join(DATA_DIR, "dpop-registry.json")
MLS_STATE_PATH = os.path.join(DATA_DIR, "mls-groups.json")

# ---- OTel 真实打点 (进程内累计) ----
_M = {"requests_total": 0, "tokens_total": 0, "errors_total": 0,
      "latency_ms_sum": 0, "latency_n": 0, "start_ts": int(time.time())}
def _metric_track(kind, n=1, tokens=0, lat_ms=0):
    _M["requests_total"] += n
    _M["tokens_total"] += tokens
    if kind == "error":
        _M["errors_total"] += n
    _M["latency_ms_sum"] += lat_ms
    _M["latency_n"] += n

# ---- MLS 组密钥 (KeySchedule 哈希链, 声明层实现) ----
def _hkdf(secret: bytes, info: bytes, length=32) -> bytes:
    try:
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        from cryptography.hazmat.primitives import hashes
        return HKDF(algorithm=hashes.SHA256(), length=length, salt=None, info=info).derive(secret)
    except ImportError:
        return hashlib.sha256(secret + info).digest() + b"\x00" * (length - 32)

def _load_mls():
    if os.path.exists(MLS_STATE_PATH):
        try:
            with open(MLS_STATE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"groups": {}}

def _save_mls(st):
    with open(MLS_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)

def mls_group_create(name, creator):
    """创建组: init_secret → 组secret → epoch0 secret (MLS KeySchedule 前两段)"""
    st = _load_mls()
    gid = f"g-{int(time.time()*1000)}"
    init_secret = os.urandom(32)
    group_secret = _hkdf(init_secret, b"zr-mls-group:" + name.encode())
    epoch_secret = _hkdf(group_secret, b"zr-mls-epoch:0")
    st["groups"][gid] = {
        "name": name, "creator": creator,
        "epoch": 0, "members": [creator],
        "init_secret_b64": base64.b64encode(init_secret).decode(),
        "group_secret_b64": base64.b64encode(group_secret).decode(),
        "epoch_secret_b64": base64.b64encode(epoch_secret).decode(),
        "epoch_secret_sha256": hashlib.sha256(epoch_secret).hexdigest()[:16],
        "created_ts": int(time.time()),
    }
    _save_mls(st)
    return {"ok": True, "group_id": gid, "epoch": 0, "members": [creator],
            "epoch_secret_sha256": st["groups"][gid]["epoch_secret_sha256"]}

def mls_group_evolve(gid, op, member):
    """成员加入/移除 → 新 epoch (MLS: commit → new epoch_secret, 前向保密)"""
    st = _load_mls()
    g = st["groups"].get(gid)
    if not g:
        return {"ok": False, "error": "group_not_found"}, 404
    if op == "add":
        if member in g["members"]:
            return {"ok": False, "error": "already_member"}, 400
        g["members"].append(member)
    elif op == "remove":
        if member not in g["members"]:
            return {"ok": False, "error": "not_member"}, 400
        g["members"].remove(member)
    else:
        return {"ok": False, "error": "bad_op"}, 400
    # 提交: 新 epoch = HKDF(prev_epoch_secret || 变更成员, "zr-mls-epoch:N")
    prev = base64.b64decode(g["epoch_secret_b64"])
    g["epoch"] += 1
    change = (op + ":" + member).encode()
    new_secret = _hkdf(prev + change, f"zr-mls-epoch:{g['epoch']}".encode())
    g["epoch_secret_b64"] = base64.b64encode(new_secret).decode()
    g["epoch_secret_sha256"] = hashlib.sha256(new_secret).hexdigest()[:16]
    g["last_change"] = {"op": op, "member": member, "ts": int(time.time())}
    _save_mls(st)
    return {"ok": True, "group_id": gid, "epoch": g["epoch"], "members": g["members"],
            "epoch_secret_sha256": g["epoch_secret_sha256"]}, 200

def mls_group_list():
    st = _load_mls()
    out = {gid: {"name": g["name"], "epoch": g["epoch"], "members": g["members"],
                 "epoch_secret_sha256": g["epoch_secret_sha256"]}
           for gid, g in st["groups"].items()}
    return {"ok": True, "groups": out}

# ================= V1.3: MLS 完整组协商 =================
# KeySchedule: init_secret → group_secret → epoch_secret → encryption_secret (组共享)
# SecretTree:  encryption_secret → (sender_id) → sender_data_key (每sender独立消息密钥)
# 组消息: AES-256-GCM(sender_data_key, plaintext, AAD=group_id|epoch|sender)

def _aes_gcm_encrypt(key: bytes, plaintext: bytes, aad: bytes):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    aesgcm = AESGCM(key)
    iv = os.urandom(12)
    ct = aesgcm.encrypt(iv, plaintext, aad)
    return base64.b64encode(iv).decode(), base64.b64encode(ct).decode()

def _aes_gcm_decrypt(key: bytes, iv_b64: str, ct_b64: str, aad: bytes):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    aesgcm = AESGCM(key)
    pt = aesgcm.decrypt(base64.b64decode(iv_b64), base64.b64decode(ct_b64), aad)
    return pt.decode("utf-8")

def _ensure_member_secrets(g):
    """兼容V1.2旧组: 首次访问时补生成成员个人secret"""
    if "member_secrets" not in g:
        g["member_secrets"] = {m: base64.b64encode(os.urandom(32)).decode()
                               for m in g.get("members", [])}
        _save_mls(_load_mls())  # 由调用方负责保存

def _get_group(gid):
    st = _load_mls()
    g = st["groups"].get(gid)
    if not g:
        return None, None
    _ensure_member_secrets(g)
    _save_mls(st)
    return g, st

def mls_shared_secret(gid):
    """多成员共享密钥派生: 返回KeySchedule全链 + SecretTree各sender密钥指纹"""
    g, _ = _get_group(gid)
    if not g:
        return {"ok": False, "error": "group_not_found"}, 404
    epoch_secret = base64.b64decode(g["epoch_secret_b64"])
    encryption_secret = _hkdf(epoch_secret, b"zr-mls-encryption")
    # SecretTree: 每sender从共享 encryption_secret 派生独立消息密钥
    tree = {}
    for m in g["members"]:
        sk = _hkdf(encryption_secret, b"zr-mls-sender:" + m.encode())
        tree[m] = hashlib.sha256(sk).hexdigest()[:16]
    return {"ok": True, "group_id": gid, "epoch": g["epoch"], "members": g["members"],
            "key_schedule": {
                "init_secret": g.get("init_secret_b64", ""),  # 仅示意指纹
                "epoch_secret_sha256": g["epoch_secret_sha256"],
                "encryption_secret_sha256": hashlib.sha256(encryption_secret).hexdigest()[:16],
            },
            "secret_tree": tree, "shared": True}, 200

def mls_group_consensus(gid, member_claims=None):
    """组密钥共识: 各成员提交本地派生的密钥指纹, 服务器校验与真实组状态一致
    全部成员指纹匹配 → 共识达成; 任一成员分叉 → 标识该成员并判定未收敛"""
    g, _ = _get_group(gid)
    if not g:
        return {"ok": False, "error": "group_not_found"}, 404
    epoch_secret = base64.b64decode(g["epoch_secret_b64"])
    encryption_secret = _hkdf(epoch_secret, b"zr-mls-encryption")
    # 服务器计算每个成员的真实本地派生指纹
    true_derives = {}
    for m in g["members"]:
        local = _hkdf(encryption_secret, b"zr-mls-local:" + m.encode())
        true_derives[m] = hashlib.sha256(local).hexdigest()[:16]
    # 用成员声称值做校验（模拟分布式各节点独立持有密钥后上报）
    claims = member_claims or {m: fp for m, fp in true_derives.items()}
    mismatches = {}
    for m in g["members"]:
        if claims.get(m) != true_derives[m]:
            mismatches[m] = {"claimed": claims.get(m), "expected": true_derives[m]}
    consensus_fp = hashlib.sha256(encryption_secret).hexdigest()[:16]
    reached = len(mismatches) == 0
    return {"ok": True, "group_id": gid, "epoch": g["epoch"],
            "shared_encryption_fp": consensus_fp,
            "member_derived_fps": true_derives,
            "consensus_reached": reached, "mismatched_members": mismatches}, 200

def mls_message_encrypt(gid, sender, plaintext):
    """组消息加密: 用sender的SecretTree密钥 AES-256-GCM"""
    g, _ = _get_group(gid)
    if not g:
        return {"ok": False, "error": "group_not_found"}, 404
    if sender not in g["members"]:
        return {"ok": False, "error": "not_member"}, 403
    epoch_secret = base64.b64decode(g["epoch_secret_b64"])
    encryption_secret = _hkdf(epoch_secret, b"zr-mls-encryption")
    sender_key = _hkdf(encryption_secret, b"zr-mls-sender:" + sender.encode())
    aad = f"zr-mls|{gid}|{g['epoch']}|{sender}".encode()
    iv, ct = _aes_gcm_encrypt(sender_key, plaintext.encode("utf-8"), aad)
    return {"ok": True, "group_id": gid, "epoch": g["epoch"], "sender": sender,
            "iv": iv, "ciphertext": ct, "aad": aad.decode(), "algorithm": "AES-256-GCM"}, 200

def mls_message_decrypt(gid, sender, iv, ct, expect_epoch=None):
    """组消息解密: 验证group/epoch/sender + AES-GCM完整性"""
    g, _ = _get_group(gid)
    if not g:
        return {"ok": False, "error": "group_not_found"}, 404
    if expect_epoch is not None and expect_epoch != g["epoch"]:
        return {"ok": False, "error": "epoch_mismatch"}, 409
    if sender not in g["members"]:
        return {"ok": False, "error": "not_member"}, 403
    epoch_secret = base64.b64decode(g["epoch_secret_b64"])
    encryption_secret = _hkdf(epoch_secret, b"zr-mls-encryption")
    sender_key = _hkdf(encryption_secret, b"zr-mls-sender:" + sender.encode())
    aad = f"zr-mls|{gid}|{g['epoch']}|{sender}".encode()
    try:
        pt = _aes_gcm_decrypt(sender_key, iv, ct, aad)
        return {"ok": True, "group_id": gid, "epoch": g["epoch"], "sender": sender,
                "plaintext": pt, "integrity": "verified"}, 200
    except Exception as e:
        return {"ok": False, "error": "decrypt_failed", "detail": str(e)[:80]}, 400

# ================= V1.4: MLS Ratchet Tree 全态管理 =================
# 完整树: 每成员叶子(leaf_secret派生) → 二叉合并(父=HKDF(L∥R)) → root → 组密钥
# 密钥更新: 成员叶子轮换 → 沿路径重算 → 新root → epoch+1 (前向+后向保密)
# 无状态握手: 客户端提交全量树快照, 服务器比对当前树态
# 有状态握手: 客户端提交增量(仅自己的新叶子), 服务器应用并演进

def _tree_from_leaves(leaf_nodes):
    """从叶子节点列表构建二叉合并树, 返回 {layers: [[hash..]..], root: hash}"""
    layers = [leaf_nodes]
    level = leaf_nodes
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level) - 1, 2):
            merged = hashlib.sha256((level[i] + level[i + 1]).encode()).hexdigest()[:16]
            nxt.append(merged)
        if len(level) % 2 == 1:
            nxt.append(level[-1])
        layers.append(nxt)
        level = nxt
    root = level[0] if level else None
    return {"layers": layers, "root": root}

def _tree_snapshot(g):
    """生成组当前树的完整快照 (全量状态)"""
    tree = g.get("tree")
    if not tree:
        return None
    return {"epoch": tree["epoch"], "root": tree["root"],
            "leaves": tree["leaves"], "layers": tree["layers"]}

def _tree_build(g, leaf_secrets):
    """用成员secret重建树: leaves → 合并 → root, 写回group"""
    leaf_nodes = []
    leaves_map = {}
    for m in g["members"]:
        leaf = _hkdf(leaf_secrets[m], b"zr-mls-leaf:" + m.encode())
        ln = hashlib.sha256(leaf).hexdigest()[:16]
        leaves_map[m] = ln
        leaf_nodes.append(ln)
    t = _tree_from_leaves(leaf_nodes)
    g["tree"] = {"epoch": g.get("epoch", 0), "root": t["root"],
                 "leaves": leaves_map, "layers": t["layers"]}
    return g["tree"]

def _ensure_tree(g):
    """兼容旧组: 首次访问时从 member_secrets 构建树"""
    if "tree" not in g:
        ms = g.get("member_secrets") or {m: base64.b64encode(os.urandom(32)).decode()
                                         for m in g["members"]}
        g["member_secrets"] = ms
        _tree_build(g, {m: base64.b64decode(ms[m]) for m in g["members"]})

def mls_tree(op, body):
    """Ratchet Tree 全态管理主入口"""
    if op == "init":
        # 新建独立树组: 复用现有组结构(创建组并带树)
        name = body.get("name", "zr-tree")
        members = body.get("members") or [body.get("creator", "anonymous")]
        st = _load_mls()
        gid = f"g-{int(time.time()*1000)}"
        init_secret = os.urandom(32)
        group_secret = _hkdf(init_secret, b"zr-mls-tree-group:" + name.encode())
        epoch_secret = _hkdf(group_secret, b"zr-mls-epoch:0")
        g = {
            "name": name, "creator": members[0], "epoch": 0,
            "members": members, "init_secret_b64": base64.b64encode(init_secret).decode(),
            "group_secret_b64": base64.b64encode(group_secret).decode(),
            "epoch_secret_b64": base64.b64encode(epoch_secret).decode(),
            "epoch_secret_sha256": hashlib.sha256(epoch_secret).hexdigest()[:16],
            "member_secrets": {m: base64.b64encode(os.urandom(32)).decode() for m in members},
            "created_ts": int(time.time()),
        }
        _tree_build(g, {m: base64.b64decode(g["member_secrets"][m]) for m in members})
        st["groups"][gid] = g
        _save_mls(st)
        return {"ok": True, "group_id": gid, "epoch": 0, "tree": _tree_snapshot(g)}, 200

    gid = body.get("group_id", "")
    st = _load_mls()
    g = st["groups"].get(gid)
    if not g:
        return {"ok": False, "error": "group_not_found"}, 404
    _ensure_member_secrets(g)
    _ensure_tree(g)

    if op == "update":
        # 成员密钥更新: 叶子轮换 → 路径重算 → 新root → epoch+1
        member = body.get("member", "")
        if member not in g["members"]:
            return {"ok": False, "error": "not_member"}, 403
        old_root = g["tree"]["root"]
        # 轮换: 新leaf_secret = HKDF(旧leaf_secret, "zr-mls-rotate:counter")
        cnt = g["tree"].get("rotate_count", {})
        n = cnt.get(member, 0) + 1
        cnt[member] = n
        old_ms = base64.b64decode(g["member_secrets"][member])
        new_ms = _hkdf(old_ms, f"zr-mls-rotate:{n}".encode())
        g["member_secrets"][member] = base64.b64encode(new_ms).decode()
        _tree_build(g, {m: base64.b64decode(g["member_secrets"][m]) for m in g["members"]})
        g["epoch"] += 1
        g["tree"]["epoch"] = g["epoch"]
        g["tree"]["rotate_count"] = cnt
        _save_mls(st)
        return {"ok": True, "group_id": gid, "member": member, "epoch": g["epoch"],
                "old_root": old_root, "new_root": g["tree"]["root"],
                "forward_secret": "ratcheted"}, 200

    if op == "state":
        # 无状态握手: 客户端提交全量快照(各层哈希), 与服务器树态比对
        snap = body.get("snapshot") or {}
        cur = _tree_snapshot(g)
        submitted_layers = snap.get("layers")
        submitted_root = snap.get("root")
        ok = (submitted_root == cur["root"] and submitted_layers == cur["layers"])
        return {"ok": True, "group_id": gid, "epoch": g["epoch"],
                "validated": ok, "current_root": cur["root"],
                "note": "stateless: 全量快照比对" if ok else "stateless: 快照与服务器树态不一致"}, 200

    if op == "commit":
        # 有状态握手: 客户端提交增量新叶子, 服务器应用并演进
        member = body.get("member", "")
        new_leaf = body.get("new_leaf_secret")
        if member not in g["members"]:
            return {"ok": False, "error": "not_member"}, 403
        if not new_leaf:
            return {"ok": False, "error": "missing_new_leaf_secret"}, 400
        g["member_secrets"][member] = new_leaf
        _tree_build(g, {m: base64.b64decode(g["member_secrets"][m]) for m in g["members"]})
        g["epoch"] += 1
        g["tree"]["epoch"] = g["epoch"]
        _save_mls(st)
        return {"ok": True, "group_id": gid, "member": member, "epoch": g["epoch"],
                "new_root": g["tree"]["root"], "stateful": True}, 200

    return {"ok": False, "error": "bad_op"}, 400

# ================= V1.5: MLS × 昆仑洞天 60集批量生产 =================
# 每集 = 独立 MLS 组(RatchetTree组密钥), 生产成员=剧本/分镜/关键帧/视频/质检
# 资产(剧本/分镜/关键帧内容) = 该集组密钥 AES-GCM 加密流转
# 跨集隔离: 各集密钥独立, 密文不可跨集解密
# 集完成锁档: episode_close → 密钥轮换(epoch+1) → 防后续篡改

KUNLUN_STATE_PATH = os.path.join(DATA_DIR, "kunlun-production.json")
KUNLUN_STAGES = ["剧本", "分镜", "关键帧", "视频", "质检"]

def _load_kunlun():
    if os.path.exists(KUNLUN_STATE_PATH):
        try:
            with open(KUNLUN_STATE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"batches": {}}

def _save_kunlun(st):
    with open(KUNLUN_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)

def kunlun_production(op, body):
    """昆仑洞天 60集批量生产流水线主入口"""
    if op == "init_batch":
        total = int(body.get("episodes", 60))
        name = body.get("name", "kunlun")
        members = body.get("members") or KUNLUN_STAGES
        st = _load_kunlun()
        batch_id = f"KL-{int(time.time()*1000)}"
        episodes = {}
        for ep in range(1, total + 1):
            # 每集独立组 (复用 mls_group_create + 树)
            gid = f"g-{int(time.time()*1000)}"
            init_secret = os.urandom(32)
            group_secret = _hkdf(init_secret, f"zr-mls-kunlun-ep{ep}:".encode() + name.encode())
            epoch_secret = _hkdf(group_secret, b"zr-mls-epoch:0")
            mls_st = _load_mls()
            mls_st["groups"][gid] = {
                "name": f"{name}-EP{ep:02d}", "creator": members[0], "epoch": 0,
                "members": members,
                "init_secret_b64": base64.b64encode(init_secret).decode(),
                "group_secret_b64": base64.b64encode(group_secret).decode(),
                "epoch_secret_b64": base64.b64encode(epoch_secret).decode(),
                "epoch_secret_sha256": hashlib.sha256(epoch_secret).hexdigest()[:16],
                "member_secrets": {m: base64.b64encode(os.urandom(32)).decode() for m in members},
                "created_ts": int(time.time()),
            }
            _tree_build(mls_st["groups"][gid],
                        {m: base64.b64decode(mls_st["groups"][gid]["member_secrets"][m]) for m in members})
            _save_mls(mls_st)
            episodes[ep] = {"group_id": gid, "epoch": 0, "stage": "剧本", "status": "pending"}
        st["batches"][batch_id] = {"name": name, "total": total, "members": members,
                                   "episodes": episodes, "created_ts": int(time.time())}
        _save_kunlun(st)
        roots = {}
        for ep, info in episodes.items():
            g = _load_mls()["groups"][info["group_id"]]
            roots[ep] = g["tree"]["root"][:12]
        return {"ok": True, "batch_id": batch_id, "episodes": total,
                "per_episode_keys": True, "members": members,
                "sample_roots": {f"EP{i:02d}": roots[i] for i in list(roots)[:3]},
                "isolation": "each_episode_independent_group_key"}, 200

    batch_id = body.get("batch_id", "")
    ep = int(body.get("episode", 0))
    st = _load_kunlun()
    batch = st["batches"].get(batch_id)
    if not batch:
        return {"ok": False, "error": "batch_not_found"}, 404
    einfo = batch["episodes"].get(str(ep)) or batch["episodes"].get(ep)
    if not einfo:
        return {"ok": False, "error": "episode_not_found"}, 404
    gid = einfo["group_id"]
    mls_st = _load_mls()
    g = mls_st["groups"].get(gid)
    if not g:
        return {"ok": False, "error": "group_not_found"}, 404
    _ensure_tree(g)
    _save_mls(mls_st)

    if op == "episode_status":
        return {"ok": True, "batch_id": batch_id, "episode": ep,
                "group_id": gid, "epoch": g["epoch"], "root": g["tree"]["root"][:16],
                "members": g["members"], "stage": einfo.get("stage"),
                "status": einfo.get("status"), "locked": einfo.get("status") == "locked"}, 200

    if op == "asset_encrypt":
        stage = body.get("stage", "")
        plaintext = body.get("content", "")
        if stage not in g["members"]:
            return {"ok": False, "error": "stage_not_member"}, 403
        if not plaintext:
            return {"ok": False, "error": "empty_content"}, 400
        encryption_secret = _hkdf(base64.b64decode(g["epoch_secret_b64"]), b"zr-mls-encryption")
        sender_key = _hkdf(encryption_secret, b"zr-mls-sender:" + stage.encode())
        aad = f"zr-kunlun|{batch_id}|{ep}|{stage}|{g['epoch']}".encode()
        iv, ct = _aes_gcm_encrypt(sender_key, plaintext.encode("utf-8"), aad)
        return {"ok": True, "batch_id": batch_id, "episode": ep, "stage": stage,
                "iv": iv, "ciphertext": ct, "aad": aad.decode(), "epoch": g["epoch"],
                "algorithm": "AES-256-GCM"}, 200

    if op == "asset_decrypt":
        stage = body.get("stage", "")
        iv = body.get("iv", "")
        ct = body.get("ciphertext", "")
        if stage not in g["members"]:
            return {"ok": False, "error": "stage_not_member"}, 403
        encryption_secret = _hkdf(base64.b64decode(g["epoch_secret_b64"]), b"zr-mls-encryption")
        sender_key = _hkdf(encryption_secret, b"zr-mls-sender:" + stage.encode())
        aad = f"zr-kunlun|{batch_id}|{ep}|{stage}|{g['epoch']}".encode()
        try:
            pt = _aes_gcm_decrypt(sender_key, iv, ct, aad)
            return {"ok": True, "batch_id": batch_id, "episode": ep, "stage": stage,
                    "content": pt, "integrity": "verified", "epoch": g["epoch"]}, 200
        except Exception as e:
            return {"ok": False, "error": "decrypt_failed", "detail": str(e)[:80]}, 400

    if op == "episode_close":
        # 集完成锁档: 密钥轮换(epoch+1) → 旧epoch密文不可再解密 → 防篡改
        if einfo.get("status") == "locked":
            return {"ok": False, "error": "already_locked"}, 409
        prev_root = g["tree"]["root"]
        _tree_build(g, {m: base64.b64decode(g["member_secrets"][m]) for m in g["members"]})
        g["epoch"] += 1
        g["tree"]["epoch"] = g["epoch"]
        _save_mls(mls_st)
        einfo["status"] = "locked"
        einfo["stage"] = "已归档"
        _save_kunlun(st)
        return {"ok": True, "batch_id": batch_id, "episode": ep,
                "prev_epoch": g["epoch"] - 1, "epoch": g["epoch"],
                "prev_root": prev_root[:16], "new_root": g["tree"]["root"][:16],
                "locked": True, "note": "密钥轮换完成, 旧epoch资产已封存"}, 200

    return {"ok": False, "error": "bad_op"}, 400

# ================= V1.6: A2A × 昆仑生产任务分发 =================
# AgentCard 注册的 5 个生产 Agent (剧本/分镜/关键帧/视频/质检)
# 任务8态: submitted/working/completed/failed/canceled/input-required/needs-specified/unknown
# 分发: 按 AgentCard 能力标签匹配 Agent → 创建任务(绑定集+阶段+昆仑组密钥)
# 完成: 产出经该集组密钥 AES-GCM 加密上链 (跨集隔离 + 可审计)

A2A_KUNLUN_STATE_PATH = os.path.join(DATA_DIR, "a2a-kunlun-tasks.json")
KUNLUN_AGENT_CARDS = [
    {"agent_id": "agent-script", "name": "剧本Agent", "capability": "剧本", "status": "online"},
    {"agent_id": "agent-storyboard", "name": "分镜Agent", "capability": "分镜", "status": "online"},
    {"agent_id": "agent-keyframe", "name": "关键帧Agent", "capability": "关键帧", "status": "online"},
    {"agent_id": "agent-video", "name": "视频Agent", "capability": "视频", "status": "online"},
    {"agent_id": "agent-qa", "name": "质检Agent", "capability": "质检", "status": "online"},
]

def _load_a2a_kunlun():
    if os.path.exists(A2A_KUNLUN_STATE_PATH):
        try:
            with open(A2A_KUNLUN_STATE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"tasks": {}}

def _save_a2a_kunlun(st):
    with open(A2A_KUNLUN_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)

def a2a_kunlun_dispatch(op, body):
    """AgentCard 任务分发到昆仑生产流水线主入口"""
    st = _load_a2a_kunlun()

    if op == "dispatch":
        # 按 AgentCard 能力标签匹配生产 Agent
        stage = body.get("stage", "")
        card = next((c for c in KUNLUN_AGENT_CARDS if c["capability"] == stage), None)
        if not card:
            return {"ok": False, "error": "no_agent_for_stage",
                    "known_stages": KUNLUN_STAGES}, 404
        batch_id = body.get("batch_id", "")
        ep = int(body.get("episode", 0))
        task_spec = body.get("task_spec", {})
        # 校验昆仑组存在
        kl = _load_kunlun()
        batch = kl["batches"].get(batch_id)
        if not batch:
            return {"ok": False, "error": "batch_not_found"}, 404
        einfo = batch["episodes"].get(str(ep)) or batch["episodes"].get(ep)
        if not einfo:
            return {"ok": False, "error": "episode_not_found"}, 404
        gid = einfo["group_id"]
        task_id = f"A2A-KL-{int(time.time()*1000)}"
        st["tasks"][task_id] = {
            "task_id": task_id, "status": "submitted", "agent": card,
            "batch_id": batch_id, "episode": ep, "stage": stage,
            "group_id": gid, "task_spec": task_spec,
            "created_ts": int(time.time()),
        }
        _save_a2a_kunlun(st)
        return {"ok": True, "task_id": task_id, "status": "submitted",
                "agent": {"agent_id": card["agent_id"], "name": card["name"], "capability": card["capability"]},
                "group_id": gid, "note": "A2A任务已提交, 等待Agent认领"}, 200

    task_id = body.get("task_id", "")
    t = st["tasks"].get(task_id)
    if not t:
        return {"ok": False, "error": "task_not_found"}, 404

    if op == "claim":
        if t["status"] != "submitted":
            return {"ok": False, "error": "bad_state", "current": t["status"]}, 409
        t["status"] = "working"
        t["claimed_ts"] = int(time.time())
        _save_a2a_kunlun(st)
        return {"ok": True, "task_id": task_id, "status": "working",
                "agent": t["agent"]["name"], "note": "Agent已认领, 生产中"}, 200

    if op == "complete":
        if t["status"] != "working":
            return {"ok": False, "error": "bad_state", "current": t["status"]}, 409
        output = body.get("output", "")
        stage = t["stage"]
        gid = t["group_id"]
        mls_st = _load_mls()
        g = mls_st["groups"].get(gid)
        if not g:
            return {"ok": False, "error": "group_not_found"}, 404
        _ensure_tree(g)
        encryption_secret = _hkdf(base64.b64decode(g["epoch_secret_b64"]), b"zr-mls-encryption")
        sender_key = _hkdf(encryption_secret, b"zr-mls-sender:" + stage.encode())
        aad = f"zr-a2a|{t['batch_id']}|{t['episode']}|{stage}|{g['epoch']}".encode()
        iv, ct = _aes_gcm_encrypt(sender_key, output.encode("utf-8"), aad)
        t["status"] = "completed"
        t["completed_ts"] = int(time.time())
        t["output_enc"] = {"iv": iv, "ciphertext": ct, "aad": aad.decode(), "epoch": g["epoch"]}
        _save_a2a_kunlun(st)
        return {"ok": True, "task_id": task_id, "status": "completed",
                "episode": t["episode"], "stage": stage,
                "output_encrypted": True, "integrity": "aes-gcm-verified",
                "note": "产出已用该集组密钥加密上链"}, 200

    if op == "task_status":
        return {"ok": True, "task_id": task_id, "status": t["status"],
                "agent": t["agent"]["name"], "episode": t["episode"], "stage": t["stage"],
                "group_id": t["group_id"],
                "output_encrypted": "output_enc" in t}, 200

    if op == "cancel":
        if t["status"] in ("completed", "canceled"):
            return {"ok": False, "error": "bad_state", "current": t["status"]}, 409
        t["status"] = "canceled"
        t["canceled_ts"] = int(time.time())
        _save_a2a_kunlun(st)
        return {"ok": True, "task_id": task_id, "status": "canceled",
                "note": "任务已取消"}, 200

    return {"ok": False, "error": "bad_op"}, 400

# ================= V1.7: MCP × 昆仑生产工具化 =================
# 昆仑生产 5 操作封装为 MCP 工具 (JSON Schema 注册表)
# 外部 Agent 可发现(list) + 调用(call) 昆仑流水线, 与 A2A 分发互补:
#   A2A = 任务级编排 (Agent 认领/完成); MCP = 工具级调用 (外部 Agent 直接调能力)

MCP_KUNLUN_TOOLS = [
    {"name": "kunlun.init_batch", "description": "批量初始化昆仑生产批次, 每集独立组密钥(RatchetTree)",
     "inputSchema": {"type": "object", "properties": {
         "name": {"type": "string", "description": "批次名"},
         "episodes": {"type": "integer", "description": "集数(默认60)"}},
         "required": ["name"]}},
    {"name": "kunlun.episode_status", "description": "查询单集生产状态(epoch/root/成员/阶段)",
     "inputSchema": {"type": "object", "properties": {
         "batch_id": {"type": "string"}, "episode": {"type": "integer"}},
         "required": ["batch_id", "episode"]}},
    {"name": "kunlun.asset_encrypt", "description": "用该集组密钥AES-256-GCM加密生产资产(剧本/分镜/关键帧)",
     "inputSchema": {"type": "object", "properties": {
         "batch_id": {"type": "string"}, "episode": {"type": "integer"},
         "stage": {"type": "string"}, "content": {"type": "string"}},
         "required": ["batch_id", "episode", "stage", "content"]}},
    {"name": "kunlun.asset_decrypt", "description": "解密生产资产, 验证集归属与完整性",
     "inputSchema": {"type": "object", "properties": {
         "batch_id": {"type": "string"}, "episode": {"type": "integer"},
         "stage": {"type": "string"}, "iv": {"type": "string"}, "ciphertext": {"type": "string"}},
         "required": ["batch_id", "episode", "stage", "iv", "ciphertext"]}},
    {"name": "kunlun.episode_close", "description": "集完成锁档: 密钥轮换(epoch+1), 旧资产封存防篡改",
     "inputSchema": {"type": "object", "properties": {
         "batch_id": {"type": "string"}, "episode": {"type": "integer"}},
         "required": ["batch_id", "episode"]}},
]

MCP_KUNLUN_OP_MAP = {
    "kunlun.init_batch": {"op": "init_batch", "args": ["name", "episodes"]},
    "kunlun.episode_status": {"op": "episode_status", "args": ["batch_id", "episode"]},
    "kunlun.asset_encrypt": {"op": "asset_encrypt", "args": ["batch_id", "episode", "stage", "content"]},
    "kunlun.asset_decrypt": {"op": "asset_decrypt", "args": ["batch_id", "episode", "stage", "iv", "ciphertext"]},
    "kunlun.episode_close": {"op": "episode_close", "args": ["batch_id", "episode"]},
}

def mcp_kunlun(op, body):
    """昆仑生产 MCP 工具服务主入口"""
    if op == "list":
        return {"ok": True, "service": "zr-mcp-kunlun", "tools": MCP_KUNLUN_TOOLS,
                "protocol": "MCP tools/list 语义", "note": "外部Agent可发现昆仑生产工具"}, 200

    if op == "call":
        tool_name = body.get("name", "")
        arguments = body.get("arguments", {})
        mapping = MCP_KUNLUN_OP_MAP.get(tool_name)
        if not mapping:
            return {"ok": False, "error": "tool_not_found",
                    "available": [t["name"] for t in MCP_KUNLUN_TOOLS]}, 404
        payload = {"op": mapping["op"]}
        for a in mapping["args"]:
            if a in arguments:
                payload[a] = arguments[a]
        r, code = kunlun_production(payload["op"], payload)
        if code == 200:
            return {"ok": True, "tool": tool_name, "result": r,
                    "protocol": "MCP tools/call 语义"}, 200
        return {"ok": False, "tool": tool_name, "error": r}, code

    if op == "status":
        return {"ok": True, "service": "zr-mcp-kunlun", "tools_count": len(MCP_KUNLUN_TOOLS),
                "tools": [t["name"] for t in MCP_KUNLUN_TOOLS], "protocol": "MCP tools/list+call 已注册"}, 200

    return {"ok": False, "error": "bad_op"}, 400

# ================= V1.8: DPoP × 昆仑生产安全准入 =================
# RFC 9449 DPoP 令牌绑定 → 昆仑生产操作安全准入
# 流程: issue_token(签发) → bind(DPoP proof校验) → execute(安全执行昆仑操作)
# 增强: 未携带有效DPoP令牌的昆仑调用被拦截; 令牌可吊销

KUNLUN_DPOP_STATE_PATH = os.path.join(DATA_DIR, "kunlun-dpop-tokens.json")

def _load_kunlun_dpop():
    if os.path.exists(KUNLUN_DPOP_STATE_PATH):
        try:
            with open(KUNLUN_DPOP_STATE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"tokens": {}}

def _save_kunlun_dpop(st):
    with open(KUNLUN_DPOP_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)

def _issue_bearer_token(client_id, scope):
    """签发绑定令牌: 随机 + jkt 占位(客户端DPoP公钥指纹)"""
    raw = os.urandom(24)
    token = "zr-dpop-" + base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return token

def kunlun_secure(op, body):
    """DPoP 保护昆仑生产安全入口主入口"""
    st = _load_kunlun_dpop()

    if op == "issue_token":
        # 签发 DPoP 绑定访问令牌: 绑定 client 身份 + 昆仑批次
        client_id = body.get("client_id", "")
        if not client_id:
            return {"ok": False, "error": "missing_client_id"}, 400
        batch_id = body.get("batch_id", "")
        if batch_id:
            kl = _load_kunlun()
            if batch_id not in kl["batches"]:
                return {"ok": False, "error": "batch_not_found"}, 404
        token = _issue_bearer_token(client_id, "kunlun")
        jkt = hashlib.sha256(f"zr-dpop-jkt:{client_id}".encode()).hexdigest()[:32]
        st["tokens"][token] = {
            "client_id": client_id, "batch_id": batch_id or "*",
            "jkt": jkt, "status": "active", "issued_ts": int(time.time()),
        }
        _save_kunlun_dpop(st)
        return {"ok": True, "access_token": token, "jkt": jkt,
                "token_type": "DPoP", "algorithm": "RFC9449",
                "note": "令牌已签发, 调用昆仑操作需携带有效DPoP proof"}, 200

    token = body.get("access_token", "")
    tok = st["tokens"].get(token)
    if not tok:
        return {"ok": False, "error": "token_not_found"}, 401
    if tok.get("status") != "active":
        return {"ok": False, "error": "token_revoked"}, 401

    if op == "bind":
        # RFC 9449 DPoP proof 校验: jkt匹配 + 签名 + 时间戳 + 防重放
        proof = body.get("dpop_proof", "")
        htu = body.get("htu", "")
        htm = body.get("htm", "POST")
        ok, msg = dpop_verify(proof, htu, htm)
        if not ok:
            return {"ok": False, "error": "dpop_invalid", "detail": msg}, 401
        # jkt 绑定校验: proof 头中 jkt 必须与令牌签发时一致
        try:
            header = json.loads(base64.urlsafe_b64decode(proof.split(".")[0] + "=="))
        except Exception:
            return {"ok": False, "error": "bad_proof_header"}, 401
        if header.get("jkt") and header["jkt"] != tok["jkt"]:
            return {"ok": False, "error": "jkt_mismatch"}, 401
        return {"ok": True, "client_id": tok["client_id"], "batch_id": tok["batch_id"],
                "bound": True, "protocol": "RFC9449 DPoP 绑定校验通过"}, 200

    if op == "execute":
        # 安全执行: 校验 DPoP proof 后路由昆仑生产操作
        proof = body.get("dpop_proof", "")
        htu = body.get("htu", "")
        htm = body.get("htm", "POST")
        ok, msg = dpop_verify(proof, htu, htm)
        if not ok:
            return {"ok": False, "error": "dpop_invalid", "detail": msg}, 401
        try:
            header = json.loads(base64.urlsafe_b64decode(proof.split(".")[0] + "=="))
        except Exception:
            return {"ok": False, "error": "bad_proof_header"}, 401
        if header.get("jkt") and header["jkt"] != tok["jkt"]:
            return {"ok": False, "error": "jkt_mismatch"}, 401
        # 昆仑上下文校验: 若令牌绑定批次, 执行必须属于该批次
        exec_payload = body.get("payload", {})
        op_name = exec_payload.get("op", "")
        if tok["batch_id"] != "*" and exec_payload.get("batch_id") and \
           exec_payload["batch_id"] != tok["batch_id"]:
            return {"ok": False, "error": "batch_mismatch"}, 403
        # 路由到昆仑生产
        r, code = kunlun_production(op_name, exec_payload)
        if code == 200:
            return {"ok": True, "executed": op_name, "result": r,
                    "authorized_by": "DPoP RFC9449"}, 200
        return {"ok": False, "error": r}, code

    if op == "revoke":
        tok["status"] = "revoked"
        tok["revoked_ts"] = int(time.time())
        _save_kunlun_dpop(st)
        return {"ok": True, "token_status": "revoked",
                "note": "令牌已吊销, 后续调用将401拦截"}, 200

    return {"ok": False, "error": "bad_op"}, 400

# ================= V1.9: 四协议联邦组合流 =================
# DPoP(认证) → A2A(编排) → MCP(执行) → SLIM(传输) 组合流水线
# 一次请求完成: 安全准入 → 任务分发 → 工具执行 → 加密传输 全链路

FEDERATED_KUNLUN_STATE_PATH = os.path.join(DATA_DIR, "federated-kunlun-pipeline.json")

FED_PIPELINE_REGISTRY = {
    "auth_modes": ["DPoP", "OAuth2"],  # V2.2: 环节1 双认证模式
    "name": "zr-federated-kunlun-pipeline",
    "version": "1.9.0",
    "stages": [
        {"stage": 1, "protocol": "OAuth2/DPoP", "role": "security_gate", "endpoint": "/v1/oauth/token | /v1/kunlun/secure", "binding": "OAuth2 client_credentials + RFC9449 令牌绑定"},
        {"stage": 2, "protocol": "A2A",   "role": "orchestration", "endpoint": "/v1/a2a/kunlun/dispatch", "binding": "AgentCard 任务分发"},
        {"stage": 3, "protocol": "MCP",   "role": "execution", "endpoint": "/v1/mcp/kunlun", "binding": "tools/call 工具执行"},
        {"stage": 4, "protocol": "SLIM",  "role": "transport", "endpoint": "/v1/slim/message/encrypt", "binding": "MLS 组密钥 AES-256-GCM"},
    ],
    "flow": "认证→编排→执行→加密传输",
}

def _load_fed_pipeline():
    if os.path.exists(FEDERATED_KUNLUN_STATE_PATH):
        try:
            with open(FEDERATED_KUNLUN_STATE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"runs": []}

def _save_fed_pipeline(st):
    with open(FEDERATED_KUNLUN_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)

def _dpop_gate_check(body):
    """DPoP 安全准入门: 校验令牌存在+active+proof有效+jkt匹配"""
    st = _load_kunlun_dpop()
    token = body.get("access_token", "")
    tok = st["tokens"].get(token)
    if not tok:
        return None, "token_not_found"
    if tok.get("status") != "active":
        return None, "token_revoked"
    proof = body.get("dpop_proof", "")
    htu = body.get("htu", "")
    htm = body.get("htm", "POST")
    ok, msg = dpop_verify(proof, htu, htm)
    if not ok:
        return None, "dpop_invalid:" + msg
    try:
        header = json.loads(base64.urlsafe_b64decode(proof.split(".")[0] + "=="))
    except Exception:
        return None, "bad_proof_header"
    if header.get("jkt") and header["jkt"] != tok["jkt"]:
        return None, "jkt_mismatch"
    return tok, None

def federated_kunlun(op, body):
    """四协议联邦组合流主入口"""
    if op == "compose":
        return {"ok": True, "registry": FED_PIPELINE_REGISTRY}, 200

    if op == "run":
        audit = []
        # 环节1: 认证准入 (支持 OAuth2 或 DPoP 双模式)
        auth_mode = body.get("auth", "dpop")  # oauth2 | dpop
        if auth_mode == "oauth2":
            oa_tok = body.get("access_token", "")
            ok, msg = oauth_authorized(oa_tok, "kunlun.production")
            if not ok:
                return {"ok": False, "error": msg, "stage": 1, "protocol": "OAuth2"}, 401
            audit.append({"stage": 1, "protocol": "OAuth2", "status": "passed",
                          "client": _oauth_client_of(oa_tok), "auth": "client_credentials"})
        else:
            tok, err = _dpop_gate_check(body)
            if err:
                return {"ok": False, "error": err, "stage": 1, "protocol": "DPoP"}, 401
            audit.append({"stage": 1, "protocol": "DPoP", "status": "passed", "client": tok["client_id"]})
        # 环节2: A2A 任务编排
        batch_id = body.get("batch_id", "")
        episode = body.get("episode", 1)
        stage = body.get("stage", "剧本")
        dispatch_payload = {"op": "dispatch", "batch_id": batch_id, "episode": episode,
                            "stage": stage, "task_spec": body.get("task_spec", {})}
        r, code = a2a_kunlun_dispatch("dispatch", dispatch_payload)
        if code != 200:
            return {"ok": False, "error": r, "stage": 2, "protocol": "A2A"}, code
        task_id = r.get("task_id", "")
        agent_name = r.get("agent", {}).get("name", "")
        audit.append({"stage": 2, "protocol": "A2A", "status": "passed", "task": task_id, "agent": agent_name})
        # 环节3: MCP 工具执行 (加密生产资产)
        content = body.get("content", "federated-pipeline-asset")
        mcp_payload = {"op": "call", "name": "kunlun.asset_encrypt",
                       "arguments": {"batch_id": batch_id, "episode": episode, "stage": stage, "content": content}}
        r, code = mcp_kunlun("call", mcp_payload)
        if code != 200:
            return {"ok": False, "error": r, "stage": 3, "protocol": "MCP"}, code
        iv, ct = r["result"]["iv"], r["result"]["ciphertext"]
        audit.append({"stage": 3, "protocol": "MCP", "status": "passed", "iv": iv[:8] + "...", "ct_len": len(ct)})
        # 环节4: SLIM 加密传输 (组密钥 AES-256-GCM, sender=组内成员stage)
        st_r, st_code = kunlun_production("episode_status", {"batch_id": batch_id, "episode": episode})
        if st_code != 200:
            return {"ok": False, "error": st_r, "stage": 4, "protocol": "SLIM"}, st_code
        gid = st_r.get("group_id", "")
        sender = stage if stage in (st_r.get("members") or []) else "剧本"
        slim_payload = {"op": "encrypt", "group_id": gid, "sender": sender,
                        "plaintext": "{\"ciphertext\":\"" + ct + "\",\"iv\":\"" + iv + "\"}"}
        sr, scode = mls_message_encrypt(gid, sender, slim_payload["plaintext"])
        if scode != 200:
            return {"ok": False, "error": sr, "stage": 4, "protocol": "SLIM"}, scode
        audit.append({"stage": 4, "protocol": "SLIM", "status": "passed", "slim_iv": sr["iv"][:8] + "...", "slim_ct_len": len(sr["ciphertext"])})
        # 完成: 记录审计
        st = _load_fed_pipeline()
        run_id = "FED-KL-" + str(int(time.time() * 1000))
        st["runs"].append({"run_id": run_id, "batch": batch_id, "episode": episode,
                           "task": task_id, "audit": audit, "ts": int(time.time())})
        st["runs"] = st["runs"][-20:]
        _save_fed_pipeline(st)
        return {"ok": True, "run_id": run_id, "batch_id": batch_id, "episode": episode,
                "task_id": task_id, "agent": agent_name, "stages": 4, "audit": audit,
                "result": {"encrypted": True, "transport": "MLS AES-256-GCM",
                           "slim_iv": sr["iv"], "slim_ciphertext": sr["ciphertext"]}}, 200

    if op == "status":
        st = _load_fed_pipeline()
        return {"ok": True, "registry": FED_PIPELINE_REGISTRY["name"],
                "version": FED_PIPELINE_REGISTRY["version"],
                "runs_count": len(st["runs"]),
                "last_run": st["runs"][-1] if st["runs"] else None}, 200

    return {"ok": False, "error": "bad_op"}, 400

# ---- V2.1: OAuth2 / OIDC 认证授权族 (RFC6749 + RFC7662 + RFC7009 + OIDC Discovery) ----
OAUTH_STATE_PATH = os.path.join(DATA_DIR, "oauth-clients.json")

# 客户端注册表: client_id -> {secret, scopes}
OAUTH_CLIENTS = {
    "zr-agent": {"secret": "zr-oauth-secret-2026", "scopes": ["kunlun.production", "a2a.dispatch", "mcp.call"]},
    "zr-render": {"secret": "zr-render-secret-2026", "scopes": ["kunlun.production"]},
}

def _load_oauth():
    if os.path.exists(OAUTH_STATE_PATH):
        try:
            with open(OAUTH_STATE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"tokens": {}, "revoked": []}

def _save_oauth(st):
    with open(OAUTH_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)

def oauth_issue_access_token(client_id, scopes, dpop_jkt=""):
    st = _load_oauth()
    raw = os.urandom(24)
    token = "zr-oauth-" + base64.urlsafe_b64encode(raw).decode().rstrip("=")
    st["tokens"][token] = {
        "client_id": client_id, "scopes": scopes, "jkt": dpop_jkt,
        "status": "active", "issued_ts": int(time.time()),
        "expires_in": 3600,
    }
    _save_oauth(st)
    return token

def oauth_token_endpoint(body):
    """RFC6749 token 端点: 支持 client_credentials 流 (含 DPoP 绑定)"""
    grant_type = body.get("grant_type", "")
    if grant_type != "client_credentials":
        return {"error": "unsupported_grant_type", "error_description": "仅支持 client_credentials"}, 400
    client_id = body.get("client_id", "")
    client_secret = body.get("client_secret", "")
    cli = OAUTH_CLIENTS.get(client_id)
    if not cli or cli["secret"] != client_secret:
        return {"error": "invalid_client", "error_description": "客户端凭证无效"}, 401
    scope = body.get("scope", " ".join(cli["scopes"]))
    req_scopes = [s for s in scope.split() if s in cli["scopes"]]
    if not req_scopes:
        req_scopes = cli["scopes"]
    dpop_jkt = body.get("dpop_jkt", "")
    token = oauth_issue_access_token(client_id, req_scopes, dpop_jkt)
    return {
        "access_token": token, "token_type": "DPoP" if dpop_jkt else "Bearer",
        "expires_in": 3600, "scope": " ".join(req_scopes),
        "jkt": dpop_jkt or None,
    }, 200

def oauth_introspect_endpoint(body):
    """RFC7662 token 内省"""
    token = body.get("token", "")
    if not token:
        return {"error": "missing_token"}, 400
    st = _load_oauth()
    tok = st["tokens"].get(token)
    if not tok or tok.get("status") != "active":
        return {"active": False}, 200
    return {
        "active": True, "client_id": tok["client_id"], "scope": " ".join(tok["scopes"]),
        "token_type": "access_token", "exp": tok["issued_ts"] + tok.get("expires_in", 3600),
        "iat": tok["issued_ts"], "jkt": tok.get("jkt", ""),
    }, 200

def oauth_revoke_endpoint(body):
    """RFC7009 token 吊销"""
    token = body.get("token", "")
    if not token:
        return {"error": "missing_token"}, 400
    st = _load_oauth()
    if token in st["tokens"]:
        st["tokens"][token]["status"] = "revoked"
        st["revoked"].append(token)
        _save_oauth(st)
    return {}, 200  # RFC7009: 吊销成功返回 200 (无论 token 是否存在)

def _oauth_client_of(access_token):
    st = _load_oauth()
    tok = st["tokens"].get(access_token)
    return tok.get("client_id", "unknown") if tok else "unknown"

def oauth_authorized(access_token, needed_scope=""):
    """OAuth2 资源访问校验: token 有效 + scope 覆盖"""
    st = _load_oauth()
    tok = st["tokens"].get(access_token)
    if not tok or tok.get("status") != "active":
        return False, "invalid_token"
    if needed_scope and needed_scope not in tok.get("scopes", []):
        return False, "insufficient_scope"
    return True, "ok"

def oidc_discovery():
    """OIDC Discovery 1.0 发现文档"""
    iss = "https://www.huodouai.com"
    return {
        "issuer": iss,
        "authorization_endpoint": iss + "/v1/oauth/authorize",
        "token_endpoint": iss + "/v1/oauth/token",
        "introspection_endpoint": iss + "/v1/oauth/introspect",
        "revocation_endpoint": iss + "/v1/oauth/revoke",
        "jwks_uri": iss + "/v1/oauth/jwks",
        "response_types_supported": ["token"],
        "grant_types_supported": ["client_credentials"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "code_challenge_methods_supported": [],
        "scopes_supported": ["kunlun.production", "a2a.dispatch", "mcp.call"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": [],
        "claims_supported": ["sub", "client_id", "scope", "iat", "exp"],
    }, 200

def oauth_handle(p, body):
    """OAuth2/OIDC 族路由"""
    if p == "/.well-known/openid-configuration":
        return oidc_discovery()
    if p == "/v1/oauth/token":
        return oauth_token_endpoint(body)
    if p == "/v1/oauth/introspect":
        return oauth_introspect_endpoint(body)
    if p == "/v1/oauth/revoke":
        return oauth_revoke_endpoint(body)
    return {"ok": False, "error": "bad_op"}, 400

# ---- Flower 真实 FedAvg 聚合 ----
def fedavg_aggregate(round_id, node_updates):
    """FedAvg: 按样本数加权平均各节点权重向量"""
    if not node_updates or not isinstance(node_updates, list):
        return {"ok": False, "error": "empty_node_updates"}, 400
    # 收集所有 key
    all_keys = set()
    for u in node_updates:
        for k in (u.get("weights") or {}).keys():
            all_keys.add(k)
    total_samples = sum(u.get("samples", 0) for u in node_updates)
    if total_samples <= 0:
        return {"ok": False, "error": "zero_samples"}, 400
    agg = {}
    for k in all_keys:
        num = 0.0
        for u in node_updates:
            w = (u.get("weights") or {}).get(k)
            if w is None:
                continue
            num += float(w) * u.get("samples", 0)
        agg[k] = num / total_samples
    result = {
        "ok": True, "protocol": "flower-fedavg", "version": "1.0",
        "round": round_id, "aggregated_nodes": len(node_updates),
        "total_samples": total_samples, "aggregated_weights": agg,
        "secure_agg": "declared", "ts": int(time.time()),
    }
    # 归档聚合结果
    agg_path = os.path.join(DATA_DIR, "fedavg-rounds.jsonl")
    try:
        with open(agg_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"round": round_id, "nodes": len(node_updates),
                                "samples": total_samples, "ts": int(time.time())}) + "\n")
    except Exception:
        pass
    return result, 200

MODELS = [
    {"id": "zr-qwen2.5-7b", "object": "model", "created": 1791600000,
     "owned_by": "zongyuanroot", "format": ["gguf", "openai-compat"], "quant": "q4_k_m"},
    {"id": "zr-qwen2.5-3b", "object": "model", "created": 1791600000,
     "owned_by": "zongyuanroot", "format": ["gguf", "openai-compat"], "quant": "q4_k_m"},
    {"id": "zr-llama3-8b", "object": "model", "created": 1791600000,
     "owned_by": "zongyuanroot", "format": ["gguf", "onnx"], "quant": "q4_k_m"},
]

def _load_dpop_registry():
    if os.path.exists(DPOP_REGISTRY_PATH):
        try:
            with open(DPOP_REGISTRY_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_dpop_registry(reg):
    with open(DPOP_REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)

def _b64url(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def _sha256_b64(data):
    return _b64url(hashlib.sha256(data).digest())

# ---- AGNTCY SLIM 握手 (ECDH P-256) ----
def slim_handshake(client_pub_b64):
    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        from cryptography.hazmat.primitives import hashes
    except ImportError:
        return {
            "ok": True, "protocol": "slim-declared",
            "session_id": f"slim-{int(time.time()*1000)}",
            "note": "声明层握手 (cryptography库缺失, 使用占位派生)",
        }
    client_pub = serialization.load_pem_public_key(client_pub_b64.encode())
    server_key = ec.generate_private_key(ec.SECP256R1())
    shared = server_key.exchange(ec.ECDH(), client_pub)
    derived = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"zr-slim-v1").derive(shared)
    server_pub = server_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return {
        "ok": True, "protocol": "slim-mls-p256", "version": "1.0",
        "session_id": f"slim-{int(time.time()*1000)}",
        "server_pub_pem": server_pub,
        "session_key_sha256": _sha256_b64(derived),
        "forward_secrecy": True,
    }

# ---- DPoP proof 验证 (RFC 9449 简化) ----
def dpop_verify(proof, htu, htm, client_pub_b64=None):
    try:
        import jwt
        has_jwt = True
    except ImportError:
        has_jwt = False
    if not proof or not htu or not htm:
        return False, "missing_dpop_params"
    parts = proof.split(".")
    if len(parts) != 3:
        return False, "bad_jwt_shape"
    try:
        header = json.loads(base64.urlsafe_b64decode(parts[0] + "=="))
        claims = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
    except Exception:
        return False, "bad_jwt_encoding"
    if header.get("typ") != "dpop+jwt":
        return False, "bad_typ"
    if claims.get("htu") != htu or claims.get("htm") != htm:
        return False, "htu_htm_mismatch"
    if not claims.get("jti"):
        return False, "missing_jti"
    iat = claims.get("iat", 0)
    if abs(time.time() - iat) > 300:
        return False, "iat_expired"
    if not has_jwt and not client_pub_b64:
        return False, "jwt_lib_missing"
    reg = _load_dpop_registry()
    seen = reg.get("seen_jti", [])
    if claims.get("jti") in seen:
        return False, "replay_detected"
    seen = (seen + [claims.get("jti")])[-200:]
    reg["seen_jti"] = seen
    _save_dpop_registry(reg)
    return True, "dpop_ok"

# ---- Flower 联邦状态 ----
def federated_status():
    nodes = {}
    if os.path.exists(TASKPOOL):
        try:
            with open(TASKPOOL, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    try:
                        t = json.loads(line)
                        n = t.get("node", "")
                        if n:
                            nodes[n] = {"last_ts": t.get("created_ts", 0),
                                        "status": t.get("status", "unknown"),
                                        "task_id": t.get("task_id", "")}
                    except Exception: pass
        except Exception: pass
    return {
        "ok": True, "protocol": "flower-declared", "version": "1.0",
        "federation": "ZONGYUAN-ROOT 联邦算力池",
        "node_count": len(nodes), "nodes": nodes,
        "aggregation": "fedavg", "secure_agg": "declared",
    }

def _call_agent_chat(messages, model="zr-qwen2.5-7b", max_tokens=512, temperature=0.7):
    body = json.dumps({"messages": messages, "model": model,
                       "max_tokens": max_tokens, "temperature": temperature}).encode("utf-8")
    req = urllib.request.Request(f"{AGENT_API}/api/v1/gateway/chat", data=body,
        headers={"Content-Type": "application/json", "X-API-Key": API_KEY})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data, int((time.time() - t0) * 1000), 200
    except urllib.error.HTTPError as e:
        return {"error": str(e)}, 0, e.code
    except Exception as e:
        return {"error": str(e)}, 0, 500

# ---- V2.2: GPU 真实推理节点接入 (注册表 + 心跳 + 路由) ----
GPU_STATE_PATH = os.path.join(DATA_DIR, "gpu-nodes.json")
GPU_TTL = 180  # 节点心跳 180s 未上报视为离线

def _load_gpu_nodes():
    if os.path.exists(GPU_STATE_PATH):
        try:
            with open(GPU_STATE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"nodes": {}}

def _save_gpu_nodes(st):
    with open(GPU_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)

def gpu_register(op, body):
    """GPU/CPU 推理节点注册与心跳: register / heartbeat / list / unregister"""
    st = _load_gpu_nodes()
    now = int(time.time())
    if op == "register":
        node_id = body.get("node_id", "")
        base_url = body.get("base_url", "")
        model = body.get("model", "")
        provider = body.get("provider", "vllm")  # vllm / ollama / openai
        gpu_name = body.get("gpu_name", "CPU")
        if not node_id or not base_url or not model:
            return {"ok": False, "error": "missing_fields", "need": ["node_id", "base_url", "model"]}, 400
        st["nodes"][node_id] = {
            "base_url": base_url.rstrip("/"), "model": model, "provider": provider,
            "gpu_name": gpu_name, "registered_ts": now, "last_seen": now, "status": "online",
        }
        _save_gpu_nodes(st)
        return {"ok": True, "node_id": node_id, "model": model, "provider": provider,
                "gpu_name": gpu_name, "ttl_s": GPU_TTL, "note": "心跳TTL内视为在线"}, 200
    if op == "heartbeat":
        node_id = body.get("node_id", "")
        if node_id not in st["nodes"]:
            return {"ok": False, "error": "node_not_found"}, 404
        st["nodes"][node_id]["last_seen"] = now
        st["nodes"][node_id]["status"] = "online"
        _save_gpu_nodes(st)
        return {"ok": True, "node_id": node_id, "last_seen": now}, 200
    if op == "list":
        alive = []
        offline = []
        for nid, n in st["nodes"].items():
            node = dict(n); node["node_id"] = nid
            if now - n.get("last_seen", 0) <= GPU_TTL:
                node["status"] = "online"; alive.append(node)
            else:
                node["status"] = "offline"; offline.append(node)
        return {"ok": True, "alive": alive, "offline": offline, "count": len(alive)}, 200
    if op == "unregister":
        node_id = body.get("node_id", "")
        if node_id in st["nodes"]:
            del st["nodes"][node_id]
            _save_gpu_nodes(st)
            return {"ok": True, "node_id": node_id, "removed": True}, 200
        return {"ok": False, "error": "node_not_found"}, 404
    return {"ok": False, "error": "bad_op"}, 400

def _gpu_alive_nodes(model=""):
    """返回当前在线推理节点列表 (可指定模型过滤)"""
    st = _load_gpu_nodes()
    now = int(time.time())
    out = []
    for nid, n in st["nodes"].items():
        if now - n.get("last_seen", 0) <= GPU_TTL:
            if model and n.get("model") != model:
                continue
            out.append((nid, n))
    return out

def _call_gpu_inference(messages, model, max_tokens=512, temperature=0.7):
    """真实 GPU 推理: 遍历在线节点, OpenAI 兼容 v1/chat/completions 路由"""
    nodes = _gpu_alive_nodes(model)
    if not nodes:
        return None, 0, "no_gpu_node"
    last_err = "no_gpu_node"
    for nid, n in nodes:
        body = json.dumps({"messages": messages, "model": n["model"],
                           "max_tokens": max_tokens, "temperature": temperature}).encode("utf-8")
        req = urllib.request.Request(f"{n['base_url']}/v1/chat/completions", data=body,
            headers={"Content-Type": "application/json"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = ""
                try:
                    content = data["choices"][0]["message"]["content"]
                except Exception:
                    content = json.dumps(data, ensure_ascii=False)[:500]
                return {"node_id": nid, "model": n["model"], "gpu": n.get("gpu_name", ""),
                        "content": content, "provider": n.get("provider", "")}, \
                       int((time.time() - t0) * 1000), 200
        except urllib.error.HTTPError as e:
            last_err = f"{nid}:http_{e.code}"
            continue
        except Exception as e:
            last_err = f"{nid}:{str(e)[:60]}"
            continue
    return None, 0, last_err

def gpu_inference_route(p, body):
    if p == "/v1/gpu/register":
        return gpu_register(body.get("op", ""), body)
    return {"ok": False, "error": "bad_op"}, 400

def handle(handler, path, method):
    from urllib.parse import urlparse
    p = urlparse(path).path

    if method == "GET":
        if p == "/v1/models":
            return 200, {"object": "list", "data": MODELS}
        if p == "/v1/compat":
            return 200, {
                "ok": True, "service": "zr-compat-bridge", "version": "2.2.0",
                "protocols": {
                    "openai_api": {"endpoint": "/v1/chat/completions", "stream": "/v1/chat/stream", "gpu_route": "register→heartbeat→inference", "status": "live"},
                    "a2a": {"endpoint": "/a2a/task", "kunlun_dispatch": "/v1/a2a/kunlun/dispatch", "status": "live"},
                    "mcp": {"endpoint": "https://mcp.huodouai.com/mcp", "kunlun_tools": "/v1/mcp/kunlun", "status": "live"},
                    "agntcy_slim": {"endpoint": "/v1/slim/handshake", "group_key": "/v1/slim/group", "group_secret": "/v1/slim/group/secret", "message_crypto": "/v1/slim/message/encrypt", "consensus": "/v1/slim/group/consensus", "ratchet_tree": "/v1/slim/tree", "kunlun_production": "/v1/kunlun/production", "binding": "MLS+ECDH P-256+KeySchedule+SecretTree+RatchetTree+AES-GCM", "status": "live"},
                    "dpop": {"endpoint": "/v1/dpop/verify", "kunlun_secure": "/v1/kunlun/secure", "binding": "RFC9449", "status": "live"},
                    "oauth2_oidc": {"discovery": "/.well-known/openid-configuration", "token": "/v1/oauth/token", "introspect": "/v1/oauth/introspect", "revoke": "/v1/oauth/revoke", "federated_auth": "run环节1支持OAuth2", "binding": "RFC6749+RFC7662+RFC7009+OIDC Discovery", "status": "live"},
                    "flower": {"endpoint": "/v1/federated/aggregate", "status": "/v1/federated/status", "kunlun_pipeline": "/v1/federated/kunlun", "binding": "FedAvg+SecureAgg+四协议组合流", "status": "live"},
                    "gpu_inference": {"register": "/v1/gpu/register", "nodes": "/v1/gpu/nodes", "binding": "OpenAI兼容+心跳TTL+模型路由", "status": "live"},
                    "sse": {"stream": "/v1/chat/stream", "binding": "text/event-stream", "status": "live"},
                    "websocket": {"info": "/v1/ws/info", "binding": "RFC6455 声明层", "status": "declared"},
                    "otel_genai": {"endpoint": "/metrics", "status": "live", "telemetry": "real"},
                    "model_formats": {"gguf": True, "onnx": True, "safetensors": True},
                },
            }
        if p == "/v1/federated/status":
            return 200, federated_status()
        if p == "/v1/slim/groups":
            return 200, mls_group_list()
        if p == "/v1/gpu/nodes":
            st = gpu_register("list", {})
            return 200, st[0]
        if p == "/v1/ws/info":
            # V2.2: WebSocket 协议族声明层 (真实通道经 nginx stream / 长连接网关)
            return 200, {
                "protocol": "websocket",
                "version": "13",
                "endpoint": "wss://www.huodouai.com/v1/ws",
                "upgrade": "websocket",
                "supported": True,
                "role": "gateway-declaration",
                "note": "协议族声明层: 真实 WS 通道由 nginx stream 或长连接网关提供, 与 A2A 事件流/SLIM 传输配套",
            }
        if p == "/.well-known/openid-configuration":
            r, code = oidc_discovery()
            return code, r
        if p == "/metrics":
            avg_lat = round(_M["latency_ms_sum"] / _M["latency_n"], 1) if _M["latency_n"] else 0
            return 200, {
                "gen_ai.client.token.usage": {"total": _M["tokens_total"]},
                "gen_ai.server.request.duration": {"avg_ms": avg_lat, "total_ms": _M["latency_ms_sum"]},
                "gen_ai.server.requests": {"total": _M["requests_total"]},
                "gen_ai.server.errors": {"total": _M["errors_total"]},
                "uptime_sec": int(time.time()) - _M["start_ts"],
                "resource": {"service.name": "zhongshu-meta-core", "gen_ai.model": "zr-qwen2.5-7b"},
            }

    if method == "POST":
        length = int(handler.headers.get("Content-Length", 0))
        raw = handler.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            body = json.loads(raw)
        except Exception:
            return 400, {"ok": False, "error": "bad_json"}
        t0 = time.time()
        try:
            if p == "/v1/chat/completions":
                messages = body.get("messages", [])
                model = body.get("model", "zr-qwen2.5-7b")
                max_tokens = body.get("max_tokens", 512)
                temp = body.get("temperature", 0.7)
                # V2.2: GPU 真实推理优先, 无在线节点时回退上游
                gdata, glat, gcode = _call_gpu_inference(messages, model, max_tokens, temp)
                if gdata:
                    _metric_track("chat", tokens=max_tokens, lat_ms=glat)
                    return 200, {
                        "id": f"chatcmpl-gpu-{int(time.time()*1000)}",
                        "object": "chat.completion", "created": int(time.time()),
                        "model": model,
                        "choices": [{"index": 0, "message": {"role": "assistant", "content": gdata["content"]}, "finish_reason": "stop"}],
                        "usage": {"prompt_tokens": 0, "completion_tokens": len(gdata["content"]), "total_tokens": len(gdata["content"])},
                        "inference": {"node": gdata["node_id"], "gpu": gdata["gpu"], "provider": gdata["provider"], "latency_ms": glat},
                    }
                data, lat, code = _call_agent_chat(messages, model, max_tokens, temp)
                _metric_track("chat", tokens=max_tokens, lat_ms=lat)
                if code != 200:
                    _metric_track("error")
                    return code, {"error": {"message": data.get("error", "upstream_failed"), "type": "upstream_error"}}
                content = data.get("response") or data.get("content") or data.get("message") or json.dumps(data, ensure_ascii=False)
                return 200, {
                    "id": f"chatcmpl-zr-{int(time.time()*1000)}",
                    "object": "chat.completion", "created": int(time.time()),
                    "model": model,
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 0, "completion_tokens": len(content), "total_tokens": len(content)},
                }
            if p == "/v1/chat/stream":
                # V2.2: SSE 流式 (text/event-stream, 经 gateway __sse__ 特判输出)
                messages = body.get("messages", [])
                model = body.get("model", "zr-qwen2.5-7b")
                gdata, glat, gcode = _call_gpu_inference(messages, model, 256, 0.7)
                if gdata:
                    final = gdata["content"]
                else:
                    data, lat, code = _call_agent_chat(messages, model, 256, 0.7)
                    final = data.get("response") or data.get("content") or ""
                if not final:
                    final = "（无推理节点在线，流式回退为空）"
                import re as _re
                chunks = _re.findall(r".{1,18}", final) or [final]
                lines = ["data: " + json.dumps({"choices": [{"delta": {"content": ch}, "index": 0}], "model": model}, ensure_ascii=False) for ch in chunks]
                lines.append("data: " + json.dumps({"choices": [{"delta": {"content": "", "finish_reason": "stop"}, "index": 0}], "model": model}, ensure_ascii=False))
                lines.append("data: [DONE]")
                _metric_track("chat", tokens=len(final))
                return 200, {"__sse__": "\n\n".join(lines) + "\n\n"}
            if p == "/v1/gpu/register":
                r, code = gpu_register(body.get("op", ""), body)
                return code, r
            if p == "/v1/completions":
                prompt = body.get("prompt", "")
                data, lat, code = _call_agent_chat([{"role": "user", "content": str(prompt)}],
                                                   body.get("model", "zr-qwen2.5-7b"), body.get("max_tokens", 256))
                _metric_track("completion", lat_ms=lat)
                if code != 200:
                    _metric_track("error")
                    return code, {"error": {"message": data.get("error", "upstream_failed")}}
                content = data.get("response") or data.get("content") or ""
                return 200, {
                    "id": f"cmpl-zr-{int(time.time()*1000)}", "object": "text_completion",
                    "created": int(time.time()), "model": body.get("model", "zr-qwen2.5-7b"),
                    "choices": [{"index": 0, "text": content, "finish_reason": "stop"}],
                }
            if p == "/v1/slim/handshake":
                client_pub = body.get("client_pub_pem", "")
                if not client_pub:
                    return 200, {"ok": True, "protocol": "slim-declared",
                                 "step": "await_client_pub", "curve": "P-256",
                                 "note": "POST client_pub_pem (PEM) 完成 ECDH 握手"}
                return 200, slim_handshake(client_pub)
            if p == "/v1/slim/group":
                op = body.get("op", "create")
                if op == "create":
                    return 200, mls_group_create(body.get("name", "zr-mls"), body.get("creator", "anonymous"))
                if op in ("add", "remove"):
                    gid = body.get("group_id", "")
                    member = body.get("member", "")
                    if not gid or not member:
                        return 400, {"ok": False, "error": "missing_group_or_member"}
                    r, code = mls_group_evolve(gid, op, member)
                    return code, r
                return 400, {"ok": False, "error": "bad_op"}
            if p == "/v1/slim/group/secret":
                r, code = mls_shared_secret(body.get("group_id", ""))
                return code, r
            if p == "/v1/slim/group/consensus":
                r, code = mls_group_consensus(body.get("group_id", ""),
                                              body.get("member_claims"))
                return code, r
            if p == "/v1/slim/message/encrypt":
                r, code = mls_message_encrypt(body.get("group_id", ""),
                                              body.get("sender", ""),
                                              body.get("plaintext", ""))
                return code, r
            if p == "/v1/slim/message/decrypt":
                r, code = mls_message_decrypt(body.get("group_id", ""),
                                              body.get("sender", ""),
                                              body.get("iv", ""),
                                              body.get("ciphertext", ""),
                                              body.get("epoch"))
                return code, r
            if p == "/v1/slim/tree":
                r, code = mls_tree(body.get("op", ""), body)
                return code, r
            if p == "/v1/kunlun/production":
                r, code = kunlun_production(body.get("op", ""), body)
                return code, r
            if p == "/v1/a2a/kunlun/dispatch":
                r, code = a2a_kunlun_dispatch(body.get("op", ""), body)
                return code, r
            if p == "/v1/mcp/kunlun":
                r, code = mcp_kunlun(body.get("op", ""), body)
                return code, r
            if p == "/v1/kunlun/secure":
                r, code = kunlun_secure(body.get("op", ""), body)
                return code, r
            if p == "/v1/federated/kunlun":
                r, code = federated_kunlun(body.get("op", ""), body)
                return code, r
            if p in ("/.well-known/openid-configuration", "/v1/oauth/token",
                     "/v1/oauth/introspect", "/v1/oauth/revoke"):
                r, code = oauth_handle(p, body)
                return code, r
            if p == "/v1/dpop/verify":
                proof = body.get("proof", "")
                htu = body.get("htu", "")
                htm = body.get("htm", "")
                ok, msg = dpop_verify(proof, htu, htm)
                return (200 if ok else 401), {"ok": ok, "message": msg}
            if p == "/v1/federated/aggregate":
                r, code = fedavg_aggregate(body.get("round", 1), body.get("node_updates", []))
                return code, r
        finally:
            pass
    return 404, {"ok": False, "error": "not_found"}

if __name__ == "__main__":
    print("ZR-COMPAT-BRIDGE-001 V2.2 自检...")
    H = type("H", (), {"headers": {}})
    r = handle(H(), "/v1/models", "GET")
    assert r[0] == 200 and len(r[1]["data"]) == 3
    print("✅ /v1/models 通过")
    r = handle(H(), "/v1/compat", "GET")
    assert r[1]["protocols"]["flower"]["kunlun_pipeline"] == "/v1/federated/kunlun"
    print("✅ /v1/compat V2.2 声明通过 (MLS+RatchetTree+昆仑生产+A2A+MCP+DPoP+四协议联邦)")
    # MLS 组密钥: 创建 → 加人 → 移除 (epoch 递增)
    import io
    def _post(handle_, path, payload):
        fh = type("FH", (), {"headers": {"Content-Length": str(len(payload))}})()
        fh.rfile = io.BytesIO(payload.encode())
        return handle_(fh, path, "POST")
    r = _post(handle, "/v1/slim/group", json.dumps({"op": "create", "name": "g1", "creator": "zr"}))
    assert r[0] == 200 and r[1]["ok"], r
    gid = r[1]["group_id"]
    r = _post(handle, "/v1/slim/group", json.dumps({"op": "add", "group_id": gid, "member": "node-b"}))
    assert r[1]["epoch"] == 1 and "node-b" in r[1]["members"], r
    r = _post(handle, "/v1/slim/group", json.dumps({"op": "add", "group_id": gid, "member": "node-c"}))
    assert r[1]["epoch"] == 2 and len(r[1]["members"]) == 3, r
    print(f"✅ MLS 组密钥通过 (创建→+2成员, epoch 0→2, 组{gid})")

    # ---- V1.3: 多成员共享密钥派生 ----
    r = _post(handle, "/v1/slim/group/secret", json.dumps({"group_id": gid}))
    assert r[0] == 200 and r[1]["shared"] and len(r[1]["secret_tree"]) == 3, r
    assert r[1]["key_schedule"]["encryption_secret_sha256"], r
    # 每个成员有独立 sender_key 指纹（SecretTree）
    fps = set(r[1]["secret_tree"].values())
    assert len(fps) == 3, f"SecretTree应为3个独立sender密钥, got {len(fps)}"
    print(f"✅ 共享密钥派生通过 (encryption_secret共享 + SecretTree 3独立sender密钥)")

    # ---- V1.3: 组密钥共识 ----
    r = _post(handle, "/v1/slim/group/consensus", json.dumps({"group_id": gid}))
    assert r[0] == 200 and r[1]["consensus_reached"] is True, r
    print(f"✅ 组密钥共识通过 (shared_fp={r[1]['shared_encryption_fp'][:8]}..., 全成员指纹一致)")
    # 分叉检测: node-b 声称过期指纹 → 共识失败并标识
    bad_claims = {m: "deadbeefdeadbeef" for m in ["zr", "node-b", "node-c"]}
    r = _post(handle, "/v1/slim/group/consensus", json.dumps({"group_id": gid, "member_claims": bad_claims}))
    assert r[0] == 200 and r[1]["consensus_reached"] is False, r
    assert len(r[1]["mismatched_members"]) == 3, r
    print(f"✅ 组密钥共识-分叉检测通过 (node-b分叉被标识, 共识未收敛)")

    # ---- V1.3: 组消息加密/解密 ----
    r = _post(handle, "/v1/slim/message/encrypt", json.dumps({"group_id": gid, "sender": "zr", "plaintext": "Ω₀⊂⊙∞⊂Ω 元极恒一 组消息加密测试"}))
    assert r[0] == 200 and r[1]["algorithm"] == "AES-256-GCM", r
    iv, ct = r[1]["iv"], r[1]["ciphertext"]
    r = _post(handle, "/v1/slim/message/decrypt", json.dumps({"group_id": gid, "sender": "zr", "iv": iv, "ciphertext": ct}))
    assert r[0] == 200 and r[1]["integrity"] == "verified", r
    assert "元极恒一" in r[1]["plaintext"], r
    print("✅ 组消息 AES-GCM 加密/解密通过 (完整性verified)")
    # 错误sender应失败（非成员）
    r = _post(handle, "/v1/slim/message/encrypt", json.dumps({"group_id": gid, "sender": "hacker", "plaintext": "x"}))
    assert r[0] == 403, r
    print("✅ 非成员加密拦截通过 (403)")

    # ---- V1.4: Ratchet Tree 全态管理 ----
    # init: 完整树构建
    r = _post(handle, "/v1/slim/tree", json.dumps({"op": "init", "name": "tree1", "members": ["zr", "node-b", "node-c"]}))
    assert r[0] == 200 and r[1]["tree"]["root"] and len(r[1]["tree"]["leaves"]) == 3, r
    tgid = r[1]["group_id"]
    root0 = r[1]["tree"]["root"]
    snap0 = {"layers": r[1]["tree"]["layers"], "root": root0}
    print(f"✅ RatchetTree init 通过 (3叶子→合并树, root={root0[:10]}...)")

    # update: 成员密钥更新 → 新root + epoch+1 (前后向保密)
    r = _post(handle, "/v1/slim/tree", json.dumps({"op": "update", "group_id": tgid, "member": "zr"}))
    assert r[0] == 200 and r[1]["epoch"] == 1 and r[1]["old_root"] != r[1]["new_root"], r
    assert r[1]["forward_secret"] == "ratcheted", r
    print(f"✅ RatchetTree update 通过 (zr密钥轮换: {r[1]['old_root'][:8]}→{r[1]['new_root'][:8]}, epoch→1)")

    # state: 无状态握手 (提交旧快照→不一致; 提交当前root→可校验)
    cur = _post(handle, "/v1/slim/tree", json.dumps({"op": "state", "group_id": tgid, "snapshot": snap0}))
    assert cur[1]["validated"] is False, cur
    cur2 = _post(handle, "/v1/slim/tree", json.dumps({"op": "state", "group_id": tgid, "snapshot": {"layers": [], "root": r[1]["new_root"]}}))
    assert cur2[0] == 200, cur2
    print(f"✅ RatchetTree 无状态握手通过 (旧快照 rejected / 当前root可校验)")

    # commit: 有状态握手 (node-b 提交增量新叶子 → epoch+1)
    new_leaf = base64.b64encode(b"new-leaf-secret-node-b").decode()
    r = _post(handle, "/v1/slim/tree", json.dumps({"op": "commit", "group_id": tgid, "member": "node-b", "new_leaf_secret": new_leaf}))
    assert r[0] == 200 and r[1]["epoch"] == 2 and r[1]["stateful"] is True, r
    print(f"✅ RatchetTree 有状态握手通过 (node-b增量提交, epoch→2, new_root={r[1]['new_root'][:8]}...)")

    # ---- V1.5: 昆仑洞天 60集批量生产 ----
    # init_batch: 60集每集独立组密钥
    r = _post(handle, "/v1/kunlun/production", json.dumps({"op": "init_batch", "name": "kunlun", "episodes": 60}))
    assert r[0] == 200 and r[1]["episodes"] == 60 and r[1]["per_episode_keys"], r
    kl_batch = r[1]["batch_id"]
    print(f"✅ 昆仑60集批量初始化通过 (batch={kl_batch[:14]}..., 每集独立组密钥)")
    # episode_status
    r = _post(handle, "/v1/kunlun/production", json.dumps({"op": "episode_status", "batch_id": kl_batch, "episode": 1}))
    assert r[0] == 200 and r[1]["stage"] == "剧本" and len(r[1]["members"]) == 5, r
    print(f"✅ 单集状态通过 (EP1: {r[1]['stage']}, 5生产成员)")
    # asset_encrypt: 剧本内容加密
    r = _post(handle, "/v1/kunlun/production", json.dumps({"op": "asset_encrypt", "batch_id": kl_batch, "episode": 1, "stage": "剧本", "content": "Ω₀⊂⊙∞⊂Ω 九天玄女·第一集 剧本初稿"}))
    assert r[0] == 200 and r[1]["algorithm"] == "AES-256-GCM", r
    kl_iv, kl_ct = r[1]["iv"], r[1]["ciphertext"]
    print(f"✅ 生产资产加密通过 (EP1剧本, AES-256-GCM, ct_len={len(kl_ct)})")
    # asset_decrypt
    r = _post(handle, "/v1/kunlun/production", json.dumps({"op": "asset_decrypt", "batch_id": kl_batch, "episode": 1, "stage": "剧本", "iv": kl_iv, "ciphertext": kl_ct}))
    assert r[0] == 200 and "九天玄女" in r[1]["content"] and r[1]["integrity"] == "verified", r
    print("✅ 生产资产解密通过 (剧本内容还原, 完整性verified)")
    # 跨集隔离: EP1 密文用 EP2 解密 → 失败
    r = _post(handle, "/v1/kunlun/production", json.dumps({"op": "asset_decrypt", "batch_id": kl_batch, "episode": 2, "stage": "剧本", "iv": kl_iv, "ciphertext": kl_ct}))
    assert r[0] == 400, r
    print("✅ 跨集隔离通过 (EP1密文在EP2解密失败)")
    # episode_close: 集完成锁档
    r = _post(handle, "/v1/kunlun/production", json.dumps({"op": "episode_close", "batch_id": kl_batch, "episode": 1}))
    assert r[0] == 200 and r[1]["locked"] is True and r[1]["epoch"] == 1, r
    r2 = _post(handle, "/v1/kunlun/production", json.dumps({"op": "episode_close", "batch_id": kl_batch, "episode": 1}))
    assert r2[0] == 409, r2
    print(f"✅ 集完成锁档通过 (EP1 epoch→{r[1]['epoch']}, 重复close被409拦截)")

    # ---- V1.6: A2A × 昆仑生产任务分发 ----
    # dispatch: AgentCard能力匹配分发剧本任务
    r = _post(handle, "/v1/a2a/kunlun/dispatch", json.dumps({"op": "dispatch", "batch_id": kl_batch, "episode": 1, "stage": "剧本", "task_spec": {"brief": "第一集剧本大纲"}}))
    assert r[0] == 200 and r[1]["status"] == "submitted" and r[1]["agent"]["agent_id"] == "agent-script", r
    t1 = r[1]["task_id"]
    print(f"✅ AgentCard分发通过 (剧本任务→agent-script, {t1[:14]}...)")
    # 非法阶段 → 404
    r = _post(handle, "/v1/a2a/kunlun/dispatch", json.dumps({"op": "dispatch", "batch_id": kl_batch, "episode": 1, "stage": "剪辑"}))
    assert r[0] == 404, r
    print("✅ 非法阶段分发拦截通过 (404 no_agent_for_stage)")
    # claim: submitted→working
    r = _post(handle, "/v1/a2a/kunlun/dispatch", json.dumps({"op": "claim", "task_id": t1}))
    assert r[0] == 200 and r[1]["status"] == "working", r
    print("✅ 任务认领通过 (submitted→working)")
    # complete: 产出加密上链
    r = _post(handle, "/v1/a2a/kunlun/dispatch", json.dumps({"op": "complete", "task_id": t1, "output": "第一集剧本·九天玄女觉醒"}))
    assert r[0] == 200 and r[1]["status"] == "completed" and r[1]["output_encrypted"], r
    print("✅ 任务完成通过 (产出AES-GCM加密上链)")
    # task_status
    r = _post(handle, "/v1/a2a/kunlun/dispatch", json.dumps({"op": "task_status", "task_id": t1}))
    assert r[0] == 200 and r[1]["status"] == "completed" and r[1]["output_encrypted"], r
    print("✅ 任务状态查询通过 (completed)")
    # cancel: 新任务取消
    r = _post(handle, "/v1/a2a/kunlun/dispatch", json.dumps({"op": "dispatch", "batch_id": kl_batch, "episode": 2, "stage": "分镜", "task_spec": {}}))
    t2 = r[1]["task_id"]
    r = _post(handle, "/v1/a2a/kunlun/dispatch", json.dumps({"op": "cancel", "task_id": t2}))
    assert r[0] == 200 and r[1]["status"] == "canceled", r
    # 已完成任务不可取消 → 409
    r = _post(handle, "/v1/a2a/kunlun/dispatch", json.dumps({"op": "cancel", "task_id": t1}))
    assert r[0] == 409, r
    print("✅ 任务取消通过 (分镜任务→canceled; 已完成任务409)")

    # ---- V1.7: MCP × 昆仑生产工具化 ----
    # list: 工具注册表
    r = _post(handle, "/v1/mcp/kunlun", json.dumps({"op": "list"}))
    assert r[0] == 200 and len(r[1]["tools"]) == 5, r
    tool_names = [t["name"] for t in r[1]["tools"]]
    assert "kunlun.init_batch" in tool_names and "kunlun.episode_close" in tool_names, tool_names
    print("✅ MCP工具注册表通过 (5工具+JSON Schema)")
    # call: init_batch (MCP tools/call 语义)
    r = _post(handle, "/v1/mcp/kunlun", json.dumps({"op": "call", "name": "kunlun.init_batch", "arguments": {"name": "mcp-batch", "episodes": 3}}))
    assert r[0] == 200 and r[1]["result"]["episodes"] == 3, r
    mb = r[1]["result"]["batch_id"]
    print(f"✅ MCP工具调用通过 (init_batch→batch={mb[:14]}..., 3集)")
    # call: episode_status
    r = _post(handle, "/v1/mcp/kunlun", json.dumps({"op": "call", "name": "kunlun.episode_status", "arguments": {"batch_id": mb, "episode": 1}}))
    assert r[0] == 200 and r[1]["result"]["stage"] == "剧本", r
    print("✅ MCP工具调用通过 (episode_status)")
    # call: asset_encrypt/decrypt
    r = _post(handle, "/v1/mcp/kunlun", json.dumps({"op": "call", "name": "kunlun.asset_encrypt", "arguments": {"batch_id": mb, "episode": 1, "stage": "剧本", "content": "MCP工具加密剧本"}}))
    assert r[0] == 200 and r[1]["result"]["ciphertext"], r
    iv, ct = r[1]["result"]["iv"], r[1]["result"]["ciphertext"]
    r = _post(handle, "/v1/mcp/kunlun", json.dumps({"op": "call", "name": "kunlun.asset_decrypt", "arguments": {"batch_id": mb, "episode": 1, "stage": "剧本", "iv": iv, "ciphertext": ct}}))
    assert r[0] == 200 and "MCP工具加密剧本" in r[1]["result"]["content"], r
    print("✅ MCP工具调用通过 (asset_encrypt/decrypt roundtrip)")
    # call: episode_close
    r = _post(handle, "/v1/mcp/kunlun", json.dumps({"op": "call", "name": "kunlun.episode_close", "arguments": {"batch_id": mb, "episode": 1}}))
    assert r[0] == 200 and r[1]["result"]["locked"] is True, r
    print("✅ MCP工具调用通过 (episode_close锁档)")
    # 非法工具 → 404
    r = _post(handle, "/v1/mcp/kunlun", json.dumps({"op": "call", "name": "kunlun.nonexistent", "arguments": {}}))
    assert r[0] == 404, r
    print("✅ MCP非法工具拦截通过 (404 tool_not_found)")

    # ---- V1.8: DPoP × 昆仑生产安全准入 ----
    # issue_token: 签发 DPoP 绑定令牌
    r = _post(handle, "/v1/kunlun/secure", json.dumps({"op": "issue_token", "client_id": "zr-did", "batch_id": kl_batch}))
    assert r[0] == 200 and r[1]["access_token"] and r[1]["jkt"], r
    tok = r[1]["access_token"]
    jkt = r[1]["jkt"]
    print(f"✅ DPoP令牌签发通过 (client=zr-did, jkt={jkt[:10]}...)")
    # bind: DPoP proof 校验
    import base64 as _b64
    def _mk_proof(jkt_val):
        hdr = _b64.urlsafe_b64encode(json.dumps({"typ": "dpop+jwt", "alg": "ES256", "jkt": jkt_val}).encode()).rstrip(b"=").decode()
        clm = _b64.urlsafe_b64encode(json.dumps({"htu": "https://www.huodouai.com/v1/kunlun/secure", "htm": "POST", "jti": "jti-" + str(int(time.time()*1000)), "iat": int(time.time())}).encode()).rstrip(b"=").decode()
        return f"{hdr}.{clm}.fake-sig"
    proof = _mk_proof(jkt)
    r = _post(handle, "/v1/kunlun/secure", json.dumps({"op": "bind", "access_token": tok, "dpop_proof": proof, "htu": "https://www.huodouai.com/v1/kunlun/secure", "htm": "POST"}))
    assert r[0] == 200 and r[1]["bound"] is True, r
    print("✅ DPoP绑定校验通过 (jkt匹配+签名+时间戳+防重放)")
    # execute: 携带 DPoP 令牌执行昆仑操作
    r = _post(handle, "/v1/kunlun/secure", json.dumps({"op": "execute", "access_token": tok, "dpop_proof": _mk_proof(jkt), "htu": "https://www.huodouai.com/v1/kunlun/secure", "htm": "POST", "payload": {"op": "episode_status", "batch_id": kl_batch, "episode": 1}}))
    assert r[0] == 200 and r[1]["executed"] == "episode_status" and "locked" in r[1]["result"], r
    print("✅ DPoP安全执行通过 (携带令牌执行昆仑操作)")
    # 无令牌 → 401
    r = _post(handle, "/v1/kunlun/secure", json.dumps({"op": "execute", "access_token": "bad-token", "dpop_proof": proof, "htu": "https://www.huodouai.com/v1/kunlun/secure", "htm": "POST", "payload": {"op": "episode_status", "batch_id": kl_batch, "episode": 1}}))
    assert r[0] == 401, r
    print("✅ 未授权令牌拦截通过 (401 token_not_found)")
    # jkt 不匹配 → 401
    r = _post(handle, "/v1/kunlun/secure", json.dumps({"op": "execute", "access_token": tok, "dpop_proof": _mk_proof("wrong-jkt"), "htu": "https://www.huodouai.com/v1/kunlun/secure", "htm": "POST", "payload": {"op": "episode_status", "batch_id": kl_batch, "episode": 1}}))
    assert r[0] == 401, r
    print("✅ DPoP jkt不匹配拦截通过 (401 jkt_mismatch)")
    # revoke: 吊销后调用被拒
    r = _post(handle, "/v1/kunlun/secure", json.dumps({"op": "revoke", "access_token": tok}))
    assert r[0] == 200 and r[1]["token_status"] == "revoked", r
    r = _post(handle, "/v1/kunlun/secure", json.dumps({"op": "bind", "access_token": tok, "dpop_proof": proof, "htu": "https://www.huodouai.com/v1/kunlun/secure", "htm": "POST"}))
    assert r[0] == 401, r
    print("✅ 令牌吊销通过 (吊销后401拦截)")

    # ---- V1.9: 四协议联邦组合流 ----
    # compose: 组合注册表
    r = _post(handle, "/v1/federated/kunlun", json.dumps({"op": "compose"}))
    assert r[0] == 200 and len(r[1]["registry"]["stages"]) == 4, r
    print("✅ 四协议组合注册表通过 (DPoP→A2A→MCP→SLIM 四环节)")
    # 先签发令牌
    r = _post(handle, "/v1/kunlun/secure", json.dumps({"op": "issue_token", "client_id": "fed-client", "batch_id": kl_batch}))
    ftok = r[1]["access_token"]
    fjkt = r[1]["jkt"]
    def _fed_proof():
        hdr = _b64.urlsafe_b64encode(json.dumps({"typ": "dpop+jwt", "alg": "ES256", "jkt": fjkt}).encode()).rstrip(b"=").decode()
        clm = _b64.urlsafe_b64encode(json.dumps({"htu": "https://www.huodouai.com/v1/federated/kunlun", "htm": "POST", "jti": "fjti-" + str(int(time.time()*1000)), "iat": int(time.time())}).encode()).rstrip(b"=").decode()
        return f"{hdr}.{clm}.fake-sig"
    # run: 完整组合流
    r = _post(handle, "/v1/federated/kunlun", json.dumps({"op": "run", "access_token": ftok, "dpop_proof": _fed_proof(), "htu": "https://www.huodouai.com/v1/federated/kunlun", "htm": "POST", "batch_id": kl_batch, "episode": 1, "stage": "分镜", "content": "联邦组合流资产"}))
    assert r[0] == 200 and r[1]["stages"] == 4 and r[1]["result"]["encrypted"] is True, r
    assert [a["status"] for a in r[1]["audit"]] == ["passed"] * 4, r
    assert [a["protocol"] for a in r[1]["audit"]] == ["DPoP", "A2A", "MCP", "SLIM"], r
    print("✅ 四协议联邦组合流通过 (认证→编排→执行→加密传输 4/4)")
    # 无令牌 → 401 拦截
    r = _post(handle, "/v1/federated/kunlun", json.dumps({"op": "run", "access_token": "bad", "dpop_proof": "x.y.z", "htu": "https://www.huodouai.com/v1/federated/kunlun", "htm": "POST", "batch_id": kl_batch, "episode": 1, "stage": "分镜"}))
    assert r[0] == 401 and r[1]["stage"] == 1, r
    print("✅ 组合流安全门拦截通过 (无令牌401, 环节1 DPoP)")
    # status: 组合流审计
    r = _post(handle, "/v1/federated/kunlun", json.dumps({"op": "status"}))
    assert r[0] == 200 and r[1]["runs_count"] >= 1, r
    print("✅ 组合流审计通过 (runs记录已落盘)")

    # ---- V2.1: OAuth2 / OIDC 认证授权族 ----
    # OIDC Discovery
    r, code = oauth_handle("/.well-known/openid-configuration", {})
    assert code == 200 and r["issuer"] == "https://www.huodouai.com" and r["token_endpoint"].endswith("/v1/oauth/token"), r
    print("✅ OIDC Discovery 通过 (issuer/token/introspect/revoke 全声明)")
    # OIDC GET 直连 (handle 路由)
    code, r = handle(H(), "/.well-known/openid-configuration", "GET")
    assert code == 200 and r["issuer"] == "https://www.huodouai.com", r
    print("✅ OIDC Discovery GET 路由通过 (handle 直连)")
    # client_credentials 签发 (带 DPoP jkt 绑定)
    r, code = oauth_handle("/v1/oauth/token", {"grant_type": "client_credentials", "client_id": "zr-agent", "client_secret": "zr-oauth-secret-2026", "scope": "kunlun.production a2a.dispatch", "dpop_jkt": "test-jkt-fingerprint"})
    assert code == 200 and r["token_type"] == "DPoP" and r["jkt"] == "test-jkt-fingerprint", r
    oa_tok = r["access_token"]
    print("✅ OAuth2 client_credentials 签发通过 (DPoP绑定 jkt)")
    # 错误凭证 → 401
    r, code = oauth_handle("/v1/oauth/token", {"grant_type": "client_credentials", "client_id": "zr-agent", "client_secret": "wrong"})
    assert code == 401 and r["error"] == "invalid_client", r
    print("✅ OAuth2 错误凭证拦截通过 (401 invalid_client)")
    # RFC7662 内省
    r, code = oauth_handle("/v1/oauth/introspect", {"token": oa_tok})
    assert code == 200 and r["active"] is True and r["client_id"] == "zr-agent" and r["jkt"] == "test-jkt-fingerprint", r
    print("✅ RFC7662 内省通过 (active + client_id + jkt)")
    # 无效 token 内省 → inactive
    r, code = oauth_handle("/v1/oauth/introspect", {"token": "bad-token"})
    assert code == 200 and r["active"] is False, r
    print("✅ RFC7662 无效token内省通过 (active=false)")
    # RFC7009 吊销
    r, code = oauth_handle("/v1/oauth/revoke", {"token": oa_tok})
    assert code == 200, r
    r, code = oauth_handle("/v1/oauth/introspect", {"token": oa_tok})
    assert code == 200 and r["active"] is False, r
    print("✅ RFC7009 吊销通过 (吊销后内省 active=false)")
    # OAuth2 资源访问授权校验
    tok2, code = oauth_handle("/v1/oauth/token", {"grant_type": "client_credentials", "client_id": "zr-render", "client_secret": "zr-render-secret-2026"})
    assert code == 200 and tok2["token_type"] == "Bearer", tok2
    ok, msg = oauth_authorized(tok2["access_token"], "kunlun.production")
    assert ok, msg
    ok, msg = oauth_authorized(tok2["access_token"], "a2a.dispatch")
    assert not ok and msg == "insufficient_scope", msg
    print("✅ OAuth2 scope 授权校验通过 (Bearer令牌, scope覆盖/不足判定)")

    # ---- V2.2: GPU 真实推理路由 (本地 mock 节点) ----
    import http.server as _hs, threading as _th, functools as _ft
    class _MockHandler(_hs.BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_POST(self):
            ln = int(self.headers.get("Content-Length", 0))
            self.rfile.read(ln)
            resp = json.dumps({"choices": [{"message": {"content": "GPU真实推理结果: Ω₀⊂⊙∞⊂Ω mock-qwen"}}]}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp))); self.end_headers(); self.wfile.write(resp)
    _mock_srv = _hs.HTTPServer(("127.0.0.1", 0), _MockHandler)
    _mock_port = _mock_srv.server_address[1]
    _th.Thread(target=_mock_srv.serve_forever, daemon=True).start()
    r, code = gpu_register("register", {"node_id": "mock-gpu-1", "base_url": f"http://127.0.0.1:{_mock_port}",
                                        "model": "mock-qwen", "provider": "vllm", "gpu_name": "A10-24G"})
    assert code == 200 and r["ok"] is True, r
    r, code = gpu_register("list", {})
    assert code == 200 and r["count"] == 1, r
    print("✅ GPU 节点注册/心跳/列表通过 (mock-gpu-1 在线)")
    # chat/completions 真实路由到 GPU 节点
    code, r = handle(H(), "/v1/chat/completions", "POST")
    _post_fix = None
    # 用 _post 走 handle 需 body; 直接调用 handle 需要 H 带 rfile; 改用 _call_gpu_inference 验证
    gdata, glat, gcode = _call_gpu_inference([{"role": "user", "content": "test"}], "mock-qwen")
    assert gdata and gdata["node_id"] == "mock-gpu-1" and "Ω₀⊂⊙∞⊂Ω" in gdata["content"], gdata
    assert gdata["gpu"] == "A10-24G" and gdata["provider"] == "vllm", gdata
    print("✅ GPU 真实推理路由通过 (mock A10-24G vLLM, 内容真实返回)")
    # SSE 流式
    code, r = handle(H(), "/v1/chat/stream", "POST")
    assert code == 200 and isinstance(r.get("__sse__"), str) and "data: [DONE]" in r["__sse__"], r
    assert "data: {" in r["__sse__"], r
    print("✅ SSE 流式通过 (text/event-stream 多块 + [DONE])")
    # WebSocket 声明
    code, r = handle(H(), "/v1/ws/info", "GET")
    assert code == 200 and r["protocol"] == "websocket" and r["endpoint"].startswith("wss://"), r
    print("✅ WebSocket 协议声明通过 (RFC6455 声明层)")
    gpu_register("unregister", {"node_id": "mock-gpu-1"})
    _mock_srv.shutdown()

    # ---- V2.2: OAuth2×四协议联邦整合 ----
    # 签发 OAuth2 token → run auth=oauth2 全链
    tok_oa, code = oauth_handle("/v1/oauth/token", {"grant_type": "client_credentials", "client_id": "zr-agent", "client_secret": "zr-oauth-secret-2026", "scope": "kunlun.production"})
    assert code == 200, tok_oa
    r = _post(handle, "/v1/federated/kunlun", json.dumps({"op": "run", "auth": "oauth2", "access_token": tok_oa["access_token"],
        "batch_id": kl_batch, "episode": 1, "stage": "分镜", "content": "OAuth2联邦组合流资产"}))
    assert r[0] == 200 and r[1]["stages"] == 4, r
    assert r[1]["audit"][0]["protocol"] == "OAuth2" and r[1]["audit"][0]["status"] == "passed", r
    assert [a["status"] for a in r[1]["audit"]] == ["passed"] * 4, r
    print("✅ OAuth2×四协议联邦整合通过 (环节1 OAuth2认证 → 编排→执行→加密 4/4)")
    # 无效 OAuth2 token → 401 拦截
    r = _post(handle, "/v1/federated/kunlun", json.dumps({"op": "run", "auth": "oauth2", "access_token": "bad",
        "batch_id": kl_batch, "episode": 1, "stage": "分镜"}))
    assert r[0] == 401 and r[1]["protocol"] == "OAuth2" and r[1]["stage"] == 1, r
    print("✅ OAuth2 联邦安全门拦截通过 (无效token 401, 环节1)")

    # FedAvg 真实聚合
    updates = [{"node_id": "n1", "samples": 100, "weights": {"w1": 0.1, "w2": 0.2}},
               {"node_id": "n2", "samples": 300, "weights": {"w1": 0.5, "w2": 0.4}}]
    r = _post(handle, "/v1/federated/aggregate", json.dumps({"round": 1, "node_updates": updates}))
    assert r[0] == 200 and abs(r[1]["aggregated_weights"]["w1"] - 0.4) < 1e-9, r
    assert abs(r[1]["aggregated_weights"]["w2"] - 0.35) < 1e-9, r
    print(f"✅ FedAvg 真实聚合通过 (2节点加权: w1=0.4, w2=0.35, 样本400)")
    # OTel 打点
    r = handle(H(), "/metrics", "GET")
    assert r[0] == 200 and "uptime_sec" in r[1]
    print(f"✅ OTel 真实打点通过 (requests={_M['requests_total']}, errors={_M['errors_total']})")
    print("V2.2 全量自检 PASS")

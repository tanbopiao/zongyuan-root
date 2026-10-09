#!/usr/bin/env python3
"""
kernel_protocol_verify.py
配置文件完整性校验脚本（独立工具）
用于离线校验 meta_homo_protocol.lock.json 的 JSON 语法、SHA256 哈希与锚点完整性。
溯源：Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 本源根 Ω-TAN-7-001
用法：
  python3 kernel_protocol_verify.py                          # 校验默认配置文件
  python3 kernel_protocol_verify.py --file <路径>            # 校验指定配置文件
  python3 kernel_protocol_verify.py --hash <期望SHA256>      # 比对期望哈希
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

DID_ANCHOR = "DID-BR-000002"
ROOT_OMEGA_ANCHOR = "Ω-TAN-7-001"
DEFAULT_FILE = Path("./kernel/config/meta_homo_protocol.lock.json")
MANDATORY_FIELDS = ["snap_id", "proto_version", "status", "axioms", "identity", "double_verify", "task_schema"]


def calc_file_hash(file_path: Path) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            sha.update(block)
    return sha.hexdigest()


def verify_config(file_path: Path, expected_hash: str = None) -> dict:
    """离线校验配置文件，返回结构化校验报告"""
    result = {"file": str(file_path), "checks": [], "passed": True}

    # 1. 存在性
    if not file_path.exists():
        result["passed"] = False
        result["checks"].append({"name": "存在性", "ok": False, "detail": "文件不存在"})
        return result
    result["checks"].append({"name": "存在性", "ok": True, "detail": "文件存在"})

    # 2. JSON 语法
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        result["checks"].append({"name": "JSON语法", "ok": True, "detail": "解析成功"})
    except json.JSONDecodeError as e:
        result["passed"] = False
        result["checks"].append({"name": "JSON语法", "ok": False, "detail": f"解析失败: {e}"})
        return result

    # 3. SHA256 哈希
    file_hash = calc_file_hash(file_path)
    result["sha256"] = file_hash
    if expected_hash:
        ok = file_hash.lower() == expected_hash.lower()
        result["passed"] = result["passed"] and ok
        result["checks"].append({"name": "SHA256比对", "ok": ok, "detail": f"实际={file_hash[:16]}… 期望={expected_hash[:16]}…"})
    else:
        result["checks"].append({"name": "SHA256计算", "ok": True, "detail": f"{file_hash}"})

    # 4. 双锚点校验
    did_ok = cfg.get("DID") == DID_ANCHOR
    root_ok = cfg.get("root_omega") == ROOT_OMEGA_ANCHOR
    anchor_ok = did_ok and root_ok
    result["passed"] = result["passed"] and anchor_ok
    result["checks"].append({"name": "双锚点", "ok": anchor_ok,
                             "detail": f"DID={cfg.get('DID')} root={cfg.get('root_omega')}"})

    # 5. 字段完整性
    missing = [f for f in MANDATORY_FIELDS if f not in cfg]
    fields_ok = not missing
    result["passed"] = result["passed"] and fields_ok
    result["checks"].append({"name": "字段完整性", "ok": fields_ok, "detail": f"缺失={missing or '无'}"})

    # 6. 任务报文字段
    task_fields = cfg.get("task_schema", {}).get("mandatory_fields", [])
    task_ok = "meta_homo_root" in task_fields and "asset_did" in task_fields
    result["passed"] = result["passed"] and task_ok
    result["checks"].append({"name": "任务字段", "ok": task_ok, "detail": f"{len(task_fields)}个字段"})

    return result


def main():
    parser = argparse.ArgumentParser(description="同源协议固化配置完整性校验")
    parser.add_argument("--file", type=str, default=str(DEFAULT_FILE), help="配置文件路径")
    parser.add_argument("--hash", type=str, default=None, help="期望SHA256哈希")
    args = parser.parse_args()

    report = verify_config(Path(args.file), args.hash)
    print(f"{'='*52}")
    print(f"配置文件完整性校验报告")
    print(f"{'='*52}")
    print(f"文件: {report['file']}")
    print(f"SHA256: {report.get('sha256','-')}")
    print("-"*52)
    for c in report["checks"]:
        mark = "✅" if c["ok"] else "❌"
        print(f"  {mark} {c['name']}: {c['detail']}")
    print("-"*52)
    if report["passed"]:
        print("✅ 校验通过：配置完整、锚点一致、可加载")
        return 0
    print("❌ 校验失败：配置存在异常，禁止加载")
    return 1


if __name__ == "__main__":
    sys.exit(main())

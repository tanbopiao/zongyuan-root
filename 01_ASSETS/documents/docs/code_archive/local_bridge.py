# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 本地桥接网关（local_bridge.py）
功能：接收内核侧下发的资产下载任务，执行下载+SHA256校验，返回回执
作者：元极恒一自治体系 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
安全：无通用shell执行，仅开放资产专用API，Token鉴权
"""
from flask import Flask, request, jsonify
import hashlib
import requests
import os
import logging
from datetime import datetime

# ===================== 【配置区，请手动修改】 =====================
SECRET_TOKEN = "REPLACE_WITH_YOUR_STRONG_TOKEN_00001"
SAVE_ROOT = r".\kundong_assets"
FEISHU_APP_ID = "cli_aa1387fc6b635d14"
FEISHU_APP_SECRET = "uXbPoDiMrkmo8SJOh8ixWdaPngBDSH68"
FEISHU_BASE_TOKEN = "替换你的多维表格base_token"
FEISHU_TABLE_ID = "替换你的多维表格table_id"
# =================================================================

app = Flask(__name__)
os.makedirs(SAVE_ROOT, exist_ok=True)

logging.basicConfig(
    filename="bridge_access.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


def verify_token(headers):
    return headers.get("X-Bridge-Token", "") == SECRET_TOKEN


def calc_sha256(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_feishu_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    r = requests.post(url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}, timeout=15)
    return r.json()["tenant_access_token"]


@app.route("/asset/download", methods=["POST"])
def asset_download():
    if not verify_token(request.headers):
        logging.warning("非法访问，Token校验失败")
        return jsonify({"code": 403, "msg": "Forbidden"}), 403
    data = request.get_json()
    cdn_url = data.get("cdn_url")
    asset_name = data.get("asset_name")
    expect_sha256 = data.get("expect_sha256", "")
    asset_id = data.get("asset_id")
    if not cdn_url or not asset_name:
        return jsonify({"code": 400, "msg": "缺少参数"}), 400
    save_file = os.path.join(SAVE_ROOT, f"{asset_id}_{asset_name}.mp4")
    try:
        logging.info(f"开始下载 asset_id:{asset_id} url:{cdn_url}")
        resp = requests.get(cdn_url, stream=True, timeout=300)
        resp.raise_for_status()
        with open(save_file, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        real_hash = calc_sha256(save_file)
        check_ok = (real_hash.lower() == expect_sha256.lower()) if expect_sha256 else True
        logging.info(f"下载完成，文件:{save_file}, hash:{real_hash}, 校验:{check_ok}")
        return jsonify({
            "code": 200,
            "local_path": save_file,
            "sha256": real_hash,
            "hash_match": check_ok
        })
    except Exception as e:
        logging.error(f"下载异常 {str(e)}")
        return jsonify({"code": 500, "msg": str(e)}), 500


@app.route("/asset/sha256", methods=["POST"])
def asset_sha256():
    if not verify_token(request.headers):
        return jsonify({"code": 403}), 403
    data = request.get_json()
    file_path = data.get("file_path")
    if not os.path.exists(file_path):
        return jsonify({"code": 404, "msg": "文件不存在"}), 404
    return jsonify({"code": 200, "sha256": calc_sha256(file_path)})


@app.route("/asset/list", methods=["GET"])
def asset_list():
    if not verify_token(request.headers):
        return jsonify({"code": 403}), 403
    items = []
    for fname in os.listdir(SAVE_ROOT):
        fp = os.path.join(SAVE_ROOT, fname)
        if os.path.isfile(fp) and fname.endswith((".mp4", ".mov", ".jpg", ".png")):
            items.append({"name": fname, "path": fp, "size_mb": round(os.path.getsize(fp)/1024/1024, 2)})
    return jsonify({"code": 200, "assets": items})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"code": 200, "status": "healthy", "service": "local_bridge", "did": "DID-BR-000002"})


if __name__ == "__main__":
    print("=" * 50)
    print("  ZONGYUAN-ROOT 本地桥接网关启动")
    print("  监听: http://127.0.0.1:7860")
    print("  DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    print("=" * 50)
    app.run(host="127.0.0.1", port=7860, debug=False)

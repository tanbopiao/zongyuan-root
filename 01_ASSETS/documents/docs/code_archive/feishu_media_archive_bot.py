#!/usr/bin/env python3
"""
飞书机器人媒体归档入口 v2.0（长连接模式）
使用飞书官方SDK WebSocket长连接接收消息，无需公网URL
用户在豆包APP生成图片/视频后，转发到飞书群
机器人自动下载文件 → 上传到9133归档 → 回复归档URL
"""
import json
import time
import os
import requests
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# ========== 配置 ==========
APP_ID = "cli_aa1387fc6b635d14"
APP_SECRET = "uXbPoDiMrkmo8SJOh8ixWdaPngBDSH68"
ARCHIVE_API = "http://127.0.0.1:9133/api/media/upload"
HEALTH_PORT = 9134

# ========== 飞书客户端 ==========
client = lark.Client.builder() \
    .app_id(APP_ID) \
    .app_secret(APP_SECRET) \
    .log_level(lark.LogLevel.ERROR) \
    .build()

def send_text(chat_id, text):
    """发送文本消息"""
    request = CreateMessageRequest.builder() \
        .receive_id_type("chat_id") \
        .request_body(CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type("text")
            .content(json.dumps({"text": text}))
            .build()) \
        .build()
    response = client.im.v1.message.create(request)
    if not response.success():
        print(f"发消息失败: {response.code}, {response.msg}")

def download_image(image_key):
    """下载图片"""
    request = GetMessageResourceRequest.builder() \
        .message_id(image_key) \
        .type("image") \
        .build()
    response = client.im.v1.message_resource.get(request)
    if not response.success():
        return None, f"下载失败: {response.msg}"
    temp_path = f"/tmp/feishu_img_{int(time.time()*1000)}.jpg"
    with open(temp_path, "wb") as f:
        f.write(response.file.read())
    return temp_path, None

def download_file(file_key):
    """下载文件（视频等）"""
    request = GetMessageResourceRequest.builder() \
        .message_id(file_key) \
        .type("file") \
        .build()
    response = client.im.v1.message_resource.get(request)
    if not response.success():
        return None, f"下载失败: {response.msg}"
    filename = getattr(response, "filename", f"feishu_file_{int(time.time()*1000)}")
    temp_path = f"/tmp/{filename}"
    with open(temp_path, "wb") as f:
        f.write(response.file.read())
    return temp_path, None

def archive_to_9133(filepath, asset_name, category="other"):
    """上传到9133归档"""
    if not os.path.exists(filepath):
        return {"status": "error", "message": "文件不存在"}
    filename = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        files = {"file": (filename, f)}
        data = {
            "asset_name": asset_name,
            "category": category,
            "node_id": "feishu-bot-ws",
            "style": "飞书转发",
            "ip_owner": "火斗云智",
            "project": "飞书归档"
        }
        resp = requests.post(ARCHIVE_API, files=files, data=data, timeout=120)
        return resp.json()

def handle_message(ctx, event):
    """处理接收消息事件"""
    try:
        msg_type = event.message.message_type
        chat_id = event.message.chat_id
        message_id = event.message.message_id

        if msg_type == "image":
            content = json.loads(event.message.content)
            image_key = content.get("image_key", "")
            send_text(chat_id, "📥 收到图片，正在归档...")
            filepath, err = download_image(image_key)
            if err:
                send_text(chat_id, f"❌ 下载失败: {err}")
                return
            result = archive_to_9133(filepath, f"飞书图片_{message_id[:8]}", "other")
            _handle_result(chat_id, result, "图片")
            if os.path.exists(filepath):
                os.remove(filepath)

        elif msg_type == "file":
            content = json.loads(event.message.content)
            file_key = content.get("file_key", "")
            send_text(chat_id, "📥 收到文件，正在归档...")
            filepath, err = download_file(file_key)
            if err:
                send_text(chat_id, f"❌ 下载失败: {err}")
                return
            ext = os.path.splitext(filepath)[1].lower()
            is_video = ext in [".mp4", ".webm", ".mov", ".mkv"]
            category = "drama" if is_video else "other"
            result = archive_to_9133(filepath, f"飞书文件_{message_id[:8]}", category)
            _handle_result(chat_id, result, "文件")
            if os.path.exists(filepath):
                os.remove(filepath)

        elif msg_type == "text":
            send_text(chat_id,
                "🤖 媒体归档机器人\n\n"
                "直接发送图片或视频文件，我会自动归档到云端本地COS。\n\n"
                "支持：图片(jpg/png/webp)、视频(mp4/webm/mov)\n"
                "归档后返回永久访问URL，自动去重。")

    except Exception as e:
        print(f"处理消息出错: {e}")
        try:
            send_text(event.message.chat_id, f"❌ 处理出错: {str(e)[:50]}")
        except:
            pass

def _handle_result(chat_id, result, type_name):
    """处理归档结果并回复"""
    if result.get("status") == "archived":
        send_text(chat_id,
            f"✅ {type_name}归档完成\n"
            f"ID: {result.get('asset_id')}\n"
            f"大小: {result.get('file_size', 0)//1024}KB\n"
            f"URL: {result.get('access_url')}")
    elif result.get("status") == "duplicate":
        send_text(chat_id,
            f"🔄 {type_name}已存在（去重）\n"
            f"URL: {result.get('access_url')}")
    else:
        send_text(chat_id, f"❌ 归档失败: {result.get('message', '未知错误')}")

# ========== 健康检查HTTP服务 ==========
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "service": "feishu-media-archive-bot",
                "mode": "websocket-long-connection",
                "port": HEALTH_PORT
            }).encode())
        else:
            self.send_response(404)
            self.end_headers()
    def log_message(self, format, *args):
        pass

def start_health_server():
    server = HTTPServer(("0.0.0.0", HEALTH_PORT), HealthHandler)
    server.serve_forever()

# ========== 启动长连接 ==========
if __name__ == "__main__":
    threading.Thread(target=start_health_server, daemon=True).start()
    print(f"健康检查: 端口{HEALTH_PORT}")

    event_handler = lark.EventDispatcherHandler.builder() \
        .register_p2_im_message_receive_v1(handle_message) \
        .build()

    ws_client = lark.ws.Client(
        app_id=APP_ID,
        app_secret=APP_SECRET,
        event_handler=event_handler,
        log_level=lark.LogLevel.INFO
    )

    print("飞书媒体归档机器人启动（长连接模式）")
    ws_client.start()

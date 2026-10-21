#!/usr/bin/env python3
# 请求路由：按类型转发到不同内核
import requests

ROUTES = {
    "/v1/chat": ("http://127.0.0.1:18080", "主chat"),
    "/v1/image": ("http://127.0.0.1:18083", "图像"),
    "/v1/video": ("http://127.0.0.1:18083", "视频"),
    "/v1/gov": ("http://127.0.0.1:18084", "政务"),
    "/v1/usage": ("http://127.0.0.1:18087", "存储用量"),
}

def route(path):
    for prefix, (target, name) in ROUTES.items():
        if path.startswith(prefix):
            return target, name
    return "http://127.0.0.1:18080", "默认主"

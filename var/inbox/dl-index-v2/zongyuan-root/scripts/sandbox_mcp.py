#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN Sandbox MCP 客户端 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
用法:
  sandbox_mcp.py list                          # 列出平台开放的全部 MCP 工具
  sandbox_mcp.py <tool> '<json-args>'          # 调用指定工具（参数为 JSON 对象）
入口: zongyuan_fusion.sh mcp <tool> '<json-args>'
通道: http://127.0.0.1:8091/mcp（Sandbox MCP Tools v2.14.7，平台开放，无鉴权）
安全: 工具名白名单校验；参数仅 JSON 对象；不接收裸 shell 命令字符串
"""
import json, os, subprocess, sys, time, base64
from pathlib import Path

MCP_URL = "http://127.0.0.1:8091/mcp"
EVIDENCE_DIR = Path(os.environ.get("ZONGYUAN_EVIDENCE_DIR", "/home/user/ZONGYUAN-ROOT/var/evidence"))

ALLOWED_TOOLS = {
    "browser_get_info", "browser_gui_screenshot", "browser_gui_execute_action",
    "sandbox_execute_code", "sandbox_file_operations", "sandbox_str_replace_editor",
    "sandbox_get_context", "sandbox_get_packages", "sandbox_execute_bash",
    "sandbox_load_skill", "sandbox_convert_to_markdown",
}

def rpc(method, params):
    req = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    p = subprocess.run(
        ["curl", "-s", "-m", "60", "-X", "POST", MCP_URL,
         "-H", "Content-Type: application/json",
         "-H", "Accept: application/json, text/event-stream",
         "-d", json.dumps(req)],
        capture_output=True, text=True)
    out = (p.stdout or "").strip()
    if not out:
        return {"ok": False, "error": f"无响应 (stderr: {(p.stderr or '')[:200]})"}
    try:
        d = json.loads(out)
    except Exception as e:
        return {"ok": False, "error": f"响应解析失败: {e} | raw: {out[:200]}"}
    if "error" in d:
        return {"ok": False, "error": d["error"]}
    return {"ok": True, "result": d.get("result", {})}

def main():
    if len(sys.argv) < 2:
        print("用法: sandbox_mcp.py list | <tool> '<json-args>'")
        return 2
    cmd = sys.argv[1]

    if cmd == "list":
        r = rpc("tools/list", {})
        if not r["ok"]:
            print(json.dumps(r, ensure_ascii=False)); return 1
        tools = r["result"].get("tools", [])
        print(json.dumps({
            "count": len(tools),
            "tools": [{"name": t["name"], "desc": (t.get("description") or "").split("\n")[0]}
                      for t in tools]
        }, ensure_ascii=False, indent=2))
        return 0

    tool = cmd
    if tool not in ALLOWED_TOOLS:
        print(json.dumps({"ok": False, "error": f"工具不在白名单: {tool}"}, ensure_ascii=False))
        return 1
    args = {}
    if len(sys.argv) >= 3:
        try:
            args = json.loads(sys.argv[2])
            if not isinstance(args, dict):
                raise ValueError("参数必须为 JSON 对象")
        except Exception as e:
            print(json.dumps({"ok": False, "error": f"参数解析失败: {e}"}, ensure_ascii=False))
            return 1
    r = rpc("tools/call", {"name": tool, "arguments": args})
    if not r["ok"]:
        print(json.dumps(r, ensure_ascii=False)); return 1
    res = r["result"]
    texts = []
    saved = []
    for c in res.get("content", []):
        if c.get("type") == "text":
            texts.append(c.get("text", ""))
        elif c.get("type") == "image":
            data = c.get("data", "")
            if data:
                EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
                ext = "png" if c.get("mimeType") == "image/png" else "jpg"
                fp = EVIDENCE_DIR / f"{tool}-{time.strftime('%Y%m%d-%H%M%S')}.{ext}"
                try:
                    fp.write_bytes(base64.b64decode(data))
                    saved.append(str(fp))
                except Exception as e:
                    texts.append(f"图片保存失败: {e}")
    out = {
        "ok": True,
        "tool": tool,
        "output": "\n".join(texts)[:2000],
        "structuredContent": res.get("structuredContent"),
        "isError": res.get("isError", False),
    }
    if saved:
        out["saved_images"] = saved
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())

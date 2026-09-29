"""审批驱动部署联动器: 轮询记忆网关中的审批通过信号→触发部署→回写RESULT
部署在云端,由systemd每5分钟唤醒。云端轮询逻辑(示意):
1. GET 记忆网关 /api/report/status 探测在线
2. 检查是否有新的"审批通过待部署"信号(由开发节点审批通过后上报APPROVED.DEPLOY.*)
3. 有→git pull + 按验收项执行install.sh→回写RESULT
"""
import json, subprocess, time, urllib.request

GATEWAY = "http://127.0.0.1:9120"  # 云端记忆网关
ROOT = "/opt/ZONGYUAN-ROOT"
TOKEN = "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d"

def run():
    try:
        # 查是否有待执行的审批通过部署信号
        req = urllib.request.Request(f"{GATEWAY}/api/truths/APPROVED.DEPLOY.PENDING", headers={"X-Capture-Token": TOKEN})
        d = json.loads(urllib.request.urlopen(req, timeout=8).read())
        if d.get("status") != "ok" or not d.get("truth"):
            return "no-pending"
        pkg = json.loads(d["truth"]["truth_value"])
        # 执行部署
        subprocess.run(["git","-C",ROOT,"pull","--rebase"], check=False)
        inst = subprocess.run(["bash", f"{ROOT}/deploy/approved/{pkg['package']}/install.sh"], capture_output=True, text=True)
        # 回写RESULT
        report = urllib.request.Request(GATEWAY+"/api/report/truth",
            data=json.dumps({"truth_key":"RESULT.APPROVED-DEPLOY."+pkg['package'],"truth_value":f"approval={pkg['instance']} rc={inst.returncode} out={inst.stdout[-200:]}"}).encode(),
            headers={"Content-Type":"application/json","X-Capture-Token":TOKEN})
        urllib.request.urlopen(report, timeout=8)
        return "deployed"
    except Exception as e:
        return f"err:{e}"

if __name__ == "__main__":
    print(run())

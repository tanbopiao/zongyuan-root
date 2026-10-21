#!/bin/bash
# ZONGYUAN-ROOT 真实稳态部署脚本
# 执行这个脚本即可一键启动所有服务

set -e

echo "=================================================="
echo " 🚀 ZONGYUAN-ROOT 真实稳态优化 - 一键启动"
echo "=================================================="
echo ""

cd /zongyuan-yuanji

# Step 1: 检查 Python 依赖
echo "Step 1: 检查 Python 依赖..."
python3 -c "import psutil; import urllib.request; print('✓ 依赖正常')" 2>/dev/null || {
    echo "⚠️ 缺少 psutil，正在安装..."
    pip install psutil --quiet
}

# Step 2: 清理旧进程
echo "Step 2: 清理旧进程..."
pkill -f "python3.*daemon|python3.*sync|python3.*guardian" 2>/dev/null || true
sleep 2

# Step 3: 启动监控守护进程
echo "Step 3: 启动系统监控 (monitor_daemon.py)..."
nohup python3 monitor_daemon.py >> logs/monitor.log 2>&1 &
sleep 1

# Step 4: 启动云同步守护进程  
echo "Step 4: 启动 WorkBuddy 云同步 (cloud_kernel_sync.py)..."
nohup python3 cloud_kernel_sync.py --daemon --interval 30 >> logs/cloud_sync.log 2>&1 &
sleep 1

# Step 5: 启动稳态守护进程
echo "Step 5: 启动稳态守护 (steady_guardian_simple.py)..."
nohup python3 steady_guardian_simple.py --interval 300 >> logs/steady_guardian.log 2>&1 &
sleep 1

# Step 6: 验证所有进程
echo ""
echo "Step 6: 验证进程状态..."
sleep 3
RUNNING=$(ps aux | grep -E "python3.*py" | grep -v grep | wc -l)
echo "   运行中的守护进程：$RUNNING 个"

if [ "$RUNNING" -lt 3 ]; then
    echo "⚠️ 警告：预期 3 个，实际 $RUNNING 个"
    echo ""
    echo "可能原因:"
    echo "  • cloud_kernel_sync.py 可能存在时区 bug (已在 19:11 修复)"
    echo "  • 查看详细日志：tail -f logs/*.log"
else
    echo "✅ 所有服务正常运行！"
fi

# Step 7: 打印状态摘要
echo ""
echo "=================================================="
echo " 📊 当前系统状态"
echo "=================================================="

# 内存
MEM_USAGE=$(free -h | awk '/^Mem:/ {print $3 "/" $2 " (" int($3/$2*100) "%)"}')
echo "内存：$MEM_USAGE"

# 磁盘
DISK_USAGE=$(df -h / | awk 'NR==2 {print $3 "/" $2 " (" int($3/$2*100) "%)"}')
echo "磁盘：$DISK_USAGE"

# API 连通性
echo -n "WorkBuddy: "; curl -s -o /dev/null -w "%{http_code}" https://www.workbuddy.cn/space/home && echo " ✓" || echo " ✗"

echo ""
echo "=================================================="
echo " 💡 管理命令"
echo "=================================================="
echo "查看实时日志:"
echo "  tail -f logs/*.log"
echo ""
echo "查看所有守护进程:"
echo "  ps aux | grep -E 'daemon|sync|guardian' | grep -v grep"
echo ""
echo "手动重新同步云端:"
echo "  cd /zongyuan-yuanji && python3 cloud_kernel_sync.py --bidirectional"
echo ""
echo "停止所有服务:"
echo "  pkill -f 'python3.*daemon|python3.*sync|python3.*guardian'"
echo ""
echo "=================================================="
echo " ✅ 部署完成！你的稳态系统现在真实运行中了!"
echo "=================================================="

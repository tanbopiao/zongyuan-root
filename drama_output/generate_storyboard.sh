#!/bin/bash
# AIOS分镜生成脚本：调用AIOS工作流生成分镜JSON并保存
# 用法: ./generate_storyboard.sh <主题> <集号>
TOPIC="$1"
EP="$2"
OUT="/opt/ZONGYUAN-ROOT/drama_output/storyboards/EP${EP}_storyboard.json"

echo "=== AIOS分镜生成 ==="
echo "主题: $TOPIC"
echo "集号: EP$EP"
echo "输出: $OUT"

# 调用AIOS短剧工作流(剧本师+分镜师两步)
RESULT=$(curl -s -X POST http://127.0.0.1:8765/api/v1/agents/workflows/wf-adc94c76/execute \
  -H "Content-Type: application/json" \
  -d "{\"input\":{\"topic\":\"$TOPIC\",\"episode\":$EP,\"shots\":5,\"duration\":10}}" \
  --max-time 180 2>/dev/null)

echo "$RESULT" > /tmp/aios_wf_result.json
echo "AIOS返回: $(echo "$RESULT" | wc -c)字节"

# 提取分镜师的输出(步骤2)作为分镜JSON
python3 << "PYEOF"
import json, re, sys
try:
    d=json.load(open("/tmp/aios_wf_result.json"))
    steps=d.get("steps_executed",[])
    # 找分镜步骤的输出
    storyboard_text = ""
    for s in steps:
        if "分镜" in s.get("step_name","") or s.get("step_id")=="s2":
            storyboard_text = str(s.get("output",""))
            break
    if not storyboard_text and steps:
        storyboard_text = str(steps[-1].get("output",""))
    # 尝试从输出中提取JSON
    json_match = re.search(r"\{[\s\S]*\}", storyboard_text)
    if json_match:
        try:
            sb = json.loads(json_match.group())
            ep = sys.argv[1] if len(sys.argv)>1 else "01"
            out = f"/opt/ZONGYUAN-ROOT/drama_output/storyboards/EP{ep}_storyboard.json"
            json.dump(sb, open(out,"w"), ensure_ascii=False, indent=2)
            print("分镜JSON已保存:", out)
            print("镜头数:", len(sb.get("episodes",[{}])[0].get("shots",[])) if sb.get("episodes") else "?")
        except:
            print("JSON解析失败，保存原始文本")
            with open("/tmp/aios_storyboard_raw.txt","w") as f:
                f.write(storyboard_text)
    else:
        print("未找到JSON，原始输出前200字:", storyboard_text[:200])
except Exception as e:
    print("处理失败:", e)
PYEOF

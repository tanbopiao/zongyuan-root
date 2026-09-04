#!/bin/bash
# ZONGYUAN-ROOT 模块一键注册脚本
set -e

MODULES_FILE="/www/wwwroot/huodouai.com/modules.json"
ID=""
NAME=""
URL=""
ICON="📦"
DESC=""
CATEGORY="system"
VERSION="1.0"
FEATURED=0

while [[ $# -gt 0 ]]; do
  case $1 in
    --id) ID="$2"; shift 2 ;;
    --name) NAME="$2"; shift 2 ;;
    --url) URL="$2"; shift 2 ;;
    --icon) ICON="$2"; shift 2 ;;
    --desc) DESC="$2"; shift 2 ;;
    --category) CATEGORY="$2"; shift 2 ;;
    --version) VERSION="$2"; shift 2 ;;
    --featured) FEATURED=1; shift ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

if [ -z "$ID" ] || [ -z "$NAME" ] || [ -z "$URL" ]; then
  echo "❌ 缺少必填参数: --id, --name, --url"
  exit 1
fi

EXISTS=$(python3 -c "
import json
d = json.load(open('$MODULES_FILE'))
print('yes' if any(m['id']=='$ID' for m in d['modules']) else 'no')
")

if [ "$EXISTS" = "yes" ]; then
  echo "⚠️  模块 $ID 已存在，执行更新..."
else
  echo "➕ 注册新模块 $ID..."
fi

python3 << PYEOF
import json
d = json.load(open("$MODULES_FILE"))
new_mod = {
    "id": "$ID", "name": "$NAME", "url": "$URL",
    "icon": "$ICON", "desc": "$DESC", "category": "$CATEGORY",
    "status": "online", "version": "$VERSION", "featured": bool($FEATURED)
}
found = False
for i, m in enumerate(d["modules"]):
    if m["id"] == "$ID":
        d["modules"][i] = new_mod
        found = True
        break
if not found:
    d["modules"].append(new_mod)
d["last_updated"] = "$(date -Iseconds)"
json.dump(d, open("$MODULES_FILE", "w"), ensure_ascii=False, indent=2)
print(f"✅ 模块 $ID 已{'更新' if found else '注册'}，当前共 {len(d['modules'])} 个模块")
PYEOF

echo ""
echo "📊 当前模块统计:"
python3 -c "
import json
d = json.load(open('$MODULES_FILE'))
cats = {}
for m in d['modules']:
    cats[m['category']] = cats.get(m['category'], 0) + 1
print(f'  总计: {len(d[\"modules\"])} 个模块')
for c, n in sorted(cats.items()):
    print(f'  {c}: {n}个')
"
echo "🌐 https://www.huodouai.com/#products"

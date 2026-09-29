#!/bin/bash
# Lv10自组织文明：自动发现新模块并注册到modules.json
# 用法: ./auto_discover_modules.sh
WEBROOT="/www/wwwroot/huodouai.com"
MODULES_JSON="$WEBROOT/modules.json"
REGISTER_SCRIPT="/opt/ZONGYUAN-ROOT/register_module.sh"

echo "=== 自组织模块发现 ==="
echo "扫描目录: $WEBROOT"

# 发现drama子目录下的新HTML页面
find "$WEBROOT/drama" -name "*.html" -type f | while read f; do
    rel="${f#$WEBROOT/}"
    name=$(basename "$f" .html)
    # 检查是否已注册
    if ! grep -q "\"$name\"" "$MODULES_JSON" 2>/dev/null; then
        echo "发现新模块: $rel"
        # 自动注册（简化版，不调用完整脚本避免参数问题）
        python3 - "$MODULES_JSON" "$name" "$rel" << 'PYEOF'
import json, sys
modules_file = sys.argv[1]
name = sys.argv[2]
url = sys.argv[3]
try:
    with open(modules_file) as f:
        data = json.load(f)
    modules = data.get('modules', data) if isinstance(data, dict) else data
    if isinstance(modules, list):
        exists = any(m.get('id') == name or m.get('url') == url for m in modules)
        if not exists:
            modules.append({
                "id": name,
                "name": name.replace('-', ' ').title(),
                "url": "/" + url,
                "icon": "📄",
                "desc": "自动发现模块",
                "category": "dev",
                "version": "1.0",
                "status": "online",
                "auto_discovered": True
            })
            data['modules'] = modules if isinstance(data, dict) else modules
            with open(modules_file, 'w') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  自动注册: {name}")
except Exception as e:
    print(f"  注册失败: {e}")
PYEOF
    fi
done

echo "=== 自动发现完成 ==="
echo "当前模块数: $(python3 -c "import json;d=json.load(open('$MODULES_JSON'));print(len(d.get('modules',d)) if isinstance(d,dict) else len(d))")"

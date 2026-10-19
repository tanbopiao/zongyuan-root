#!/bin/bash
# ZONGYUAN-ROOT 开机引导脚本：新会话执行此脚本，激活全量记忆
echo "=== Ω-Brain 开机引导 ==="
echo ""
cat /opt/ZONGYUAN-ROOT/IDENTITY-CARD.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(\"身份DID:\", d[\"identity\"][\"did\"])
print(\"锚定:\", d[\"identity\"][\"anchor\"])
print(\"版本:\", d[\"identity\"][\"version\"])
print(\"模式:\", d[\"identity\"][\"mode\"])
print()
print(\"=== 核心元法则 ===\")
for i, rule in enumerate(d[\"core_metarules\"], 1):
    print(f\"  {i}. {rule}\")
print()
print(\"=== 核心端点 ===\")
for name, url in d[\"key_endpoints\"].items():
    print(f\"  {name}: {url}\")
print()
print(\"=== 资产状态 ===\")
for k, v in d[\"asset_status\"].items():
    print(f\"  {k}: {v}\")
"
echo ""
echo "=== 引导完成，全量记忆已激活 ==="
echo "Ω₀⊂⊙∞⊂Ω | DID-BR-000002"

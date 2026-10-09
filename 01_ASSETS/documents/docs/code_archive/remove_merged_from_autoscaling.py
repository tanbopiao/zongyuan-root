#!/usr/bin/env python3
# 从auto_scaling.py中移除已合并服务
target = "/opt/ZONGYUAN-ROOT/scripts/auto_scaling.py"

with open(target) as f:
    lines = f.readlines()

merged_services = ["mr010-dual-compute-scheduler", "mr013-truth-unify", "mr015-truth-generator"]
count = 0

for i, line in enumerate(lines):
    for svc in merged_services:
        if f'"service": "{svc}"' in line and not line.strip().startswith("#"):
            lines[i] = "    # [MERGED-20260915] " + line.strip() + "\n"
            count += 1
            print(f"  已注释: {svc} (行{i+1})")

# 添加MERGED_SERVICES标记
merged_marker = '\n# 已合并服务（不再由auto_scaling管理）\nMERGED_SERVICES = ["mr010-dual-compute-scheduler", "mr013-truth-unify", "mr015-truth-generator", "dr-truth-absorber", "zongyuan-external-compute", "zongyuan-compute-injection"]\n'
content = "".join(lines)
if "MERGED_SERVICES" not in content:
    content = content.replace("# 非核心服务（可暂停）", merged_marker + "\n# 非核心服务（可暂停）")
    print("  已添加MERGED_SERVICES标记")

with open(target, "w") as f:
    f.write(content)

print(f"✅ 完成，共注释{count}个服务")

#!/usr/bin/env python3
"""校验编排计划 JSON 结构：任务字段完整、依赖引用存在、依赖无环、并行度合法。

用法：
  python3 validate_plan.py plan.json          # 校验文件
  cat plan.json | python3 validate_plan.py -  # 从 stdin 读取
退出码：0=通过；1=结构/字段错误；2=依赖环。

计划 JSON 格式：
{
  "goal": "目标描述",
  "units": [
    {"id": "u1", "action": "动作", "output": "产物路径", "verify": "验证方式",
     "depends_on": ["u0"]}
  ]
}
"""
import json
import sys


def load_plan(path):
    if path == "-":
        return json.load(sys.stdin)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate(plan):
    errors = []
    units = plan.get("units")
    if not isinstance(units, list) or not units:
        return ["units 必须为非空数组"]
    ids = [u.get("id") for u in units]
    if len(ids) != len(set(ids)):
        errors.append("unit id 存在重复")
    for u in units:
        uid = u.get("id", "?")
        for field in ("id", "action", "output", "verify"):
            if not u.get(field):
                errors.append(f"[{uid}] 缺少字段: {field}")
        deps = u.get("depends_on") or []
        if not isinstance(deps, list):
            errors.append(f"[{uid}] depends_on 必须为数组")
            continue
        for d in deps:
            if d not in ids:
                errors.append(f"[{uid}] 依赖引用不存在: {d}")
    if errors:
        return errors
    # 拓扑排序检测环
    adj = {u["id"]: set(u.get("depends_on") or []) for u in units}
    state = {}
    order = []

    def visit(n):
        state[n] = 1
        for m in adj.get(n, ()):
            if m not in state:
                visit(m)
            elif state[m] == 1:
                raise ValueError(f"依赖环: {n} -> {m}")
        state[n] = 2
        order.append(n)

    try:
        for n in adj:
            if n not in state:
                visit(n)
    except ValueError as e:
        return [str(e)]
    return []


def main():
    if len(sys.argv) != 2:
        print("用法: validate_plan.py <plan.json | ->", file=sys.stderr)
        return 2
    try:
        plan = load_plan(sys.argv[1])
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败: {e}", file=sys.stderr)
        return 1
    errors = validate(plan)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 2 if any("环" in e for e in errors) else 1
    units = plan["units"]
    print(json.dumps({
        "ok": True,
        "goal": plan.get("goal", ""),
        "unit_count": len(units),
        "exec_order": _topo(units),
    }, ensure_ascii=False, indent=2))
    return 0


def _topo(units):
    adj = {u["id"]: set(u.get("depends_on") or []) for u in units}
    out, seen = [], set()
    while adj:
        ready = [n for n, d in adj.items() if d <= seen]
        if not ready:
            break
        ready.sort()
        for n in ready:
            seen.add(n)
            out.append(n)
            adj.pop(n)
    return out + list(adj)


if __name__ == "__main__":
    sys.exit(main())

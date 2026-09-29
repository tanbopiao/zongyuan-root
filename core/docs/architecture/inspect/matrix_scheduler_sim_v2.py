#!/usr/bin/env python3
"""
矩阵组织资源调度原型 v2 - 优化版
优化点：截止日仲裁 + 闲置资源自动补位 + 次优匹配
DID-BR-000002 | ZONGYUAN-ROOT
"""
import json
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Resource:
    rid: str
    name: str
    func_dept: str
    skills: list
    max_parallel: int = 2
    current_load: int = 0
    auto_bind: bool = False  # 自动绑定项目（闲置资源激活）

@dataclass
class Project:
    pid: str
    name: str
    priority: int
    deadline: str
    required_skills: list
    team_size: int
    assigned: list = field(default_factory=list)
    status: str = "pending"

# ===== 优化后资源池（v2）=====
RESOURCE_POOL = [
    Resource("R01", "智谱GLM-4-Flash", "模型工程组", ["文本生成","摘要","分类","提示词初稿"], 3),
    Resource("R02", "通义千问Max",     "模型工程组", ["深度推理","文档解析","多模态"], 2),
    Resource("R03", "火山豆包Pro-K2",  "模型工程组", ["中文创意","剧本生成","东方神话"], 3),  # max从2→3
    Resource("R03B","火山豆包Pro-K3",  "模型工程组", ["中文创意","剧本生成"], 2),               # 新增Key3
    Resource("R04", "提示词精修组",    "提示词组",   ["提示词精修","分镜设计","角色一致性"], 2),
    Resource("R05", "视觉关键帧A",     "视觉组",     ["国风绘画","神女角色","岩彩风格"], 1),
    Resource("R06", "视觉关键帧B",     "视觉组",     ["场景原画","PV分镜","色调控制"], 1),
    Resource("R06B","视觉关键帧C",     "视觉组",     ["短剧分镜","角色一致性","场景延展"], 1), # 新增C
    Resource("R07", "运维内核组",      "运维组",     ["Git同步","快照锁档","巡检脚本"], 2),
    Resource("R08", "合规锁档组",      "合规组",     ["哈希校验","审计日志","飞书归档"], 2, auto_bind=True),
    Resource("R09", "IMA知识库",       "知识组",     ["RAG检索","笔记CRUD","文件上传"], 3, auto_bind=True),
    Resource("R10", "百度网盘",        "存储组",     ["文件备份","批量传输"], 2, auto_bind=True),
]

PROJECTS = [
    Project("P01", "太阴月神PV",      1, "2026-09-15", ["中文创意","国风绘画","剧本生成"], 3),
    Project("P02", "九天玄女EP05",    2, "2026-09-20", ["剧本生成","分镜设计","神女角色"], 3),
    Project("P03", "RAG知识库工程",    3, "2026-09-25", ["RAG检索","文档解析","摘要"], 2),
    Project("P04", "短剧量产线",      2, "2026-09-30", ["剧本生成","分镜设计","色调控制","东方神话"], 4),
    Project("P05", "运维巡检自动化",  1, "2026-09-12", ["Git同步","快照锁档","巡检脚本"], 2),
]

class MatrixSchedulerV2:
    def __init__(self, resources, projects):
        self.resources = {r.rid: r for r in resources}
        self.projects = {p.pid: p for p in projects}
        self.assignments = []
        self.conflicts = []

    def _match_score(self, res, proj):
        """计算匹配分"""
        return len(set(res.skills) & set(proj.required_skills))

    def _find_matches(self, proj, min_score=1):
        """找匹配资源，返回排序后的候选"""
        candidates = []
        for rid, res in self.resources.items():
            if res.current_load >= res.max_parallel:
                continue
            score = self._match_score(res, proj)
            if score >= min_score:
                candidates.append((score, res))
        candidates.sort(key=lambda x: (-x[0], x[1].current_load))
        return [r for _, r in candidates]

    def _check_conflict(self, res, proj):
        """冲突检测：同优先级项目争抢同资源"""
        for a in self.assignments:
            if a["resource"] == res.rid:
                existing = self.projects[a["project"]]
                if existing.priority == proj.priority:
                    # 优化：截止日近的优先，不产生硬冲突，仅记录
                    self.conflicts.append({
                        "resource": res.name,
                        "project_a": existing.name,
                        "project_b": proj.name,
                        "resolution": "截止日优先仲裁"
                    })
                    return True
        return False

    def schedule(self):
        """优化调度：截止日排序 + 次优补位 + 自动绑定"""
        # 按优先级+截止日排序
        sorted_projects = sorted(self.projects.values(),
                               key=lambda p: (p.priority, p.deadline))

        for proj in sorted_projects:
            matches = self._find_matches(proj)
            assigned = 0

            for res in matches:
                if assigned >= proj.team_size:
                    break
                self._check_conflict(res, proj)
                self.assignments.append({
                    "project": proj.pid, "resource": res.rid,
                    "skill": list(set(res.skills) & set(proj.required_skills))[0]
                })
                res.current_load += 1
                proj.assigned.append(res.name)
                assigned += 1

            # 次优补位：如果还没满，放宽匹配条件
            if assigned < proj.team_size:
                loose_matches = self._find_matches(proj, min_score=0)
                for res in loose_matches:
                    if assigned >= proj.team_size:
                        break
                    if res.name in proj.assigned:
                        continue
                    self.assignments.append({
                        "project": proj.pid, "resource": res.rid,
                        "skill": "次优补位"
                    })
                    res.current_load += 1
                    proj.assigned.append(res.name)
                    assigned += 1

            proj.status = "assigned" if assigned >= proj.team_size else "PARTIAL"

        # 自动绑定：auto_bind资源自动接入所有项目
        for proj in self.projects.values():
            for res in self.resources.values():
                if res.auto_bind and res.name not in proj.assigned:
                    proj.assigned.append(f"[自动]{res.name}")

    def report(self):
        print("=" * 70)
        print("矩阵组织资源调度 v2（优化版）仿真报告")
        print(f"时间: {datetime.now().isoformat()}")
        print("=" * 70)

        print("\n【项目分配结果】")
        for proj in sorted(self.projects.values(), key=lambda p: p.priority):
            icon = "✅" if proj.status == "assigned" else "⚠️"
            print(f"\n{icon} [{proj.pid}] {proj.name} (P{proj.priority}, 截止:{proj.deadline})")
            print(f"   {', '.join(proj.assigned)}")
            print(f"   状态: {proj.status}")

        print("\n【资源负载】")
        for rid, res in self.resources.items():
            pct = res.current_load / res.max_parallel * 100
            bar = "█" * res.current_load + "░" * (res.max_parallel - res.current_load)
            auto = " [自动]" if res.auto_bind else ""
            print(f"  {res.name:18s}{auto} [{bar}] {res.current_load}/{res.max_parallel} ({pct:.0f}%)")

        print("\n【冲突仲裁】")
        if self.conflicts:
            for c in self.conflicts:
                print(f"  ⚖️ {c['resource']}: {c['project_a']} vs {c['project_b']} → {c['resolution']}")
        else:
            print("  ✅ 无冲突")

        full = sum(1 for p in self.projects.values() if p.status == "assigned")
        avg_util = sum(r.current_load / r.max_parallel for r in self.resources.values()) / len(self.resources) * 100
        print(f"\n【统计】满载项目: {full}/{len(self.projects)} | 平均利用率: {avg_util:.1f}% | 冲突: {len(self.conflicts)}")

        return {"full": full, "avg_util": avg_util, "conflicts": len(self.conflicts)}

if __name__ == "__main__":
    scheduler = MatrixSchedulerV2(RESOURCE_POOL, PROJECTS)
    scheduler.schedule()
    stats = scheduler.report()

    result = {"snapshot": "SNAP-20260909-MATRIX-SIM-V2", "stats": stats}
    with open("/tmp/matrix_sim_v2.json", "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("\n✅ v2仿真完成 | /tmp/matrix_sim_v2.json")

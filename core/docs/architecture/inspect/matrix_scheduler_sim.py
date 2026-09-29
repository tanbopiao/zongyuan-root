#!/usr/bin/env python3
"""
矩阵组织资源调度原型 - 火斗云智AIOS
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω
仿真测试：职能池×项目矩阵，任务分配+冲突检测+优先级调度
"""
import json
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

# ===================== 数据模型 =====================

@dataclass
class Resource:
    """职能池资源（人/模型/算力）"""
    rid: str
    name: str
    func_dept: str        # 职能部门
    skills: list          # 技能标签
    max_parallel: int = 2 # 最大并行项目数
    current_load: int = 0 # 当前负载
    available: bool = True

@dataclass
class Project:
    """横向项目"""
    pid: str
    name: str
    priority: int         # 1=最高
    deadline: str
    required_skills: list # 需要的技能
    team_size: int        # 需要人数
    assigned: list = field(default_factory=list)
    status: str = "pending"

@dataclass
class Assignment:
    """分配记录"""
    project_id: str
    resource_id: str
    skill_used: str
    assigned_at: str
    conflict: bool = False

# ===================== 职能池 =====================
RESOURCE_POOL = [
    Resource("R01", "智谱GLM-4-Flash", "模型工程组", ["文本生成","摘要","分类"], 3),
    Resource("R02", "通义千问Max",     "模型工程组", ["深度推理","文档解析","多模态"], 2),
    Resource("R03", "火山豆包Pro",     "模型工程组", ["中文创意","剧本生成","东方神话"], 2),
    Resource("R04", "提示词资产组",    "提示词组",   ["提示词工程","分镜设计","角色一致性"], 2),
    Resource("R05", "视觉关键帧A",     "视觉组",     ["国风绘画","神女角色","岩彩风格"], 1),
    Resource("R06", "视觉关键帧B",     "视觉组",     ["场景原画","PV分镜","色调控制"], 1),
    Resource("R07", "运维内核组",      "运维组",     ["Git同步","快照锁档","巡检脚本"], 2),
    Resource("R08", "合规锁档组",      "合规组",     ["哈希校验","审计日志","飞书归档"], 2),
    Resource("R09", "IMA知识库",       "知识组",     ["RAG检索","笔记CRUD","文件上传"], 3),
    Resource("R10", "百度网盘",        "存储组",     ["文件备份","批量传输","记忆恢复"], 2),
]

# ===================== 项目实例 =====================
PROJECTS = [
    Project("P01", "太阴月神PV",          priority=1, deadline="2026-09-15",
            required_skills=["中文创意","国风绘画","剧本生成"], team_size=3),
    Project("P02", "九天玄女EP05",        priority=2, deadline="2026-09-20",
            required_skills=["剧本生成","分镜设计","神女角色"], team_size=3),
    Project("P03", "RAG知识库工程",        priority=3, deadline="2026-09-25",
            required_skills=["RAG检索","文档解析","摘要"], team_size=2),
    Project("P04", "短剧量产线",          priority=2, deadline="2026-09-30",
            required_skills=["剧本生成","分镜设计","色调控制","东方神话"], team_size=4),
    Project("P05", "运维巡检自动化",      priority=1, deadline="2026-09-12",
            required_skills=["Git同步","快照锁档","巡检脚本"], team_size=2),
]

# ===================== 调度引擎 =====================

class MatrixScheduler:
    def __init__(self, resources, projects):
        self.resources = {r.rid: r for r in resources}
        self.projects = {p.pid: p for p in projects}
        self.assignments = []
        self.conflicts = []

    def _find_best_match(self, project: Project) -> list[Resource]:
        """为项目匹配最佳资源"""
        candidates = []
        for rid, res in self.resources.items():
            if not res.available:
                continue
            if res.current_load >= res.max_parallel:
                continue
            # 计算技能匹配分
            match_score = len(set(res.skills) & set(project.required_skills))
            if match_score > 0:
                candidates.append((match_score, res))
        # 按匹配分降序
        candidates.sort(key=lambda x: -x[0])
        return [r for _, r in candidates]

    def _check_conflict(self, resource: Resource, project: Project):
        """检查资源是否被同优先级或更高优先级项目争抢"""
        for a in self.assignments:
            if a.resource_id == resource.rid:
                existing_proj = self.projects[a.project_id]
                if existing_proj.priority <= project.priority:
                    self.conflicts.append({
                        "resource": resource.name,
                        "project_a": existing_proj.name,
                        "project_b": project.name,
                        "severity": "HIGH" if existing_proj.priority == project.priority else "MEDIUM"
                    })
                    return True
        return False

    def schedule(self):
        """执行调度：按优先级排序项目，逐项目分配资源"""
        sorted_projects = sorted(self.projects.values(), key=lambda p: (p.priority, p.deadline))

        for proj in sorted_projects:
            matches = self._find_best_match(proj)
            assigned_count = 0

            for res in matches:
                if assigned_count >= proj.team_size:
                    break
                # 检查冲突
                has_conflict = self._check_conflict(res, proj)

                # 分配
                self.assignments.append(Assignment(
                    project_id=proj.pid,
                    resource_id=res.rid,
                    skill_used=list(set(res.skills) & set(proj.required_skills))[0],
                    assigned_at=datetime.now().isoformat(),
                    conflict=has_conflict
                ))
                res.current_load += 1
                proj.assigned.append(res.name)
                assigned_count += 1

            proj.status = "assigned" if assigned_count == proj.team_size else "PARTIAL"

    def report(self):
        """输出调度报告"""
        print("=" * 70)
        print("矩阵组织资源调度仿真报告")
        print(f"时间: {datetime.now().isoformat()}")
        print("=" * 70)

        print("\n【项目分配结果】")
        for proj in sorted(self.projects.values(), key=lambda p: p.priority):
            status_icon = "✅" if proj.status == "assigned" else "⚠️"
            print(f"\n{status_icon} [{proj.pid}] {proj.name} (优先级:{proj.priority}, 截止:{proj.deadline})")
            print(f"   分配: {', '.join(proj.assigned) if proj.assigned else '无'}")
            print(f"   状态: {proj.status} (需要{proj.team_size}人, 分到{len(proj.assigned)}人)")

        print("\n【资源负载状态】")
        for rid, res in self.resources.items():
            pct = res.current_load / res.max_parallel * 100
            bar = "█" * res.current_load + "░" * (res.max_parallel - res.current_load)
            print(f"  {res.name:15s} [{bar}] {res.current_load}/{res.max_parallel} ({pct:.0f}%)")

        print("\n【冲突检测】")
        if self.conflicts:
            for c in self.conflicts:
                print(f"  ⚠️ {c['severity']}: {c['resource']} 被 [{c['project_a']}] 与 [{c['project_b']}] 争抢")
        else:
            print("  ✅ 无资源冲突")

        print("\n【统计】")
        total_tasks = len(self.assignments)
        conflict_count = len(self.conflicts)
        full_assigned = sum(1 for p in self.projects.values() if p.status == "assigned")
        print(f"  总分配: {total_tasks} 项")
        print(f"  冲突: {conflict_count} 项")
        print(f"  满载项目: {full_assigned}/{len(self.projects)}")

        return {
            "total_assignments": total_tasks,
            "conflicts": conflict_count,
            "full_assigned": full_assigned,
            "total_projects": len(self.projects)
        }


# ===================== 主程序 =====================

if __name__ == "__main__":
    print("初始化职能池...")
    print(f"  资源数: {len(RESOURCE_POOL)}")
    print(f"  项目数: {len(PROJECTS)}")
    print()

    scheduler = MatrixScheduler(RESOURCE_POOL, PROJECTS)
    scheduler.schedule()
    stats = scheduler.report()

    # 输出JSON供锁档
    result = {
        "snapshot": "SNAP-20260909-MATRIX-SIM",
        "did": "DID-BR-000002",
        "stats": stats,
        "assignments": [
            {
                "project_id": a.project_id,
                "resource_id": a.resource_id,
                "skill_used": a.skill_used,
                "conflict": a.conflict
            } for a in scheduler.assignments
        ],
        "conflicts": scheduler.conflicts
    }

    with open("/tmp/matrix_sim_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print(f"仿真完成 | 结果已写入 /tmp/matrix_sim_result.json")
    print("=" * 70)

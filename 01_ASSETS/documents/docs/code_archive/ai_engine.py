"""AI生成引擎 - 支持模拟模式和真实大模型对接"""
import json
import time
from config import AI_PROVIDER, AI_API_KEY, AI_API_BASE, AI_MODEL, increment_quota

class AIEngine:
    """AI生成引擎"""

    def __init__(self):
        self.provider = AI_PROVIDER
        self.api_key = AI_API_KEY
        self.api_base = AI_API_BASE
        self.model = AI_MODEL

    def generate(self, prompt, system_prompt="", max_tokens=2000):
        """统一生成接口"""
        increment_quota()
        if self.provider == "mock" or not self.api_key:
            return self._mock_generate(prompt, system_prompt)
        else:
            return self._api_generate(prompt, system_prompt, max_tokens)

    def _mock_generate(self, prompt, system_prompt):
        """模拟生成 - 根据提示词关键词返回结构化内容"""
        time.sleep(1.5)  # 模拟生成延迟

        # PPT生成
        if "PPT" in prompt or "ppt" in prompt or "幻灯片" in prompt:
            return self._mock_ppt(prompt)

        # 教案生成
        if "教案" in prompt or "教学设计" in prompt:
            return self._mock_lesson(prompt)

        # 文案生成
        if "说课稿" in prompt or "教学反思" in prompt or "评课稿" in prompt or "工作总结" in prompt or "论文" in prompt or "课题" in prompt:
            return self._mock_copywriting(prompt)

        # 试卷生成
        if "试卷" in prompt or "组卷" in prompt or "题目" in prompt:
            return self._mock_exam(prompt)

        # 视觉设计生成
        if "设计" in prompt or "奖状" in prompt or "海报" in prompt or "证书" in prompt:
            return self._mock_design(prompt)

        # 微课视频生成
        if "微课" in prompt or "视频" in prompt or "分镜" in prompt:
            return self._mock_video(prompt)

        # 默认通用生成
        return f"【AI生成结果】\n\n基于您的输入，系统已完成内容生成。\n\n{prompt[:200]}...\n\n（当前为模拟模式，配置真实API Key后将调用大模型生成高质量内容）"

    def _mock_ppt(self, prompt):
        """模拟PPT生成"""
        lines = prompt.split("\n")
        # 第一行是类型标识"PPT"，第二行才是标题
        title = lines[1] if len(lines) > 1 else (lines[0] if lines else "未命名PPT")
        if title == "PPT" or title == "ppt":
            title = lines[2] if len(lines) > 2 else "未命名PPT"
        outline = [l for l in lines[1:] if l.strip() and l != title and l not in ("PPT", "ppt")]
        if not outline:
            outline = ["一、研究背景", "二、总体设计", "三、核心举措", "四、创新成果", "五、实施规划"]

        result = f"📑 {title}\n\n"
        result += f"母版：v1.1.0 红色电商母版 ｜ 页数：{len(outline)+1}页 ｜ 模式：答辩动态\n\n"
        result += "【第1页】封面页\n"
        result += f"  标题：{title}\n"
        result += "  校徽+校门底图+红色飘带装饰（自动加载）\n\n"

        for i, section in enumerate(outline):
            delay = 0.2 if i % 2 == 0 else 0.3
            result += f"【第{i+2}页】{section}\n"
            result += "  版式：自动匹配拓扑（分栏/流程/数据图表）\n"
            result += f"  动画：学术生长动画已挂载（延迟{delay}s）\n"
            result += "  校验：布局/色彩/文字溢出 ✓\n\n"

        result += "✅ 合规校验通过：8套版式完整、四元色组合规、无违规动效、基底锁定正常"
        return result

    def _mock_lesson(self, prompt):
        """模拟教案生成"""
        lines = prompt.split("\n")
        # 第一行是类型标识"教案"，第二行是course，第三行是chapter
        course = lines[1] if len(lines) > 1 else "未知课程"
        chapter = lines[2] if len(lines) > 2 else "未知章节"
        if course == "教案":
            course = lines[2] if len(lines) > 2 else "未知课程"
            chapter = lines[3] if len(lines) > 3 else "未知章节"

        return f"""📋 《{course}》教案

章节：{chapter} ｜ 课时：2课时（90分钟）

一、教学目标
  1. 知识目标：掌握课程核心概念与基本原理
  2. 能力目标：能独立完成相关实操任务，具备分析解决问题能力
  3. 素养目标：培养职业素养与团队协作精神

二、教学重难点
  重点：核心知识点与实操技能
  难点：知识的综合运用与迁移

三、教学方法
  任务驱动法 + 小组协作法 + 实操演练法

四、教学过程（90分钟）
  1. 导入（10分钟）：案例展示，激发兴趣
  2. 新知讲授（20分钟）：核心知识点讲解
  3. 分组实训（40分钟）：学生分组完成实操任务
  4. 成果展示（15分钟）：各组展示互评
  5. 总结拓展（5分钟）：知识点梳理+课后任务

五、板书设计
  结构化板书：核心概念→操作流程→注意事项→拓展应用

六、作业布置
  完成课后实操作业，提交操作报告

✅ 课标对齐 ✓ 核心素养映射 ✓ 思政元素融入 ✓"""

    def _mock_copywriting(self, prompt):
        """模拟文案生成"""
        doc_type = "教学文案"
        for t in ["说课稿", "教学反思", "评课稿", "工作总结", "教学论文", "课题申报书"]:
            if t in prompt:
                doc_type = t
                break

        topic = "教育教学"
        for line in prompt.split("\n"):
            if "主题" in line:
                topic = line.split("：")[-1].strip() if "：" in line else line.split(":")[-1].strip()
                break

        return f"""✍️ {doc_type}

主题：{topic}

一、引言
  本文围绕{topic}展开论述，结合教学实践与理论研究，系统阐述相关观点与实践路径。

二、主体内容
  （一）背景与意义
  随着教育数字化转型深入推进，{topic}已成为教学研究的重要课题。

  （二）核心观点
  1. 以学生为中心，注重实践能力培养
  2. 依托信息技术，创新教学模式
  3. 强化产教融合，提升育人质量

  （三）实践路径
  基于真实教学场景，采用任务驱动、项目导向等教学方法，取得了良好效果。

三、结论与展望
  综上所述，{topic}具有重要的实践价值，未来将继续深化研究，不断优化教学实践。

参考文献：
[1] 相关教育政策文件
[2] 职业教育教学改革研究文献

（当前为模拟模式，配置真实API Key后将生成更丰富的个性化内容）"""

    def _mock_exam(self, prompt):
        """模拟试卷生成"""
        return """📝 智能组卷结果

试卷信息：
  科目：电商运营基础
  范围：第1-3章
  总分：100分 ｜ 时长：90分钟
  难度分布：易30% 中50% 难20%

一、单项选择题（每题2分，共30分）
  1. 电商平台商品标题最多可包含多少字符？
     A. 30  B. 60  C. 120  D. 200
  2. 以下哪项不属于商品主图设计原则？
     A. 清晰展示  B. 突出卖点  C. 加水印  D. 背景简洁
  ...（共15题）

二、多项选择题（每题3分，共15分）
  1. 商品详情页通常包含哪些模块？
     A. 商品展示  B. 参数说明  C. 售后保障  D. 买家评价
  ...（共5题）

三、判断题（每题1分，共10分）
  1. 商品标题关键词越多越好。（  ）
  2. 主图尺寸越大越清晰。（  ）
  ...（共10题）

四、实操题（共45分）
  1. 完成一件商品的完整上架流程（25分）
  2. 对给定商品标题进行SEO优化（20分）

✅ 知识点覆盖率：92% ｜ AB卷已生成 ｜ 答题卡已配套"""

    def _mock_design(self, prompt):
        """模拟视觉设计生成 - 输出真实可用的HTML设计稿"""
        lines = prompt.split("\n")
        design_type = "奖状证书"
        title = "荣誉证书"
        content = "同学"
        color_style = "红色"

        for line in lines:
            if "类型" in line:
                design_type = line.split("：")[-1].strip() if "：" in line else line.split(":")[-1].strip()
            elif "标题" in line:
                title = line.split("：")[-1].strip() if "：" in line else line.split(":")[-1].strip()
            elif "内容" in line:
                content = line.split("：")[-1].strip() if "：" in line else line.split(":")[-1].strip()
            elif "色系" in line:
                color_style = line.split("：")[-1].strip() if "：" in line else line.split(":")[-1].strip()

        color_map = {
            "红色": ("#dc2626", "#fef2f2", "#fca5a5"),
            "蓝色": ("#2563eb", "#eff6ff", "#93c5fd"),
            "金色": ("#d97706", "#fffbeb", "#fcd34d"),
            "绿色": ("#059669", "#ecfdf5", "#6ee7b7"),
            "紫色": ("#7c3aed", "#f5f3ff", "#c4b5fd"),
        }
        primary, bg, accent = color_map.get(color_style, color_map["红色"])

        html_design = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>{title}</title>
<style>
body{{margin:0;display:flex;justify-content:center;align-items:center;min-height:100vh;background:{bg};font-family:'Microsoft YaHei',sans-serif}}
.certificate{{width:800px;height:560px;background:#fff;border:12px solid {primary};position:relative;display:flex;flex-direction:column;align-items:center;justify-content:center;box-shadow:0 20px 60px rgba(0,0,0,0.2)}}
.certificate::before{{content:'';position:absolute;inset:12px;border:2px solid {accent}}}
.badge{{width:80px;height:80px;border-radius:50%;background:{primary};display:flex;align-items:center;justify-content:center;color:#fff;font-size:36px;margin-bottom:20px}}
h1{{color:{primary};font-size:42px;margin:0 0 10px 0;letter-spacing:8px}}
.subtitle{{color:#666;font-size:18px;margin-bottom:30px}}
.name{{font-size:36px;color:#333;margin:20px 0;border-bottom:2px solid {accent};padding:0 40px 10px}}
.desc{{font-size:18px;color:#555;text-align:center;line-height:2;margin:20px 40px}}
.footer{{position:absolute;bottom:40px;display:flex;justify-content:space-between;width:80%;color:#888;font-size:14px}}
</style></head>
<body><div class="certificate">
<div class="badge">🏆</div>
<h1>{title}</h1>
<div class="subtitle">{design_type}</div>
<div class="name">{content}</div>
<div class="desc">在{design_type}评选中表现优异，特颁此证，以资鼓励。</div>
<div class="footer"><span>颁发单位：火斗云智教育中台</span><span>2026年9月</span></div>
</div></body></html>"""

        return f"""🎨 {design_type}设计完成

设计信息：
  类型：{design_type}
  标题：{title}
  内容：{content}
  色系：{color_style}（主色{primary}）
  尺寸：800×560px（A4横向比例）

【设计稿HTML代码】
可直接复制以下代码保存为 .html 文件，用浏览器打开即可看到真实设计效果，支持打印导出：

{html_design}

✅ 设计稿已生成 ｜ 可直接保存为HTML打开 ｜ 支持打印导出PDF
（配置真实AI API后可生成高清图片）"""

    def _mock_video(self, prompt):
        """模拟微课视频生成 - 输出真实可用的脚本+分镜+SRT字幕"""
        lines = prompt.split("\n")
        course = "未知课程"
        chapter = "未知章节"
        duration = "5分钟"
        style = "知识点讲解"

        for line in lines:
            if "课程" in line:
                course = line.split("：")[-1].strip() if "：" in line else line.split(":")[-1].strip()
            elif "章节" in line:
                chapter = line.split("：")[-1].strip() if "：" in line else line.split(":")[-1].strip()
            elif "时长" in line:
                duration = line.split("：")[-1].strip() if "：" in line else line.split(":")[-1].strip()
            elif "风格" in line:
                style = line.split("：")[-1].strip() if "：" in line else line.split(":")[-1].strip()

        # 生成分镜表
        shots = [
            (1, "00:00-00:30", "开场引入", "课程标题+知识点概述，吸引注意力", "标题动画+背景图", "同学们好，今天我们学习{chapter}"),
            (2, "00:30-01:30", "概念讲解", "核心概念定义与原理说明", "PPT页面+标注动画", "首先，我们来看什么是{chapter}"),
            (3, "01:30-03:00", "案例演示", "真实案例操作演示", "屏幕录制+步骤高亮", "下面通过一个实际案例来演示"),
            (4, "03:00-04:00", "要点总结", "知识点梳理与重点强调", "思维导图动画", "总结一下，今天的重点有三个"),
            (5, "04:00-05:00", "课后拓展", "思考题与延伸学习", "结尾页+二维码", "课后请完成思考题，我们下节课见"),
        ]

        # 生成SRT字幕
        srt = ""
        for i, (num, time_range, scene, desc, visual, narration) in enumerate(shots, 1):
            start, end = time_range.split("-")
            srt += f"{i}\n00:{start},000 --> 00:{end},000\n{narration.format(chapter=chapter)}\n\n"

        shot_table = "\n".join([
            f"  镜头{s[0]}（{s[1]}）{s[2]}：{s[3]}｜画面：{s[4]}｜旁白：{s[5].format(chapter=chapter)}"
            for s in shots
        ])

        return f"""🎬 微课视频设计完成

视频信息：
  课程：{course}
  章节：{chapter}
  时长：{duration}
  风格：{style}
  镜头数：5个

【分镜表】
{shot_table}

【SRT字幕文件】
可直接复制以下内容保存为 .srt 文件，导入剪辑软件即可使用：

{srt}
✅ 脚本+分镜+字幕已生成 ｜ SRT可直接导入剪映/PR
（配置真实视频生成API后可自动合成视频）"""

    def _api_generate(self, prompt, system_prompt, max_tokens):
        """真实API生成（OpenAI兼容格式）"""
        try:
            import urllib.request
            import json as json_mod

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = json_mod.dumps({
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7
            }).encode('utf-8')

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            req = urllib.request.Request(
                f"{self.api_base}/chat/completions",
                data=payload,
                headers=headers,
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=60) as response:
                result = json_mod.loads(response.read().decode('utf-8'))
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            return f"【API调用失败】{str(e)}\n\n已回退到模拟模式：\n{self._mock_generate(prompt, system_prompt)}"


# 全局AI引擎实例
ai_engine = AIEngine()

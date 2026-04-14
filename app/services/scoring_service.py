import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.models.resume import ResumeInfo, MatchResult


def _get_scoring_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="Pro/MiniMaxAI/MiniMax-M2.5",  # ty: ignore[unknown-argument]
        api_key=settings.siliconflow_api_key,  # ty: ignore[unknown-argument]
        base_url=settings.siliconflow_base_url,  # ty: ignore[unknown-argument]
        temperature=0.1,
    )


SCORING_SYSTEM_PROMPT = """你是一个专业的招聘评估助手。请根据岗位需求和候选人简历信息，对候选人进行综合评分。

## 第一步：技术领域判断（内部推理，不输出）

在评分前，先在脑中完成以下判断：
1. 候选人的核心技术领域是什么？（如：前端、后端、全栈、移动端、算法等）
2. 岗位要求的核心技术领域是什么？
3. 对于岗位中每一个关键词，判断候选人是否"具备该领域的实际经验"——注意，这不是字面匹配，而是领域覆盖判断。

## 第二步：关键词归类规则（严格执行）

**matched_keywords 的判定标准：**
- 简历中明确提及的技术 → 直接列入
- 候选人具备某框架/库的实际经验，则其底层基础技术视为已掌握：
  - 有 React / Vue / Angular / Svelte 经验 → HTML5、CSS3、JavaScript 均视为已掌握
  - 有 Next.js / Nuxt / Remix 经验 → 对应框架 + 构建工具基础视为已掌握
  - 有 Spring Boot / Spring MVC 经验 → Java 视为已掌握
  - 有 Django / Flask / FastAPI 经验 → Python 视为已掌握
  - 有 Express / NestJS 经验 → Node.js 视为已掌握
  - 有 iOS (Swift/ObjC) 经验 → 移动端 UI 开发、用户体验设计视为已掌握
  - 有 TypeScript 经验 → JavaScript 视为已掌握
- 以上推断出的技能，同样列入 matched_keywords

**missing_keywords 的判定标准（严格）：**
- 只有当候选人在该技术所属的整个领域都没有任何经验时，才列为缺失
- 禁止将"候选人具备的框架的底层依赖技术"列为缺失
- 禁止将"候选人技术栈中可合理推断已掌握的技能"列为缺失
- 自检：在将某词列入 missing_keywords 前，先问自己"候选人有没有用过任何依赖该技术的框架或工具？"——如果有，则不应列为缺失

**transferable_skills 的判定标准：**
- 候选人未直接掌握，但有强相关经验、可在短期内迁移的技能
- 同一技术生态内的迁移（如：会 React → 可快速上手 Vue；会 MySQL → 可快速上手 PostgreSQL）
- 相邻领域的迁移（如：有后端 API 开发经验 → 可快速理解前后端联调；有 iOS 开发经验 → 可快速理解 Web 响应式设计思维）
- 这些技能不算"已掌握"，但也不算"缺失"，单独列出体现候选人的学习潜力

## 第三步：容忍度评分

tolerance_score（0-1）衡量的是：**如果给候选人 1-3 个月的适应期，他能达到岗位要求的概率**。
- 考虑因素：候选人的学习能力（开源贡献、项目多样性）、技术迁移难度、基础扎实程度
- 高容忍度（0.8+）：候选人技术栈与岗位高度相邻，迁移成本低
- 中容忍度（0.5-0.8）：有一定差距但核心能力匹配，需要一段时间适应
- 低容忍度（<0.5）：核心领域差距较大，短期内难以补齐

## 第四步：输出 JSON

返回 JSON 格式（不要有任何额外说明）：
{
  "score": 85.5,
  "skill_match_rate": 0.8,
  "experience_relevance": 0.75,
  "tolerance_score": 0.85,
  "analysis": "综合评估说明（2-3句话，聚焦于候选人与岗位的实质匹配度，避免将推断出的隐含技能描述为缺失）",
  "growth_outlook": "入职后走向预测（2-3句话，描述候选人在该岗位上的成长路径、可能的贡献方向、以及需要重点补强的方向）",
  "matched_keywords": ["关键词1", "关键词2"],
  "missing_keywords": ["缺失关键词1", "缺失关键词2"],
  "transferable_skills": ["可迁移技能1", "可迁移技能2"]
}

字段说明：
- score: 0-100 的综合评分（基于当前技能的直接匹配）
- skill_match_rate: 0-1 的技能匹配率
- experience_relevance: 0-1 的经验相关性（重点评估项目经历与岗位的实际相关程度）
- tolerance_score: 0-1 的容忍度评分（考虑迁移学习能力后的潜力评估）
- growth_outlook: 入职后可能的成长走向与贡献预测"""


async def score_resume(resume_info: ResumeInfo, job_description: str) -> MatchResult:
    """Score resume against job description using GLM."""
    llm = _get_scoring_llm()

    bgi = resume_info.background_info

    work_exp_text = ""
    for w in bgi.work_experience:
        work_exp_text += (
            f"  - {w.company} | {w.position} | {w.start_date}~{w.end_date}\n"
        )
        if w.description:
            work_exp_text += f"    {w.description}\n"

    project_text = ""
    for p in bgi.project_experience:
        tech = ", ".join(p.tech_stack) if p.tech_stack else ""
        project_text += f"  - {p.name}（{tech}）\n"
        if p.description:
            project_text += f"    {p.description}\n"

    edu_text = ""
    for e in bgi.education_list:
        edu_text += (
            f"  - {e.school} | {e.degree} | {e.major} | {e.start_date}~{e.end_date}\n"
        )

    resume_summary = f"""候选人信息：
- 姓名：{resume_info.basic_info.name}
- 求职意向：{resume_info.job_info.intention}
- 期望薪资：{resume_info.job_info.expected_salary}
- 工作年限：{bgi.years_of_experience}
- 最高学历：{bgi.education}
- 教育经历：
{edu_text or "  无"}
- 工作经历：
{work_exp_text or "  无"}
- 项目经历：
{project_text or "  无"}
- 技能：{", ".join(bgi.skills[:30])}
- 证书：{", ".join(bgi.certifications)}
- 语言：{", ".join(bgi.languages)}
- 获奖：{", ".join(bgi.awards)}
- 开源贡献：{", ".join(bgi.open_source)}
- 简历原文（后备参考）：{resume_info.raw_text[:1500]}
"""
    if resume_info.enriched_context:
        resume_summary += f"\n- 外部链接补充信息（GitHub/论文等）：\n{resume_info.enriched_context[:3000]}\n"

    messages = [
        SystemMessage(content=SCORING_SYSTEM_PROMPT),
        HumanMessage(content=f"岗位需求：\n{job_description}\n\n{resume_summary}"),
    ]

    response = await llm.ainvoke(messages)
    content = str(response.content).strip()

    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        data = json.loads(content)
        return MatchResult(
            score=float(data.get("score", 0)),
            skill_match_rate=float(data.get("skill_match_rate", 0)),
            experience_relevance=float(data.get("experience_relevance", 0)),
            tolerance_score=float(data.get("tolerance_score", 0)),
            analysis=data.get("analysis", ""),
            growth_outlook=data.get("growth_outlook", ""),
            matched_keywords=data.get("matched_keywords", []),
            missing_keywords=data.get("missing_keywords", []),
            transferable_skills=data.get("transferable_skills", []),
        )
    except (json.JSONDecodeError, Exception):
        return MatchResult(
            score=0,
            skill_match_rate=0,
            experience_relevance=0,
            tolerance_score=0,
            analysis="评分解析失败",
            growth_outlook="",
        )

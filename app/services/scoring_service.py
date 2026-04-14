# 简历评分服务
# 调用 LLM（MiniMax M2.5）对候选人简历与岗位需求进行综合评分。
#
# 评分维度：
#   - score：综合评分（0-100），基于当前技能的直接匹配
#   - skill_match_rate：技能匹配率（0-1）
#   - experience_relevance：经验相关性（0-1）
#   - tolerance_score：适应潜力（0-1），考虑迁移学习能力后的潜力评估
#
# 关键词分类逻辑（由 LLM 执行）：
#   - matched_keywords：已掌握的技能，含从框架经验推断出的底层技术
#   - missing_keywords：整个领域都无经验时才列为缺失（严格标准）
#   - transferable_skills：有相关经验但非直接匹配，可短期迁移的技能
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.models.resume import ResumeInfo, MatchResult


def _get_scoring_llm() -> ChatOpenAI:
    """构造用于评分的 LLM 客户端（MiniMax M2.5，推理能力强）。"""
    return ChatOpenAI(
        model="Pro/MiniMaxAI/MiniMax-M2.5",  # ty: ignore[unknown-argument]
        api_key=settings.siliconflow_api_key,  # ty: ignore[unknown-argument]
        base_url=settings.siliconflow_base_url,  # ty: ignore[unknown-argument]
        temperature=0.1,
    )


# 评分系统提示：包含详细的评分规则和关键词归类标准
# 核心设计原则：避免将"框架底层依赖技术"误判为缺失（如有 React 经验不应将 JS 列为缺失）
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
    """将简历信息与岗位需求发送给 LLM，返回结构化的匹配评分结果。

    构造候选人摘要时，优先使用结构化字段（工作/项目经历），
    同时附上原始文本（截取 1500 字符）作为后备参考，
    以及外部链接富化内容（截取 3000 字符）作为补充。

    若 LLM 返回的 JSON 解析失败，返回全零评分，避免抛出异常。
    """
    llm = _get_scoring_llm()

    bgi = resume_info.background_info

    # 格式化工作经历为可读文本
    work_exp_text = ""
    for w in bgi.work_experience:
        work_exp_text += (
            f"  - {w.company} | {w.position} | {w.start_date}~{w.end_date}\n"
        )
        if w.description:
            work_exp_text += f"    {w.description}\n"

    # 格式化项目经历为可读文本（含技术栈）
    project_text = ""
    for p in bgi.project_experience:
        tech = ", ".join(p.tech_stack) if p.tech_stack else ""
        project_text += f"  - {p.name}（{tech}）\n"
        if p.description:
            project_text += f"    {p.description}\n"

    # 格式化教育经历
    edu_text = ""
    for e in bgi.education_list:
        edu_text += (
            f"  - {e.school} | {e.degree} | {e.major} | {e.start_date}~{e.end_date}\n"
        )

    # 构造发送给 LLM 的候选人摘要
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
    # 若有外部链接富化内容（GitHub/论文等），追加到摘要末尾
    if resume_info.enriched_context:
        resume_summary += f"\n- 外部链接补充信息（GitHub/论文等）：\n{resume_info.enriched_context[:3000]}\n"

    messages = [
        SystemMessage(content=SCORING_SYSTEM_PROMPT),
        HumanMessage(content=f"岗位需求：\n{job_description}\n\n{resume_summary}"),
    ]

    response = await llm.ainvoke(messages)
    content = str(response.content).strip()

    # 剥离 LLM 可能返回的 markdown 代码块包装
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
        # 解析失败时返回全零评分，避免整个请求失败
        return MatchResult(
            score=0,
            skill_match_rate=0,
            experience_relevance=0,
            tolerance_score=0,
            analysis="评分解析失败",
            growth_outlook="",
        )

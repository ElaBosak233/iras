# 简历信息提取服务
# 调用 LLM（GLM 系列）从简历原始文本中提取结构化信息，
# 并并行触发外部链接富化（GitHub/论文页面抓取）。
#
# 提取流程：
#   1. 将原始文本（截取前 12000 字符）发送给 LLM
#   2. LLM 返回 JSON 格式的结构化简历信息
#   3. 解析 JSON 并映射到 Pydantic 模型
#   4. 同时抓取简历中的外部链接作为补充上下文
import asyncio
import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.models.resume import (
    ResumeInfo,
    BasicInfo,
    JobInfo,
    BackgroundInfo,
    EducationItem,
    WorkExperienceItem,
    ProjectItem,
)
from app.services.enrichment_service import enrich_from_links

logger = logging.getLogger(__name__)


def _get_llm(model: str = "Pro/zai-org/GLM-5.1") -> ChatOpenAI:
    """构造用于信息提取的 LLM 客户端。"""
    return ChatOpenAI(
        model=model,  # ty: ignore[unknown-argument]
        api_key=settings.siliconflow_api_key,  # ty: ignore[unknown-argument]
        base_url=settings.siliconflow_base_url,  # ty: ignore[unknown-argument]
        temperature=0.1,   # 低温度保证提取结果稳定，减少随机性
        request_timeout=120,
    )


# LLM 系统提示：定义提取任务、输出格式和提取规则
# 明确要求返回纯 JSON，避免 LLM 添加额外说明文字
EXTRACT_SYSTEM_PROMPT = """你是一个专业的简历信息提取助手。请从给定的简历文本中尽可能完整地提取所有信息，以 JSON 格式返回。

返回格式如下（找不到的字段返回 null 或空数组，不要省略任何字段）：
{
  "basic_info": {
    "name": "姓名",
    "phone": "电话号码",
    "email": "邮箱地址",
    "address": "居住地/地址",
    "gender": "性别",
    "birth_date": "出生日期",
    "github": "GitHub 主页链接",
    "linkedin": "LinkedIn 链接",
    "website": "个人网站/博客链接",
    "wechat": "微信号"
  },
  "job_info": {
    "intention": "求职意向/目标岗位",
    "expected_salary": "期望薪资",
    "job_type": "全职/兼职/实习",
    "available_date": "到岗时间",
    "preferred_location": "期望工作地点"
  },
  "background_info": {
    "years_of_experience": "总工作年限（如：3年）",
    "education": "最高学历（如：本科/硕士）",
    "education_list": [
      {
        "school": "学校名称",
        "degree": "学历层次（本科/硕士/博士/专科）",
        "major": "专业",
        "start_date": "入学时间",
        "end_date": "毕业时间",
        "gpa": "GPA 或排名",
        "description": "在校经历、荣誉、社团等"
      }
    ],
    "work_experience": [
      {
        "company": "公司名称",
        "position": "职位名称",
        "start_date": "开始时间",
        "end_date": "结束时间（在职则填 至今）",
        "location": "工作地点",
        "description": "工作内容、职责、成就（尽量完整保留原文）"
      }
    ],
    "project_experience": [
      {
        "name": "项目名称",
        "role": "担任角色",
        "start_date": "开始时间",
        "end_date": "结束时间",
        "tech_stack": ["技术1", "技术2"],
        "description": "项目描述、职责、成果（尽量完整保留原文）",
        "url": "项目链接或 GitHub 地址"
      }
    ],
    "skills": ["技能1", "技能2", "技能3"],
    "certifications": ["证书1", "证书2"],
    "languages": ["中文（母语）", "英语（CET-6）"],
    "awards": ["奖项1", "奖项2"],
    "publications": ["论文/出版物1"],
    "open_source": ["开源项目/贡献1"]
  }
}

提取要求：
1. work_experience 和 project_experience 的 description 字段要尽量完整保留原文内容，不要过度压缩
2. skills 要拆分为独立条目，不要合并成一个字符串
3. 时间格式统一为 YYYY-MM 或 YYYY，无法确定则保留原文
4. 只返回 JSON，不要有任何额外说明"""


def _parse_education_list(raw: list) -> list[EducationItem]:
    """将 LLM 返回的教育经历原始列表解析为 EducationItem 列表。
    使用白名单过滤，只保留模型中定义的字段，忽略 LLM 可能返回的多余字段。
    """
    result = []
    for item in raw:
        if isinstance(item, dict):
            result.append(
                EducationItem(
                    **{k: v for k, v in item.items() if k in EducationItem.model_fields}
                )
            )
    return result


def _parse_work_experience(raw: list) -> list[WorkExperienceItem]:
    """将 LLM 返回的工作经历原始列表解析为 WorkExperienceItem 列表。"""
    result = []
    for item in raw:
        if isinstance(item, dict):
            result.append(
                WorkExperienceItem(
                    **{
                        k: v
                        for k, v in item.items()
                        if k in WorkExperienceItem.model_fields
                    }
                )
            )
    return result


def _parse_projects(raw: list) -> list[ProjectItem]:
    """将 LLM 返回的项目经历原始列表解析为 ProjectItem 列表。"""
    result = []
    for item in raw:
        if isinstance(item, dict):
            result.append(
                ProjectItem(
                    **{k: v for k, v in item.items() if k in ProjectItem.model_fields}
                )
            )
    return result


async def extract_resume_info(text: str) -> ResumeInfo:
    """调用 LLM 从简历文本中提取结构化信息。

    同时并行触发外部链接富化（enrich_from_links），
    将 GitHub/论文等页面内容作为补充上下文存入 enriched_context。

    若 LLM 返回的 JSON 解析失败，返回仅含原始文本的 ResumeInfo，
    保证后续评分流程仍可使用 raw_text 作为后备。
    """
    llm = _get_llm()
    logger.info("invoking LLM, model=%s, text_len=%d", llm.model_name, len(text))

    messages = [
        SystemMessage(content=EXTRACT_SYSTEM_PROMPT),
        # 截取前 12000 字符，避免超出模型上下文窗口
        HumanMessage(content=f"简历内容：\n\n{text[:12000]}"),
    ]

    try:
        response = await asyncio.wait_for(llm.ainvoke(messages), timeout=120)
    except asyncio.TimeoutError:
        logger.error("LLM call timed out after 120s")
        raise
    except Exception as e:
        logger.exception("LLM call failed: %s", e)
        raise

    content = str(response.content).strip()
    logger.info("LLM responded, content_len=%d", len(content))

    # 部分 LLM 会在 JSON 外包裹 markdown 代码块（```json ... ```），需要剥离
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    # 在解析 JSON 的同时，并行抓取简历中的外部链接（不阻塞主流程）
    logger.info("starting link enrichment...")
    enriched_context = await enrich_from_links(text)
    logger.info("enrichment done, context_len=%d", len(enriched_context))

    try:
        data = json.loads(content)
        bi = data.get("basic_info") or {}
        ji = data.get("job_info") or {}
        bgi = data.get("background_info") or {}

        background = BackgroundInfo(
            years_of_experience=bgi.get("years_of_experience"),
            education=bgi.get("education"),
            education_list=_parse_education_list(bgi.get("education_list") or []),
            work_experience=_parse_work_experience(bgi.get("work_experience") or []),
            project_experience=_parse_projects(bgi.get("project_experience") or []),
            skills=bgi.get("skills") or [],
            certifications=bgi.get("certifications") or [],
            languages=bgi.get("languages") or [],
            awards=bgi.get("awards") or [],
            publications=bgi.get("publications") or [],
            open_source=bgi.get("open_source") or [],
        )

        return ResumeInfo(
            basic_info=BasicInfo(
                **{k: v for k, v in bi.items() if k in BasicInfo.model_fields}
            ),
            job_info=JobInfo(
                **{k: v for k, v in ji.items() if k in JobInfo.model_fields}
            ),
            background_info=background,
            raw_text=text,
            enriched_context=enriched_context,
        )
    except json.JSONDecodeError as e:
        # LLM 偶尔会返回非法 JSON，降级处理：保留原始文本供评分时参考
        logger.error(
            "failed to parse LLM JSON response: %s\nraw content: %.500s", e, content
        )
        return ResumeInfo(raw_text=text, enriched_context=enriched_context)
    except Exception as e:
        logger.exception("failed to build ResumeInfo: %s", e)
        return ResumeInfo(raw_text=text, enriched_context=enriched_context)

# 简历数据模型
# 使用 Pydantic 定义所有简历相关的数据结构，同时作为 API 的请求/响应 Schema。
# 所有字段均允许 None，因为 LLM 提取结果不保证完整性。
from pydantic import BaseModel


class BasicInfo(BaseModel):
    """候选人基本联系信息。"""
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    gender: str | None = None
    birth_date: str | None = None
    github: str | None = None
    linkedin: str | None = None
    website: str | None = None
    wechat: str | None = None


class EducationItem(BaseModel):
    """单条教育经历。"""
    school: str | None = None
    degree: str | None = None  # 学历层次：本科/硕士/博士/专科
    major: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    gpa: str | None = None
    description: str | None = None  # 在校经历、荣誉、社团等


class WorkExperienceItem(BaseModel):
    """单条工作经历。"""
    company: str | None = None
    position: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None
    description: str | None = None  # 工作内容、职责、成就（尽量保留原文）


class ProjectItem(BaseModel):
    """单条项目经历。"""
    name: str | None = None
    role: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    tech_stack: list[str] = []  # 技术栈列表，每项为独立技术名称
    description: str | None = None
    url: str | None = None  # 项目链接或 GitHub 地址


class JobInfo(BaseModel):
    """候选人求职意向信息。"""
    intention: str | None = None       # 目标岗位
    expected_salary: str | None = None
    job_type: str | None = None        # 全职/兼职/实习
    available_date: str | None = None  # 到岗时间
    preferred_location: str | None = None


class BackgroundInfo(BaseModel):
    """候选人背景信息，包含教育、工作、项目经历及技能。"""
    years_of_experience: str | None = None
    education: str | None = None              # 最高学历（简要，如"本科"）
    education_list: list[EducationItem] = []  # 完整教育经历列表
    work_experience: list[WorkExperienceItem] = []
    project_experience: list[ProjectItem] = []
    skills: list[str] = []           # 技能列表，每项为独立技术/工具名称
    certifications: list[str] = []   # 证书/资质
    languages: list[str] = []        # 语言能力（如"英语 CET-6"）
    awards: list[str] = []           # 获奖经历
    publications: list[str] = []     # 论文/出版物
    open_source: list[str] = []      # 开源贡献


class ResumeInfo(BaseModel):
    """完整的简历信息，由 LLM 从原始文本中提取。"""
    basic_info: BasicInfo = BasicInfo()
    job_info: JobInfo = JobInfo()
    background_info: BackgroundInfo = BackgroundInfo()
    raw_text: str = ""           # PDF 提取的原始文本，供评分时作为后备参考
    enriched_context: str = ""   # 从外部链接（GitHub/论文等）抓取的补充信息


class MatchResult(BaseModel):
    """简历与岗位的匹配评分结果。"""
    score: float                      # 综合评分，0-100
    skill_match_rate: float           # 技能匹配率，0-1
    experience_relevance: float       # 经验相关性，0-1
    tolerance_score: float = 0.0      # 适应潜力评分，0-1（考虑迁移学习能力后的潜力）
    analysis: str                     # 综合评估说明（2-3句话）
    growth_outlook: str = ""          # 入职后成长走向预测
    matched_keywords: list[str] = []  # 已匹配的岗位关键词（含推断出的隐含技能）
    missing_keywords: list[str] = []  # 缺失的岗位关键词（仅整个领域都无经验时才列出）
    transferable_skills: list[str] = []  # 可迁移技能（有相关经验但非直接匹配）


# ---- API 请求/响应模型 ----

class ResumeSubmitResponse(BaseModel):
    """上传简历接口的响应，返回异步任务 ID。"""
    resume_id: str


class ResumeStatusResponse(BaseModel):
    """查询简历解析状态的响应。"""
    resume_id: str
    status: str  # "pending" | "done" | "error"
    resume_info: ResumeInfo | None = None
    cached: bool = False   # True 表示命中缓存，未重新调用 LLM
    error: str | None = None


class ResumeAnalysisResponse(BaseModel):
    """Redis 中存储的完整简历解析结果。"""
    resume_id: str
    resume_info: ResumeInfo
    cached: bool = False


class MatchResponse(BaseModel):
    """同步匹配接口的响应（当前未使用，保留备用）。"""
    resume_id: str
    job_description: str
    match_result: MatchResult
    cached: bool = False


class MatchSubmitResponse(BaseModel):
    """提交匹配任务接口的响应，返回异步任务 ID。"""
    match_id: str


class MatchStatusResponse(BaseModel):
    """查询匹配任务状态的响应。"""
    match_id: str
    status: str  # "pending" | "done" | "error"
    match_result: MatchResult | None = None
    cached: bool = False
    error: str | None = None

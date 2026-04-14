from pydantic import BaseModel


class BasicInfo(BaseModel):
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
    school: str | None = None
    degree: str | None = None  # 学历：本科/硕士/博士等
    major: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    gpa: str | None = None
    description: str | None = None  # 在校经历、荣誉等


class WorkExperienceItem(BaseModel):
    company: str | None = None
    position: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None
    description: str | None = None  # 工作内容、成就


class ProjectItem(BaseModel):
    name: str | None = None
    role: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    tech_stack: list[str] = []
    description: str | None = None
    url: str | None = None  # 项目链接/GitHub


class JobInfo(BaseModel):
    intention: str | None = None
    expected_salary: str | None = None
    job_type: str | None = None  # 全职/兼职/实习
    available_date: str | None = None  # 到岗时间
    preferred_location: str | None = None


class BackgroundInfo(BaseModel):
    years_of_experience: str | None = None
    education: str | None = None  # 最高学历（简要）
    education_list: list[EducationItem] = []  # 完整教育经历
    work_experience: list[WorkExperienceItem] = []  # 工作经历
    project_experience: list[ProjectItem] = []  # 项目经历
    skills: list[str] = []  # 技能列表
    certifications: list[str] = []  # 证书/资质
    languages: list[str] = []  # 语言能力
    awards: list[str] = []  # 获奖经历
    publications: list[str] = []  # 论文/出版物
    open_source: list[str] = []  # 开源贡献


class ResumeInfo(BaseModel):
    basic_info: BasicInfo = BasicInfo()
    job_info: JobInfo = JobInfo()
    background_info: BackgroundInfo = BackgroundInfo()
    raw_text: str = ""
    enriched_context: str = ""


class MatchResult(BaseModel):
    score: float  # 0-100
    skill_match_rate: float
    experience_relevance: float
    tolerance_score: float = 0.0  # 0-1，考虑迁移学习能力后的潜力评分
    analysis: str
    growth_outlook: str = ""  # 入职后可能的走向与成长预测
    matched_keywords: list[str] = []
    missing_keywords: list[str] = []
    transferable_skills: list[str] = []  # 可迁移技能（有相关经验但非直接匹配）


class ResumeSubmitResponse(BaseModel):
    resume_id: str


class ResumeStatusResponse(BaseModel):
    resume_id: str
    status: str  # "pending" | "done" | "error"
    resume_info: ResumeInfo | None = None
    cached: bool = False
    error: str | None = None


class ResumeAnalysisResponse(BaseModel):
    resume_id: str
    resume_info: ResumeInfo
    cached: bool = False


class MatchResponse(BaseModel):
    resume_id: str
    job_description: str
    match_result: MatchResult
    cached: bool = False


class MatchSubmitResponse(BaseModel):
    match_id: str


class MatchStatusResponse(BaseModel):
    match_id: str
    status: str  # "pending" | "done" | "error"
    match_result: MatchResult | None = None
    cached: bool = False
    error: str | None = None

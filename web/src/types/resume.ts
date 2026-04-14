/**
 * 全局类型定义
 * 与后端 app/models/resume.py 中的 Pydantic 模型一一对应。
 * 所有可选字段均为 null（而非 undefined），与后端 JSON 序列化行为一致。
 */

/** 候选人基本联系信息 */
export interface BasicInfo {
  name: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  gender: string | null;
  birth_date: string | null;
  github: string | null;
  linkedin: string | null;
  website: string | null;
  wechat: string | null;
}

/** 候选人求职意向信息 */
export interface JobInfo {
  intention: string | null;       // 目标岗位
  expected_salary: string | null;
  job_type: string | null;        // 全职/兼职/实习
  available_date: string | null;  // 到岗时间
  preferred_location: string | null;
}

/** 单条教育经历 */
export interface EducationItem {
  school: string | null;
  degree: string | null;      // 学历层次：本科/硕士/博士/专科
  major: string | null;
  start_date: string | null;
  end_date: string | null;
  gpa: string | null;
  description: string | null; // 在校经历、荣誉、社团等
}

/** 单条工作经历 */
export interface WorkExperienceItem {
  company: string | null;
  position: string | null;
  start_date: string | null;
  end_date: string | null;
  location: string | null;
  description: string | null;
}

/** 单条项目经历 */
export interface ProjectItem {
  name: string | null;
  role: string | null;
  start_date: string | null;
  end_date: string | null;
  tech_stack: string[];       // 技术栈列表，每项为独立技术名称
  description: string | null;
  url: string | null;         // 项目链接或 GitHub 地址
}

/** 候选人背景信息（教育、工作、项目经历及技能） */
export interface BackgroundInfo {
  years_of_experience: string | null;
  education: string | null;              // 最高学历（简要，如"本科"）
  education_list: EducationItem[];
  work_experience: WorkExperienceItem[];
  project_experience: ProjectItem[];
  skills: string[];
  certifications: string[];
  languages: string[];
  awards: string[];
  publications: string[];
  open_source: string[];
}

/** 完整的简历信息（LLM 提取结果） */
export interface ResumeInfo {
  basic_info: BasicInfo;
  job_info: JobInfo;
  background_info: BackgroundInfo;
  raw_text: string;          // PDF 原始文本，供评分时作为后备参考
  enriched_context: string;  // 从外部链接抓取的补充信息
}

/** Redis 中存储的完整简历解析结果 */
export interface ResumeAnalysisResponse {
  resume_id: string;
  resume_info: ResumeInfo;
  cached: boolean;
}

/** 上传简历接口的响应 */
export interface ResumeSubmitResponse {
  resume_id: string;
}

/** 简历解析状态 */
export type ResumeParseStatus = "pending" | "done" | "error";

/** 查询简历解析状态的响应 */
export interface ResumeStatusResponse {
  resume_id: string;
  status: ResumeParseStatus;
  resume_info: ResumeInfo | null;
  cached: boolean;   // true 表示命中缓存，未重新调用 LLM
  error: string | null;
}

/** 简历与岗位的匹配评分结果 */
export interface MatchResult {
  score: number;                  // 综合评分，0-100
  skill_match_rate: number;       // 技能匹配率，0-1
  experience_relevance: number;   // 经验相关性，0-1
  tolerance_score: number;        // 适应潜力，0-1（考虑迁移学习能力）
  analysis: string;               // 综合评估说明
  growth_outlook: string;         // 入职后成长走向预测
  matched_keywords: string[];     // 已匹配关键词（含推断出的隐含技能）
  missing_keywords: string[];     // 缺失关键词（整个领域无经验时才列出）
  transferable_skills: string[];  // 可迁移技能（有相关经验但非直接匹配）
}

/** 同步匹配接口的响应（当前未使用，保留备用） */
export interface MatchResponse {
  resume_id: string;
  job_description: string;
  match_result: MatchResult;
  cached: boolean;
}

/** 匹配任务状态 */
export type MatchJobStatus = "pending" | "done" | "error";

/** 提交匹配任务接口的响应 */
export interface MatchSubmitResponse {
  match_id: string;
}

/** 查询匹配任务状态的响应 */
export interface MatchStatusResponse {
  match_id: string;
  status: MatchJobStatus;
  match_result: MatchResult | null;
  cached: boolean;
  error: string | null;
}

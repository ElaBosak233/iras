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

export interface JobInfo {
  intention: string | null;
  expected_salary: string | null;
  job_type: string | null;
  available_date: string | null;
  preferred_location: string | null;
}

export interface EducationItem {
  school: string | null;
  degree: string | null;
  major: string | null;
  start_date: string | null;
  end_date: string | null;
  gpa: string | null;
  description: string | null;
}

export interface WorkExperienceItem {
  company: string | null;
  position: string | null;
  start_date: string | null;
  end_date: string | null;
  location: string | null;
  description: string | null;
}

export interface ProjectItem {
  name: string | null;
  role: string | null;
  start_date: string | null;
  end_date: string | null;
  tech_stack: string[];
  description: string | null;
  url: string | null;
}

export interface BackgroundInfo {
  years_of_experience: string | null;
  education: string | null;
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

export interface ResumeInfo {
  basic_info: BasicInfo;
  job_info: JobInfo;
  background_info: BackgroundInfo;
  raw_text: string;
  enriched_context: string;
}

export interface ResumeAnalysisResponse {
  resume_id: string;
  resume_info: ResumeInfo;
  cached: boolean;
}

export interface ResumeSubmitResponse {
  resume_id: string;
}

export type ResumeParseStatus = "pending" | "done" | "error";

export interface ResumeStatusResponse {
  resume_id: string;
  status: ResumeParseStatus;
  resume_info: ResumeInfo | null;
  cached: boolean;
  error: string | null;
}

export interface MatchResult {
  score: number;
  skill_match_rate: number;
  experience_relevance: number;
  tolerance_score: number;
  analysis: string;
  growth_outlook: string;
  matched_keywords: string[];
  missing_keywords: string[];
  transferable_skills: string[];
}

export interface MatchResponse {
  resume_id: string;
  job_description: string;
  match_result: MatchResult;
  cached: boolean;
}

export type MatchJobStatus = "pending" | "done" | "error";

export interface MatchSubmitResponse {
  match_id: string;
}

export interface MatchStatusResponse {
  match_id: string;
  status: MatchJobStatus;
  match_result: MatchResult | null;
  cached: boolean;
  error: string | null;
}

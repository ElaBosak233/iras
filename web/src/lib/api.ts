/**
 * API 客户端
 * 封装所有与后端的 HTTP 通信，统一处理 baseURL 和 Cookie 传递。
 * withCredentials: true 确保跨域请求时携带 session_id Cookie。
 */
import axios from "axios";
import type {
  MatchStatusResponse,
  MatchSubmitResponse,
  ResumeStatusResponse,
  ResumeSubmitResponse,
} from "@/types/resume";

// 所有请求统一走 /api 前缀，由 Vite 代理转发到后端（开发环境）
const api = axios.create({ baseURL: "/api", withCredentials: true });

/**
 * 上传 PDF 简历。
 * 返回 resume_id，后端立即响应（202），实际解析在后台进行。
 */
export async function submitResume(file: File): Promise<ResumeSubmitResponse> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<ResumeSubmitResponse>("/resumes", form);
  return data;
}

/**
 * 查询简历解析状态和结果。
 * 前端通过轮询此接口等待 status 变为 "done" 或 "error"。
 */
export async function getResume(
  resumeId: string
): Promise<ResumeStatusResponse> {
  const { data } = await api.get<ResumeStatusResponse>(`/resumes/${resumeId}`);
  return data;
}

/**
 * 列出当前会话下所有 resume_id。
 * 用于页面刷新后从服务端恢复历史简历列表。
 */
export async function listResumes(): Promise<string[]> {
  const { data } = await api.get<string[]>("/resumes");
  return data;
}

/**
 * 提交岗位匹配任务。
 * 返回 match_id，后端立即响应（202），实际评分在后台进行。
 */
export async function submitMatch(
  resumeId: string,
  jobDescription: string
): Promise<MatchSubmitResponse> {
  const { data } = await api.post<MatchSubmitResponse>(
    `/resumes/${resumeId}/matches`,
    { job_description: jobDescription }
  );
  return data;
}

/**
 * 查询匹配任务状态和结果。
 * 前端通过轮询此接口等待 status 变为 "done" 或 "error"。
 */
export async function getMatch(
  resumeId: string,
  matchId: string
): Promise<MatchStatusResponse> {
  const { data } = await api.get<MatchStatusResponse>(
    `/resumes/${resumeId}/matches/${matchId}`
  );
  return data;
}

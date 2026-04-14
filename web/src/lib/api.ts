import axios from "axios";
import type {
  MatchStatusResponse,
  MatchSubmitResponse,
  ResumeStatusResponse,
  ResumeSubmitResponse,
} from "@/types/resume";

const api = axios.create({ baseURL: "/api", withCredentials: true });

export async function submitResume(file: File): Promise<ResumeSubmitResponse> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<ResumeSubmitResponse>("/resumes", form);
  return data;
}

export async function getResume(
  resumeId: string
): Promise<ResumeStatusResponse> {
  const { data } = await api.get<ResumeStatusResponse>(`/resumes/${resumeId}`);
  return data;
}

export async function listResumes(): Promise<string[]> {
  const { data } = await api.get<string[]>("/resumes");
  return data;
}

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

export async function getMatch(
  resumeId: string,
  matchId: string
): Promise<MatchStatusResponse> {
  const { data } = await api.get<MatchStatusResponse>(
    `/resumes/${resumeId}/matches/${matchId}`
  );
  return data;
}

/**
 * 简历列表项组件
 * 展示单条简历的解析状态，并在 status 为 "pending" 时自动轮询后端。
 *
 * 轮询逻辑：
 *   - 每 2 秒调用一次 GET /api/resumes/{id}
 *   - 状态变为 "done" 或 "error" 时停止轮询，通过 onStatusChange 通知父组件
 *   - 组件卸载时清除定时器，防止内存泄漏
 *
 * 点击行为：
 *   - done 状态：跳转到 /resume/{id} 详情页
 *   - pending/error 状态：不可点击
 */
import { AlertCircle, ChevronRight, Loader2 } from "lucide-react";
import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { getResume } from "@/lib/api";
import type { ResumeInfo, ResumeParseStatus } from "@/types/resume";

/** 简历列表项的数据结构，由父组件（App.tsx）维护 */
export interface ResumeEntry {
  resumeId: string;
  fileName: string;          // 原始文件名（从 localStorage 恢复）
  status: ResumeParseStatus;
  resumeInfo: ResumeInfo | null;
  cached: boolean;
  error: string | null;
}

interface ResumeListItemProps {
  entry: ResumeEntry;
  /** 状态变化时通知父组件，使用 patch 局部更新避免覆盖其他字段 */
  onStatusChange: (id: string, patch: Partial<ResumeEntry>) => void;
}

export function ResumeListItem({ entry, onStatusChange }: ResumeListItemProps) {
  const navigate = useNavigate();
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 仅在 pending 状态时启动轮询，状态变化后自动停止
  useEffect(() => {
    if (entry.status !== "pending") return;

    pollRef.current = setInterval(async () => {
      try {
        const res = await getResume(entry.resumeId);
        if (res.status !== "pending") {
          if (pollRef.current) clearInterval(pollRef.current);
          onStatusChange(entry.resumeId, {
            status: res.status,
            resumeInfo: res.resume_info,
            cached: res.cached,
            error: res.error,
          });
        }
      } catch {
        // 忽略瞬时网络错误，继续轮询
      }
    }, 2000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [entry.resumeId, entry.status, onStatusChange]);

  const isPending = entry.status === "pending";
  const isError = entry.status === "error";
  const isDone = entry.status === "done";

  // 解析完成后优先显示候选人姓名，否则显示文件名
  const displayName =
    isDone && entry.resumeInfo?.basic_info?.name
      ? entry.resumeInfo.basic_info.name
      : entry.fileName;

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      <button
        type="button"
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors disabled:cursor-default"
        onClick={() => isDone && navigate(`/resume/${entry.resumeId}`)}
        disabled={isPending}
      >
        {/* 状态图标：解析中 / 失败 / 成功 */}
        {isPending && (
          <Loader2 className="h-4 w-4 text-blue-500 animate-spin shrink-0" />
        )}
        {isError && <AlertCircle className="h-4 w-4 text-red-500 shrink-0" />}
        {isDone && (
          <div className="h-4 w-4 rounded-full bg-green-500 shrink-0" />
        )}

        <span className="flex-1 text-sm font-medium text-gray-800 truncate">
          {displayName}
        </span>

        {isPending && <span className="text-xs text-gray-400">解析中...</span>}
        {isError && <span className="text-xs text-red-500">解析失败</span>}
        {isDone && entry.cached && (
          <span className="text-xs text-gray-400 mr-1">缓存</span>
        )}
        {isDone && <ChevronRight className="h-4 w-4 text-gray-400 shrink-0" />}
      </button>
    </div>
  );
}

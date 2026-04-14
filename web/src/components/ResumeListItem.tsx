import { AlertCircle, ChevronRight, Loader2 } from "lucide-react";
import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { getResume } from "@/lib/api";
import type { ResumeInfo, ResumeParseStatus } from "@/types/resume";

export interface ResumeEntry {
  resumeId: string;
  fileName: string;
  status: ResumeParseStatus;
  resumeInfo: ResumeInfo | null;
  cached: boolean;
  error: string | null;
}

interface ResumeListItemProps {
  entry: ResumeEntry;
  onStatusChange: (id: string, patch: Partial<ResumeEntry>) => void;
}

export function ResumeListItem({ entry, onStatusChange }: ResumeListItemProps) {
  const navigate = useNavigate();
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (entry.status !== "pending") return;

    pollRef.current = setInterval(async () => {
      try {
        const res = await getResume(entry.resumeId);
        if (res.status !== "pending") {
          clearInterval(pollRef.current!);
          onStatusChange(entry.resumeId, {
            status: res.status,
            resumeInfo: res.resume_info,
            cached: res.cached,
            error: res.error,
          });
        }
      } catch {
        // ignore transient errors
      }
    }, 2000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [entry.resumeId, entry.status, onStatusChange]);

  const isPending = entry.status === "pending";
  const isError = entry.status === "error";
  const isDone = entry.status === "done";

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

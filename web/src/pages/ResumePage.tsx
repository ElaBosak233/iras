/**
 * 简历详情页
 * 路由：/resume/:id
 *
 * 功能：
 *   1. 进入页面时立即轮询解析状态（每 2 秒），直到 done 或 error
 *   2. 解析完成后展示 ResumeCard（左侧）和 MatchPanel（右侧）双栏布局
 *   3. 用户提交 JD 后，轮询匹配状态（每 1.5 秒），直到评分完成
 *
 * 轮询实现：
 *   - 简历解析轮询：useEffect + setInterval，组件卸载时清除
 *   - 匹配评分轮询：Promise 包装的 setInterval，await 等待结果
 */
import { AlertCircle, ArrowLeft, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { MatchPanel } from "@/components/MatchPanel";
import { ResumeCard } from "@/components/ResumeCard";
import { getMatch, getResume, submitMatch } from "@/lib/api";
import type { MatchResult, ResumeInfo } from "@/types/resume";

export function ResumePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // 简历解析状态
  const [status, setStatus] = useState<"pending" | "done" | "error">("pending");
  const [resumeInfo, setResumeInfo] = useState<ResumeInfo | null>(null);
  const [cached, setCached] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);

  // 匹配评分状态
  const [matchResult, setMatchResult] = useState<{
    match_result: MatchResult;
    cached: boolean;
  } | null>(null);
  const [matchLoading, setMatchLoading] = useState(false);
  const [matchError, setMatchError] = useState<string | null>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 轮询简历解析状态，直到 done 或 error
  useEffect(() => {
    if (!id) return;

    const poll = async () => {
      try {
        const res = await getResume(id);
        if (res.status === "done") {
          setResumeInfo(res.resume_info ?? null);
          setCached(res.cached);
          setStatus("done");
          if (pollRef.current) clearInterval(pollRef.current);
        } else if (res.status === "error") {
          setParseError(res.error ?? "解析失败");
          setStatus("error");
          if (pollRef.current) clearInterval(pollRef.current);
        }
        // pending 状态继续轮询
      } catch {
        // 忽略瞬时网络错误
      }
    };

    // 立即执行一次，避免等待第一个 interval
    poll();
    pollRef.current = setInterval(poll, 2000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [id]);

  const handleMatch = async (jd: string) => {
    if (!id) return;
    setMatchLoading(true);
    setMatchError(null);
    setMatchResult(null);
    try {
      const { match_id } = await submitMatch(id, jd);

      // 用 Promise 包装轮询，await 等待评分完成后再更新 UI
      await new Promise<void>((resolve, reject) => {
        const timer = setInterval(async () => {
          try {
            const res = await getMatch(id, match_id);
            if (res.status === "done" && res.match_result) {
              clearInterval(timer);
              setMatchResult({
                match_result: res.match_result,
                cached: res.cached,
              });
              resolve();
            } else if (res.status === "error") {
              clearInterval(timer);
              reject(new Error(res.error ?? "匹配失败"));
            }
          } catch (e) {
            clearInterval(timer);
            reject(e);
          }
        }, 1500);
      });
    } catch (e: unknown) {
      setMatchError(e instanceof Error ? e.message : "匹配失败，请重试");
    } finally {
      setMatchLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate("/")}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            返回列表
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* 解析中：全屏居中加载动画 */}
        {status === "pending" && (
          <div className="flex flex-col items-center justify-center gap-3 py-24 text-gray-400">
            <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            <span className="text-sm">正在解析简历，请稍候...</span>
          </div>
        )}

        {/* 解析失败：错误提示 */}
        {status === "error" && (
          <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {parseError}
          </div>
        )}

        {/* 解析完成：左侧简历详情 + 右侧匹配面板 */}
        {status === "done" && resumeInfo && (
          <div className="space-y-4">
            {matchError && (
              <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                <AlertCircle className="h-4 w-4 shrink-0" />
                {matchError}
              </div>
            )}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <ResumeCard info={resumeInfo} cached={cached} />
              <MatchPanel
                onMatch={handleMatch}
                result={matchResult}
                loading={matchLoading}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

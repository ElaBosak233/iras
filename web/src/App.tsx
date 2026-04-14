/**
 * 主页面组件（App.tsx）
 * 负责：
 *   - 页面挂载时从服务端恢复历史简历列表（listResumes + getResume）
 *   - 处理 PDF 上传，立即将新简历以 pending 状态插入列表顶部
 *   - 通过 onStatusChange 回调接收子组件的状态更新，统一管理 resumes 状态
 *
 * 文件名映射（resume_id → 原始文件名）存储在 localStorage，
 * 因为服务端不保存文件名，刷新后需从本地恢复。
 */
import { AlertCircle, FileSearch } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { ResumeEntry } from "@/components/ResumeListItem";
import { ResumeListItem } from "@/components/ResumeListItem";
import { UploadZone } from "@/components/UploadZone";
import { getResume, listResumes, submitResume } from "@/lib/api";

// localStorage key，用于持久化 resume_id → 文件名的映射
const STORAGE_KEY = "iras_resume_filenames";

function loadFileNames(): Record<string, string> {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function saveFileName(resumeId: string, fileName: string) {
  const map = loadFileNames();
  map[resumeId] = fileName;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
}

export default function App() {
  const [resumes, setResumes] = useState<ResumeEntry[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // 页面挂载时从服务端恢复历史简历列表，并获取每条记录的实时状态
  useEffect(() => {
    listResumes()
      .then(async (ids) => {
        if (ids.length === 0) return;
        const fileNames = loadFileNames();
        const entries = await Promise.all(
          ids.map(async (id) => {
            try {
              const res = await getResume(id);
              return {
                resumeId: id,
                fileName: fileNames[id] ?? id,  // 无文件名时降级显示 id
                status: res.status,
                resumeInfo: res.resume_info ?? null,
                cached: res.cached,
                error: res.error ?? null,
              } satisfies ResumeEntry;
            } catch {
              // 单条记录获取失败时跳过，不影响其他记录
              return null;
            }
          })
        );
        setResumes(entries.filter((e): e is ResumeEntry => e !== null));
      })
      .catch(() => {
        // 会话不存在时 listResumes 可能返回空或报错，静默忽略
      });
  }, []);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setUploadError(null);
    try {
      const { resume_id } = await submitResume(file);
      saveFileName(resume_id, file.name);
      // 立即插入 pending 状态，ResumeListItem 会自动开始轮询
      setResumes((prev) => [
        {
          resumeId: resume_id,
          fileName: file.name,
          status: "pending",
          resumeInfo: null,
          cached: false,
          error: null,
        },
        ...prev,
      ]);
    } catch (e: unknown) {
      setUploadError(e instanceof Error ? e.message : "上传失败，请重试");
    } finally {
      setUploading(false);
    }
  };

  // 子组件通过此回调上报状态变化（pending → done/error），使用 patch 局部更新
  const handleStatusChange = useCallback(
    (id: string, patch: Partial<ResumeEntry>) => {
      setResumes((prev) =>
        prev.map((r) => (r.resumeId === id ? { ...r, ...patch } : r))
      );
    },
    []
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center gap-3">
          <FileSearch className="h-6 w-6 text-blue-600" />
          <h1 className="text-xl font-semibold text-gray-900">IRAS</h1>
          <span className="text-sm text-gray-400">智能简历分析系统</span>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-4">
        {uploadError && (
          <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {uploadError}
          </div>
        )}

        <UploadZone onUpload={handleUpload} loading={uploading} />

        {resumes.map((entry) => (
          <ResumeListItem
            key={entry.resumeId}
            entry={entry}
            onStatusChange={handleStatusChange}
          />
        ))}
      </main>
    </div>
  );
}

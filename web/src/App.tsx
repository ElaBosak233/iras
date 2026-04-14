import { AlertCircle, FileSearch } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { ResumeEntry } from "@/components/ResumeListItem";
import { ResumeListItem } from "@/components/ResumeListItem";
import { UploadZone } from "@/components/UploadZone";
import { getResume, listResumes, submitResume } from "@/lib/api";

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

  // Restore resume list from server on mount, fetching real status for each
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
                fileName: fileNames[id] ?? id,
                status: res.status,
                resumeInfo: res.resume_info ?? null,
                cached: res.cached,
                error: res.error ?? null,
              } satisfies ResumeEntry;
            } catch {
              // If we can't fetch status, skip this entry
              return null;
            }
          })
        );
        setResumes(entries.filter((e): e is ResumeEntry => e !== null));
      })
      .catch(() => {
        /* session may not exist yet, ignore */
      });
  }, []);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setUploadError(null);
    try {
      const { resume_id } = await submitResume(file);
      saveFileName(resume_id, file.name);
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

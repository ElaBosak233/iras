/**
 * 拖拽上传区域组件
 * 支持两种上传方式：
 *   1. 拖拽 PDF 文件到区域内释放
 *   2. 点击区域弹出文件选择框
 *
 * 拖拽状态（dragging）会改变边框颜色，提供视觉反馈。
 * loading 状态下禁用交互，显示加载动画。
 */
import { Loader2, Upload } from "lucide-react";
import { useCallback, useState } from "react";
import { cn } from "@/lib/utils";

interface UploadZoneProps {
  onUpload: (file: File) => void;
  loading: boolean;
}

export function UploadZone({ onUpload, loading }: UploadZoneProps) {
  const [dragging, setDragging] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      // 只接受 PDF 文件，其他格式静默忽略
      if (file?.type === "application/pdf") onUpload(file);
    },
    [onUpload]
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
  };

  return (
    // 使用 label 包裹隐藏的 input，点击整个区域即可触发文件选择
    <label
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-12 cursor-pointer transition-colors",
        dragging
          ? "border-blue-500 bg-blue-50"
          : "border-gray-300 hover:border-blue-400 hover:bg-gray-50",
        loading && "pointer-events-none opacity-60"
      )}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      <input
        type="file"
        accept=".pdf"
        className="hidden"
        onChange={handleChange}
        disabled={loading}
      />
      {loading ? (
        <Loader2 className="h-10 w-10 text-blue-500 animate-spin" />
      ) : (
        <Upload className="h-10 w-10 text-gray-400" />
      )}
      <div className="text-center">
        <p className="text-sm font-medium text-gray-700">
          {loading ? "正在解析简历..." : "拖拽 PDF 文件到此处，或点击上传"}
        </p>
        <p className="text-xs text-gray-400 mt-1">仅支持 PDF 格式，最大 10MB</p>
      </div>
    </label>
  );
}

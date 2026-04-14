/**
 * 工具函数
 * cn：合并 Tailwind CSS 类名，处理条件类名和类名冲突。
 * 使用 clsx 处理条件逻辑，twMerge 解决 Tailwind 类名冲突（如 p-2 和 p-4 同时存在时保留后者）。
 */
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

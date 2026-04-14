import {
  Award,
  BookOpen,
  Briefcase,
  Code2,
  FolderOpen,
  Globe,
  GraduationCap,
  User,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type {
  EducationItem,
  ProjectItem,
  ResumeInfo,
  WorkExperienceItem,
} from "@/types/resume";

interface ResumeCardProps {
  info: ResumeInfo;
  cached: boolean;
}

function InfoRow({ label, value }: { label: string; value: string | null }) {
  if (!value) return null;
  return (
    <div className="flex gap-2 text-sm">
      <span className="text-gray-500 min-w-24 shrink-0">{label}</span>
      <span className="text-gray-900 break-all">{value}</span>
    </div>
  );
}

function TagList({ label, items }: { label: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div className="space-y-1">
      <span className="text-sm text-gray-500">{label}</span>
      <div className="flex flex-wrap gap-1">
        {items.map((item) => (
          <Badge key={item} variant="secondary" className="text-xs">
            {item}
          </Badge>
        ))}
      </div>
    </div>
  );
}

function EducationBlock({ item }: { item: EducationItem }) {
  return (
    <div className="border-l-2 border-blue-100 pl-3 space-y-0.5">
      <div className="text-sm font-medium text-gray-800">
        {item.school}
        {item.degree && (
          <span className="ml-2 text-xs font-normal text-gray-500">
            {item.degree}
          </span>
        )}
      </div>
      {item.major && <div className="text-xs text-gray-600">{item.major}</div>}
      {(item.start_date || item.end_date) && (
        <div className="text-xs text-gray-400">
          {item.start_date} ~ {item.end_date}
          {item.gpa && <span className="ml-2">GPA: {item.gpa}</span>}
        </div>
      )}
      {item.description && (
        <div className="text-xs text-gray-600 mt-1">{item.description}</div>
      )}
    </div>
  );
}

function WorkBlock({ item }: { item: WorkExperienceItem }) {
  return (
    <div className="border-l-2 border-green-100 pl-3 space-y-0.5">
      <div className="text-sm font-medium text-gray-800">
        {item.position}
        {item.company && (
          <span className="ml-2 text-xs font-normal text-gray-500">
            @ {item.company}
          </span>
        )}
      </div>
      {(item.start_date || item.end_date || item.location) && (
        <div className="text-xs text-gray-400">
          {item.start_date} ~ {item.end_date}
          {item.location && <span className="ml-2">{item.location}</span>}
        </div>
      )}
      {item.description && (
        <div className="text-xs text-gray-600 mt-1 whitespace-pre-line">
          {item.description}
        </div>
      )}
    </div>
  );
}

function ProjectBlock({ item }: { item: ProjectItem }) {
  return (
    <div className="border-l-2 border-purple-100 pl-3 space-y-0.5">
      <div className="text-sm font-medium text-gray-800">
        {item.name}
        {item.role && (
          <span className="ml-2 text-xs font-normal text-gray-500">
            {item.role}
          </span>
        )}
      </div>
      {item.tech_stack.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1">
          {item.tech_stack.map((t) => (
            <Badge key={t} variant="outline" className="text-xs px-1 py-0">
              {t}
            </Badge>
          ))}
        </div>
      )}
      {(item.start_date || item.end_date) && (
        <div className="text-xs text-gray-400">
          {item.start_date} ~ {item.end_date}
        </div>
      )}
      {item.description && (
        <div className="text-xs text-gray-600 mt-1 whitespace-pre-line">
          {item.description}
        </div>
      )}
      {item.url && (
        <a
          href={item.url}
          target="_blank"
          rel="noreferrer"
          className="text-xs text-blue-500 hover:underline"
        >
          {item.url}
        </a>
      )}
    </div>
  );
}

export function ResumeCard({ info, cached }: ResumeCardProps) {
  const bi = info.basic_info;
  const ji = info.job_info;
  const bgi = info.background_info;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h2 className="text-lg font-semibold">简历解析结果</h2>
        {cached && <Badge variant="secondary">缓存</Badge>}
      </div>

      {/* 基本信息 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <User className="h-4 w-4 text-blue-500" />
            基本信息
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <InfoRow label="姓名" value={bi.name} />
          <InfoRow label="性别" value={bi.gender} />
          <InfoRow label="出生日期" value={bi.birth_date} />
          <InfoRow label="电话" value={bi.phone} />
          <InfoRow label="邮箱" value={bi.email} />
          <InfoRow label="地址" value={bi.address} />
          <InfoRow label="微信" value={bi.wechat} />
          {bi.github && (
            <div className="flex gap-2 text-sm">
              <span className="text-gray-500 min-w-24 shrink-0">GitHub</span>
              <a
                href={bi.github}
                target="_blank"
                rel="noreferrer"
                className="text-blue-500 hover:underline break-all"
              >
                {bi.github}
              </a>
            </div>
          )}
          {bi.linkedin && (
            <div className="flex gap-2 text-sm">
              <span className="text-gray-500 min-w-24 shrink-0">LinkedIn</span>
              <a
                href={bi.linkedin}
                target="_blank"
                rel="noreferrer"
                className="text-blue-500 hover:underline break-all"
              >
                {bi.linkedin}
              </a>
            </div>
          )}
          {bi.website && (
            <div className="flex gap-2 text-sm">
              <span className="text-gray-500 min-w-24 shrink-0">
                <Globe className="inline h-3.5 w-3.5 mr-1" />
                个人网站
              </span>
              <a
                href={bi.website}
                target="_blank"
                rel="noreferrer"
                className="text-blue-500 hover:underline break-all"
              >
                {bi.website}
              </a>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 求职信息 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Briefcase className="h-4 w-4 text-blue-500" />
            求职信息
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <InfoRow label="求职意向" value={ji.intention} />
          <InfoRow label="期望薪资" value={ji.expected_salary} />
          <InfoRow label="工作类型" value={ji.job_type} />
          <InfoRow label="到岗时间" value={ji.available_date} />
          <InfoRow label="期望地点" value={ji.preferred_location} />
        </CardContent>
      </Card>

      {/* 教育经历 */}
      {bgi.education_list.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <GraduationCap className="h-4 w-4 text-blue-500" />
              教育经历
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {bgi.education_list.map((edu, i) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: static list
              <EducationBlock key={i} item={edu} />
            ))}
          </CardContent>
        </Card>
      )}

      {/* 工作经历 */}
      {bgi.work_experience.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Briefcase className="h-4 w-4 text-green-500" />
              工作经历
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {bgi.work_experience.map((w, i) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: static list
              <WorkBlock key={i} item={w} />
            ))}
          </CardContent>
        </Card>
      )}

      {/* 项目经历 */}
      {bgi.project_experience.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <FolderOpen className="h-4 w-4 text-purple-500" />
              项目经历
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {bgi.project_experience.map((p, i) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: static list
              <ProjectBlock key={i} item={p} />
            ))}
          </CardContent>
        </Card>
      )}

      {/* 技能 & 其他 */}
      {(bgi.skills.length > 0 ||
        bgi.certifications.length > 0 ||
        bgi.languages.length > 0 ||
        bgi.awards.length > 0 ||
        bgi.publications.length > 0 ||
        bgi.open_source.length > 0) && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Code2 className="h-4 w-4 text-blue-500" />
              技能 & 其他
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <TagList label="技能" items={bgi.skills} />
            <TagList label="语言能力" items={bgi.languages} />
            <TagList label="证书" items={bgi.certifications} />
            {bgi.awards.length > 0 && (
              <div className="space-y-1">
                <div className="flex items-center gap-1 text-sm text-gray-500">
                  <Award className="h-3.5 w-3.5" />
                  获奖经历
                </div>
                <ul className="space-y-0.5 pl-4">
                  {bgi.awards.map((a, i) => (
                    // biome-ignore lint/suspicious/noArrayIndexKey: static list
                    <li key={i} className="text-sm text-gray-700 list-disc">
                      {a}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {bgi.publications.length > 0 && (
              <div className="space-y-1">
                <div className="flex items-center gap-1 text-sm text-gray-500">
                  <BookOpen className="h-3.5 w-3.5" />
                  论文 / 出版物
                </div>
                <ul className="space-y-0.5 pl-4">
                  {bgi.publications.map((p, i) => (
                    // biome-ignore lint/suspicious/noArrayIndexKey: static list
                    <li key={i} className="text-sm text-gray-700 list-disc">
                      {p}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {bgi.open_source.length > 0 && (
              <div className="space-y-1">
                <div className="flex items-center gap-1 text-sm text-gray-500">
                  <Code2 className="h-3.5 w-3.5" />
                  开源贡献
                </div>
                <ul className="space-y-0.5 pl-4">
                  {bgi.open_source.map((o, i) => (
                    // biome-ignore lint/suspicious/noArrayIndexKey: static list
                    <li key={i} className="text-sm text-gray-700 list-disc">
                      {o}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

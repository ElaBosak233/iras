import { Loader2, Target } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { MatchResult } from "@/types/resume";

interface MatchPanelProps {
  onMatch: (jd: string) => Promise<void>;
  result: { match_result: MatchResult; cached: boolean } | null;
  loading: boolean;
}

function ScoreRing({ score }: { score: number }) {
  const color =
    score >= 75
      ? "text-green-600"
      : score >= 50
        ? "text-yellow-600"
        : "text-red-600";
  return (
    <div className="flex flex-col items-center gap-1">
      <span className={`text-5xl font-bold ${color}`}>{score.toFixed(0)}</span>
      <span className="text-sm text-gray-500">综合评分</span>
    </div>
  );
}

export function MatchPanel({ onMatch, result, loading }: MatchPanelProps) {
  const [jd, setJd] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (jd.trim()) await onMatch(jd.trim());
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">岗位匹配</h2>

      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handleSubmit} className="space-y-3">
            <textarea
              className="w-full rounded-lg border border-gray-300 p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={6}
              placeholder="粘贴岗位需求描述..."
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              disabled={loading}
            />
            <Button
              type="submit"
              disabled={loading || !jd.trim()}
              className="w-full"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  匹配中...
                </>
              ) : (
                <>
                  <Target className="h-4 w-4 mr-2" />
                  开始匹配
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center justify-between text-base">
              <span>匹配结果</span>
              {result.cached && <Badge variant="secondary">缓存</Badge>}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="flex justify-center py-2">
              <ScoreRing score={result.match_result.score} />
            </div>

            <div className="space-y-3">
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">技能匹配率</span>
                  <span className="font-medium">
                    {(result.match_result.skill_match_rate * 100).toFixed(0)}%
                  </span>
                </div>
                <Progress value={result.match_result.skill_match_rate * 100} />
              </div>
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">经验相关性</span>
                  <span className="font-medium">
                    {(result.match_result.experience_relevance * 100).toFixed(
                      0
                    )}
                    %
                  </span>
                </div>
                <Progress
                  value={result.match_result.experience_relevance * 100}
                />
              </div>
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">适应潜力</span>
                  <span className="font-medium">
                    {(result.match_result.tolerance_score * 100).toFixed(0)}%
                  </span>
                </div>
                <Progress value={result.match_result.tolerance_score * 100} />
              </div>
            </div>

            <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3">
              {result.match_result.analysis}
            </p>

            {result.match_result.growth_outlook && (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  入职走向预测
                </p>
                <p className="text-sm text-blue-800 bg-blue-50 rounded-lg p-3">
                  {result.match_result.growth_outlook}
                </p>
              </div>
            )}

            {result.match_result.matched_keywords.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  匹配关键词
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {result.match_result.matched_keywords.map((kw) => (
                    <Badge key={kw} variant="success">
                      {kw}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {result.match_result.transferable_skills.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  可迁移技能
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {result.match_result.transferable_skills.map((kw) => (
                    <Badge key={kw} variant="secondary">
                      {kw}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {result.match_result.missing_keywords.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  缺失关键词
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {result.match_result.missing_keywords.map((kw) => (
                    <Badge key={kw} variant="destructive">
                      {kw}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {!result && !loading && (
        <p className="text-sm text-gray-400 text-center py-4">
          上传简历后，输入岗位需求进行匹配分析
        </p>
      )}
    </div>
  );
}

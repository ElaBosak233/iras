# IRAS — 智能简历分析系统

AI 赋能的简历解析、关键信息提取与岗位匹配平台。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.13+ · FastAPI · uv · LangChain |
| AI | 硅基流动 API（DeepSeek VL OCR · GLM-5.1 提取 · MiniMax M2.5 评分） |
| 缓存 | Redis |
| 前端 | Vite · React 19 · TypeScript · Tailwind CSS v4 · Biome |

## 项目结构

```
iras/
├── app/
│   ├── api/
│   │   ├── resume.py         # 简历上传、状态查询、列表接口
│   │   └── match.py          # 岗位匹配提交与状态查询接口
│   ├── core/
│   │   ├── config.py         # 环境变量配置（pydantic-settings）
│   │   ├── cache.py          # Redis 连接管理（懒加载单例）
│   │   └── session.py        # 基于 Cookie 的轻量级会话管理
│   ├── models/
│   │   └── resume.py         # Pydantic 数据模型（简历 + 匹配结果）
│   ├── services/
│   │   ├── pdf_service.py    # PDF 文本提取 + DeepSeek VL OCR 回退
│   │   ├── extraction_service.py  # LLM 结构化信息提取
│   │   ├── scoring_service.py     # LLM 简历与 JD 匹配评分
│   │   └── enrichment_service.py  # 外部链接（GitHub/论文）内容抓取
│   └── main.py               # FastAPI 应用入口、CORS、路由注册
├── web/
│   ├── src/
│   │   ├── components/       # UI 组件（上传区、简历卡片、匹配面板等）
│   │   ├── pages/            # 页面组件（主页、简历详情页）
│   │   ├── lib/              # API 客户端、工具函数
│   │   └── types/            # TypeScript 类型定义
│   └── vite.config.ts
├── main.py                   # 直接运行入口（uvicorn）
└── pyproject.toml
```

## 快速开始

### 前置条件

- Python 3.13+
- Node.js 20+
- Redis（本地运行或 Docker）
- 硅基流动 API Key（[申请地址](https://cloud.siliconflow.cn)）

### 后端

```bash
cp .env.example .env
# 编辑 .env，填入 SILICONFLOW_API_KEY
uv run uvicorn app.main:app --reload
```

API 文档：http://localhost:8000/docs

### 前端

```bash
cd web
npm install
npm run dev
```

访问：http://localhost:5173

### Redis（Docker）

```bash
docker run -d -p 6379:6379 redis:alpine
```

## API 接口

### 上传简历

```
POST /api/resumes
Content-Type: multipart/form-data

file: <PDF 文件>
```

返回 `resume_id`，后台异步解析，前端轮询以下接口获取结果：

```
GET /api/resumes/{resume_id}
```

### 岗位匹配

```
POST /api/resumes/{resume_id}/matches
Content-Type: application/json

{ "job_description": "岗位需求描述..." }
```

返回 `match_id`，后台异步评分，前端轮询以下接口获取结果：

```
GET /api/resumes/{resume_id}/matches/{match_id}
```

## 功能说明

- **PDF 解析**：优先直接提取文本；扫描件（文本 < 100 字符）自动调用 DeepSeek VL OCR
- **信息提取**：GLM-5.1 从简历文本中提取姓名、联系方式、教育/工作/项目经历、技能等结构化字段
- **外部富化**：自动抓取简历中的学术/开源链接（Google Scholar、HuggingFace、GitLab 等）作为补充上下文
- **智能评分**：MiniMax M2.5 对简历与 JD 进行综合评分，输出技能匹配率、经验相关性、适应潜力、关键词分析及成长预测
- **缓存加速**：Redis 缓存解析结果（24h TTL），相同 PDF 和相同 JD 组合命中缓存直接返回，不重复调用 LLM
- **会话隔离**：基于 Cookie 的轻量级会话，每个用户只能访问自己上传的简历

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `SILICONFLOW_API_KEY` | — | 硅基流动 API Key（必填） |
| `SILICONFLOW_BASE_URL` | `https://api.siliconflow.cn/v1` | API 基础 URL |
| `REDIS_URL` | `redis://localhost:6379` | Redis 连接地址 |

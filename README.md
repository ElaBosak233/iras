# IRAS — 智能简历分析系统

AI 赋能的简历解析、关键信息提取与岗位匹配平台。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python · FastAPI · uv · LangChain · LangGraph |
| AI | 硅基流动 API（DeepSeek VL OCR · GLM-4 Flash 评分） |
| 缓存 | Redis |
| 前端 | Vite · React 19 · TypeScript · Tailwind CSS v4 · Biome |

## 项目结构

```
iras/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI 路由
│   │   ├── core/         # 配置、Redis 连接
│   │   ├── models/       # Pydantic 数据模型
│   │   └── services/     # PDF 解析、信息提取、评分
│   ├── main.py
│   └── pyproject.toml
└── frontend/
    ├── src/
    │   ├── components/   # UI 组件
    │   ├── lib/          # API 客户端、工具函数
    │   └── types/        # TypeScript 类型定义
    └── package.json
```

## 快速开始

### 前置条件

- Python 3.13+
- Node.js 20+
- Redis（本地运行或 Docker）
- 硅基流动 API Key

### 后端

```bash
cd backend
cp .env.example .env
# 编辑 .env，填入 SILICONFLOW_API_KEY
uv run uvicorn app.main:app --reload
```

API 文档：http://localhost:8000/docs

### 前端

```bash
cd frontend
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
POST /api/resume/upload
Content-Type: multipart/form-data

file: <PDF 文件>
```

### 岗位匹配

```
POST /api/match/{resume_id}
Content-Type: application/json

{ "job_description": "岗位需求描述..." }
```

## 功能说明

- **模块一**：上传 PDF，自动提取文本；扫描件自动调用 DeepSeek VL OCR
- **模块二**：LLM 提取姓名、电话、邮箱、地址、求职意向、薪资、学历、项目经历
- **模块三**：GLM-4 Flash 对简历与岗位需求进行综合评分，输出技能匹配率、经验相关性、关键词分析
- **模块四**：Redis 缓存解析结果（24h TTL），相同 PDF 和相同 JD 组合命中缓存直接返回
- **模块五**：拖拽上传 + 结构化展示 + 实时匹配评分可视化

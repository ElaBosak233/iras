# 应用配置模块
# 使用 pydantic-settings 从环境变量或 .env 文件中读取配置，
# 所有字段均可通过同名大写环境变量覆盖（如 SILICONFLOW_API_KEY）。
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 硅基流动 API Key，用于调用 DeepSeek OCR 和 GLM 系列模型
    siliconflow_api_key: str = ""
    # 硅基流动 API 基础 URL，兼容 OpenAI 接口格式
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"
    # Redis 连接 URL，用于缓存解析结果和会话数据
    redis_url: str = "redis://localhost:6379"

    class Config:
        env_file = ".env"


settings = Settings()

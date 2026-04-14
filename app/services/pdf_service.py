# PDF 解析服务
# 负责从 PDF 文件中提取文本，支持两种模式：
#   1. 直接文本提取（PyPDF2）：适用于可选中文本的 PDF
#   2. OCR 回退（DeepSeek VL）：当直接提取文本过少时（扫描件），
#      将 PDF 转为图片后调用多模态 LLM 进行 OCR
import base64
import hashlib
import io
import logging
import re

from PyPDF2 import PdfReader
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_llm(model: str = "deepseek-ai/DeepSeek-OCR") -> ChatOpenAI:
    """构造用于 OCR 的 LLM 客户端（兼容 OpenAI 接口的硅基流动 API）。"""
    return ChatOpenAI(
        model=model,  # ty: ignore[unknown-argument]
        api_key=settings.siliconflow_api_key,  # ty: ignore[unknown-argument]
        base_url=settings.siliconflow_base_url,  # ty: ignore[unknown-argument]
        temperature=0.1,   # 低温度保证 OCR 输出稳定，减少幻觉
        request_timeout=120,
    )


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """使用 PyPDF2 直接从 PDF 中提取文本（适用于可选中文本的 PDF）。"""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages_text = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)
    return "\n".join(pages_text)


async def ocr_pdf_with_deepseek(pdf_bytes: bytes) -> str:
    """将 PDF 转为图片后，调用 DeepSeek VL 多模态模型进行 OCR。

    仅在直接文本提取失败（扫描件）时调用。最多处理前 5 页，
    避免超出模型上下文限制和增加不必要的 API 费用。
    如果 pdf2image 不可用，回退到 PyPDF2 直接提取。
    """
    try:
        from pdf2image import convert_from_bytes  # ty: ignore[unresolved-import]

        # dpi=150 在清晰度和文件大小之间取得平衡
        images = convert_from_bytes(pdf_bytes, dpi=150)
        base64_images = []
        for img in images[:5]:  # 最多处理 5 页，避免超出模型限制
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            base64_images.append(base64.b64encode(buf.getvalue()).decode())
    except Exception:
        # pdf2image 依赖 poppler，若未安装则回退到直接提取
        return extract_text_from_pdf(pdf_bytes)

    if not base64_images:
        return extract_text_from_pdf(pdf_bytes)

    # 构造多模态消息：先放图片，再放文字指令
    content: list[str | dict] = [
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
        for b64 in base64_images
    ]
    content.append(
        {
            "type": "text",
            "text": "请提取这份简历图片中的所有文字内容，保持原有格式和结构，不要添加任何额外说明。",
        }
    )

    llm = _get_llm(model="deepseek-ai/DeepSeek-OCR")
    response = await llm.ainvoke([HumanMessage(content=content)])
    return str(response.content)


def clean_text(text: str) -> str:
    """清理并规范化提取的文本：去除多余空行、连续空格和不可打印字符。"""
    # 将 3 个以上连续换行压缩为 2 个，保留段落结构
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 将连续空格压缩为单个空格
    text = re.sub(r" {2,}", " ", text)
    # 将非换行的空白字符（制表符等）统一替换为空格
    text = re.sub(r"[^\S\n]+", " ", text)
    text = text.strip()
    return text


def compute_pdf_hash(pdf_bytes: bytes) -> str:
    """计算 PDF 文件的 SHA-256 哈希，用于缓存命中判断。"""
    return hashlib.sha256(pdf_bytes).hexdigest()


async def parse_pdf(pdf_bytes: bytes) -> tuple[str, str]:
    """解析 PDF，返回 (清理后的文本, pdf_hash)。

    策略：
    1. 先尝试 PyPDF2 直接提取文本
    2. 若提取文本少于 100 字符（判定为扫描件），且配置了 API Key，
       则调用 DeepSeek VL OCR
    """
    pdf_hash = compute_pdf_hash(pdf_bytes)
    logger.info("parse_pdf start, size=%d, hash=%s", len(pdf_bytes), pdf_hash[:8])

    # 第一步：尝试直接文本提取
    text = extract_text_from_pdf(pdf_bytes)
    logger.info("direct text extraction: text_len=%d", len(text.strip()))

    # 第二步：文本过少说明是扫描件，启用 OCR 回退
    if len(text.strip()) < 100 and settings.siliconflow_api_key:
        logger.info("text too short, falling back to OCR")
        try:
            text = await ocr_pdf_with_deepseek(pdf_bytes)
            logger.info("OCR done, text_len=%d", len(text.strip()))
        except Exception as e:
            logger.exception("OCR failed: %s", e)
            raise

    return clean_text(text), pdf_hash

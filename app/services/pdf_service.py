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
    return ChatOpenAI(
        model=model,  # ty: ignore[unknown-argument]
        api_key=settings.siliconflow_api_key,  # ty: ignore[unknown-argument]
        base_url=settings.siliconflow_base_url,  # ty: ignore[unknown-argument]
        temperature=0.1,
        request_timeout=120,
    )


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF using PyPDF2."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages_text = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)
    return "\n".join(pages_text)


async def ocr_pdf_with_deepseek(pdf_bytes: bytes) -> str:
    """Use DeepSeek VL model via SiliconFlow to OCR PDF pages."""
    try:
        from pdf2image import convert_from_bytes  # ty: ignore[unresolved-import]

        images = convert_from_bytes(pdf_bytes, dpi=150)
        base64_images = []
        for img in images[:5]:  # limit to 5 pages
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            base64_images.append(base64.b64encode(buf.getvalue()).decode())
    except Exception:
        return extract_text_from_pdf(pdf_bytes)

    if not base64_images:
        return extract_text_from_pdf(pdf_bytes)

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
    """Clean and normalize extracted text."""
    # Remove excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    # Remove non-printable characters except newlines
    text = re.sub(r"[^\S\n]+", " ", text)
    text = text.strip()
    return text


def compute_pdf_hash(pdf_bytes: bytes) -> str:
    return hashlib.sha256(pdf_bytes).hexdigest()


async def parse_pdf(pdf_bytes: bytes) -> tuple[str, str]:
    """Parse PDF and return (text, pdf_hash)."""
    pdf_hash = compute_pdf_hash(pdf_bytes)
    logger.info("parse_pdf start, size=%d, hash=%s", len(pdf_bytes), pdf_hash[:8])

    # Try direct text extraction first
    text = extract_text_from_pdf(pdf_bytes)
    logger.info("direct text extraction: text_len=%d", len(text.strip()))

    # If text is too short (likely scanned PDF), use OCR
    if len(text.strip()) < 100 and settings.siliconflow_api_key:
        logger.info("text too short, falling back to OCR")
        try:
            text = await ocr_pdf_with_deepseek(pdf_bytes)
            logger.info("OCR done, text_len=%d", len(text.strip()))
        except Exception as e:
            logger.exception("OCR failed: %s", e)
            raise

    return clean_text(text), pdf_hash

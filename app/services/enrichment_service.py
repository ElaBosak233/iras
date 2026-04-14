# 外部链接富化服务
# 从简历文本中提取有价值的外部链接（学术论文、开源项目等），
# 抓取其页面内容作为补充上下文，帮助评分模型更全面地了解候选人。
#
# 只抓取白名单域名（学术/开源平台），避免抓取个人隐私页面或无关网站。
# 整个富化过程有总超时限制，不会阻塞主流程。
import asyncio
import re
from urllib.parse import urlparse

import httpx


# 匹配 http/https URL 的正则表达式
_URL_RE = re.compile(r"https?://[^\s\)\]\>\"\']+", re.IGNORECASE)

# 允许富化的域名白名单：仅抓取学术/开源平台，避免隐私风险
_ENRICHABLE_HOSTS = {
    "scholar.google.com",
    "semanticscholar.org",
    "dl.acm.org",
    "ieeexplore.ieee.org",
    "researchgate.net",
    "huggingface.co",
    "gitlab.com",
    "bitbucket.org",
}

_MAX_LINKS = 8              # 每份简历最多处理的链接数
_FETCH_TIMEOUT = 10         # 单个链接的请求超时（秒）
_MAX_CONTENT_PER_LINK = 2000  # 每个链接保留的最大字符数，控制上下文长度
_ENRICH_TOTAL_TIMEOUT = 30  # 整个富化过程的总超时（秒），防止拖慢解析流程


def _is_enrichable(url: str) -> bool:
    """判断 URL 是否在白名单域名内（支持子域名匹配）。"""
    try:
        host = urlparse(url).netloc.lower().lstrip("www.")
        return any(host == h or host.endswith("." + h) for h in _ENRICHABLE_HOSTS)
    except Exception:
        return False


def extract_links(text: str) -> list[str]:
    """从文本中提取去重后的可富化 URL，最多返回 _MAX_LINKS 个。"""
    seen: set[str] = set()
    result: list[str] = []
    for url in _URL_RE.findall(text):
        url = url.rstrip(".,;)")  # 去除 URL 末尾可能粘连的标点符号
        if url not in seen and _is_enrichable(url):
            seen.add(url)
            result.append(url)
            if len(result) >= _MAX_LINKS:
                break
    return result


async def _fetch_text(client: httpx.AsyncClient, url: str) -> str:
    """抓取 URL 页面，去除 HTML 标签后返回纯文本片段。
    任何异常（超时、404、网络错误）均静默返回空字符串，不影响主流程。
    """
    try:
        r = await client.get(url, timeout=_FETCH_TIMEOUT, follow_redirects=True)
        if r.status_code != 200:
            return ""
        # 简单去除 HTML 标签，不依赖 BeautifulSoup 等重型库
        text = re.sub(r"<[^>]+>", " ", r.text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:_MAX_CONTENT_PER_LINK]
    except Exception:
        return ""


async def enrich_from_links(text: str) -> str:
    """从简历文本中提取外部链接，并发抓取内容，返回拼接后的补充上下文字符串。

    返回格式：
        [来源: https://...]\n<页面内容片段>

        [来源: https://...]\n<页面内容片段>

    若无可富化链接或全部抓取失败，返回空字符串。
    """
    links = extract_links(text)
    if not links:
        return ""

    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": "IRAS-ResumeEnricher/1.0"},
            follow_redirects=True,
        ) as client:
            # 并发抓取所有链接，整体受 _ENRICH_TOTAL_TIMEOUT 限制
            contents = await asyncio.wait_for(
                asyncio.gather(
                    *[_fetch_text(client, url) for url in links], return_exceptions=True
                ),
                timeout=_ENRICH_TOTAL_TIMEOUT,
            )
    except asyncio.TimeoutError:
        # 超时时静默返回空，不影响简历解析主流程
        return ""

    sections: list[str] = []
    for url, content in zip(links, contents):
        if isinstance(content, Exception) or not content:
            continue
        if content.strip():
            sections.append(f"[来源: {url}]\n{content.strip()}")

    return "\n\n".join(sections)

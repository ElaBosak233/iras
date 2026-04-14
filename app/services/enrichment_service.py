import asyncio
import re
from urllib.parse import urlparse

import httpx


# Patterns for links worth enriching
_URL_RE = re.compile(r"https?://[^\s\)\]\>\"\']+", re.IGNORECASE)

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

_MAX_LINKS = 8
_FETCH_TIMEOUT = 10  # seconds per request
_MAX_CONTENT_PER_LINK = 2000  # chars to keep per fetched page
_ENRICH_TOTAL_TIMEOUT = 30  # seconds for the entire enrichment process


def _is_enrichable(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower().lstrip("www.")
        return any(host == h or host.endswith("." + h) for h in _ENRICHABLE_HOSTS)
    except Exception:
        return False


def extract_links(text: str) -> list[str]:
    """Return unique enrichable URLs found in text, capped at _MAX_LINKS."""
    seen: set[str] = set()
    result: list[str] = []
    for url in _URL_RE.findall(text):
        url = url.rstrip(".,;)")  # strip trailing punctuation
        if url not in seen and _is_enrichable(url):
            seen.add(url)
            result.append(url)
            if len(result) >= _MAX_LINKS:
                break
    return result


async def _fetch_text(client: httpx.AsyncClient, url: str) -> str:
    """Fetch a URL and return a plain-text snippet."""
    try:
        r = await client.get(url, timeout=_FETCH_TIMEOUT, follow_redirects=True)
        if r.status_code != 200:
            return ""
        text = re.sub(r"<[^>]+>", " ", r.text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:_MAX_CONTENT_PER_LINK]
    except Exception:
        return ""


async def enrich_from_links(text: str) -> str:
    """
    Extract external links from resume text, fetch their content, and return
    a combined context string to be appended to the candidate's information.
    """
    links = extract_links(text)
    if not links:
        return ""

    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": "IRAS-ResumeEnricher/1.0"},
            follow_redirects=True,
        ) as client:
            contents = await asyncio.wait_for(
                asyncio.gather(
                    *[_fetch_text(client, url) for url in links], return_exceptions=True
                ),
                timeout=_ENRICH_TOTAL_TIMEOUT,
            )
    except asyncio.TimeoutError:
        return ""

    sections: list[str] = []
    for url, content in zip(links, contents):
        if isinstance(content, Exception) or not content:
            continue
        if content.strip():
            sections.append(f"[来源: {url}]\n{content.strip()}")

    return "\n\n".join(sections)

import logging
import os
import re

import httpx

logger = logging.getLogger(__name__)

PLATFORM_PATTERNS = {
    "onlinejobs.ph": "OLJ",
    "linkedin.com": "LinkedIn",
    "upwork.com": "Upwork",
    "indeed.com": "Indeed",
    "jobstreet.com": "JobStreet",
    "freelancer.com": "Freelancer",
}

_ERROR_PREFIX = "error:"


def detect_platform(url: str) -> str:
    url_lower = url.lower()
    for domain, name in PLATFORM_PATTERNS.items():
        if domain in url_lower:
            return name
    return "direct"


def is_url(text: str) -> bool:
    return text.strip().startswith(("http://", "https://"))


async def _fetch_with_bs4(url: str) -> str:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return f"{_ERROR_PREFIX} FIRECRAWL_API_KEY not set and beautifulsoup4 not installed — paste the job description text instead"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                follow_redirects=True,
            )
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup.find_all(["nav", "footer", "header", "script", "style", "aside"]):
            tag.decompose()

        main = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", class_=re.compile(r"job|content|description|posting", re.I))
            or soup.find("body")
        )
        raw_text = main.get_text(separator="\n", strip=True) if main else soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in raw_text.splitlines() if len(line.strip()) > 20]
        content = "\n".join(lines)[:4000]

        if len(content) < 100:
            return f"{_ERROR_PREFIX} Couldn't extract enough text from that page — paste the job description text instead"

        return content

    except Exception as e:
        logger.warning(f"url_fetcher: BS4 fallback failed for {url}: {e}")
        return f"{_ERROR_PREFIX} Couldn't read that page — paste the job description text instead"


async def fetch_job_post(url: str) -> str:
    """
    Scrape a job post URL.

    Primary: Firecrawl API (if FIRECRAWL_API_KEY is set).
    Fallback: httpx + BeautifulSoup4.

    Returns extracted job text on success.
    Returns a string starting with "error:" on failure.
    """
    api_key = os.getenv("FIRECRAWL_API_KEY", "")
    if not api_key:
        logger.info("url_fetcher: no Firecrawl key — using BS4 fallback")
        return await _fetch_with_bs4(url)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "url": url,
                    "formats": ["markdown"],
                    "onlyMainContent": True,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content: str = (
            (data.get("data") or {}).get("markdown", "")
            or data.get("markdown", "")
            or ""
        )
        content = content.strip()

        if len(content) < 100:
            logger.warning(f"url_fetcher: Firecrawl returned short content ({len(content)} chars) — trying BS4")
            return await _fetch_with_bs4(url)

        return content[:4000]

    except httpx.HTTPStatusError as e:
        logger.warning(f"url_fetcher: Firecrawl HTTP {e.response.status_code} — trying BS4")
        return await _fetch_with_bs4(url)
    except Exception as e:
        logger.warning(f"url_fetcher: Firecrawl failed ({e}) — trying BS4")
        return await _fetch_with_bs4(url)


def is_fetch_error(text: str) -> bool:
    return text.startswith(_ERROR_PREFIX)


def fetch_error_message(text: str) -> str:
    return text.removeprefix(_ERROR_PREFIX).strip()

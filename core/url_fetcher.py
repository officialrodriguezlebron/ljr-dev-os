import logging
import os

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


async def fetch_job_post(url: str) -> str:
    """
    Scrape a job post URL using Firecrawl API.

    Returns extracted job description text on success.
    Returns a string starting with "error:" on failure — callers should check
    with is_fetch_error() and surface the message to the user.
    """
    api_key = os.getenv("FIRECRAWL_API_KEY", "")
    if not api_key:
        logger.warning("url_fetcher: FIRECRAWL_API_KEY not set")
        return f"{_ERROR_PREFIX} FIRECRAWL_API_KEY not set — paste the job description text instead"

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
            logger.warning(f"url_fetcher: content too short ({len(content)} chars) for {url}")
            return f"{_ERROR_PREFIX} Couldn't read that page — paste the job description text instead"

        # Truncate: KYN/analyze works best with ~2000-3000 chars
        return content[:4000]

    except httpx.HTTPStatusError as e:
        logger.warning(f"url_fetcher: HTTP {e.response.status_code} for {url}")
        return f"{_ERROR_PREFIX} Couldn't read that page (HTTP {e.response.status_code}) — paste the job description text instead"
    except Exception as e:
        logger.warning(f"url_fetcher: failed for {url}: {e}")
        return f"{_ERROR_PREFIX} Couldn't read that page — paste the job description text instead"


def is_fetch_error(text: str) -> bool:
    return text.startswith(_ERROR_PREFIX)


def fetch_error_message(text: str) -> str:
    return text.removeprefix(_ERROR_PREFIX).strip()

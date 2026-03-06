"""
Job-description scraper for LinkedIn and Indeed URLs.

Features
--------
- Respects ``robots.txt`` before fetching.
- Enforces a minimum 2-second delay between requests.
- 24-hour Redis / fallback cache keyed on the URL.
- Cleans HTML artifacts, normalises whitespace and returns
  structured fields: title, company, location, requirements, salary_range.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup, Tag

from app.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "scrape"
_CACHE_TTL = 86_400  # 24 hours

# Track last request time per domain for rate-limiting
_last_request: Dict[str, float] = {}
_MIN_DELAY = 2.0  # seconds

_USER_AGENT = (
    "Mozilla/5.0 (compatible; ResumeMatcherBot/1.0; +https://example.com/bot)"
)

_ALLOWED_DOMAINS = {"linkedin.com", "www.linkedin.com", "indeed.com", "www.indeed.com"}

_REQUEST_TIMEOUT = 15  # seconds


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def scrape_job(url: str) -> Dict[str, Any]:
    """Scrape a LinkedIn or Indeed job URL and return structured data.

    Returns a dict with keys:
        url, title, company, location, requirements, salary_range,
        raw_description, scraped_at
    """
    url = url.strip()
    _validate_url(url)

    # ── Cache hit? ───────────────────────────────────────────────
    cached = cache_get(url, prefix=_CACHE_PREFIX)
    if cached is not None:
        logger.debug("Scrape cache HIT for %s", url)
        return cached

    # ── robots.txt check ─────────────────────────────────────────
    _check_robots(url)

    # ── Rate-limit (2 s per domain) ──────────────────────────────
    _throttle(url)

    # ── Fetch page ───────────────────────────────────────────────
    html = _fetch(url)

    # ── Parse ────────────────────────────────────────────────────
    domain = urlparse(url).hostname or ""
    if "linkedin" in domain:
        result = _parse_linkedin(html, url)
    else:
        result = _parse_indeed(html, url)

    # ── Cache for 24 h ───────────────────────────────────────────
    cache_set(url, result, ttl=_CACHE_TTL, prefix=_CACHE_PREFIX)

    return result


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------

def _validate_url(url: str) -> None:
    """Ensure *url* is an HTTP(S) LinkedIn or Indeed job URL."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http and https URLs are accepted")
    host = (parsed.hostname or "").lower()
    if not any(host == d or host.endswith(f".{d}") for d in _ALLOWED_DOMAINS):
        raise ValueError(
            f"Unsupported domain '{host}'. Only LinkedIn and Indeed URLs are accepted."
        )


# ------------------------------------------------------------------
# robots.txt
# ------------------------------------------------------------------

_robots_cache: Dict[str, RobotFileParser] = {}


def _check_robots(url: str) -> None:
    """Raise ``PermissionError`` if robots.txt disallows fetching *url*."""
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.hostname}"
    robots_url = f"{origin}/robots.txt"

    if robots_url not in _robots_cache:
        rp = RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
        except Exception:
            logger.debug("Could not fetch robots.txt at %s – allowing", robots_url)
            return  # be permissive on failure
        _robots_cache[robots_url] = rp

    rp = _robots_cache[robots_url]
    if not rp.can_fetch(_USER_AGENT, url):
        raise PermissionError(f"robots.txt disallows fetching {url}")


# ------------------------------------------------------------------
# Throttling
# ------------------------------------------------------------------

def _throttle(url: str) -> None:
    domain = urlparse(url).hostname or ""
    now = time.monotonic()
    last = _last_request.get(domain, 0.0)
    wait = _MIN_DELAY - (now - last)
    if wait > 0:
        time.sleep(wait)
    _last_request[domain] = time.monotonic()


# ------------------------------------------------------------------
# HTTP fetch
# ------------------------------------------------------------------

def _fetch(url: str) -> str:
    resp = requests.get(
        url,
        headers={"User-Agent": _USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
        timeout=_REQUEST_TIMEOUT,
        allow_redirects=True,
    )
    resp.raise_for_status()
    return resp.text


# ------------------------------------------------------------------
# HTML → text helpers
# ------------------------------------------------------------------

def _clean(text: str | None) -> str:
    """Strip HTML artifacts and normalise whitespace."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)          # leftover tags
    text = re.sub(r"&[a-zA-Z]+;", " ", text)      # HTML entities
    text = re.sub(r"&#?\w+;", " ", text)           # numeric entities
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_text(tag: Tag | None) -> str:
    if tag is None:
        return ""
    return _clean(tag.get_text(separator=" "))


def _extract_list(soup: BeautifulSoup, container: Tag | None) -> List[str]:
    """Pull bullet-point items from <li> inside *container*."""
    if container is None:
        return []
    items = []
    for li in container.find_all("li"):
        txt = _clean(li.get_text(separator=" "))
        if txt:
            items.append(txt)
    return items


def _guess_salary(text: str) -> str:
    """Try to find a salary range in *text*."""
    m = re.search(
        r"\$[\d,]+(?:\.\d{2})?\s*[-–—to]+\s*\$[\d,]+(?:\.\d{2})?(?:\s*(?:per|/)\s*\w+)?",
        text,
        re.IGNORECASE,
    )
    if m:
        return m.group(0).strip()
    m = re.search(
        r"\$[\d,]+(?:\.\d{2})?(?:\s*(?:per|/)\s*\w+)?",
        text,
        re.IGNORECASE,
    )
    if m:
        return m.group(0).strip()
    return ""


# ------------------------------------------------------------------
# LinkedIn parser
# ------------------------------------------------------------------

_REQUIREMENT_HEADINGS = re.compile(
    r"(requirements?|qualifications?|what\s+you.ll\s+need|must\s+have|skills?\s+required)",
    re.IGNORECASE,
)


def _parse_linkedin(html: str, url: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    title = _extract_text(
        soup.find("h1", class_=re.compile(r"top-card-layout__title|jobs-unified-top-card__job-title"))
    ) or _extract_text(soup.find("h1"))

    company = _extract_text(
        soup.find("a", class_=re.compile(r"topcard__org-name-link|jobs-unified-top-card__company-name"))
    ) or _extract_text(
        soup.find("span", class_=re.compile(r"topcard__flavor|company-name"))
    )

    location = _extract_text(
        soup.find("span", class_=re.compile(r"topcard__flavor--bullet|jobs-unified-top-card__bullet"))
    )

    # Description body
    desc_div = (
        soup.find("div", class_=re.compile(r"show-more-less-html__markup|description__text"))
        or soup.find("section", class_=re.compile(r"description"))
        or soup.find("div", class_="description")
    )
    raw_desc = _extract_text(desc_div)

    requirements = _extract_requirements(soup, desc_div, raw_desc)
    salary = _guess_salary(raw_desc) or _extract_text(
        soup.find("div", class_=re.compile(r"salary|compensation"))
    )

    return _build_result(url, title, company, location, requirements, salary, raw_desc)


# ------------------------------------------------------------------
# Indeed parser
# ------------------------------------------------------------------

def _parse_indeed(html: str, url: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    title = _extract_text(
        soup.find("h1", class_=re.compile(r"jobsearch-JobInfoHeader-title|JobInfoHeader"))
    ) or _extract_text(soup.find("h1"))

    company = _extract_text(
        soup.find("div", attrs={"data-company-name": True})
    ) or _extract_text(
        soup.find("span", class_=re.compile(r"companyName|company"))
    )

    location = _extract_text(
        soup.find("div", attrs={"data-testid": "job-location"})
    ) or _extract_text(
        soup.find("div", class_=re.compile(r"companyLocation|location"))
    )

    desc_div = (
        soup.find("div", id="jobDescriptionText")
        or soup.find("div", class_=re.compile(r"jobsearch-jobDescriptionText"))
    )
    raw_desc = _extract_text(desc_div)

    requirements = _extract_requirements(soup, desc_div, raw_desc)
    salary = _extract_text(
        soup.find("span", class_=re.compile(r"salary-snippet|attribute_snippet"))
    ) or _guess_salary(raw_desc)

    return _build_result(url, title, company, location, requirements, salary, raw_desc)


# ------------------------------------------------------------------
# Shared helpers
# ------------------------------------------------------------------

def _extract_requirements(
    soup: BeautifulSoup,
    desc_div: Tag | None,
    raw_desc: str,
) -> List[str]:
    """Try to extract a requirements list from the page."""
    # Strategy 1: look for a heading that says "Requirements" / "Qualifications"
    # then grab the next <ul>.
    for tag in soup.find_all(re.compile(r"^h[2-4]$|^strong$|^b$|^p$")):
        if _REQUIREMENT_HEADINGS.search(tag.get_text()):
            ul = tag.find_next("ul")
            if ul:
                items = _extract_list(soup, ul)
                if items:
                    return items

    # Strategy 2: all <li> in the description div
    if desc_div:
        items = _extract_list(soup, desc_div)
        if items:
            return items

    # Strategy 3: split raw text on bullet-like patterns
    bullets = re.findall(r"[•\-–]\s*(.+?)(?=[•\-–]|\Z)", raw_desc)
    return [b.strip() for b in bullets if len(b.strip()) > 10]


def _build_result(
    url: str,
    title: str,
    company: str,
    location: str,
    requirements: List[str],
    salary: str,
    raw_desc: str,
) -> Dict[str, Any]:
    return {
        "url": url,
        "title": title or "Unknown",
        "company": company or "Unknown",
        "location": location or "Not specified",
        "requirements": requirements,
        "salary_range": salary,
        "raw_description": raw_desc,
        "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

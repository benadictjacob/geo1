"""Crawl a small sample of a website and turn each page into structured facts the checks can use."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .fetcher import FetchResult, fetch, normalize_url

SKIP_EXTENSIONS = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".zip", ".mp4", ".mp3",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".css", ".js", ".xml", ".ico",
)

# Pages most useful for the audit get crawled first.
PRIORITY_PATTERNS = [
    r"about", r"faq", r"blog|articles|news|resources|insights|guides",
    r"service|product|solution|treatment|course|program", r"pricing|price|fees|cost",
    r"contact", r"\bvs\b|versus|compare|comparison|alternative|best|top-", r"review|testimonial|case-stud",
]


class AuditError(RuntimeError):
    pass


@dataclass
class Page:
    url: str
    status: int
    elapsed: float
    title: str = ""
    meta_description: str = ""
    h1s: List[str] = field(default_factory=list)
    h2s: List[str] = field(default_factory=list)
    question_headings: List[str] = field(default_factory=list)
    paragraphs: List[str] = field(default_factory=list)
    text: str = ""
    word_count: int = 0
    script_count: int = 0
    jsonld: List[Dict[str, Any]] = field(default_factory=list)
    meta: Dict[str, str] = field(default_factory=dict)
    time_datetimes: List[str] = field(default_factory=list)
    links: List[Tuple[str, str]] = field(default_factory=list)  # (absolute url, anchor text)
    iframes: List[str] = field(default_factory=list)


@dataclass
class Site:
    start_url: str
    origin: str
    host: str
    home: Page
    pages: List[Page]
    robots_status: int
    robots_txt: Optional[str]
    sitemap_urls: List[str]
    sitemap_lastmods: List[datetime]
    llms_txt_present: bool

    @property
    def all_pages(self) -> List[Page]:
        return [self.home] + self.pages

    def internal_links(self) -> List[Tuple[str, str]]:
        seen = {}
        for page in self.all_pages:
            for url, text in page.links:
                if same_site(url, self.host) and url not in seen:
                    seen[url] = text
        return list(seen.items())

    def external_links(self) -> List[str]:
        urls = []
        for page in self.all_pages:
            for url, _ in page.links:
                if not same_site(url, self.host):
                    urls.append(url)
            urls.extend(page.iframes)
        return urls


def _bare_host(host: str) -> str:
    host = (host or "").lower()
    return host[4:] if host.startswith("www.") else host


def same_site(url: str, host: str) -> bool:
    return _bare_host(urlparse(url).hostname or "") == _bare_host(host)


def _flatten_jsonld(data: Any) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if isinstance(data, list):
        for entry in data:
            items.extend(_flatten_jsonld(entry))
    elif isinstance(data, dict):
        if "@graph" in data:
            items.extend(_flatten_jsonld(data["@graph"]))
        items.append(data)
    return items


def jsonld_types(item: Dict[str, Any]) -> List[str]:
    value = item.get("@type", [])
    return [value] if isinstance(value, str) else [v for v in value if isinstance(v, str)]


def parse_html(url: str, html: str, status: int = 200, elapsed: float = 0.0) -> Page:
    soup = BeautifulSoup(html, "html.parser")
    page = Page(url=url, status=status, elapsed=elapsed)

    page.title = soup.title.get_text(" ", strip=True) if soup.title else ""
    for tag in soup.find_all("meta"):
        key = (tag.get("property") or tag.get("name") or tag.get("itemprop") or "").lower()
        if key and tag.get("content"):
            page.meta[key] = tag["content"].strip()
    page.meta_description = page.meta.get("description", "")

    for script in soup.find_all("script", type=lambda t: t and "ld+json" in t.lower()):
        try:
            page.jsonld.extend(_flatten_jsonld(json.loads(script.string or script.get_text() or "")))
        except (json.JSONDecodeError, TypeError):
            continue
    page.script_count = len(soup.find_all("script"))

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            page.links.append((href, a.get_text(" ", strip=True)))
            continue
        absolute = urldefrag(urljoin(url, href))[0]
        page.links.append((absolute, a.get_text(" ", strip=True)))
    page.iframes = [urljoin(url, f["src"]) for f in soup.find_all("iframe", src=True)]
    page.time_datetimes = [t["datetime"] for t in soup.find_all("time", datetime=True)]

    for tag in soup(["script", "style", "noscript", "template", "svg"]):
        tag.decompose()

    page.h1s = [h.get_text(" ", strip=True) for h in soup.find_all("h1")]
    page.h2s = [h.get_text(" ", strip=True) for h in soup.find_all("h2")]
    page.question_headings = [
        h.get_text(" ", strip=True)
        for h in soup.find_all(["h2", "h3", "h4", "summary", "dt", "button"])
        if h.get_text(" ", strip=True).endswith("?")
    ]
    page.paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
    body = soup.body or soup
    page.text = re.sub(r"\s+", " ", body.get_text(" ", strip=True))
    page.word_count = len(page.text.split())
    return page


def _parse_date(value: str) -> Optional[datetime]:
    value = (value or "").strip()
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(value[:10], "%Y-%m-%d")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _read_sitemaps(origin: str, robots_txt: Optional[str], session: requests.Session) -> Tuple[List[str], List[datetime]]:
    candidates = []
    if robots_txt:
        candidates = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots_txt)
    if not candidates:
        candidates = [origin + "/sitemap.xml", origin + "/sitemap_index.xml"]

    urls: List[str] = []
    lastmods: List[datetime] = []
    queue = candidates[:3]
    fetched = 0
    while queue and fetched < 6:
        sitemap_url = queue.pop(0)
        fetched += 1
        try:
            result = fetch(sitemap_url, session)
        except Exception:
            continue
        if not result.ok or "<loc>" not in result.text:
            continue
        locs = re.findall(r"<loc>\s*(.*?)\s*</loc>", result.text, re.S)
        lastmods.extend(d for d in (_parse_date(m) for m in re.findall(r"<lastmod>\s*(.*?)\s*</lastmod>", result.text, re.S)) if d)
        if "<sitemapindex" in result.text:
            queue.extend(locs[:3])
        else:
            urls.extend(locs)
        if urls:
            break
    return urls, lastmods


def _priority(url: str, text: str) -> int:
    haystack = f"{url} {text}".lower()
    for index, pattern in enumerate(PRIORITY_PATTERNS):
        if re.search(pattern, haystack):
            return index
    return len(PRIORITY_PATTERNS)


def _fetch_page(url: str, session: requests.Session) -> Optional[Page]:
    result: FetchResult = fetch(url, session)
    if not result.ok or "html" not in result.content_type:
        return None
    return parse_html(result.url, result.text, result.status, result.elapsed)


def crawl(url: str, max_pages: int = 10, progress=None) -> Site:
    """Fetch the homepage, robots.txt, sitemap, llms.txt and up to max_pages-1 important internal pages."""
    session = requests.Session()
    say = progress or (lambda message: None)

    say(f"Fetching homepage {url}")
    home_result = fetch(normalize_url(url), session)
    if home_result.error or home_result.status >= 400:
        raise AuditError(f"Could not load homepage ({home_result.status}): {home_result.error or 'HTTP error'}")
    home = parse_html(home_result.url, home_result.text, home_result.status, home_result.elapsed)

    parsed = urlparse(home_result.url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    say("Checking robots.txt")
    robots = fetch(origin + "/robots.txt", session)
    robots_txt = robots.text if robots.ok and "html" not in robots.content_type else None

    say("Reading sitemap")
    sitemap_urls, sitemap_lastmods = _read_sitemaps(origin, robots_txt, session)

    llms = fetch(origin + "/llms.txt", session)
    llms_present = llms.ok and "html" not in llms.content_type and len(llms.text.strip()) > 20

    candidates: Dict[str, str] = {}
    for link, text in home.links:
        if same_site(link, parsed.hostname or "") and link.rstrip("/") != home_result.url.rstrip("/"):
            candidates.setdefault(link, text)
    for link in sitemap_urls[:200]:
        if same_site(link, parsed.hostname or ""):
            candidates.setdefault(link, "")

    ordered = sorted(
        (u for u in candidates if not urlparse(u).path.lower().endswith(SKIP_EXTENSIONS)),
        key=lambda u: (_priority(u, candidates[u]), len(u)),
    )

    pages: List[Page] = []
    for link in ordered:
        if len(pages) >= max_pages - 1:
            break
        say(f"Fetching {link}")
        page = _fetch_page(link, session)
        if page and page.url.rstrip("/") != home.url.rstrip("/"):
            pages.append(page)

    return Site(
        start_url=url,
        origin=origin,
        host=parsed.hostname or "",
        home=home,
        pages=pages,
        robots_status=robots.status,
        robots_txt=robots_txt,
        sitemap_urls=sitemap_urls,
        sitemap_lastmods=sitemap_lastmods,
        llms_txt_present=llms_present,
    )

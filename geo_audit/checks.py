"""GEO checks. Each one is grounded in the research summary (GEO-Research/GEO-System.md).

Evidence tiers (from the video proof ranking):
  A = backed by large-scale data or controlled tests (Ahrefs studies, GEO paper)
  B = backed by live demos / single-site results
  C = commonly advised, but evidence is weak or mixed
Weights follow the tier, so weakly-proven tips cannot dominate the score.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Callable, List, Optional
from urllib import robotparser
from urllib.parse import urlparse

from .site import Site, _parse_date, jsonld_types, same_site

TIER_WEIGHT = {"A": 10, "B": 6, "C": 2, "info": 0}

AI_BOTS = {
    "GPTBot": "OpenAI (training)",
    "OAI-SearchBot": "ChatGPT search",
    "ChatGPT-User": "ChatGPT live browsing",
    "ClaudeBot": "Anthropic Claude",
    "PerplexityBot": "Perplexity",
    "Google-Extended": "Google Gemini (training)",
    "Bingbot": "Bing (powers ChatGPT search)",
    "Googlebot": "Google Search / AI Overviews",
}
CRITICAL_BOTS = {"OAI-SearchBot", "Bingbot", "Googlebot", "PerplexityBot"}


@dataclass
class Finding:
    id: str
    category: str
    title: str
    tier: str
    status: str  # pass | warn | fail | info
    score: float  # 0.0 - 1.0 earned
    evidence: str
    why: str
    fix: str
    sources: str

    @property
    def weight(self) -> int:
        return TIER_WEIGHT[self.tier]

    @property
    def lost_points(self) -> float:
        return self.weight * (1 - self.score)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["weight"] = self.weight
        return data


def _status(score: float) -> str:
    if score >= 0.8:
        return "pass"
    if score >= 0.4:
        return "warn"
    return "fail"


def _all_text(site: Site) -> str:
    return " ".join(p.text for p in site.all_pages)


# ---------------------------------------------------------------- Access


def check_ai_crawlers(site: Site) -> Finding:
    meta = dict(id="ai_crawlers", category="Access", title="AI crawlers are allowed in robots.txt", tier="A",
                why="If AI bots are blocked they cannot read your pages, so they cannot recommend them. "
                    "About 5.9% of sites block GPTBot without realising; Cloudflare's AI-bot setting can add blocks by default.",
                sources="Ahrefs 009, Helena Liu 001")
    if site.robots_status in (401, 403):
        return Finding(**meta, status="fail", score=0.0,
                       evidence=f"robots.txt returns HTTP {site.robots_status}, which crawlers treat as 'blocked everywhere'.",
                       fix="Make /robots.txt publicly readable and allow the AI bots listed below.")
    if not site.robots_txt:
        return Finding(**meta, status="pass", score=1.0,
                       evidence="No robots.txt found, so all crawlers are allowed by default.",
                       fix="Optional: add a robots.txt that explicitly allows AI bots and lists your sitemap.")

    parser = robotparser.RobotFileParser()
    parser.parse(site.robots_txt.splitlines())
    blocked = [bot for bot in AI_BOTS if not parser.can_fetch(bot, site.home.url)]
    score = 1 - len(blocked) / len(AI_BOTS)
    if any(bot in CRITICAL_BOTS for bot in blocked):
        score = min(score, 0.2)
    if not blocked:
        evidence = "All major AI and search crawlers may access the homepage: " + ", ".join(AI_BOTS) + "."
    else:
        evidence = "Blocked: " + ", ".join(f"{b} ({AI_BOTS[b]})" for b in blocked) + "."
    return Finding(**meta, status=_status(score), score=score, evidence=evidence,
                   fix="Remove the Disallow rules for these bots in robots.txt (and check Cloudflare > Security > Bots "
                       "'Instruct AI bot traffic' setting).")


def check_no_js_content(site: Site) -> Finding:
    words = site.home.word_count
    avg = sum(p.word_count for p in site.all_pages) / len(site.all_pages)
    score = 1.0 if words >= 250 else 0.5 if words >= 80 else 0.0
    return Finding(
        id="no_js_content", category="Access", title="Content is readable without JavaScript", tier="A",
        status=_status(score), score=score,
        evidence=f"The homepage shows {words} words of readable text in the raw HTML (average {avg:.0f} across "
                 f"{len(site.all_pages)} pages), with {site.home.script_count} script tags.",
        why="ChatGPT's crawler does not run JavaScript. If your text is only built by JavaScript, ChatGPT sees an empty page.",
        fix="Use server-side rendering or static pre-rendering so the main text is in the HTML. Test: disable JavaScript "
            "in your browser and reload your site.",
        sources="Ahrefs 009, OMNIUS 003",
    )


def check_speed(site: Site) -> Finding:
    seconds = site.home.elapsed
    score = 1.0 if seconds < 1.5 else 0.5 if seconds < 3.5 else 0.0
    return Finding(
        id="speed", category="Access", title="Pages load fast", tier="B",
        status=_status(score), score=score,
        evidence=f"Homepage HTML downloaded in {seconds:.1f}s (single measurement from our server).",
        why="AI assistants fetch pages live while answering; slow pages can be dropped before they are read.",
        fix="Improve server response time and Core Web Vitals (caching, CDN, lighter pages).",
        sources="Ahrefs 009",
    )


# ---------------------------------------------------------------- Content


def _collect_dates(site: Site) -> List[datetime]:
    raw: List[str] = []
    for page in site.all_pages:
        for item in page.jsonld:
            for key in ("dateModified", "datePublished"):
                if isinstance(item.get(key), str):
                    raw.append(item[key])
        for key in ("article:modified_time", "article:published_time", "og:updated_time", "last-modified", "datemodified"):
            if key in page.meta:
                raw.append(page.meta[key])
        raw.extend(page.time_datetimes)
    dates = [d for d in (_parse_date(r) for r in raw) if d]
    dates.extend(site.sitemap_lastmods)
    now = datetime.now(timezone.utc)
    return [d for d in dates if d <= now.replace(year=now.year + 1)]


def check_freshness(site: Site) -> Finding:
    dates = _collect_dates(site)
    now = datetime.now(timezone.utc)
    if not dates:
        score, evidence = 0.0, "No update or publish dates found on pages, in structured data, or in the sitemap."
    else:
        newest = max(d for d in dates if d <= now) if any(d <= now for d in dates) else min(dates)
        age = (now - newest).days
        score = 1.0 if age <= 30 else 0.7 if age <= 90 else 0.3 if age <= 365 else 0.0
        evidence = f"Most recent update date found: {newest.date().isoformat()} ({age} days ago), from {len(dates)} dates checked."
    return Finding(
        id="freshness", category="Content", title="Content is recently updated", tier="A",
        status=_status(score), score=score, evidence=evidence,
        why="AI-cited pages are ~26% fresher than normal search results, and 76% of ChatGPT's top-cited pages were "
            "updated in the last 30 days.",
        fix="Make real updates (new stats, examples, prices) to your top 5-10 pages every month, show a visible "
            "'Last updated' date, and keep sitemap <lastmod> accurate.",
        sources="Ahrefs 012/007, Hasan 010",
    )


STAT_PATTERN = re.compile(
    r"\b\d[\d,]*(?:\.\d+)?\s?(?:%|percent|x\b|×|\+|million|billion|crore|lakh|k\b|years?|customers|clients|users|"
    r"patients|students|projects|reviews|businesses|companies|countries|cities|beds|doctors|rooms)",
    re.I,
)
SOURCE_PATTERN = re.compile(r"\b(according to|study|survey|report(?:ed)? by|research(?:ers)?|data from|source:)", re.I)


def check_statistics(site: Site) -> Finding:
    text = _all_text(site)
    stats = STAT_PATTERN.findall(text)
    sources = SOURCE_PATTERN.findall(text)
    score = 1.0 if len(stats) >= 10 and len(sources) >= 2 else 0.6 if len(stats) >= 5 else 0.3 if len(stats) >= 2 else 0.0
    samples = []
    for match in STAT_PATTERN.finditer(text):
        start = max(0, match.start() - 50)
        samples.append("…" + text[start:match.end() + 30].strip() + "…")
        if len(samples) == 2:
            break
    evidence = f"Found {len(stats)} specific numbers and {len(sources)} source references across {len(site.all_pages)} pages."
    if samples:
        evidence += " Examples: " + " | ".join(samples)
    return Finding(
        id="statistics", category="Content", title="Uses specific numbers, proof and cited sources", tier="A",
        status=_status(score), score=score, evidence=evidence,
        why="The GEO research paper found adding statistics, quotations and cited sources raised AI visibility by over 40%. "
            "AI prefers specific facts it can quote over vague claims.",
        fix="Replace vague claims ('we helped many clients') with specific facts ('trained 500 students since 2023, "
            "73% placed within 90 days'), and cite trusted sources (government data, industry reports).",
        sources="Exposure Ninja 004 (GEO paper), Helena Liu 001, Hasan 010",
    )


LISTICLE_PATTERN = re.compile(r"\b(best|top \d+|top-\d+|vs\.?|versus|compare|comparison|alternatives?|reviews?)\b", re.I)


def check_comparison_content(site: Site) -> Finding:
    hits = []
    for url, text in site.internal_links():
        label = f"{urlparse(url).path.replace('-', ' ').replace('/', ' ')} {text}"
        if LISTICLE_PATTERN.search(label):
            hits.append(text or url)
    for page in site.all_pages:
        if LISTICLE_PATTERN.search(page.title):
            hits.append(page.title)
    hits = list(dict.fromkeys(hits))
    score = 1.0 if len(hits) >= 3 else 0.5 if hits else 0.0
    return Finding(
        id="comparison_content", category="Content", title="Has 'best X' / comparison / review content", tier="A",
        status=_status(score), score=score,
        evidence=f"Found {len(hits)} comparison or list-style pages" + (": " + "; ".join(hits[:4]) if hits else "."),
        why="43.8% of pages ChatGPT cites are listicles and comparisons ('best X', 'X vs Y'), because they match how people ask AI.",
        fix="Publish honest comparison pages for your category (e.g. 'Best cardiac hospitals in Kochi: how to choose', "
            "'Plan A vs Plan B') with clear tables and real data.",
        sources="Ahrefs 012/007, Hasan 010",
    )


def check_faq(site: Site) -> Finding:
    questions = [q for p in site.all_pages for q in p.question_headings]
    has_faq_schema = any("FAQPage" in jsonld_types(item) for p in site.all_pages for item in p.jsonld)
    faq_page = any("faq" in url.lower() or "frequently asked" in text.lower() for url, text in site.internal_links())
    unique = list(dict.fromkeys(questions))
    score = 1.0 if len(unique) >= 5 else 0.6 if len(unique) >= 2 or faq_page or has_faq_schema else 0.0
    return Finding(
        id="faq", category="Content", title="Answers customer questions directly (FAQ)", tier="B",
        status=_status(score), score=score,
        evidence=f"{len(unique)} question-style headings found; FAQ page link: {'yes' if faq_page else 'no'}; "
                 f"FAQPage schema: {'yes' if has_faq_schema else 'no'}."
                 + (f" Examples: {'; '.join(unique[:3])}" if unique else ""),
        why="People ask AI full questions. Pages that contain the same question with a direct answer are easy for AI to quote.",
        fix="Add an FAQ page and FAQ sections on key service pages, using the real questions customers ask before buying. "
            "Answer each in the first sentence.",
        sources="Helena Liu 001, Hasan 010, Amir Rasheed 005, MarkeTech 008",
    )


def check_paragraphs(site: Site) -> Finding:
    paragraphs = [p for page in site.all_pages for p in page.paragraphs if len(p.split()) >= 8]
    if not paragraphs:
        return Finding(
            id="paragraphs", category="Content", title="Short, self-contained paragraphs", tier="B",
            status="fail", score=0.0, evidence="No real text paragraphs (<p>) were found.",
            why="AI cuts pages into chunks and quotes them individually.",
            fix="Write your key information as clear text paragraphs, not only images, sliders or buttons.",
            sources="Ahrefs 012/009",
        )
    long_ones = [p for p in paragraphs if len(p.split()) > 120]
    vague_start = [p for p in paragraphs if re.match(r"^(it|this|they|these|that)\b", p, re.I)]
    share_long = len(long_ones) / len(paragraphs)
    share_vague = len(vague_start) / len(paragraphs)
    score = max(0.0, 1.0 - share_long * 2 - share_vague)
    return Finding(
        id="paragraphs", category="Content", title="Short, self-contained paragraphs", tier="B",
        status=_status(score), score=round(score, 2),
        evidence=f"{len(paragraphs)} paragraphs checked: {len(long_ones)} are over 120 words, "
                 f"{len(vague_start)} start with a vague word (it/this/they) that depends on earlier text.",
        why="AI splits pages into chunks and quotes one chunk at a time. Each section must make sense on its own, with the answer first.",
        fix="Start each section with the direct answer, keep one idea per paragraph, and name things explicitly "
            "('Acme Hospital's cardiac unit…' instead of 'It…').",
        sources="Ahrefs 012 (BLUF, atomic content), Helena Liu 001",
    )


def check_content_hub(site: Site) -> Finding:
    hub = [url for url, text in site.internal_links()
           if re.search(r"/(blog|articles?|news|resources|insights|guides|learn|knowledge)", urlparse(url).path, re.I)]
    score = 1.0 if len(hub) >= 3 else 0.5 if hub else 0.0
    return Finding(
        id="content_hub", category="Content", title="Has a blog / resource section covering the topic", tier="B",
        status=_status(score), score=score,
        evidence=f"Found {len(hub)} links to blog, guide or resource pages.",
        why="AI splits each question into ~10 sub-searches. Covering the whole topic (not one page per keyword) "
            "lets you match more of them.",
        fix="Build a resource section that answers the related questions around your service (costs, how to choose, "
            "process, comparisons).",
        sources="Ahrefs 011/007 (query fan-out)",
    )


# ---------------------------------------------------------------- Authority


def _profile_links(site: Site) -> List[str]:
    urls = site.external_links()
    for page in site.all_pages:
        for item in page.jsonld:
            same_as = item.get("sameAs")
            if isinstance(same_as, str):
                urls.append(same_as)
            elif isinstance(same_as, list):
                urls.extend(u for u in same_as if isinstance(u, str))
    return urls


def check_youtube(site: Site) -> Finding:
    yt = [u for u in _profile_links(site) if re.search(r"(youtube\.com|youtu\.be)", u, re.I)]
    score = 1.0 if yt else 0.0
    return Finding(
        id="youtube", category="Authority", title="Has a YouTube presence linked from the site", tier="A",
        status=_status(score), score=score,
        evidence=f"{len(set(yt))} YouTube links or embedded videos found." if yt else "No YouTube channel link or embedded video found.",
        why="YouTube mentions had the strongest correlation (0.737) with ChatGPT visibility of any factor Ahrefs studied, "
            "and YouTube is the most cited domain in Google AI Overviews.",
        fix="Create search-focused videos answering customer questions: keyword in the title, a real description, "
            "timestamps, and say the keyword out loud. Link the channel from your site.",
        sources="Ahrefs 007, Helena Liu 001",
    )


CITABLE_PLATFORMS = {
    "LinkedIn": r"linkedin\.com", "Reddit": r"reddit\.com", "Quora": r"quora\.com", "Medium": r"medium\.com",
    "Wikipedia": r"wikipedia\.org", "G2": r"g2\.com", "Capterra": r"capterra\.", "Trustpilot": r"trustpilot\.",
    "Google Business": r"(g\.page|maps\.google|google\.com/maps|maps\.app\.goo\.gl)", "Justdial": r"justdial\.com",
    "Practo": r"practo\.com", "Tripadvisor": r"tripadvisor\.", "Clutch": r"clutch\.co", "GitHub": r"github\.com",
    "X / Twitter": r"(twitter\.com|x\.com)/",
}
WALLED_PLATFORMS = {"Instagram": r"instagram\.com", "Facebook": r"facebook\.com", "TikTok": r"tiktok\.com"}


def check_offsite_profiles(site: Site) -> Finding:
    links = _profile_links(site)
    found = [name for name, pattern in CITABLE_PLATFORMS.items() if any(re.search(pattern, u, re.I) for u in links)]
    walled = [name for name, pattern in WALLED_PLATFORMS.items() if any(re.search(pattern, u, re.I) for u in links)]
    score = 1.0 if len(found) >= 3 else 0.5 if found else 0.0
    evidence = f"Linked profiles AI can read: {', '.join(found) if found else 'none'}."
    if walled:
        evidence += f" Also linked (mostly behind logins, little AI value): {', '.join(walled)}."
    return Finding(
        id="offsite_profiles", category="Authority", title="Present on platforms AI reads (reviews, LinkedIn, Reddit…)", tier="A",
        status=_status(score), score=score, evidence=evidence,
        why="Brand mentions across the web are the strongest single signal for AI visibility (0.664 correlation), "
            "stronger than backlinks. AI reads LinkedIn, Reddit, review sites and Wikipedia; Instagram/TikTok are mostly walled off.",
        fix="Claim and fill profiles on review sites for your industry (Google Business, Justdial/Practo/Tripadvisor/G2), "
            "post on LinkedIn, and answer real questions on Reddit/Quora. Link them from your site and in Organization schema 'sameAs'.",
        sources="Ahrefs 007, Helena Liu 001, OMNIUS 003, Hasan 010",
    )


PHONE_PATTERN = re.compile(r"(\+?\d[\d\s\-()]{8,}\d)")


def _brand_name(site: Site) -> Optional[str]:
    for page in site.all_pages:
        for item in page.jsonld:
            if set(jsonld_types(item)) & {"Organization", "LocalBusiness", "Corporation", "Hospital", "Hotel",
                                          "EducationalOrganization", "Store", "MedicalOrganization", "ProfessionalService"}:
                if isinstance(item.get("name"), str):
                    return item["name"].strip()
    if site.home.meta.get("og:site_name"):
        return site.home.meta["og:site_name"]
    if site.home.title:
        return re.split(r"\s[|\-–—:]\s", site.home.title)[-1].strip() or None
    return None


def check_entity_clarity(site: Site) -> Finding:
    name = _brand_name(site)
    links = site.internal_links()
    all_text = _all_text(site)
    org_schema = any(
        set(jsonld_types(i)) & {"Organization", "LocalBusiness", "Corporation", "Hospital", "Hotel",
                                "EducationalOrganization", "Store", "MedicalOrganization", "ProfessionalService"}
        for p in site.all_pages for i in p.jsonld
    )
    checks = {
        "brand name in homepage title": bool(name and name.lower() in site.home.title.lower()),
        "About page": any(re.search(r"about", f"{u} {t}", re.I) for u, t in links),
        "contact details (phone/email/address)": any(u.startswith(("mailto:", "tel:")) for p in site.all_pages for u, _ in p.links)
        or bool(PHONE_PATTERN.search(all_text)),
        "Organization/LocalBusiness schema": org_schema,
    }
    score = sum(checks.values()) / len(checks)
    missing = [k for k, v in checks.items() if not v]
    return Finding(
        id="entity_clarity", category="Authority", title="Clear, consistent business identity", tier="B",
        status=_status(score), score=score,
        evidence=f"Detected brand name: {name or 'unclear'}. Present: {', '.join(k for k, v in checks.items() if v) or 'none'}."
                 + (f" Missing: {', '.join(missing)}." if missing else ""),
        why="AI must be sure who you are, where you are and what you do. When facts are vague or missing, AI can repeat "
            "wrong information from other sites.",
        fix="Keep one consistent business name, address, phone and description everywhere; add an About page with founders, "
            "dates and numbers; add Organization/LocalBusiness schema.",
        sources="Ahrefs 007 (misinformation test), Helena Liu 001",
    )


# ---------------------------------------------------------------- Structure (weak evidence, low weight)


def check_headings(site: Site) -> Finding:
    one_h1 = len(site.home.h1s) == 1
    with_h2 = sum(1 for p in site.all_pages if p.h2s) / len(site.all_pages)
    score = (0.5 if one_h1 else 0.0) + 0.5 * min(1.0, with_h2 / 0.7)
    return Finding(
        id="headings", category="Structure", title="Clean heading structure (H1/H2)", tier="B",
        status=_status(score), score=round(score, 2),
        evidence=f"Homepage has {len(site.home.h1s)} H1 heading(s); {with_h2:.0%} of crawled pages use H2 sections.",
        why="AI follows your headings to split the page into sections it can quote.",
        fix="Use exactly one H1 per page and H2/H3 headings for each topic, ideally phrased as the question they answer.",
        sources="Ahrefs 009, OMNIUS 003",
    )


def check_sitemap(site: Site) -> Finding:
    count = len(site.sitemap_urls)
    score = 1.0 if count else 0.0
    return Finding(
        id="sitemap", category="Structure", title="XML sitemap available", tier="C",
        status=_status(score), score=score,
        evidence=f"Sitemap lists {count} URLs." if count else "No sitemap found in robots.txt or at /sitemap.xml.",
        why="Helps search engines (including Bing, used by ChatGPT) discover all your pages.",
        fix="Generate a sitemap.xml, reference it in robots.txt, and submit it in Google Search Console and Bing Webmaster Tools.",
        sources="Exposure Ninja 004, OMNIUS 003",
    )


def check_schema(site: Site) -> Finding:
    types = sorted({t for p in site.all_pages for i in p.jsonld for t in jsonld_types(i)})
    score = 1.0 if types else 0.0
    return Finding(
        id="schema", category="Structure", title="Structured data (Schema.org JSON-LD)", tier="C",
        status=_status(score), score=score,
        evidence=f"Schema types found: {', '.join(types)}." if types else "No JSON-LD structured data found.",
        why="Helps machines read key facts. Note: Ahrefs found no proof it directly increases AI citations, so it is weighted low.",
        fix="Add Organization/LocalBusiness, Article, Product/Service and FAQPage schema where relevant. AI tools can draft the JSON-LD from your page text.",
        sources="Helena Liu 001, Hasan 010; caution: Ahrefs 009",
    )


def check_meta_description(site: Site) -> Finding:
    with_desc = sum(1 for p in site.all_pages if len(p.meta_description) >= 50) / len(site.all_pages)
    score = with_desc
    return Finding(
        id="meta_description", category="Structure", title="Pages have descriptive meta descriptions", tier="C",
        status=_status(score), score=round(score, 2),
        evidence=f"{with_desc:.0%} of crawled pages have a meta description of 50+ characters.",
        why="A clear one-line summary of each page helps search engines and AI understand it quickly.",
        fix="Write a specific 1-2 sentence description for each important page, naming the service and location.",
        sources="MarkeTech 008",
    )


def check_llms_txt(site: Site) -> Finding:
    return Finding(
        id="llms_txt", category="Structure", title="llms.txt file", tier="info",
        status="info", score=1.0,
        evidence="llms.txt is present." if site.llms_txt_present else "No llms.txt found.",
        why="Not scored: no major AI provider officially reads llms.txt yet.",
        fix="Optional and low priority. Focus on robots.txt and content first.",
        sources="Ahrefs 009",
    )


ALL_CHECKS: List[Callable[[Site], Finding]] = [
    check_ai_crawlers, check_no_js_content, check_speed,
    check_freshness, check_statistics, check_comparison_content, check_faq, check_paragraphs, check_content_hub,
    check_youtube, check_offsite_profiles, check_entity_clarity,
    check_headings, check_sitemap, check_schema, check_meta_description, check_llms_txt,
]


def run_checks(site: Site) -> List[Finding]:
    return [check(site) for check in ALL_CHECKS]

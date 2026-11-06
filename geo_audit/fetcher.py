"""Safe HTTP fetching for user-supplied URLs (blocks private/internal addresses, limits size and redirects)."""

from __future__ import annotations

import ipaddress
import socket
import time
from dataclasses import dataclass, field
from typing import Dict, Optional
from urllib.parse import urljoin, urlparse

import requests

USER_AGENT = "Mozilla/5.0 (compatible; GEOAuditBot/0.1; +https://example.com/bot)"
MAX_BYTES = 3_000_000
TIMEOUT = 15
MAX_REDIRECTS = 5


class UnsafeURLError(ValueError):
    """Raised when a URL points somewhere we must not fetch (internal network, bad scheme, ...)."""


@dataclass
class FetchResult:
    url: str
    status: int
    headers: Dict[str, str] = field(default_factory=dict)
    text: str = ""
    elapsed: float = 0.0
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status < 300

    @property
    def content_type(self) -> str:
        return self.headers.get("Content-Type", self.headers.get("content-type", "")).lower()


def normalize_url(url: str) -> str:
    url = url.strip()
    if not urlparse(url).scheme:
        url = "https://" + url
    return url


def _assert_public_host(host: str) -> None:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Cannot resolve host: {host}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if not ip.is_global:
            raise UnsafeURLError(f"Refusing to fetch non-public address {ip} for host {host}")


def fetch(url: str, session: Optional[requests.Session] = None) -> FetchResult:
    """GET a URL, following redirects manually so every hop is checked against internal addresses.

    Network errors are returned as FetchResult.error; unsafe URLs raise UnsafeURLError.
    """
    session = session or requests.Session()
    current = url
    start = time.monotonic()

    for _ in range(MAX_REDIRECTS + 1):
        parsed = urlparse(current)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise UnsafeURLError(f"Only public http(s) URLs are allowed: {current}")
        _assert_public_host(parsed.hostname)

        try:
            resp = session.get(
                current,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"},
                timeout=TIMEOUT,
                allow_redirects=False,
                stream=True,
            )
        except requests.RequestException as exc:
            return FetchResult(url=current, status=0, error=f"{type(exc).__name__}: {exc}", elapsed=time.monotonic() - start)

        if resp.status_code in (301, 302, 303, 307, 308) and "location" in resp.headers:
            current = urljoin(current, resp.headers["location"])
            resp.close()
            continue

        chunks = []
        size = 0
        try:
            for chunk in resp.iter_content(65536):
                size += len(chunk)
                if size > MAX_BYTES:
                    break
                chunks.append(chunk)
        except requests.RequestException as exc:
            resp.close()
            return FetchResult(url=current, status=resp.status_code, error=f"{type(exc).__name__}: {exc}", elapsed=time.monotonic() - start)
        resp.close()

        content_type = resp.headers.get("content-type", "").lower()
        encoding = resp.encoding if "charset" in content_type and resp.encoding else "utf-8"
        try:
            text = b"".join(chunks).decode(encoding, errors="replace")
        except LookupError:
            text = b"".join(chunks).decode("utf-8", errors="replace")

        return FetchResult(
            url=current,
            status=resp.status_code,
            headers=dict(resp.headers),
            text=text,
            elapsed=time.monotonic() - start,
        )

    raise UnsafeURLError(f"Too many redirects starting from {url}")

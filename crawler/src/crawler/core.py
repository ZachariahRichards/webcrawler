from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from typing import Protocol


class Database(Protocol):
    def record_page(self, url: str, **values: object) -> None: ...
    def record_link(self, source_url: str, target_url: str) -> None: ...
    def commit(self) -> None: ...


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() not in {"a", "area"}:
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                self.links.append(value.strip())
                break


def normalize_url(url: str, base_url: str | None = None) -> str | None:
    absolute = urljoin(base_url, url) if base_url else url
    parts = urlsplit(absolute)
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"} or not parts.hostname:
        return None
    if parts.username is not None or parts.password is not None:
        # Avoid crawling URLs containing credentials.
        return None

    hostname = parts.hostname.lower()
    try:
        port = parts.port
    except ValueError:
        return None
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    netloc = hostname if port is None or default_port else f"{hostname}:{port}"
    path = parts.path or "/"
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def url_origin(url: str) -> tuple[str, str, int]:
    parts = urlsplit(url)
    if parts.scheme == "http":
        port = parts.port or 80
    elif parts.scheme == "https":
        port = parts.port or 443
    else:
        raise ValueError("URL must use HTTP or HTTPS")
    if not parts.hostname:
        raise ValueError("URL must include a host")
    return (parts.scheme, parts.hostname.lower(), port)


@dataclass
class CrawlStats:
    pages_attempted: int = 0
    pages_succeeded: int = 0
    links_found: int = 0
    errors: int = 0


class Crawler:
    def __init__(
        self,
        database: Database,
        *,
        max_pages: int = 100,
        max_depth: int = 5,
        timeout: float = 10.0,
        delay: float = 0.0,
        same_host: bool = True,
        user_agent: str = "crawler/0.1 (+https://example.invalid/crawler)",
    ) -> None:
        if max_pages < 1 or max_depth < 0 or timeout <= 0 or delay < 0:
            raise ValueError("invalid crawl limits")
        self.database = database
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.timeout = timeout
        self.delay = delay
        self.same_host = same_host
        self.user_agent = user_agent

    def crawl(self, start_url: str) -> CrawlStats:
        start = normalize_url(start_url)
        if start is None:
            raise ValueError("start URL must be an absolute HTTP or HTTPS URL")

        start_origin = url_origin(start)
        queue: deque[tuple[str, int]] = deque([(start, 0)])
        queued = {start}
        visited: set[str] = set()
        stats = CrawlStats()

        while queue and stats.pages_attempted < self.max_pages:
            url, depth = queue.popleft()
            if url in visited:
                continue
            visited.add(url)
            stats.pages_attempted += 1

            try:
                request = Request(url, headers={"User-Agent": self.user_agent, "Accept": "text/html,*/*;q=0.1"})
                with urlopen(request, timeout=self.timeout) as response:
                    final_url = normalize_url(response.geturl()) or url
                    status = response.status
                    content_type = response.headers.get_content_type()
                    charset = response.headers.get_content_charset() or "utf-8"
                    body = response.read()
                visited.add(final_url)
                queued.add(final_url)
                self.database.record_page(final_url, status_code=status, content_type=content_type)
                stats.pages_succeeded += 1
            except (HTTPError, URLError, TimeoutError, OSError) as exc:
                status = exc.code if isinstance(exc, HTTPError) else None
                self.database.record_page(url, status_code=status, error=str(exc))
                stats.errors += 1
                if self.delay:
                    time.sleep(self.delay)
                continue

            if content_type not in {"text/html", "application/xhtml+xml"}:
                if self.delay:
                    time.sleep(self.delay)
                continue

            parser = LinkParser()
            try:
                parser.feed(body.decode(charset, errors="replace"))
            except (LookupError, UnicodeError):
                parser.feed(body.decode("utf-8", errors="replace"))

            for raw_link in parser.links:
                target = normalize_url(raw_link, final_url)
                if target is None:
                    continue
                self.database.record_link(final_url, target)
                stats.links_found += 1
                in_scope = not self.same_host or url_origin(target) == start_origin
                if depth < self.max_depth and in_scope and target not in queued:
                    queued.add(target)
                    queue.append((target, depth + 1))
            self.database.commit()

            if self.delay:
                time.sleep(self.delay)

        return stats

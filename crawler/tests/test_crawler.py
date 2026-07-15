from __future__ import annotations

import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from crawler.core import Crawler, normalize_url


class MemoryDatabase:
    def __init__(self) -> None:
        self.pages: dict[str, dict[str, object]] = {}
        self.links: set[tuple[str, str]] = set()

    def record_page(self, url: str, **values: object) -> None:
        self.pages[url] = values

    def record_link(self, source_url: str, target_url: str) -> None:
        self.links.add((source_url, target_url))

    def commit(self) -> None:
        pass


class SiteHandler(BaseHTTPRequestHandler):
    pages = {
        "/": b'<a href="/one">one</a><a href="https://outside.example/x#part">out</a>',
        "/one": b'<a href="/two?x=1#section">two</a><a href="/">home</a>',
        "/two?x=1": b"<p>finished</p>",
        "/redirected": b'<a href="/one">one</a>',
    }

    def do_GET(self) -> None:
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/redirected")
            self.end_headers()
            return
        body = self.pages.get(self.path)
        if body is None:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_: object) -> None:
        pass


class CrawlerTests(unittest.TestCase):
    def test_normalize_url(self) -> None:
        self.assertEqual(
            normalize_url("../next?q=1#frag", "HTTPS://Example.COM/a/page"),
            "https://example.com/next?q=1",
        )
        self.assertIsNone(normalize_url("mailto:hello@example.com", "https://example.com"))
        self.assertIsNone(normalize_url("https://user:secret@example.com"))
        self.assertIsNone(normalize_url("https://:secret@example.com"))

    def test_crawls_and_records_links(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), SiteHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            database = MemoryDatabase()
            start = f"http://127.0.0.1:{server.server_port}/"
            stats = Crawler(database, max_pages=10).crawl(start)

            self.assertEqual(stats.pages_succeeded, 3)
            self.assertEqual(len(database.pages), 3)
            self.assertEqual(len(database.links), 4)
            self.assertTrue(any(target == "https://outside.example/x" for _, target in database.links))
        finally:
            server.shutdown()
            server.server_close()

    def test_records_redirected_page_under_final_url(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), SiteHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            database = MemoryDatabase()
            start = f"http://127.0.0.1:{server.server_port}/redirect"
            final_url = f"http://127.0.0.1:{server.server_port}/redirected"
            stats = Crawler(database, max_pages=1).crawl(start)

            self.assertEqual(stats.pages_succeeded, 1)
            self.assertIn(final_url, database.pages)
            self.assertNotIn(start, database.pages)
            self.assertIn((final_url, f"http://127.0.0.1:{server.server_port}/one"), database.links)
        finally:
            server.shutdown()
            server.server_close()

    def test_same_host_scope_does_not_follow_other_ports(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), SiteHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            database = MemoryDatabase()
            other_port_url = f"http://127.0.0.1:{server.server_port + 1}/one"
            SiteHandler.pages["/"] = f'<a href="{other_port_url}">other port</a>'.encode()
            start = f"http://127.0.0.1:{server.server_port}/"
            stats = Crawler(database, max_pages=10).crawl(start)

            self.assertEqual(stats.pages_attempted, 1)
            self.assertIn((start, other_port_url), database.links)
            self.assertNotIn(other_port_url, database.pages)
        finally:
            SiteHandler.pages["/"] = b'<a href="/one">one</a><a href="https://outside.example/x#part">out</a>'
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()

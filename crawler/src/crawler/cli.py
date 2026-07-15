from __future__ import annotations

import argparse
import sys

import pymysql

from .core import Crawler
from .database import CrawlDatabase


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crawler",
        description="Crawl HTML pages and record discovered links in MySQL.",
    )
    parser.add_argument("url", help="absolute HTTP(S) URL at which to start")
    parser.add_argument(
        "-d",
        "--database",
        required=True,
        metavar="MYSQL_URL",
        help="MySQL connection URL, for example mysql://user:pass@localhost/crawler",
    )
    parser.add_argument("--max-pages", type=int, default=100, help="maximum pages to request (default: 100)")
    parser.add_argument("--max-depth", type=int, default=5, help="maximum link depth (default: 5)")
    parser.add_argument("--timeout", type=float, default=10.0, help="request timeout in seconds (default: 10)")
    parser.add_argument("--delay", type=float, default=0.0, help="delay between requests in seconds")
    parser.add_argument("--include-external", action="store_true", help="follow links to other hosts")
    parser.add_argument("--user-agent", default="crawler/0.1 (+https://example.invalid/crawler)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with CrawlDatabase(args.database) as database:
            crawler = Crawler(
                database,
                max_pages=args.max_pages,
                max_depth=args.max_depth,
                timeout=args.timeout,
                delay=args.delay,
                same_host=not args.include_external,
                user_agent=args.user_agent,
            )
            stats = crawler.crawl(args.url)
    except (ValueError, OSError, pymysql.MySQLError) as exc:
        print(f"crawler: error: {exc}", file=sys.stderr)
        return 2

    print(
        f"Crawl complete: {stats.pages_succeeded}/{stats.pages_attempted} pages fetched, "
        f"{stats.links_found} links found, {stats.errors} errors."
    )
    return 0 if stats.pages_succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())

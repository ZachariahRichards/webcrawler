# Webcrawler

Python command-line web crawler with URL normalization, same-host crawl limits, MySQL persistence, and automated tests.

## Overview

This project starts from a single URL, downloads HTML pages, extracts links, records page/link data, and follows newly discovered links within configurable limits. It is structured as an installable Python package with a CLI entry point and a small persistence layer.

## Features

- Command-line interface for running crawls from a starting URL
- URL normalization for relative links, fragments, hosts, ports, and paths
- Configurable maximum page count, crawl depth, timeout, and request delay
- Same-host crawling by default, with an option to include external links
- MySQL-backed storage for visited pages and discovered links
- Unit tests using a local HTTP test server

## Tech Stack

- Python 3.10+
- PyMySQL
- MySQL
- unittest
- CLI/package layout with pyproject.toml

## Project Structure

```text
crawler/
  pyproject.toml
  src/crawler/
    cli.py
    core.py
    database.py
  tests/
    test_crawler.py
```

## Install

```bash
cd crawler
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

On Windows PowerShell:

```powershell
cd crawler
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## Run

```bash
crawler https://example.com \
  --database 'mysql://crawler_user:password@localhost:3306/crawler'
```

Common options:

```bash
crawler https://example.com \
  --database 'mysql://crawler_user:password@localhost:3306/crawler' \
  --max-pages 500 \
  --max-depth 10 \
  --delay 0.25 \
  --include-external
```

The database must already exist. The crawler creates its `pages` and `links` tables automatically.

## Test

```bash
cd crawler
python -m unittest discover -s tests -v
```

## Concepts Demonstrated

- Backend-style command-line tooling
- HTTP request handling
- HTML link extraction
- URL normalization
- Database persistence
- Testable design with dependency injection

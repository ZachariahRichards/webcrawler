# crawler

`crawler` is a command-line web crawler. Starting from one URL, it downloads HTML,
extracts links, stores each link and when it was seen in MySQL, and follows newly
discovered links.

## Install

```bash
cd crawler
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

## Use

```bash
crawler https://example.com \
  --database 'mysql://crawler_user:password@localhost:3306/crawler'
```

By default, the crawl stays on the starting host, visits at most 100 pages, follows
links five levels deep. The MySQL database must already exist; the crawler creates
its `pages` and `links` tables automatically.

```bash
crawler https://example.com \
  --database 'mysql://crawler_user:password@localhost:3306/crawler' \
  --max-pages 500 \
  --max-depth 10 \
  --delay 0.25 \
  --include-external
```

Run `crawler --help` for all options. The database contains:

- `pages`: requested pages and their fetch result.
- `links`: unique source/target pairs with `first_seen` and `last_seen` UTC times.

Only HTTP(S) links are recorded. Links are normalized by removing fragments and
standardizing hosts, ports, and paths. `--include-external` permits following links
to other hosts; without it, external links are still recorded but not followed.

## Test

```bash
python -m unittest discover -s tests -v
```

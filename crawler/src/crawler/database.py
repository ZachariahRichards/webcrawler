from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class CrawlDatabase:
    def __init__(self, connection_url: str) -> None:
        import pymysql

        parts = urlsplit(connection_url)
        if parts.scheme not in {"mysql", "mysql+pymysql"}:
            raise ValueError("database URL must start with mysql:// or mysql+pymysql://")
        if not parts.hostname or not parts.path.strip("/"):
            raise ValueError("database URL must include a host and database name")

        self.connection = pymysql.connect(
            host=parts.hostname,
            port=parts.port or 3306,
            user=unquote(parts.username or ""),
            password=unquote(parts.password or ""),
            database=unquote(parts.path.lstrip("/")),
            charset="utf8mb4",
            autocommit=False,
        )
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS pages (
                url VARCHAR(2048) NOT NULL,
                url_hash BINARY(32) NOT NULL,
                first_seen VARCHAR(32) NOT NULL,
                last_seen VARCHAR(32) NOT NULL,
                status_code INTEGER,
                content_type VARCHAR(255),
                error TEXT,
                PRIMARY KEY (url_hash)
            ) CHARACTER SET utf8mb4
                """
            )
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS links (
                source_url VARCHAR(2048) NOT NULL,
                target_url VARCHAR(2048) NOT NULL,
                link_hash BINARY(32) NOT NULL,
                target_hash BINARY(32) NOT NULL,
                first_seen VARCHAR(32) NOT NULL,
                last_seen VARCHAR(32) NOT NULL,
                PRIMARY KEY (link_hash),
                INDEX idx_links_target (target_hash)
            ) CHARACTER SET utf8mb4
                """
            )
        self.connection.commit()

    def record_page(
        self,
        url: str,
        *,
        status_code: int | None = None,
        content_type: str | None = None,
        error: str | None = None,
    ) -> None:
        seen = utc_now()
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO pages(url, url_hash, first_seen, last_seen, status_code, content_type, error)
                VALUES (%s, UNHEX(SHA2(%s, 256)), %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    url = VALUES(url),
                    last_seen = VALUES(last_seen),
                    status_code = VALUES(status_code),
                    content_type = VALUES(content_type),
                    error = VALUES(error)
                """,
                (url, url, seen, seen, status_code, content_type, error),
            )
        self.connection.commit()

    def record_link(self, source_url: str, target_url: str) -> None:
        seen = utc_now()
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO links(
                    source_url, target_url, link_hash, target_hash, first_seen, last_seen
                )
                VALUES (
                    %s, %s, UNHEX(SHA2(CONCAT(%s, CHAR(0), %s), 256)),
                    UNHEX(SHA2(%s, 256)), %s, %s
                )
                ON DUPLICATE KEY UPDATE last_seen = VALUES(last_seen)
                """,
                (source_url, target_url, source_url, target_url, target_url, seen, seen),
            )

    def commit(self) -> None:
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "CrawlDatabase":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

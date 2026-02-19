#!/usr/bin/env python3
"""
Moodle documentation crawler for Crawl4AI.

Features:
- BFS crawl within /403/en/ namespace
- Markdown + HTML extraction
- Internal/external links capture
- Images capture
- YouTube links capture (from external links + HTML)
- JSONL outputs and optional screenshots
"""

import argparse
import asyncio
import base64
import json
import os
import re
from collections import deque
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

# Keep Crawl4AI state inside the project to avoid permission issues.
os.environ.setdefault("CRAWL4_AI_BASE_DIRECTORY", str(Path.cwd()))

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig


YOUTUBE_HOSTS = (
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
)
NOISY_QUERY_PARAMS = {"oldid", "printable", "diff"}
SKIP_TOKENS = ("special:", "action=edit", "action=history", "veaction=edit", "printable=yes")
YOUTUBE_URL_RE = re.compile(r'https?://[^\s"\'<>]+', re.IGNORECASE)
HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)


def ensure_dirs(out_dir: Path, with_screenshots: bool) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    screenshots = out_dir / "screenshots"
    if with_screenshots:
        screenshots.mkdir(parents=True, exist_ok=True)
    return {
        "pages": out_dir / "pages.jsonl",
        "images": out_dir / "images.jsonl",
        "youtube": out_dir / "youtube_links.jsonl",
        "errors": out_dir / "errors.jsonl",
        "screenshots": screenshots,
    }


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())._replace(fragment="")
    params = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in NOISY_QUERY_PARAMS
    ]
    return urlunparse(parsed._replace(query=urlencode(params, doseq=True)))


def iter_link_urls(items: list[Any] | None) -> list[str]:
    urls: list[str] = []
    for item in items or []:
        if isinstance(item, str) and item.strip():
            urls.append(item)
            continue
        if isinstance(item, dict):
            for key in ("href", "url", "link"):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    urls.append(value)
                    break
    return urls


def normalize_links(base_url: str, items: list[Any] | None) -> list[str]:
    return sorted({normalize_url(urljoin(base_url, raw)) for raw in iter_link_urls(items)})


def extract_links_from_html(base_url: str, html: str) -> tuple[list[str], list[str]]:
    if not html:
        return [], []

    internal: set[str] = set()
    external: set[str] = set()
    for raw in HREF_RE.findall(html):
        href = raw.strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        link = normalize_url(urljoin(base_url, href))
        parsed = urlparse(link)
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc == "docs.moodle.org":
            internal.add(link)
        else:
            external.add(link)
    return sorted(internal), sorted(external)


def is_moodle_doc_url(url: str, docs_prefix: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme in {"http", "https"}
        and parsed.netloc == "docs.moodle.org"
        and parsed.path.startswith(docs_prefix)
    )


def should_skip_url(url: str) -> bool:
    lowered = url.lower()
    return any(token in lowered for token in SKIP_TOKENS)


def is_youtube_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(host.endswith(pattern) for pattern in YOUTUBE_HOSTS)


def extract_youtube_from_html(html: str) -> set[str]:
    if not html:
        return set()
    urls = {raw.rstrip(").,;") for raw in YOUTUBE_URL_RE.findall(html)}
    return {u for u in urls if is_youtube_url(u)}


def normalize_images(base_url: str, images_raw: list[Any] | None) -> list[dict[str, Any]]:
    images: list[dict[str, Any]] = []
    for item in images_raw or []:
        if isinstance(item, str):
            images.append({"src": normalize_url(urljoin(base_url, item))})
            continue
        if not isinstance(item, dict):
            continue
        raw_src = item.get("src") or item.get("url")
        if not raw_src:
            continue
        img_url = normalize_url(urljoin(base_url, raw_src))
        images.append({**item, "src": img_url})
    return images


def safe_filename_from_url(url: str, suffix: str = ".png") -> str:
    path = urlparse(url).path.strip("/").replace("/", "_") or "main_page"
    return f"{path[:120]}{suffix}"


def write_screenshot(raw: Any, output_path: Path) -> str | None:
    if not raw:
        return None
    data: bytes | None = None
    if isinstance(raw, bytes):
        data = raw
    elif isinstance(raw, str):
        try:
            data = base64.b64decode(raw)
        except Exception:
            return None
    if not data:
        return None
    output_path.write_bytes(data)
    return str(output_path)


def load_cookie_config(cookies_file: str | None) -> dict[str, Any]:
    if not cookies_file:
        return {"cookies": None, "storage_state": None}

    path = Path(cookies_file)
    if not path.exists():
        raise FileNotFoundError(f"Cookies file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, list):
        return {"cookies": payload, "storage_state": None}
    if isinstance(payload, dict) and isinstance(payload.get("cookies"), list):
        return {"cookies": None, "storage_state": payload}
    raise ValueError("Unsupported cookies file format. Expected JSON array or storage_state object.")


def build_browser_config(cookies_file: str | None, user_agent: str | None) -> BrowserConfig:
    cookie_config = load_cookie_config(cookies_file)
    kwargs: dict[str, Any] = {
        "headless": True,
        "viewport_width": 1440,
        "viewport_height": 900,
        "cookies": cookie_config["cookies"],
        "storage_state": cookie_config["storage_state"],
    }
    if user_agent:
        kwargs["user_agent"] = user_agent
    return BrowserConfig(**kwargs)


async def crawl_moodle_docs(
    start_url: str,
    docs_prefix: str,
    out_dir: Path,
    max_pages: int,
    max_concurrent: int,
    with_screenshots: bool,
    delay_seconds: float,
    cookies_file: str | None,
    user_agent: str | None,
) -> None:
    paths = ensure_dirs(out_dir, with_screenshots)
    browser_config = build_browser_config(cookies_file, user_agent)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        remove_overlay_elements=True,
        wait_for="css:body",
        page_timeout=60000,
        screenshot=with_screenshots,
    )

    frontier: deque[str] = deque([normalize_url(start_url)])
    queued = {frontier[0]}
    visited: set[str] = set()

    page_limit = max_pages if max_pages > 0 else None
    discovered = 0
    success = 0
    failed = 0
    unique_youtube: set[str] = set()
    unique_images: set[str] = set()

    async with AsyncWebCrawler(config=browser_config) as crawler:
        while frontier and (page_limit is None or discovered < page_limit):
            batch: list[str] = []
            while frontier and len(batch) < max_concurrent:
                if page_limit is not None and discovered + len(batch) >= page_limit:
                    break
                url = frontier.popleft()
                if url in visited:
                    continue
                visited.add(url)
                batch.append(url)
            if not batch:
                continue

            results = await crawler.arun_many(urls=batch, config=run_config, max_concurrent=max_concurrent)
            for result in results:
                discovered += 1
                url = normalize_url(result.url)

                if not result.success:
                    failed += 1
                    append_jsonl(paths["errors"], {"url": url, "error": result.error_message})
                    continue

                success += 1
                links = result.links or {}
                media = result.media or {}
                metadata = result.metadata or {}

                internal_urls = normalize_links(url, links.get("internal", []))
                external_urls = normalize_links(url, links.get("external", []))
                if not internal_urls and not external_urls:
                    html_internal, html_external = extract_links_from_html(url, result.html or "")
                    internal_urls = html_internal
                    external_urls = html_external

                for link in internal_urls:
                    if link in visited or link in queued:
                        continue
                    if not is_moodle_doc_url(link, docs_prefix) or should_skip_url(link):
                        continue
                    frontier.append(link)
                    queued.add(link)

                images = normalize_images(url, media.get("images", []))
                for image in images:
                    src = image.get("src")
                    if not isinstance(src, str) or src in unique_images:
                        continue
                    unique_images.add(src)
                    append_jsonl(paths["images"], {"page_url": url, **image})

                youtube_links = {link for link in external_urls if is_youtube_url(link)}
                youtube_links.update(extract_youtube_from_html(result.html or ""))
                youtube_links = {normalize_url(link) for link in youtube_links}

                for yt in sorted(youtube_links):
                    if yt in unique_youtube:
                        continue
                    unique_youtube.add(yt)
                    append_jsonl(paths["youtube"], {"page_url": url, "youtube_url": yt})

                screenshot_file = None
                if with_screenshots and result.screenshot:
                    screenshot_path = paths["screenshots"] / safe_filename_from_url(url)
                    screenshot_file = write_screenshot(result.screenshot, screenshot_path)

                append_jsonl(
                    paths["pages"],
                    {
                        "url": url,
                        "title": metadata.get("title"),
                        "description": metadata.get("description"),
                        "markdown": result.markdown,
                        "html": result.html,
                        "internal_links": internal_urls,
                        "external_links": external_urls,
                        "images": images,
                        "youtube_links": sorted(youtube_links),
                        "screenshot_file": screenshot_file,
                    },
                )

            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

            print(
                f"Processed={discovered} Success={success} Failed={failed} "
                f"Queue={len(frontier)} YouTube={len(unique_youtube)} Images={len(unique_images)}"
            )

    print("Crawl finished.")
    print(f"Output dir: {out_dir}")
    print(f"Pages: {success}, Failed: {failed}, Discovered: {discovered}")
    print(f"Unique images: {len(unique_images)}, Unique YouTube links: {len(unique_youtube)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl Moodle docs with Crawl4AI.")
    parser.add_argument("--start-url", default="https://docs.moodle.org/501/en/Main_page", help="Start URL.")
    parser.add_argument("--docs-prefix", default="/403/en/", help="Path prefix for allowed doc pages.")
    parser.add_argument("--out-dir", default="data/moodle_docs", help="Output directory.")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=20,
        help="Maximum number of pages to crawl. Use 0 for no limit.",
    )
    parser.add_argument("--max-concurrent", type=int, default=3, help="Maximum concurrent crawl requests.")
    parser.add_argument("--delay-seconds", type=float, default=0.5, help="Delay between batches in seconds.")
    parser.add_argument("--with-screenshots", action="store_true", help="Save page screenshots to output folder.")
    parser.add_argument(
        "--cookies-file",
        default=None,
        help="Path to JSON cookies file (cookies array or Playwright storage_state).",
    )
    parser.add_argument("--user-agent", default=None, help="Custom User-Agent string.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(
        crawl_moodle_docs(
            start_url=args.start_url,
            docs_prefix=args.docs_prefix,
            out_dir=Path(args.out_dir),
            max_pages=args.max_pages,
            max_concurrent=args.max_concurrent,
            with_screenshots=args.with_screenshots,
            delay_seconds=args.delay_seconds,
            cookies_file=args.cookies_file,
            user_agent=args.user_agent,
        )
    )


if __name__ == "__main__":
    main()

import argparse
import json
import re
from collections.abc import Generator
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

CHALLENGE_MARKERS = (
    "just a moment",
    "one moment",
    "security check",
    "cloudflare",
    "captcha",
    "проверка выполнена успешно",
    "taking you to moodle.org",
    "egy pillanat",
)

FOOTER_MARKERS = (
    'retrieved from "[',
    "[tools](",
    "[what links here](",
    "[related changes](",
    "[special pages](",
    "[printable version](",
    "[permanent link](",
    "[page information](",
    "[in other languages](",
    "this page was last edited",
    "content is available under",
    "[privacy](",
    "[about moodle docs](",
    "[disclaimers](",
    "[accessibility statement](",
    "[![powered by mediawiki]",
)
BAD_YOUTUBE_PATTERNS = ("youtube.com/howyoutubeworks/user-settings/privacy",)

DROP_EXACT_LINES = {
    "Menu",
    "Main page",
    "Table of contents",
    "Docs overview",
    "Recent changes",
    "Log in",
    "Article",
    "View history",
    "From MoodleDocs",
    "Load video",
    "YouTube",
    "Continue",
    "---",
}

DROP_LINE_STARTS = (
    "# Documentation",
    "[Main page](",
    "[Table of contents](",
    "[Docs overview](",
    "[Recent changes](",
    "[Random page](",
    "[Category index](",
    "[Global search](",
    "[log in](",
    "[4.5 docs](",
    "[4.4 docs](",
    "[article](",
    "[page comments](",
    "[view source](",
    "[view history](",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare clean markdown corpus from pages.jsonl")
    parser.add_argument("--input", default="data/moodle_docs/pages.jsonl", help="Path to raw pages.jsonl")
    parser.add_argument(
        "--output-jsonl",
        default="data/moodle_docs/pages.cleaned.jsonl",
        help="Path to cleaned JSONL output",
    )
    parser.add_argument(
        "--output-md-dir",
        default="data/moodle_docs/clean_markdown",
        help="Directory where cleaned .md files will be stored",
    )
    parser.add_argument(
        "--min-markdown-chars",
        type=int,
        default=500,
        help="Minimum markdown length to keep record",
    )
    parser.add_argument(
        "--youtube-links-jsonl",
        default="data/moodle_docs/youtube_links.jsonl",
        help="Path to youtube_links.jsonl (page_url + youtube_url).",
    )
    return parser.parse_args()


def normalize_url(url: str) -> str:
    parsed = urlparse((url or "").strip())._replace(fragment="")
    return urlunparse(parsed)


def iter_jsonl(path: Path) -> "Generator[dict[str, Any], None, None]":
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def is_blocked_youtube(url: str) -> bool:
    lowered = normalize_url(url).lower().rstrip("/")
    return any(pattern in lowered for pattern in BAD_YOUTUBE_PATTERNS)


def load_youtube_links_map(path: Path) -> dict[str, set[str]]:
    if not path.exists():
        return {}
    by_page: dict[str, set[str]] = {}
    for row in iter_jsonl(path):
        page_url = normalize_url(row.get("page_url") or "")
        yt_url = normalize_url(row.get("youtube_url") or "")
        if not page_url or not yt_url:
            continue
        if not yt_url.startswith(("http://", "https://")):
            continue
        if is_blocked_youtube(yt_url):
            continue
        by_page.setdefault(page_url, set()).add(yt_url)
    return by_page


def is_challenge_page(title: str, markdown: str) -> bool:
    haystack = ((title or "") + "\n" + (markdown or "")[:4000]).lower()
    return any(marker in haystack for marker in CHALLENGE_MARKERS)


def clean_title(title: str, fallback: str = "Untitled") -> str:
    raw = (title or "").strip()
    if not raw:
        return fallback
    return raw.split(" - ", 1)[0].strip() or fallback


def strip_markdown_to_text(markdown: str, title: str) -> str:
    lines = markdown.splitlines()
    expected_h1 = f"# {title}".strip()
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip() == expected_h1:
            start_idx = i
            break
    else:
        for i, line in enumerate(lines):
            if line.strip().startswith("# "):
                start_idx = i
                break

    lines = lines[start_idx:]
    out: list[str] = []
    in_toc = False

    for raw_line in lines:
        line = raw_line.rstrip()
        s = line.strip()
        s_lower = s.lower()

        if any(s_lower.startswith(marker) for marker in FOOTER_MARKERS):
            break

        if s == "## Contents":
            in_toc = True
            continue
        if in_toc:
            if s.startswith("## "):
                in_toc = False
            else:
                continue

        if s in DROP_EXACT_LINES:
            continue
        if s.startswith(DROP_LINE_STARTS) or s_lower.startswith(DROP_LINE_STARTS):
            continue
        if "[ctrl-option-" in s_lower:
            continue
        if re.fullmatch(r"\d\.\d docs(?: \d\.\d docs)+", s_lower):
            continue
        if "YouTube might collect personal data." in s:
            continue

        # Remove image-only markdown artifacts.
        if re.fullmatch(r"!\[.*\]\(.*\)", s) or re.fullmatch(r"\[\s*.*\s*\]\(https?://.*\)", s):
            continue

        # Keep text, drop markdown URL targets.
        line = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r"\1", line)
        line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", line)
        line = re.sub(r"`{1,3}", "", line)
        out.append(line)

    compact: list[str] = []
    for line in out:
        if line.strip() == "" and compact and compact[-1].strip() == "":
            continue
        if compact and line.strip() == expected_h1 and compact[-1].strip() == expected_h1:
            continue
        compact.append(line)

    # Remove leading nav list under the first H1, e.g.:
    # # About Moodle FAQ
    #   * Features
    #   * ...
    if compact and compact[0].strip() == expected_h1:
        i = 1
        while i < len(compact) and compact[i].strip() == "":
            i += 1
        j = i
        while j < len(compact) and compact[j].lstrip().startswith("* "):
            j += 1
        if j - i >= 3:
            compact = compact[:i] + compact[j:]
            while len(compact) > 1 and compact[1].strip() == "":
                compact.pop(1)

    return "\n".join(compact).strip()


def related_media_links(row: dict[str, Any], youtube_from_jsonl: set[str] | None) -> tuple[list[str], list[str]]:
    youtube_set = set(youtube_from_jsonl or set())
    youtube_set.update(
        normalize_url(link)
        for link in (row.get("youtube_links") or [])
        if isinstance(link, str) and link.startswith(("http://", "https://"))
    )
    youtube = sorted(link for link in youtube_set if not is_blocked_youtube(link))

    image_links: set[str] = set()
    for item in row.get("images") or []:
        if isinstance(item, str):
            url = item
        elif isinstance(item, dict):
            url = item.get("src") or item.get("url") or ""
        else:
            continue
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            image_links.add(normalize_url(url))

    return youtube, sorted(image_links)


def build_markdown(title: str, url: str, body_text: str, youtube: list[str], images: list[str]) -> str:
    heading = f"# {title}"
    body_lines = body_text.splitlines()

    while body_lines and body_lines[0].strip() == "":
        body_lines.pop(0)
    while body_lines and body_lines[0].strip() == heading:
        body_lines.pop(0)
        while body_lines and body_lines[0].strip() == "":
            body_lines.pop(0)

    bullet_end = 0
    while bullet_end < len(body_lines) and body_lines[bullet_end].lstrip().startswith("* "):
        bullet_end += 1
    if bullet_end >= 3:
        body_lines = body_lines[bullet_end:]
        while body_lines and body_lines[0].strip() == "":
            body_lines.pop(0)

    body_text = "\n".join(body_lines).strip()

    lines = [heading, "", body_text or "(empty)"]
    lines.extend(["", "## Sources", f"- [{title}]({url})"])

    if youtube or images:
        lines.extend(["", "## Media"])
        if youtube:
            lines.append("### YouTube")
            lines.extend(f"- {link}" for link in youtube)
        if images:
            lines.append("### Images")
            lines.extend(f"- {link}" for link in images)

    return "\n".join(lines).strip() + "\n"


def slug_from_url(url: str) -> str:
    slug = urlparse(url).path.strip("/").replace("/", "__")
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", slug)
    return slug or "page"


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_jsonl = Path(args.output_jsonl)
    output_md_dir = Path(args.output_md_dir)
    youtube_links_path = Path(args.youtube_links_jsonl)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    output_md_dir.mkdir(parents=True, exist_ok=True)
    youtube_by_page = load_youtube_links_map(youtube_links_path)

    by_url: dict[str, dict[str, Any]] = {}
    total = 0
    skipped_missing = 0
    skipped_challenge = 0
    skipped_short = 0

    for row in iter_jsonl(input_path):
        total += 1
        url = normalize_url(row.get("url") or "")
        markdown = row.get("markdown") or ""
        title = (row.get("title") or "").strip()

        if not url or not markdown:
            skipped_missing += 1
            continue
        if is_challenge_page(title, markdown):
            skipped_challenge += 1
            continue
        if len(markdown.strip()) < args.min_markdown_chars:
            skipped_short += 1
            continue

        current = by_url.get(url)
        if current is None or len(markdown) > len(current.get("markdown") or ""):
            by_url[url] = row

    kept = 0
    with output_jsonl.open("w", encoding="utf-8") as out:
        for url in sorted(by_url):
            row = by_url[url]
            title = clean_title(row.get("title") or "", fallback="Untitled")
            body_text = strip_markdown_to_text(row.get("markdown") or "", title)
            youtube, images = related_media_links(row, youtube_by_page.get(url))
            markdown_clean = build_markdown(title, url, body_text, youtube, images)

            payload = {
                "url": url,
                "title": title,
                "markdown_clean": markdown_clean,
                "youtube_links": youtube,
                "image_links": images,
                "source": {"title": title, "url": url},
            }
            out.write(json.dumps(payload, ensure_ascii=False) + "\n")

            md_path = output_md_dir / f"{slug_from_url(url)}.md"
            md_path.write_text(markdown_clean, encoding="utf-8")
            kept += 1

    print("Done.")
    print(f"Input rows: {total}")
    print(f"Kept rows: {kept}")
    print(f"Skipped challenge: {skipped_challenge}")
    print(f"Skipped short: {skipped_short}")
    print(f"Skipped missing: {skipped_missing}")
    print(f"JSONL output: {output_jsonl}")
    print(f"Markdown dir: {output_md_dir}")


if __name__ == "__main__":
    main()

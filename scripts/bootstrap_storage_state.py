#!/usr/bin/env python3
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

STATE_PATH = Path(".state/moodle_storage_state.json")
UA_PATH = Path(".state/moodle_user_agent.txt")

CHALLENGE_MARKERS = [
    "just a moment",
    "один момент",
    "egy pillanat",
    "security check",
    "captcha",
    "cloudflare",
]


def is_challenge(title: str, body: str) -> tuple[bool, list[str]]:
    t = (title or "").lower()
    b = (body or "").lower()
    hits = [m for m in CHALLENGE_MARKERS if m in t or m in b]
    return (len(hits) > 0, hits)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cdp-url",
        default="http://127.0.0.1:9222",
        help="CDP URL of manually opened Chrome.",
    )
    return parser.parse_args()


args = parse_args()

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(args.cdp_url)
    context = browser.contexts[0] if browser.contexts else browser.new_context()

    page = context.pages[0] if context.pages else context.new_page()
    print("Переключись в Chrome, пройди challenge и открой реальную страницу Moodle.")
    input("После этого нажми Enter... ")

    title = page.title()
    body = page.content()
    current_url = page.url
    blocked, hits = is_challenge(title, body)

    print(f"Current URL: {current_url}")
    print(f"Current title: {title}")

    if blocked:
        print(f"Похоже, всё ещё challenge-страница. Маркеры: {', '.join(hits)}")
        print("State не сохраняю.")
    else:
        ua = page.evaluate("() => navigator.userAgent")
        UA_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        UA_PATH.write_text(ua, encoding="utf-8")
        context.storage_state(path=str(STATE_PATH))
        print(f"UA saved: {UA_PATH}")
        print(f"Storage state saved: {STATE_PATH}")

    browser.close()

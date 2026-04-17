#!/usr/bin/env python3
"""
Reiss stock checker for Valencia dress (AP6-297, Ivory/Black, size 12).
Uses Playwright to render the JS page and bypass bot protection.
"""

import os
import json
import re
import urllib.request

PRODUCT_URL = "https://www.reiss.com/style/su581028/ap6297"
TARGET_SIZE  = "12"

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]


def check_size_available() -> bool:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-GB",
        )
        page = context.new_page()

        print(f"Opening {PRODUCT_URL} ...")
        # Wait for the page to fully load including JS
        page.goto(PRODUCT_URL, wait_until="networkidle", timeout=30000)
        # Extra pause to let React render size buttons
        page.wait_for_timeout(3000)

        html = page.content()
        browser.close()

    print("Page loaded, analysing sizes...")

    # ── Strategy 1: find JSON blobs with size + stock info ───────────────
    # Reiss embeds Next.js __NEXT_DATA__ or similar JSON in the page
    json_blobs = re.findall(r'\{[^{}]{20,5000}\}', html)
    for blob in json_blobs:
        if '"12"' not in blob and "'12'" not in blob and ':12,' not in blob:
            continue
        try:
            data = json.loads(blob)
            result = walk_json_for_size(data, TARGET_SIZE)
            if result is not None:
                print(f"✅ Found via JSON blob: size 12 in_stock={result}")
                return result
        except Exception:
            pass

    # ── Strategy 2: regex on raw HTML ───────────────────────────────────
    # Pattern: size label near stock/available field
    in_stock_patterns = [
        r'"(?:size|label|sizeLabel)"\s*:\s*"12"[^}]{0,120}"(?:available|inStock|isAvailable)"\s*:\s*true',
        r'"(?:available|inStock|isAvailable)"\s*:\s*true[^}]{0,120}"(?:size|label|sizeLabel)"\s*:\s*"12"',
        r'data-size=["\']12["\'][^>]*(?<!disabled)(?<!sold-out)(?<!unavailable)>',
    ]
    out_of_stock_patterns = [
        r'"(?:size|label|sizeLabel)"\s*:\s*"12"[^}]{0,120}"(?:available|inStock|isAvailable)"\s*:\s*false',
        r'"(?:available|inStock|isAvailable)"\s*:\s*false[^}]{0,120}"(?:size|label|sizeLabel)"\s*:\s*"12"',
        r'data-size=["\']12["\'][^>]*(?:disabled|sold-out|unavailable)',
    ]

    for pat in in_stock_patterns:
        if re.search(pat, html, re.IGNORECASE):
            print(f"✅ Regex matched in-stock: {pat[:60]}")
            return True

    for pat in out_of_stock_patterns:
        if re.search(pat, html, re.IGNORECASE):
            print(f"❌ Regex matched out-of-stock: {pat[:60]}")
            return False

    # ── Strategy 3: look at __NEXT_DATA__ specifically ──────────────────
    next_data = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if next_data:
        try:
            data = json.loads(next_data.group(1))
            result = walk_json_for_size(data, TARGET_SIZE)
            if result is not None:
                print(f"✅ Found in __NEXT_DATA__: size 12 in_stock={result}")
                return result
        except Exception as e:
            print(f"[WARN] Could not parse __NEXT_DATA__: {e}")

    print("⚠️  Could not determine stock status — assuming OUT of stock to avoid false alerts.")
    return False


def walk_json_for_size(obj, target_size: str, depth: int = 0):
    """Recursively walk JSON looking for size/stock pairs."""
    if depth > 10:
        return None

    if isinstance(obj, dict):
        size_val = str(
            obj.get("size") or obj.get("label") or obj.get("sizeLabel") or ""
        ).strip()
        if size_val == target_size:
            for key in ("available", "inStock", "isAvailable", "stockLevel", "qty"):
                if key in obj:
                    val = obj[key]
                    if isinstance(val, bool):
                        return val
                    if isinstance(val, (int, float)):
                        return val > 0
        for v in obj.values():
            result = walk_json_for_size(v, target_size, depth + 1)
            if result is not None:
                return result

    elif isinstance(obj, list):
        for item in obj:
            result = walk_json_for_size(item, target_size, depth + 1)
            if result is not None:
                return result

    return None


def send_telegram(message: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
        if not result.get("ok"):
            raise RuntimeError(f"Telegram error: {result}")

def main() -> None:
    print(f"Checking stock for Valencia dress size {TARGET_SIZE}...")
    available = check_size_available()

    if available:
        print("✅ Size 12 IN STOCK — sending Telegram notification!")
        message = (
            f"🛍 <b>Valencia dress — Size {TARGET_SIZE} is back in stock!</b>\n\n"
            f"Reiss Valencia Contrast-Trim Flared Midi Dress\n"
            f"Colour: Ivory/Black · Size: {TARGET_SIZE}\n\n"
            f'👉 <a href="{PRODUCT_URL}">Buy now — £128</a>'
        )
        send_telegram(message)
        print("Telegram message sent.")
    else:
        print(f"❌ Size {TARGET_SIZE} still out of stock. No notification sent.")


if __name__ == "__main__":
    main()

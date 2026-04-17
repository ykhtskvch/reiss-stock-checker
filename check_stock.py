#!/usr/bin/env python3
"""
Reiss stock checker for Valencia dress (AP6-297, Ivory/Black).
Checks multiple sizes and sends a Telegram notification for each one in stock.
"""

import os
import json
import re
import urllib.request

PRODUCT_URL  = "https://www.reiss.com/style/su581028/ap6297"
TARGET_SIZES = ["10", "12"]  # Add or remove sizes here

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]


def check_size_available(target_size: str) -> bool:
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

        print(f"  Opening {PRODUCT_URL} ...")
        page.goto(PRODUCT_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)

        html = page.content()
        browser.close()

    print(f"  Page loaded, analysing size {target_size}...")

    # ── Strategy 1: find JSON blobs with size + stock info ───────────────
    json_blobs = re.findall(r'\{[^{}]{20,5000}\}', html)
    for blob in json_blobs:
        if f'"{target_size}"' not in blob and f"'{target_size}'" not in blob:
            continue
        try:
            data = json.loads(blob)
            result = walk_json_for_size(data, target_size)
            if result is not None:
                print(f"  Found via JSON blob: size {target_size} in_stock={result}")
                return result
        except Exception:
            pass

    # ── Strategy 2: regex on raw HTML ────────────────────────────────────
    in_stock_patterns = [
        rf'"(?:size|label|sizeLabel)"\s*:\s*"{target_size}"[^}}]{{0,120}}"(?:available|inStock|isAvailable)"\s*:\s*true',
        rf'"(?:available|inStock|isAvailable)"\s*:\s*true[^}}]{{0,120}}"(?:size|label|sizeLabel)"\s*:\s*"{target_size}"',
    ]
    out_of_stock_patterns = [
        rf'"(?:size|label|sizeLabel)"\s*:\s*"{target_size}"[^}}]{{0,120}}"(?:available|inStock|isAvailable)"\s*:\s*false',
        rf'"(?:available|inStock|isAvailable)"\s*:\s*false[^}}]{{0,120}}"(?:size|label|sizeLabel)"\s*:\s*"{target_size}"',
    ]

    for pat in in_stock_patterns:
        if re.search(pat, html, re.IGNORECASE):
            print(f"  Regex matched in-stock for size {target_size}")
            return True

    for pat in out_of_stock_patterns:
        if re.search(pat, html, re.IGNORECASE):
            print(f"  Regex matched out-of-stock for size {target_size}")
            return False

    # ── Strategy 3: __NEXT_DATA__ ─────────────────────────────────────────
    next_data = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if next_data:
        try:
            data = json.loads(next_data.group(1))
            result = walk_json_for_size(data, target_size)
            if result is not None:
                print(f"  Found in __NEXT_DATA__: size {target_size} in_stock={result}")
                return result
        except Exception as e:
            print(f"  [WARN] Could not parse __NEXT_DATA__: {e}")

    print(f"  Could not determine stock status for size {target_size} — assuming OUT of stock.")
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
    for size in TARGET_SIZES:
        print(f"\nChecking size {size}...")
        available = check_size_available(size)

        if available:
            print(f"✅ Size {size} IN STOCK — sending Telegram notification!")
            message = (
                f"🛍 <b>Valencia dress — Size {size} is back in stock!</b>\n\n"
                f"Reiss Valencia Contrast-Trim Flared Midi Dress\n"
                f"Colour: Ivory/Black · Size: {size}\n\n"
                f'👉 <a href="{PRODUCT_URL}">Buy now — £128</a>'
            )
            send_telegram(message)
            print("  Telegram message sent.")
        else:
            print(f"❌ Size {size} still out of stock. No notification sent.")


if __name__ == "__main__":
    main()

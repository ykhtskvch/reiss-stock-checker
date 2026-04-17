#!/usr/bin/env python3
"""
Reiss stock checker for Valencia dress (AP6-297, Ivory/Black, size 12).
Uses Playwright to render the JS page and bypass bot protection.
"""

import os
import sys
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
        page.goto(PRODUCT_URL, wait_until="networkidle", timeout=30000)

        # Wait for the size buttons to appear
        page.wait_for_selector(
            "[data-testid='size-selector'], .size-selector, [class*='SizeButton'], [class*='size']",
            timeout=15000
        )

        html = page.content()
        browser.close()

    print("Page loaded, analysing sizes...")

    # Patterns that confirm size 12 is IN stock
    patterns_in_stock = [
        r'"size"\s*:\s*"12"\s*,[^}]*"(?:available|inStock)"\s*:\s*true',
        r'"label"\s*:\s*"12"\s*,[^}]*"available"\s*:\s*true',
        r'"sizeLabel"\s*:\s*"12"\s*,[^}]*"inStock"\s*:\s*true',
    ]
    # Patterns that confirm size 12 is OUT of stock
    patterns_out_of_stock = [
        r'"size"\s*:\s*"12"\s*,[^}]*"(?:available|inStock)"\s*:\s*false',
        r'"label"\s*:\s*"12"\s*,[^}]*"available"\s*:\s*false',
        r'"sizeLabel"\s*:\s*"12"\s*,[^}]*"inStock"\s*:\s*false',
    ]

    for pat in patterns_in_stock:
        if re.search(pat, html, re.IGNORECASE):
            print(f"✅ Pattern matched (in stock): {pat}")
            return True

    for pat in patterns_out_of_stock:
        if re.search(pat, html, re.IGNORECASE):
            print(f"❌ Pattern matched (out of stock): {pat}")
            return False

    # Safe fallback: assume out of stock to avoid false alerts
    print("⚠️  Could not determine stock status definitively — assuming OUT of stock.")
    return False


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
        print("✅ Size 12 is IN STOCK — sending Telegram notification!")
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

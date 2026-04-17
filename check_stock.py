#!/usr/bin/env python3
"""
Reiss stock checker for Valencia dress (AP6-297, Ivory/Black, size 12).
Sends a Telegram notification when size 12 becomes available.
"""

import os
import re
import sys
import json
import urllib.request
import urllib.parse
import urllib.error

# ── Configuration ────────────────────────────────────────────────────────────
PRODUCT_URL = "https://www.reiss.com/style/su581028/ap6297"
# Reiss serves stock data via their Next platform API
STOCK_API_URL = "https://www.reiss.com/api/product/AP6-297"
TARGET_SIZE   = "12"

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]   # set in GitHub Secrets
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]     # set in GitHub Secrets
# ─────────────────────────────────────────────────────────────────────────────


def fetch_url(url: str, headers: dict | None = None) -> str:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")


def check_size_available() -> bool:
    """
    Reiss pages are JS-rendered, so we hit their internal JSON API directly.
    The endpoint returns a list of variants with 'size' and 'stockLevel' fields.
    Falls back to HTML scraping if the API shape changes.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; StockBot/1.0)"
        ),
        "Accept": "application/json, text/html",
    }

    # ── Try JSON API first ────────────────────────────────────────────────
    try:
        raw = fetch_url(STOCK_API_URL, headers)
        data = json.loads(raw)

        # Shape: {"variants": [{"size": "12", "stockLevel": 3, ...}, ...]}
        variants = data.get("variants") or data.get("items") or []
        for v in variants:
            size = str(v.get("size", "") or v.get("sizeLabel", "")).strip()
            stock = int(v.get("stockLevel", 0) or v.get("inStock", 0) or 0)
            if size == TARGET_SIZE and stock > 0:
                return True
        # If we found size 12 with stock 0 → definitely out of stock
        for v in variants:
            size = str(v.get("size", "") or v.get("sizeLabel", "")).strip()
            if size == TARGET_SIZE:
                return False
    except Exception as e:
        print(f"[INFO] JSON API attempt failed ({e}), falling back to HTML scrape.")

    # ── Fallback: HTML scrape ────────────────────────────────────────────
    # The page's HTML includes a JSON blob inside a <script> tag with stock info
    try:
        html = fetch_url(PRODUCT_URL, headers)

        # Look for Next.js / embedded JSON that lists sizes and availability
        # Pattern: "size":"12","available":true  OR "size":"12","soldOut":false
        pattern_available = r'"size"\s*:\s*"12"\s*,\s*"(?:available|inStock)"\s*:\s*true'
        pattern_soldout   = r'"size"\s*:\s*"12"\s*,\s*"soldOut"\s*:\s*false'

        if re.search(pattern_available, html, re.IGNORECASE):
            return True
        if re.search(pattern_soldout, html, re.IGNORECASE):
            return True

        # Also check if size 12 button is NOT marked disabled/sold-out in HTML
        # e.g.  data-size="12" class="... sold-out ..."
        soldout_pattern = r'data-size=["\']12["\'][^>]*class=["\'][^"\']*sold.out'
        if re.search(soldout_pattern, html, re.IGNORECASE):
            return False

        # Last resort: if "12" appears in the size selector without "sold-out"
        size_block = re.search(
            r'(Size|sizes)[^{]{0,200}12', html, re.IGNORECASE | re.DOTALL
        )
        if size_block:
            block = size_block.group(0)
            if "sold" not in block.lower() and "unavailable" not in block.lower():
                return True

    except Exception as e:
        print(f"[ERROR] HTML scrape also failed: {e}")
        sys.exit(1)

    return False


def send_telegram(message: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
        if not result.get("ok"):
            raise RuntimeError(f"Telegram error: {result}")


def main() -> None:
    print(f"Checking stock for Valencia dress size {TARGET_SIZE}…")
    available = check_size_available()

    if available:
        print(f"✅ Size {TARGET_SIZE} is IN STOCK — sending Telegram notification!")
        message = (
            f"🛍 <b>Valencia dress — Size {TARGET_SIZE} is back in stock!</b>\n\n"
            f"Reiss Valencia Contrast-Trim Flared Midi Dress\n"
            f"Colour: Ivory/Black · Size: {TARGET_SIZE}\n\n"
            f"👉 <a href=\"{PRODUCT_URL}\">Buy now — £128</a>"
        )
        send_telegram(message)
        print("Telegram message sent.")
    else:
        print(f"❌ Size {TARGET_SIZE} is still out of stock. No notification sent.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Publix Weekly Ad Deal Finder - configuration driven version.
"""

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver as webdriver

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]

DEFAULT_WAIT_SECONDS = 5
DEFAULT_SCROLL_PASSES = 5
DEFAULT_HEADLESS = True
DEFAULT_CONFIG_PATH = Path("config.toml")
DEFAULT_CACHE_PATH = Path(".cache/publix_deals.json")
DEFAULT_CACHE_TTL_MINUTES = 60


def setup_driver(headless=True):
    """Set up Chrome WebDriver."""
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    return webdriver(options=options)


def scroll_page(driver, passes=DEFAULT_SCROLL_PASSES, pause_seconds=2):
    """Scroll to load all lazy-loaded content."""
    last_height = driver.execute_script("return document.body.scrollHeight")

    for _ in range(passes):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_seconds)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def detect_bogo(text):

    # Detect BOGO deals with multiple patterns.

    text_lower = text.lower()

    # Pattern 1: "Buy 1 Get 1" (most common)
    if re.search(r"buy\s*\d+\s*get\s*\d+", text_lower):
        return True

    # Pattern 2: Traditional "BOGO"
    if "bogo" in text_lower:
        return True

    # Pattern 3: Spelled out variations
    bogo_phrases = ["buy one get one", "buy 1 get 1", "b1g1", "buy one, get one"]

    return any(phrase in text_lower for phrase in bogo_phrases)


def categorize_deal(text, prices):
    if detect_bogo(text):
        return "BOGO"
    elif "save" in text.lower() or re.search(r"save\s*up\s*to", text.lower()):
        return "Discount"
    elif len(prices) > 1:
        return "Price Drop"
    return "Deal"


def extract_deal_info(container):
    try:
        full_text = container.get_text(separator="\n", strip=True)

        if not full_text or len(full_text) < 5:
            return None

        lines = [l.strip() for l in full_text.split("\n") if l.strip()]
        product_name = lines[0] if lines else "Unknown Product"

        # Extract prices
        prices = re.findall(r"\$\d+\.\d{2}", full_text)
        current_price = prices[0] if prices else None

        # Detect BOGO
        is_bogo = detect_bogo(full_text)

        # Extract savings amount
        savings = None
        savings_match = re.search(r"save\s*up\s*to\s*\$(\d+\.\d{2})", full_text.lower())
        if savings_match:
            savings = f"${savings_match.group(1)}"
        elif not savings_match:
            savings_match = re.search(r"save\s*\$(\d+\.\d{2})", full_text.lower())
            if savings_match:
                savings = f"${savings_match.group(1)}"

        # Get deal description
        deal_description = None
        for line in lines:
            line_lower = line.lower()
            if "buy" in line_lower and "get" in line_lower:
                deal_description = line
                break
            elif "save" in line_lower:
                deal_description = line
                break

        # Categorize deal type
        deal_type = categorize_deal(full_text, prices)

        # Only include if there's actually a deal
        has_deal = is_bogo or savings or deal_description or len(prices) > 1

        if not has_deal:
            return None

        return {
            "product_name": product_name,
            "current_price": current_price,
            "savings": savings,
            "deal_type": deal_type,
            "deal_description": deal_description,
            "is_bogo": is_bogo,
            "full_text": full_text,
        }

    except Exception:
        return None


def find_deals(soup):
    """Find all product deals on the page."""
    deals = []

    # Strategy: Look for price elements and walk up to find containers
    price_elements = soup.find_all(string=re.compile(r"\$\d+\.\d{2}"))

    product_containers = set()
    for price_elem in price_elements:
        parent = price_elem.parent
        for _ in range(10):
            if parent and parent.name == "div":
                classes = parent.get("class", [])
                class_str = " ".join(classes).lower()

                if any(
                    keyword in class_str
                    for keyword in ["product", "item", "card", "deal", "tile"]
                ):
                    product_containers.add(parent)
                    break

                if parent.get("data-testid") or parent.get("data-product-id"):
                    product_containers.add(parent)
                    break

            parent = parent.parent if parent else None

    # Extract deals from containers
    for container in product_containers:
        deal = extract_deal_info(container)
        if deal:
            deals.append(deal)

    return deals


def print_deal(deal, index):
    """Print a single deal in a formatted way."""
    print(f"\n{'=' * 80}")
    print(f"#{index}. {deal['product_name']}")
    print("-" * 80)

    # Deal type with emoji
    emoji_map = {"BOGO": "🎁", "Discount": "💵", "Price Drop": "📉", "Deal": "🏷️"}
    emoji = emoji_map.get(deal["deal_type"], "🏷️")
    print(f"{emoji} Deal Type: {deal['deal_type']}")

    if deal.get("is_bogo"):
        print(f"🎁 BUY 1 GET 1 FREE!")

    if deal.get("current_price"):
        print(f"💰 Price: {deal['current_price']}")

    if deal.get("savings"):
        print(f"💵 Savings: {deal['savings']}")

    if deal.get("deal_description"):
        print(f"📋 Details: {deal['deal_description']}")


def parse_args():
    parser = argparse.ArgumentParser(description="Publix Weekly Ad Deal Finder")
    parser.add_argument(
        "--config",
        type=str,
        help=f"Path to TOML config file (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--search-item",
        action="append",
        help="Override search term defined in config (repeat for multiple queries)",
    )
    parser.add_argument(
        "--store-number", help="Override Publix store number from config"
    )
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Toggle headless browser mode (default: true)",
    )
    parser.add_argument(
        "--wait-seconds",
        type=float,
        help="Seconds to wait after loading the page before scraping (default: 5)",
    )
    parser.add_argument(
        "--scroll-passes",
        type=int,
        help="Number of scroll passes to load more deals (default: 5)",
    )
    parser.add_argument("--cache-file", type=str, help="Path to cache JSON file")
    parser.add_argument(
        "--cache-ttl-minutes",
        type=int,
        help=f"Minutes to reuse cached results (default: {DEFAULT_CACHE_TTL_MINUTES})",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable cache reads/writes for this run",
    )
    return parser.parse_args()


def load_config(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def normalize_search_items(raw_value) -> list[str]:
    if raw_value is None:
        return []

    if isinstance(raw_value, str):
        candidates = [raw_value]
    elif isinstance(raw_value, list):
        candidates = []
        for value in raw_value:
            if isinstance(value, str):
                candidates.append(value)
    else:
        return []

    normalized = []
    seen = set()
    for value in candidates:
        item = value.strip()
        if not item:
            continue
        item_lower = item.lower()
        if item_lower in seen:
            continue
        seen.add(item_lower)
        normalized.append(item)
    return normalized


def resolve_settings(args) -> dict:
    config_path = Path(args.config).expanduser() if args.config else DEFAULT_CONFIG_PATH
    config_data = {}
    if config_path.exists():
        config_data = load_config(config_path)
    elif args.config:
        raise SystemExit(f"❌ Config file not found: {config_path}")

    cli_search_items = normalize_search_items(args.search_item)
    config_search_items = normalize_search_items(
        config_data.get("search_item", config_data.get("search_items"))
    )
    search_items = cli_search_items or config_search_items
    if not search_items:
        raise SystemExit(
            "❌ search_item is required. Set it as an array in config or pass --search-item."
        )

    store_number = args.store_number or config_data.get("store_number")
    if store_number is not None:
        store_number = str(store_number).strip() or None

    headless = (
        args.headless
        if args.headless is not None
        else config_data.get("headless", DEFAULT_HEADLESS)
    )
    wait_seconds = args.wait_seconds or config_data.get(
        "wait_seconds", DEFAULT_WAIT_SECONDS
    )
    scroll_passes = args.scroll_passes or config_data.get(
        "scroll_passes", DEFAULT_SCROLL_PASSES
    )
    cache_enabled = config_data.get("cache_enabled", True)
    if args.no_cache:
        cache_enabled = False

    cache_file_value = args.cache_file or config_data.get(
        "cache_file", DEFAULT_CACHE_PATH
    )
    cache_file = Path(cache_file_value).expanduser()

    cache_ttl_minutes = args.cache_ttl_minutes or config_data.get(
        "cache_ttl_minutes", DEFAULT_CACHE_TTL_MINUTES
    )
    cache_ttl_seconds = max(60, int(cache_ttl_minutes) * 60)

    return {
        "search_items": search_items,
        "store_number": store_number,
        "headless": bool(headless),
        "wait_seconds": float(wait_seconds),
        "scroll_passes": int(scroll_passes),
        "config_path": config_path if config_path.exists() else None,
        "cache_enabled": bool(cache_enabled),
        "cache_file": cache_file,
        "cache_ttl_seconds": cache_ttl_seconds,
    }


def build_cache_key(store_number: str | None) -> str:
    store_part = store_number or "ALL"
    return f"all_deals::{store_part}"


def load_cache_data(cache_path: Path) -> dict:
    if not cache_path.exists():
        return {}
    try:
        with cache_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def read_cache_entry(cache_path: Path, key: str, ttl_seconds: int) -> dict | None:
    cache = load_cache_data(cache_path)
    entry = cache.get(key)
    if not entry:
        return None
    timestamp = entry.get("timestamp")
    if not isinstance(timestamp, (int, float)):
        return None
    if time.time() - timestamp > ttl_seconds:
        return None
    return entry


def write_cache_entry(cache_path: Path, key: str, payload: dict) -> None:
    cache = load_cache_data(cache_path)
    cache[key] = payload
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("w", encoding="utf-8") as handle:
        json.dump(cache, handle, indent=2)


def present_results(
    search_items: list[str],
    store_number: str | None,
    total_products: int,
    matching_deals: list[dict],
    *,
    from_cache: bool = False,
    cached_timestamp: float | None = None,
) -> None:
    joined_searches = ", ".join(f"'{item}'" for item in search_items)
    print(f"✅ Found {total_products} total products")
    print(f"✅ Found {len(matching_deals)} matching {joined_searches}")

    if from_cache and cached_timestamp:
        cached_time = datetime.fromtimestamp(cached_timestamp).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        print(f"💾 Served from cache (fetched at {cached_time})")

    print()

    if not matching_deals:
        print("😞 No deals found for your search")
        print()
        print("💡 Tips:")
        print(
            "   - Try broader search terms (e.g., 'lay' instead of 'frito lay party size')"
        )
        print("   - Check if the item is actually on sale this week")
        print("   - Try a different store number")
        return

    print(f"🎉 FOUND {len(matching_deals)} DEAL(S):")

    for i, deal in enumerate(matching_deals, 1):
        print_deal(deal, i)

    print("\n" + "=" * 80)

    bogo_count = sum(1 for d in matching_deals if d.get("is_bogo"))
    discount_count = sum(1 for d in matching_deals if d.get("deal_type") == "Discount")
    print(f"\n📊 Summary: {bogo_count} BOGO deals, {discount_count} Discounts")


def run_scraper(settings: dict):
    print("=" * 80)
    print("  PUBLIX WEEKLY AD DEAL FINDER")
    print("=" * 80)
    print()

    search_items = settings["search_items"]
    store_number = settings["store_number"]
    headless = settings["headless"]
    wait_seconds = settings["wait_seconds"]
    scroll_passes = settings["scroll_passes"]
    cache_enabled = settings["cache_enabled"]
    cache_file: Path = settings["cache_file"]
    cache_ttl_seconds = settings["cache_ttl_seconds"]
    cache_key_value = build_cache_key(store_number)
    search_lowers = [item.lower() for item in search_items]

    print()
    print(f"🔍 Searching for: {', '.join(search_items)}")
    if store_number:
        print(f"📍 Store: #{store_number}")
    else:
        print(f"📍 Store: All stores (generic weekly ad)")
    print()

    if cache_enabled:
        cached_entry = read_cache_entry(cache_file, cache_key_value, cache_ttl_seconds)
        if cached_entry:
            cached_ts = cached_entry.get("timestamp")
            cached_deals = cached_entry.get("all_deals")
            if not isinstance(cached_deals, list):
                # Backward compatibility with older cache payloads.
                cached_deals = cached_entry.get("matching_deals")
            if not isinstance(cached_deals, list):
                cached_deals = []
            total_products = int(cached_entry.get("total_products", len(cached_deals)))
            matching_deals = [
                d
                for d in cached_deals
                if isinstance(d, dict)
                and any(
                    term in str(d.get("product_name", "")).lower()
                    for term in search_lowers
                )
            ]
            age_minutes = (
                (time.time() - cached_ts) / 60
                if isinstance(cached_ts, (int, float))
                else None
            )
            if age_minutes is not None:
                print(f"💾 Using cached results (~{age_minutes:.1f} minutes old).")
            else:
                print("💾 Using cached results.")
            present_results(
                search_items,
                store_number,
                total_products,
                matching_deals,
                from_cache=True,
                cached_timestamp=cached_ts
                if isinstance(cached_ts, (int, float))
                else None,
            )
            return

    # Build URL
    if store_number:
        url = f"https://www.publix.com/savings/weekly-ad/view-all?storeNumber={store_number}"
    else:
        url = "https://www.publix.com/savings/weekly-ad/view-all"

    # Set up browser
    print("🔧 Setting up browser...")
    driver = setup_driver(headless=headless)

    try:
        # Load page
        print("🌐 Loading weekly ad page...")
        driver.get(url)

        # Wait and scroll
        print("⏳ Waiting for page to load...")
        time.sleep(wait_seconds)

        print("📜 Scrolling to load all products...")
        scroll_page(driver, passes=scroll_passes)

        # Parse page
        print("🔍 Analyzing page...")
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Find all deals
        all_deals = find_deals(soup)
        total_products = len(all_deals)

        # Filter by search term
        matching_deals = [
            d
            for d in all_deals
            if any(term in d["product_name"].lower() for term in search_lowers)
        ]

        present_results(search_items, store_number, total_products, matching_deals)

        if cache_enabled:
            write_cache_entry(
                cache_file,
                cache_key_value,
                {
                    "timestamp": time.time(),
                    "search_items": search_items,
                    "store_number": store_number,
                    "total_products": total_products,
                    "all_deals": all_deals,
                    "matching_deals": matching_deals,
                },
            )

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        driver.quit()
        print("\n✅ Done!")


def main():
    args = parse_args()
    settings = resolve_settings(args)
    run_scraper(settings)


if __name__ == "__main__":
    main()

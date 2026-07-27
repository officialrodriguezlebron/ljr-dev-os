"""
LazySun PDP Live Verification Script
Checks every product edited this engagement against the live site.

Handles loaded from: C:/Users/HomePC/AppData/Local/Temp/products_export.csv
  -- only rows with a non-empty SEO Description field are included.

Checks per page:
  1. Page loads (HTTP 200, not Shopify 404)
  2. Product title correct  (og:title meta — avoids "Your Bag" cart h1)
  3. Description present and non-empty  (.js-pdp-tab-text[body="Description"])
  4. Meta description non-empty
  5. Price > $0  (og:price:amount meta — reads main product price, not upsell)
  6. Page title present
  7. No broken HTML in description (escaped tags, doubled tags)
  [GGNC only]
  8. Meta description contains "Gumtree Golf" (SEO golf keyword)

Run:  python scripts/verify_pdp_live.py
Deps: pip install playwright && playwright install chromium
"""

import asyncio
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from playwright.async_api import async_playwright, Page
except ImportError:
    print("ERROR: Playwright not installed.")
    print("  pip install playwright && playwright install chromium")
    sys.exit(1)

BASE_URL = "https://lazysun.com/products"
CSV_PATH = Path("C:/Users/HomePC/AppData/Local/Temp/products_export.csv")

GGNC_HANDLES = {
    "puma-x-ggnc-5-panel-cap-dark-sage",
    "puma-x-ggnc-5-panel-cap-sandstone",
    "puma-x-ggnc-unstructured-cap-warm-white-fudge",
    "puma-x-ggnc-wildflower-t-shirt-warm-white",
    "puma-x-ggnc-pardoides-t-shirt-dark-sage",
    "puma-x-ggnc-short-warm-white",
}

# ── Load handles from CSV ──────────────────────────────────────────────────────

def load_handles() -> list[tuple[str, str]]:
    """Return [(handle, title), ...] for all rows with non-empty SEO Description."""
    if not CSV_PATH.exists():
        print(f"ERROR: CSV not found at {CSV_PATH}")
        sys.exit(1)

    seen: set[str] = set()
    results: list[tuple[str, str]] = []

    with open(CSV_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            handle = row.get("Handle", "").strip()
            seo_desc = row.get("SEO Description", "").strip()
            title = row.get("Title", "").strip()
            if handle and handle not in seen and seo_desc:
                seen.add(handle)
                results.append((handle, title))

    return results


# ── Selectors ─────────────────────────────────────────────────────────────────

DESC_SELECTORS = [
    '.js-pdp-tab-text[body="Description"]',  # LazySun primary (confirmed)
    ".Product-tabBody .js-pdp-tab-text",
    ".Product-tabBody",
    ".product__description",
    ".product-description",
    '[data-product-description]',
    ".rte",
]

BROKEN_HTML_PATTERNS = [
    "&lt;p&gt;",
    "&lt;br&gt;",
    "&lt;/p&gt;",
    "&lt;h",
    "&lt;ul&gt;",
    "</p></p>",
    "<p><p>",
    "<br><br><br><br>",
]

GOLF_KEYWORD = "gumtree golf"


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    handle: str
    csv_title: str = ""

    # Core checks
    loaded: bool = False
    status_code: Optional[int] = None
    error: Optional[str] = None

    has_product_title: bool = False
    product_title: str = ""

    has_description: bool = False
    description_preview: str = ""

    has_meta_desc: bool = False
    meta_desc_preview: str = ""

    has_page_title: bool = False
    page_title: str = ""

    has_price: bool = False
    price_raw: str = ""

    html_ok: bool = True
    broken_pattern: str = ""

    # GGNC-only
    is_ggnc: bool = False
    meta_has_golf_keyword: Optional[bool] = None

    @property
    def all_pass(self) -> bool:
        checks = [
            self.loaded,
            self.has_product_title,
            self.has_description,
            self.has_meta_desc,
            self.has_page_title,
            self.has_price,
            self.html_ok,
        ]
        if self.is_ggnc and self.meta_has_golf_keyword is not None:
            checks.append(self.meta_has_golf_keyword)
        return all(checks)

    @property
    def fail_reasons(self) -> list[str]:
        reasons = []
        if not self.loaded:             reasons.append("404")
        if not self.has_product_title:  reasons.append("no-title")
        if not self.has_description:    reasons.append("no-desc")
        if not self.has_meta_desc:      reasons.append("no-meta")
        if not self.has_page_title:     reasons.append("no-pg-title")
        if not self.has_price:          reasons.append("no-price")
        if not self.html_ok:            reasons.append(f"html({self.broken_pattern[:20]})")
        if self.is_ggnc and self.meta_has_golf_keyword is False:
            reasons.append("no-golf-kw")
        return reasons


# ── Check function ─────────────────────────────────────────────────────────────

async def check_product(page: Page, handle: str, csv_title: str) -> CheckResult:
    r = CheckResult(handle=handle, csv_title=csv_title, is_ggnc=(handle in GGNC_HANDLES))
    url = f"{BASE_URL}/{handle}"

    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        r.status_code = response.status if response else None

        if not response or response.status != 200:
            r.error = f"HTTP {r.status_code}"
            return r

        body_text = (await page.inner_text("body"))[:600]
        error_phrases = ["page not found", "404", "this page does not exist"]
        if any(p in body_text.lower() for p in error_phrases):
            r.error = "Shopify 404 (HTTP 200)"
            return r

        r.loaded = True

        # ── Product title via og:title (avoids cart "Your Bag" h1) ───────────
        og_title_elem = await page.query_selector('meta[property="og:title"]')
        if og_title_elem:
            og_title = (await og_title_elem.get_attribute("content") or "").strip()
            # Strip trailing " – LazySun" site suffix if present
            for suffix in [" – LazySun", " - LazySun", " | LazySun"]:
                if og_title.endswith(suffix):
                    og_title = og_title[: -len(suffix)]
            r.has_product_title = len(og_title) > 3
            r.product_title = og_title[:80]

        # ── Page title ────────────────────────────────────────────────────────
        title = await page.title()
        r.page_title = title.strip()
        r.has_page_title = len(r.page_title) > 5

        # ── Meta description ──────────────────────────────────────────────────
        meta_elem = await page.query_selector('meta[name="description"]')
        if meta_elem:
            meta_content = (await meta_elem.get_attribute("content") or "").strip()
            r.has_meta_desc = len(meta_content) > 10
            r.meta_desc_preview = meta_content[:120]

        if r.is_ggnc:
            r.meta_has_golf_keyword = GOLF_KEYWORD in r.meta_desc_preview.lower()

        # ── Price via og:price:amount (main product price, not upsell) ────────
        og_price_elem = await page.query_selector('meta[property="og:price:amount"]')
        if og_price_elem:
            price_str = (await og_price_elem.get_attribute("content") or "").strip()
            r.price_raw = price_str
            try:
                r.has_price = float(price_str) > 0
            except ValueError:
                r.has_price = False
        else:
            # Fallback: first .Product-price element (not upsell)
            try:
                elem = await page.query_selector(".js-price-preview.current_price.Product-price")
                if elem:
                    pt = (await elem.inner_text()).strip()
                    r.price_raw = pt
                    r.has_price = "$" in pt and pt != "$0"
            except Exception:
                pass

        # ── Description text ──────────────────────────────────────────────────
        desc_text = ""
        desc_html = ""
        for selector in DESC_SELECTORS:
            try:
                elem = await page.query_selector(selector)
                if elem:
                    candidate = (await elem.inner_text()).strip()
                    if len(candidate) > 30:
                        desc_text = candidate
                        desc_html = await elem.inner_html()
                        break
            except Exception:
                continue
        r.has_description = len(desc_text) > 30
        r.description_preview = desc_text[:100].replace("\n", " ")

        # ── Broken HTML ───────────────────────────────────────────────────────
        for pattern in BROKEN_HTML_PATTERNS:
            if pattern in desc_html:
                r.html_ok = False
                r.broken_pattern = pattern
                break

    except Exception as exc:
        r.error = str(exc)[:120]

    return r


# ── Output helpers ─────────────────────────────────────────────────────────────

W = 90

def ck(val: bool) -> str:
    return "OK" if val else "--"


def print_table(results: list[CheckResult]) -> None:
    # Sort: FAILs first, then PASSes alphabetically
    fails = sorted([r for r in results if not r.all_pass], key=lambda r: r.handle)
    passes = sorted([r for r in results if r.all_pass], key=lambda r: r.handle)
    ordered = fails + passes

    HEADER = (
        f"{'HANDLE':<52} {'LD':<4} {'TL':<4} {'DS':<4} {'MT':<4} "
        f"{'PR':<8} {'HT':<4} {'GK':<4} RESULT"
    )
    SEP = "=" * W
    print("\n" + SEP)
    print(HEADER)
    print("-" * W)

    for r in ordered:
        gk = ck(r.meta_has_golf_keyword) if r.is_ggnc else "  "
        meta_ok = r.has_meta_desc
        price_col = f"${float(r.price_raw):.0f}" if r.price_raw and r.price_raw.replace(".", "").isdigit() else (r.price_raw[:6] if r.price_raw else "--")
        handle_col = r.handle[:51]
        result_str = "PASS" if r.all_pass else f"FAIL [{','.join(r.fail_reasons)}]"
        print(
            f"{handle_col:<52} "
            f"{ck(r.loaded):<4} "
            f"{ck(r.has_product_title):<4} "
            f"{ck(r.has_description):<4} "
            f"{ck(meta_ok):<4} "
            f"{price_col:<8} "
            f"{ck(r.has_page_title):<4} "
            f"{gk:<4} "
            f"{result_str}"
        )

    print(SEP)
    print("Columns: LD=loads  TL=product title  DS=description  MT=meta desc  PR=price  HT=page title  GK=golf keyword (GGNC only)")


def print_fail_details(results: list[CheckResult]) -> None:
    failures = [r for r in results if not r.all_pass]
    if not failures:
        return
    print(f"\n-- Failure details ({len(failures)} products) " + "-" * 50)
    for r in failures:
        print(f"\n  {r.handle}")
        if r.error:
            print(f"    error         : {r.error}")
        print(f"    csv title     : {r.csv_title}")
        print(f"    product title : {r.product_title or '(MISSING)'}")
        print(f"    price         : {r.price_raw or '(MISSING)'}")
        if r.meta_desc_preview:
            print(f"    meta desc     : {r.meta_desc_preview[:100]}")
        else:
            print(f"    meta desc     : (MISSING)")
        if r.description_preview:
            print(f"    desc preview  : {r.description_preview[:100]}")
        else:
            print(f"    desc preview  : (MISSING)")
        if r.broken_pattern:
            print(f"    broken HTML   : '{r.broken_pattern}'")
        if r.is_ggnc and not r.meta_has_golf_keyword:
            print(f"    golf keyword  : NOT FOUND in meta desc")


# ── Main ───────────────────────────────────────────────────────────────────────

async def run_checks() -> bool:
    products = load_handles()
    if not products:
        print("No products found in CSV with SEO Description.")
        return False

    print(f"\nLazySun PDP Live Verification — {len(products)} products")
    print(f"Source: {CSV_PATH}")
    print(f"Base:   {BASE_URL}/")
    print(f"GGNC:   {len(GGNC_HANDLES)} products with extended golf-keyword check")
    print("=" * W)

    results: list[CheckResult] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await ctx.new_page()

        for i, (handle, csv_title) in enumerate(products, 1):
            tag = "[GGNC]" if handle in GGNC_HANDLES else "      "
            print(f"[{i:2}/{len(products)}] {tag} {handle[:55]:<57}", end="", flush=True)
            r = await check_product(page, handle, csv_title)
            results.append(r)

            if r.error and not r.loaded:
                print(f"  ERROR: {r.error}")
            elif r.all_pass:
                price_label = f"  ${float(r.price_raw):.0f}" if r.price_raw and r.price_raw.replace(".", "").isdigit() else ""
                print(f"  PASS{price_label}")
            else:
                print(f"  FAIL [{', '.join(r.fail_reasons)}]")

        await browser.close()

    print_table(results)

    passed = sum(1 for r in results if r.all_pass)
    failed = len(results) - passed
    print(f"\nResult: {passed}/{len(results)} passed   {failed} failed")

    print_fail_details(results)

    # Price sanity: flag if all prices identical or any $0
    prices = [r.price_raw for r in results if r.loaded and r.price_raw]
    if prices:
        price_set = set(prices)
        if len(price_set) == 1:
            print(f"\n[!] PRICE WARNING: all {len(prices)} products show identical price '{prices[0]}' — may be reading wrong element")
        zero_prices = [r.handle for r in results if r.loaded and r.price_raw in ("0", "0.00", "")]
        if zero_prices:
            print(f"\n[!] PRICE WARNING: $0 or missing price on: {zero_prices}")

    return passed == len(results)


if __name__ == "__main__":
    ok = asyncio.run(run_checks())
    sys.exit(0 if ok else 1)

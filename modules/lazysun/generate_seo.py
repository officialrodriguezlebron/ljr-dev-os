"""
modules/lazysun/generate_seo.py
Generate SEO Title + Meta Description for Gramicci products.

Usage (from repo root):
    python modules/lazysun/generate_seo.py
    python modules/lazysun/generate_seo.py --vendor "Kestin" --audit output/audit_gaps.csv
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from groq import Groq

# ── Constants ─────────────────────────────────────────────────────────────────

BANNED_WORDS = {"luxury", "premium", "elevated", "curated", "timeless", "effortless"}
GROQ_MODEL   = "llama-3.3-70b-versatile"
BATCH_SIZE   = 8

# These HTML patterns signal a pasted chat interface response, not real product copy
CORRUPT_MARKERS = [
    'data-turn="assistant"',
    'data-testid="conversation',
    'font-claude-response',
    'data-scroll-anchor',
    'class="text-token-text',
    'data-start=',           # Claude annotated spans
]

# ── HTML stripping ─────────────────────────────────────────────────────────────

class _Stripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []

    def handle_data(self, d):
        d = d.strip()
        if d:
            self._parts.append(d)

    def text(self):
        return " ".join(self._parts)


def _strip_html(raw: str) -> str:
    if not raw or not raw.strip():
        return ""
    s = _Stripper()
    try:
        s.feed(raw)
    except Exception:
        pass
    return " ".join(s.text().split())


def extract_body_text(html: str, max_chars: int = 500) -> str:
    """Return clean plain text from body HTML. Returns '' for corrupt/missing bodies."""
    if not html or not html.strip():
        return ""
    # Corrupt bodies from pasted chat interfaces have no usable product copy
    if any(m in html for m in CORRUPT_MARKERS):
        return ""
    text = _strip_html(html)
    return text[:max_chars]


# ── Groq prompt ───────────────────────────────────────────────────────────────

def build_system_prompt(brand: str) -> str:
    return f"""\
You write SEO copy for Lazy Sun, a menswear store in Park City, UT.
Audience: men 25-40, heritage/Americana, outdoor-adjacent, buys on story.

RULES — follow every one exactly:

SEO TITLE:
- Max 60 characters. Count every character including spaces.
- Format: [keyword phrase] {brand} Shop at Lazy Sun
- Keyword = product type only, never the colorway.
- Good: "Flannel Workshirt {brand} Shop at Lazy Sun" (no color in keyword)
- Bad: "Navy Flannel Workshirt {brand} Shop at Lazy Sun" (includes color)

SEO DESCRIPTION:
- MUST be between 150 and 160 characters. Count carefully.
- Plain text only — no HTML, no punctuation tricks to pad length.
- Structure: hook sentence (what makes it specific) + one concrete detail (material, fit, or use case).
- Vary the opener for every product. Never start two descriptions the same way.
- Write two full sentences when needed to hit 150 chars. Do not stop short.
- Target exactly 155 characters. If you're under 150, add a specific detail. If over 160, cut a word.
- Example (153 chars): "Built from 9 oz cotton canvas with a relaxed straight leg, these work pants handle hard use without looking like they're trying. Integrated belt system."
- Never use: luxury, premium, elevated, curated, timeless, effortless, em dashes (—).
- No "Shop now", "Free shipping", "Available at" filler.

Return ONLY a JSON array. No prose before or after. No markdown fences.
Each element: {{"handle": "...", "seo_title": "...", "seo_description": "..."}}
"""


def _build_batch_prompt(batch: list[dict], brand: str) -> str:
    lines = [f"Generate SEO Title + Description for these {brand} products:\n"]
    for p in batch:
        lines.append(f'Handle: {p["handle"]}')
        lines.append(f'Title: {p["title"]}')
        if p["body_text"]:
            lines.append(f'Body: {p["body_text"]}')
        else:
            lines.append("Body: (not available — use title only)")
        lines.append("")
    return "\n".join(lines)


def generate_batch(client: Groq, batch: list[dict], brand: str, retries: int = 2) -> list[dict]:
    prompt = _build_batch_prompt(batch, brand)
    system = build_system_prompt(brand)
    for attempt in range(retries + 1):
        try:
            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.7,
                max_tokens=1800,
            )
            raw = resp.choices[0].message.content.strip()
            # Strip markdown code fences if present
            raw = re.sub(r"^```json\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            return json.loads(raw)
        except (json.JSONDecodeError, Exception) as e:
            if attempt < retries:
                print(f"    ↻ retry {attempt + 1}: {e}")
                time.sleep(2)
            else:
                print(f"    ✗ batch failed after {retries + 1} attempts: {e}")
                return []
    return []


# ── Post-processing ──────────────────────────────────────────────────────────

def trim_desc(desc: str, max_chars: int = 160) -> str:
    """Trim a too-long description to max_chars at the last sentence or word boundary."""
    if len(desc) <= max_chars:
        return desc
    # Prefer cutting at a sentence boundary ('. ') before max_chars
    window = desc[:max_chars]
    last_period = window.rfind('. ')
    if last_period > 100:  # only cut at sentence if we keep a reasonable chunk
        return desc[:last_period + 1]
    # Otherwise cut at last word boundary
    last_space = window.rfind(' ')
    return desc[:last_space] if last_space > 100 else window


REFILL_SYSTEM = """\
You write SEO meta descriptions for Lazy Sun, a menswear store.
Audience: men 25-40, heritage/Americana.

Write ONE meta description of EXACTLY 150-160 characters (count every character).
Plain text only. Hook first — one specific detail about the product, then one practical note.
Never use: luxury, premium, elevated, curated, timeless, effortless, em dashes.
Return ONLY the description text. No quotes, no labels, no extra text.
"""


def refill_short(client: Groq, product: dict) -> str:
    """Re-generate a single description that came back too short."""
    user_msg = (
        f"Product: {product['title']}\n"
        + (f"Body context: {product['body_text']}\n" if product["body_text"] else "")
        + "Write a meta description of exactly 150-160 characters. "
        "Count each character. Do not stop before 150."
    )
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": REFILL_SYSTEM},
                    {"role": "user",   "content": user_msg},
                ],
                temperature=0.75,
                max_tokens=300,
            )
            result = resp.choices[0].message.content.strip().strip('"')
            if 140 <= len(result) <= 170:
                return result
        except Exception as e:
            if attempt == 2:
                print(f"    ✗ refill failed: {e}")
        time.sleep(0.5)
    return ""


# ── QA ────────────────────────────────────────────────────────────────────────

def qa_check(seo_title: str, seo_desc: str) -> str:
    warnings = []
    if len(seo_title) > 60:
        warnings.append(f"title_too_long({len(seo_title)})")
    if len(seo_desc) < 140:
        warnings.append(f"desc_too_short({len(seo_desc)})")
    if len(seo_desc) > 165:
        warnings.append(f"desc_too_long({len(seo_desc)})")
    found_banned = [w for w in BANNED_WORDS if w in seo_title.lower() or w in seo_desc.lower()]
    if found_banned:
        warnings.append(f"banned_word({'|'.join(found_banned)})")
    if "—" in seo_title or "—" in seo_desc:
        warnings.append("em_dash_found")
    return "; ".join(warnings) if warnings else "OK"


# ── Main ──────────────────────────────────────────────────────────────────────

def run(vendor: str, audit_csv: str, dry_run: bool = False, brand: str = None,
        skip_titles: list[str] = None):
    audit_path = ROOT / audit_csv
    if not audit_path.exists():
        print(f"✗ Not found: {audit_path}")
        sys.exit(1)

    skip_set = set(skip_titles or [])

    # Load and filter
    with open(audit_path, encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))

    skipped = []
    products = []
    for row in all_rows:
        if (row.get("Vendor", "").strip() == vendor
                and str(row.get("missing_seo_title", "")).strip() in ("1", "True", "true", "1.0")):
            if row["Title"] in skip_set:
                skipped.append(row["Title"])
                continue
            products.append({
                "handle":    row["Handle"],
                "title":     row["Title"],
                "body_html": row.get("Body (HTML)", ""),
                "body_text": extract_body_text(row.get("Body (HTML)", "")),
            })

    if skipped:
        print(f"  ⊘  Skipped ({len(skipped)}) — no description, flagged for later:")
        for t in skipped:
            print(f"     · {t}")

    brand = brand or vendor
    print(f"\n{vendor} — {len(products)} products to process (brand suffix: '{brand} Shop at Lazy Sun')")
    no_body = [p for p in products if not p["body_text"]]
    if no_body:
        print(f"  ⚠  {len(no_body)} with no usable body copy (title-only fallback):")
        for p in no_body:
            print(f"     · {p['handle']}")

    if dry_run:
        print("\nDRY RUN — no API calls made.")
        return

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("✗ GROQ_API_KEY not set in .env")
        sys.exit(1)

    client = Groq(api_key=api_key)
    results_map: dict[str, dict] = {}

    # Process in batches
    batches = [products[i:i + BATCH_SIZE] for i in range(0, len(products), BATCH_SIZE)]
    for i, batch in enumerate(batches, 1):
        print(f"\n  Batch {i}/{len(batches)} ({len(batch)} products)...")
        raw_results = generate_batch(client, batch, brand)
        for item in raw_results:
            results_map[item["handle"]] = item
        print(f"  ✓ {len(raw_results)} returned")
        if i < len(batches):
            time.sleep(1)  # light rate-limit buffer

    # ── Post-processing pass 1: trim longs ────────────────────────────────────
    trim_count = 0
    for h, item in results_map.items():
        desc = item.get("seo_description", "")
        if len(desc) > 165:
            trimmed = trim_desc(desc)
            if len(trimmed) != len(desc):
                trim_count += 1
            item["seo_description"] = trimmed
    if trim_count:
        print(f"\n  ✂  Trimmed {trim_count} over-long descriptions")

    # ── Post-processing pass 2: refill shorts ─────────────────────────────────
    short_products = [
        p for p in products
        if p["handle"] in results_map
        and len(results_map[p["handle"]].get("seo_description", "")) < 140
    ]
    if short_products:
        print(f"\n  ↻  Re-generating {len(short_products)} under-length descriptions...")
        for p in short_products:
            new_desc = refill_short(client, p)
            if new_desc:
                results_map[p["handle"]]["seo_description"] = new_desc
                print(f"     ✓ {p['handle']} ({len(new_desc)} chars)")
            else:
                print(f"     ✗ {p['handle']} still short")

    # Build output rows
    slug = vendor.lower().replace(" ", "_")
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    import_path = out_dir / f"proposed_seo_{slug}_shopify_import.csv"
    qa_path     = out_dir / f"proposed_seo_{slug}_qa.csv"

    import_cols = ["Handle", "Title", "SEO Title", "SEO Description"]
    qa_cols     = ["Handle", "Title", "SEO Title", "SEO Description",
                   "seo_title_len", "seo_desc_len", "qa_warnings", "body_available"]

    import_rows = []
    qa_rows     = []

    ok_count   = 0
    warn_count = 0
    miss_count = 0

    for p in products:
        h = p["handle"]
        if h not in results_map:
            miss_count += 1
            seo_title = ""
            seo_desc  = ""
            warnings  = "GENERATION_FAILED"
        else:
            seo_title = results_map[h].get("seo_title", "").strip()
            seo_desc  = results_map[h].get("seo_description", "").strip()
            warnings  = qa_check(seo_title, seo_desc)
            if warnings == "OK":
                ok_count += 1
            else:
                warn_count += 1

        import_rows.append({
            "Handle":          h,
            "Title":           p["title"],
            "SEO Title":       seo_title,
            "SEO Description": seo_desc,
        })
        qa_rows.append({
            "Handle":          h,
            "Title":           p["title"],
            "SEO Title":       seo_title,
            "SEO Description": seo_desc,
            "seo_title_len":   len(seo_title),
            "seo_desc_len":    len(seo_desc),
            "qa_warnings":     warnings,
            "body_available":  "yes" if p["body_text"] else "no",
        })

    with open(import_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=import_cols)
        w.writeheader()
        w.writerows(import_rows)

    with open(qa_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=qa_cols)
        w.writeheader()
        w.writerows(qa_rows)

    print(f"\n{'─'*60}")
    print(f"  Shopify import : {import_path.relative_to(ROOT)} ({len(import_rows)} rows)")
    print(f"  QA file        : {qa_path.relative_to(ROOT)} ({len(qa_rows)} rows)")
    print(f"  Results        : {ok_count} OK · {warn_count} warnings · {miss_count} failed")

    # Print QA summary
    flagged = [r for r in qa_rows if r["qa_warnings"] != "OK"]
    if flagged:
        print(f"\n  QA Flags ({len(flagged)}):")
        for r in flagged:
            print(f"    [{r['qa_warnings']}] {r['Handle']} — {r['SEO Title'][:50]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor",     default="Gramicci")
    parser.add_argument("--brand",      default=None, help="Brand name for SEO title suffix (defaults to vendor name)")
    parser.add_argument("--audit",      default="output/audit_gaps.csv")
    parser.add_argument("--skip-title", action="append", default=[], dest="skip_titles",
                        help="Product title to skip (repeat for multiple)")
    parser.add_argument("--dry-run",    action="store_true")
    args = parser.parse_args()
    run(args.vendor, args.audit, args.dry_run, args.brand, args.skip_titles)

"""
Full PDP audit — all 1,188 unique Shopify products.
Checks 9 fields per product, outputs 3 files + vendor summary.
"""
import csv
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
SRC  = ROOT / 'output' / 'products_export_1.csv'
OUT  = ROOT / 'output'

AUDIT_CSV    = OUT / 'full_pdp_audit.csv'
PRIORITY_CSV = OUT / 'priority_fixes.csv'

# ── Home & Wellness filter ────────────────────────────────────────────────────
HW_VENDORS  = {'BabaBoogs Candles', 'BabaBoogs', 'Tinned Candle',
               'Yay for Earth', 'Samurai', 'Wishy Fishies'}

def is_hw(row):
    if row['Vendor'] in HW_VENDORS:
        return True
    if row['Vendor'] == 'Gramicci' and 'frisbee' in row['Title'].lower():
        return True
    return False

# ── HTML helpers ──────────────────────────────────────────────────────────────
_TAG_RE  = re.compile(r'<[^>]+>')
_CORR_RE = re.compile(r'font-claude-response-body|ChatGPT|class="prose"', re.I)

def body_status(html):
    """Returns: 'missing' | 'corrupt' | 'thin' | 'ok'"""
    if not html or not html.strip():
        return 'missing'
    if _CORR_RE.search(html):
        return 'corrupt'
    text = _TAG_RE.sub('', html).strip()
    if len(text) < 100:
        return 'thin'
    return 'ok'

def text_len(html):
    if not html:
        return 0
    return len(_TAG_RE.sub('', html).strip())

# ── Load export — keep first row per handle (product row, not variant) ────────
print(f'Reading {SRC.name}…')
seen      = {}
all_rows  = []

with open(SRC, encoding='utf-8') as f:
    for row in csv.DictReader(f):
        h = row['Handle']
        if h not in seen:
            seen[h] = True
            all_rows.append(row)

print(f'  {len(all_rows):,} unique products (from {SRC.name})\n')

# ── Audit each product ────────────────────────────────────────────────────────
audit_rows   = []
vendor_stats = defaultdict(lambda: {
    'total': 0, 'no_desc': 0, 'thin_desc': 0, 'corrupt_desc': 0,
    'no_seo_title': 0, 'no_seo_desc': 0,
    'no_type': 0, 'no_tags': 0, 'no_image': 0,
})

for row in all_rows:
    h      = row['Handle']
    title  = row.get('Title', '').strip()
    body   = row.get('Body (HTML)', '').strip()
    vendor = row.get('Vendor', '').strip()
    vtype  = row.get('Type', '').strip()
    tags   = row.get('Tags', '').strip()
    seo_t  = row.get('SEO Title', '').strip()
    seo_d  = row.get('SEO Description', '').strip()
    image  = row.get('Image Src', '').strip()
    status = row.get('Status', '').strip()

    bs          = body_status(body)
    has_desc    = bs == 'ok'
    desc_status = bs                        # missing / corrupt / thin / ok
    desc_len    = text_len(body)
    has_seo_t   = bool(seo_t)
    has_seo_d   = bool(seo_d)
    has_type    = bool(vtype)
    has_tags    = bool(tags)
    has_image   = bool(image)

    # gap_count: count each field that needs fixing
    gaps = sum([
        not has_desc,          # missing/corrupt/thin all count
        not has_seo_t,
        not has_seo_d,
        not has_type,
        not has_tags,
        not has_image,
    ])

    audit_rows.append({
        'Handle':           h,
        'Title':            title,
        'Vendor':           vendor,
        'Status':           status,
        'has_description':  'yes' if has_desc else 'no',
        'description_status': desc_status,
        'description_length': desc_len,
        'has_seo_title':    'yes' if has_seo_t else 'no',
        'has_seo_desc':     'yes' if has_seo_d else 'no',
        'has_product_type': 'yes' if has_type else 'no',
        'has_tags':         'yes' if has_tags else 'no',
        'has_image':        'yes' if has_image else 'no',
        'gap_count':        gaps,
    })

    # Vendor stats
    vs = vendor_stats[vendor]
    vs['total'] += 1
    if bs in ('missing', 'corrupt', 'thin'):
        vs['no_desc'] += 1
    if bs == 'thin':
        vs['thin_desc'] += 1
    if bs == 'corrupt':
        vs['corrupt_desc'] += 1
    if not has_seo_t:
        vs['no_seo_title'] += 1
    if not has_seo_d:
        vs['no_seo_desc'] += 1
    if not has_type:
        vs['no_type'] += 1
    if not has_tags:
        vs['no_tags'] += 1
    if not has_image:
        vs['no_image'] += 1

# ── OUTPUT 1: full audit CSV ──────────────────────────────────────────────────
AUDIT_COLS = ['Handle','Title','Vendor','Status','has_description',
              'description_status','description_length','has_seo_title',
              'has_seo_desc','has_product_type','has_tags','has_image','gap_count']

with open(AUDIT_CSV, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=AUDIT_COLS)
    w.writeheader()
    w.writerows(audit_rows)

print(f'OUTPUT 1  →  {AUDIT_CSV.name}  ({len(audit_rows)} rows)')

# ── OUTPUT 2: vendor summary ──────────────────────────────────────────────────
sorted_vendors = sorted(vendor_stats.items(),
                        key=lambda x: x[1]['no_seo_title'] + x[1]['no_seo_desc'],
                        reverse=True)

COL = 26
print(f'\n{"─"*110}')
print(f'{"Vendor":<{COL}} {"Total":>6} {"NDesc":>6} {"Thin":>5} {"Crpt":>5} '
      f'{"NoSEOt":>7} {"NoSEOd":>7} {"NoType":>7} {"NoTags":>7} {"NoImg":>6}')
print(f'{"─"*110}')

for vendor, s in sorted_vendors:
    print(f'{vendor:<{COL}} {s["total"]:>6} {s["no_desc"]:>6} {s["thin_desc"]:>5} '
          f'{s["corrupt_desc"]:>5} {s["no_seo_title"]:>7} {s["no_seo_desc"]:>7} '
          f'{s["no_type"]:>7} {s["no_tags"]:>7} {s["no_image"]:>6}')

# Totals row
tot = {k: sum(s[k] for _, s in vendor_stats.items())
       for k in ('total','no_desc','thin_desc','corrupt_desc',
                 'no_seo_title','no_seo_desc','no_type','no_tags','no_image')}
print(f'{"─"*110}')
print(f'{"TOTAL":<{COL}} {tot["total"]:>6} {tot["no_desc"]:>6} {tot["thin_desc"]:>5} '
      f'{tot["corrupt_desc"]:>5} {tot["no_seo_title"]:>7} {tot["no_seo_desc"]:>7} '
      f'{tot["no_type"]:>7} {tot["no_tags"]:>7} {tot["no_image"]:>6}')

# ── OUTPUT 3: priority fixes (3+ gaps) ───────────────────────────────────────
priority = sorted([r for r in audit_rows if r['gap_count'] >= 3],
                  key=lambda x: x['gap_count'], reverse=True)

with open(PRIORITY_CSV, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=AUDIT_COLS)
    w.writeheader()
    w.writerows(priority)

print(f'\nOUTPUT 3  →  {PRIORITY_CSV.name}  ({len(priority)} products with 3+ gaps)')

# ── OUTPUT 4: Home & Wellness ─────────────────────────────────────────────────
hw_rows = [r for r in audit_rows if is_hw(
    next(p for p in all_rows if p['Handle'] == r['Handle'])
)]

print(f'\n{"─"*110}')
print(f'HOME & WELLNESS AUDIT  ({len(hw_rows)} products)')
print(f'{"─"*110}')
print(f'{"Handle":<45} {"Vendor":<22} {"Desc":<8} {"SEOt":<5} {"SEOd":<5} {"Type":<5} {"Tags":<5} {"Img":<4} {"Gaps"}')
print(f'{"─"*110}')

for r in sorted(hw_rows, key=lambda x: x['gap_count'], reverse=True):
    desc_col = r['description_status'][:7]
    print(f'{r["Handle"]:<45} {r["Vendor"]:<22} {desc_col:<8} '
          f'{r["has_seo_title"]:<5} {r["has_seo_desc"]:<5} '
          f'{r["has_product_type"]:<5} {r["has_tags"]:<5} '
          f'{r["has_image"]:<4} {r["gap_count"]}')

# ── Summary ───────────────────────────────────────────────────────────────────
ok_count  = sum(1 for r in audit_rows if r['gap_count'] == 0)
pct_clean = ok_count / len(audit_rows) * 100

print(f'\n{"═"*60}')
print(f'AUDIT COMPLETE')
print(f'  Total products   : {len(audit_rows):,}')
print(f'  Zero gaps (clean): {ok_count:,}  ({pct_clean:.1f}%)')
print(f'  1-2 gaps         : {sum(1 for r in audit_rows if 1 <= r["gap_count"] <= 2):,}')
print(f'  3+ gaps (priority): {len(priority):,}')
print(f'  Files written    : full_pdp_audit.csv  |  priority_fixes.csv')
print(f'{"═"*60}')

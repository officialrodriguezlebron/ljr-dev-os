import csv

SRC = r'C:\Users\HomePC\AppData\Local\Temp\products_export_1.csv'
OUT = r'C:\Users\HomePC\ljr-dev-os\audit_gaps.csv'

# 1. Read + deduplicate by Handle (first row = main product row)
seen = set()
products = []
with open(SRC, encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        h = row['Handle']
        if h not in seen:
            seen.add(h)
            products.append(row)

print(f'Unique products: {len(products)}')

OUTPUT_COLS = [
    'Handle', 'Title', 'Vendor', 'Status',
    'Body (HTML)', 'SEO Title', 'SEO Description',
    'missing_seo_title', 'missing_seo_desc', 'missing_body',
]

# 2. Gap detection
gap_rows = []
vendor_gaps = {}

for row in products:
    vendor = row.get('Vendor', '').strip() or '(no vendor)'
    missing_seo_title = 1 if not row.get('SEO Title', '').strip() else 0
    missing_seo_desc  = 1 if not row.get('SEO Description', '').strip() else 0
    missing_body      = 1 if not row.get('Body (HTML)', '').strip() else 0
    has_gap = missing_seo_title or missing_seo_desc or missing_body

    if vendor not in vendor_gaps:
        vendor_gaps[vendor] = {
            'total': 0, 'products_with_gaps': 0,
            'missing_seo_title': 0, 'missing_seo_desc': 0, 'missing_body': 0,
        }
    vendor_gaps[vendor]['total'] += 1
    if has_gap:
        vendor_gaps[vendor]['products_with_gaps'] += 1
    vendor_gaps[vendor]['missing_seo_title'] += missing_seo_title
    vendor_gaps[vendor]['missing_seo_desc']  += missing_seo_desc
    vendor_gaps[vendor]['missing_body']      += missing_body

    if has_gap:
        gap_rows.append({
            'Handle':           row['Handle'],
            'Title':            row['Title'],
            'Vendor':           row.get('Vendor', ''),
            'Status':           row.get('Status', ''),
            'Body (HTML)':      row.get('Body (HTML)', ''),
            'SEO Title':        row.get('SEO Title', ''),
            'SEO Description':  row.get('SEO Description', ''),
            'missing_seo_title': missing_seo_title,
            'missing_seo_desc':  missing_seo_desc,
            'missing_body':      missing_body,
        })

# 3. Write audit_gaps.csv
with open(OUT, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=OUTPUT_COLS)
    writer.writeheader()
    writer.writerows(gap_rows)

print(f'Products with at least one gap: {len(gap_rows)}')
print(f'Wrote: {OUT}')

# 4. Vendor summary
sorted_vendors = sorted(vendor_gaps.items(), key=lambda x: -x[1]['products_with_gaps'])

W = 36
print()
print(f"{'Vendor':<{W}} {'Total':>6} {'w/Gaps':>7} {'NoSEOTitle':>11} {'NoSEODesc':>10} {'NoBody':>7}")
print('-' * (W + 6 + 7 + 11 + 10 + 7 + 5))
for v, s in sorted_vendors:
    if s['products_with_gaps'] > 0:
        print(
            f"{v:<{W}} "
            f"{s['total']:>6} "
            f"{s['products_with_gaps']:>7} "
            f"{s['missing_seo_title']:>11} "
            f"{s['missing_seo_desc']:>10} "
            f"{s['missing_body']:>7}"
        )

print()
print('--- Vendors with zero gaps ---')
for v, s in sorted_vendors:
    if s['products_with_gaps'] == 0:
        print(f"  {v:<{W}} total={s['total']}")

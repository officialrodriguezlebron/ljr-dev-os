"""
modules/lazysun/audit.py
Gap audit on a Shopify products CSV export.
Run via Claude Code or directly: python modules/lazysun/audit.py --csv output/products_export_1.csv
"""

import argparse
import pandas as pd
from pathlib import Path


def run_audit(csv_path: str, vendor_filter: str = None) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    products = df.drop_duplicates(subset="Handle").copy()

    missing_seo_title = products["SEO Title"].isna() | (products["SEO Title"].str.strip() == "")
    missing_seo_desc  = products["SEO Description"].isna() | (products["SEO Description"].str.strip() == "")
    missing_body      = products["Body (HTML)"].isna() | (products["Body (HTML)"].str.strip() == "")
    any_gap           = missing_seo_title | missing_seo_desc | missing_body

    print("\n=== LAZYSUN CATALOG AUDIT ===")
    print(f"Total unique products : {len(products)}")
    print(f"Missing SEO Title     : {missing_seo_title.sum()} ({missing_seo_title.mean()*100:.1f}%)")
    print(f"Missing SEO Desc      : {missing_seo_desc.sum()} ({missing_seo_desc.mean()*100:.1f}%)")
    print(f"Missing Body (HTML)   : {missing_body.sum()} ({missing_body.mean()*100:.1f}%)")
    print(f"Products with ANY gap : {any_gap.sum()} ({any_gap.mean()*100:.1f}%)")

    gap_df = products[any_gap][
        ["Handle", "Title", "Vendor", "Status", "Body (HTML)", "SEO Title", "SEO Description"]
    ].copy()
    gap_df["missing_seo_title"] = missing_seo_title[any_gap].values
    gap_df["missing_seo_desc"]  = missing_seo_desc[any_gap].values
    gap_df["missing_body"]      = missing_body[any_gap].values
    gap_df["gap_count"]         = gap_df[["missing_seo_title","missing_seo_desc","missing_body"]].sum(axis=1)
    gap_df["strategy"]          = gap_df["missing_body"].map({False: "SEO-only", True: "SEO + desc needed"})

    print("\n=== GAPS BY VENDOR ===")
    summary = gap_df.groupby("Vendor").agg(
        products_with_gaps=("Handle","count"),
        missing_seo_title=("missing_seo_title","sum"),
        missing_seo_desc=("missing_seo_desc","sum"),
        missing_body=("missing_body","sum"),
    ).sort_values("products_with_gaps", ascending=False)
    print(summary.to_string())

    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "audit_gaps.csv"
    gap_df.to_csv(out_path, index=False)
    print(f"\n✓ Saved: {out_path} ({len(gap_df)} products flagged)")

    if vendor_filter:
        v = gap_df[gap_df["Vendor"].str.lower() == vendor_filter.lower()]
        slug = vendor_filter.lower().replace(" ", "_")
        vpath = out_dir / f"{slug}_queue.csv"
        v.to_csv(vpath, index=False)
        print(f"✓ Saved: {vpath} ({len(v)} products)")

    return gap_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--vendor", default=None)
    args = parser.parse_args()
    run_audit(args.csv, args.vendor)

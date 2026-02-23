# fetch_aum.py
# ---------------------------------------------------------------------------
# Fetches scheme-level AUM from AMFI's monthly data and populates aum_cr
# in the `funds` table.
#
# Source: AMFI Monthly AUM report (Excel)
# Available at: https://www.amfiindia.com/research-information/amfi-monthly
#
# HOW TO USE:
# 1. Go to https://www.amfiindia.com/research-information/amfi-monthly
# 2. Expand the latest fiscal year (e.g. "April 2025-March 2026")
# 3. Find the most recent month row — click "AUM Data" Excel icon to download
# 4. Save the file as 'amfi_aum.xlsx' in this directory (c:\mf_etl)
# 5. Run: python fetch_aum.py
#
# Why not auto-download?
# AMFI's website is JS-rendered (React). The Excel links are loaded
# client-side and their URL patterns change each month — there is no
# stable programmatic endpoint.
#
# Run frequency: Once a month after the 10th (when AMFI publishes data)
# ---------------------------------------------------------------------------

import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from pathlib import Path

DB_URL = os.getenv("DB_URL")
if DB_URL is None:
    raise RuntimeError("DB_URL environment variable not set.")

engine = create_engine(DB_URL, pool_pre_ping=True)

EXCEL_PATH = Path(__file__).parent / "amfi_aum.xlsx"


def parse_aum_excel(path: Path) -> pd.DataFrame:
    """
    Parse the AMFI AUM Excel file.

    The file columns typically include:
      - Scheme Code (AMFI / AMFI Code)
      - Scheme Name
      - Average AUM / Closing AUM (in Crores)

    This function tries multiple sheets and header row positions
    to handle AMFI's inconsistent formatting.

    Returns a DataFrame with columns: fund_id (str), aum_cr (float)
    """
    import re

    xl = pd.ExcelFile(path)
    print(f"  Excel sheets found: {xl.sheet_names}")

    for sheet in xl.sheet_names:
        for skip in range(0, 8):
            try:
                df = pd.read_excel(path, sheet_name=sheet, skiprows=skip, dtype=str)
                df.columns = [str(c).strip() for c in df.columns]

                # Find scheme code column
                code_col = next(
                    (c for c in df.columns if re.search(r'scheme.?code|amfi.?code', c, re.IGNORECASE)),
                    None
                )
                # Find AUM column (prefer "Closing AUM" or "Average AUM")
                aum_col = next(
                    (c for c in df.columns if re.search(r'closing.?aum|average.?aum|aum.?cr|net.?asset', c, re.IGNORECASE)),
                    None
                )
                # Fallback: any AUM column
                if not aum_col:
                    aum_col = next(
                        (c for c in df.columns if re.search(r'\baum\b', c, re.IGNORECASE)),
                        None
                    )

                if code_col and aum_col:
                    print(f"  Found columns: [{code_col}] + [{aum_col}] on sheet '{sheet}' (skip={skip})")
                    result = df[[code_col, aum_col]].copy()
                    result.columns = ['fund_id', 'aum_cr']
                    result['fund_id'] = result['fund_id'].astype(str).str.strip().str.split('.').str[0]  # remove .0
                    result['aum_cr'] = pd.to_numeric(result['aum_cr'], errors='coerce')
                    result = result.dropna(subset=['aum_cr'])
                    result = result[result['fund_id'].str.match(r'^\d{5,7}$')]
                    if len(result) > 50:
                        return result

            except Exception as e:
                continue

    raise RuntimeError(
        "Could not parse AUM columns from the Excel file.\n"
        "Expected columns containing 'Scheme Code' and 'AUM'.\n"
        f"Please open '{path.name}' and check column names, then update the regex if needed."
    )


def update_aum_in_db(df_aum: pd.DataFrame):
    """
    UPDATE funds SET aum_cr = <value> WHERE fund_id = <scheme_code>
    """
    updated = 0
    skipped = 0

    with engine.begin() as conn:
        for _, row in df_aum.iterrows():
            result = conn.execute(
                text("UPDATE funds SET aum_cr = :aum WHERE fund_id = :fid"),
                {"aum": float(row['aum_cr']), "fid": str(row['fund_id'])}
            )
            if result.rowcount > 0:
                updated += 1
            else:
                skipped += 1

    return updated, skipped


def main():
    if not EXCEL_PATH.exists():
        print(f"""
ERROR: Excel file not found at: {EXCEL_PATH}

HOW TO GET THE FILE:
1. Open: https://www.amfiindia.com/research-information/amfi-monthly
2. Expand latest fiscal year (e.g. "April 2025-March 2026")
3. Find the latest month — click the "AUM Data" Excel download icon
4. Save it as 'amfi_aum.xlsx' in: {EXCEL_PATH.parent}
5. Re-run: python fetch_aum.py
""")
        sys.exit(1)

    print(f"Parsing AUM data from: {EXCEL_PATH.name}")
    df_aum = parse_aum_excel(EXCEL_PATH)
    print(f"  Records parsed: {len(df_aum)}")
    print(f"  AUM range: {df_aum['aum_cr'].min():.0f} - {df_aum['aum_cr'].max():.0f} Cr")

    print("\nUpdating aum_cr in DB...")
    updated, skipped = update_aum_in_db(df_aum)
    print(f"  Updated: {updated} funds | No match: {skipped}")

    if updated > 0:
        print(f"\nDone. AUM filter (>= 1000 Cr) in score_service.py is now active.")
        # Verify
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT COUNT(*) FROM funds WHERE aum_cr >= 1000"
            )).scalar()
            print(f"Funds with AUM >= 1000 Cr in DB: {result}")
    else:
        print(
            "\nWARNING: 0 funds matched. Your fund_id column may not align with "
            "the Scheme Code column in the Excel. Check manually."
        )


if __name__ == "__main__":
    main()

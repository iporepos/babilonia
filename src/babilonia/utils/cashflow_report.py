# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2025 The Project Authors
# See pyproject.toml for authors/maintainers.
# See LICENSE for license details.
"""
todo refactor docstring

"""
# IMPORTS
# ***********************************************************************
# import modules from other libs

# Native imports
# =======================================================================
import glob
import argparse
from pathlib import Path

# ... {develop}

# External imports
# =======================================================================
import pandas as pd

# ... {develop}

# Project-level imports
# =======================================================================
# import {module}
from babilonia.accounting import CashFlow

# ... {develop}

# FUNCTIONS
# ***********************************************************************


def get_arguments():
    parser = argparse.ArgumentParser(
        description="Analyst for cashflow files",
        epilog="Usage example: python -m module path type --year 2024",
    )

    # Positional arguments
    parser.add_argument("folder", help="The path to folder you want to process.")
    parser.add_argument("type", help="The type of account (e.g. BB-CCPJ).")

    # Optional arguments
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Process a single year instead of all detected years.",
    )

    args = parser.parse_args()

    return {
        "folder": args.folder,
        "type": args.type,
        "year": args.year,
    }


def main():
    """
    Entry point for yearly cash flow reporting.

    Loads daily cash flow data and initial balances, computes yearly
    cash flow panels and summaries, prints results to the terminal,
    and exports CSV reports.
    """

    # ------------------------------------------------------------------
    # Parse CLI arguments
    # ------------------------------------------------------------------
    dc = get_arguments()

    s = dc["type"].upper()
    bank, account = s.split("-")

    folder = Path(dc["folder"])
    ls_files = glob.glob(f"{folder}/CAIXA_*_DIARIO.csv")
    file_csv = Path(ls_files[0])
    file_initial = folder / "saldos.csv"

    # ------------------------------------------------------------------
    # Load data
    # ------------------------------------------------------------------
    print("=" * 72)
    print(f"Cash Flow Report | {bank} – {account}")
    print("=" * 72)

    cf = CashFlow()
    cf.load_data(file_csv)

    df_initial = pd.read_csv(file_initial, sep=";")

    # ------------------------------------------------------------------
    # Determine available years
    # ------------------------------------------------------------------
    all_years = sorted(cf.data["Data"].dt.year.unique())
    year_arg = dc["year"]

    if year_arg is not None:
        if year_arg not in all_years:
            raise ValueError(
                f"Requested year {year_arg} not found in data. "
                f"Available years: {all_years}"
            )
        years = [year_arg]
        print(f"[INFO] Year selected via CLI: {year_arg}")
    else:
        years = all_years
        print(f"[INFO] Years detected: {', '.join(map(str, years))}")

    # ------------------------------------------------------------------
    # Process each year independently
    # ------------------------------------------------------------------
    for year in years:
        print("\n" + "-" * 72)
        print(f"[INFO] Processing year {year}")

        # Retrieve initial balance for the year
        initial_cash = df_initial.query(f"Year == {year}")["Amount"].values[0]

        # Generate cash flow report
        dc_cfa = cf.get_cashflow_report(
            df=cf.data,
            year=year,
            initial_cash=initial_cash,
        )

        # ------------------------------------------------------------------
        # Terminal output
        # ------------------------------------------------------------------
        print("\n[Panel]")
        print(dc_cfa["Pannel"].to_string(index=False))

        print("\n[Summary]")
        print(dc_cfa["Summary"].to_string(index=False))

        # ------------------------------------------------------------------
        # Export results
        # ------------------------------------------------------------------
        out_dir = folder / f"{year}"
        out_dir.mkdir(parents=True, exist_ok=True)

        file_panel = out_dir / f"REPORT_{bank}_{account}_{year}.csv"
        file_summary = out_dir / f"SUMMARY_{bank}_{account}_{year}.csv"

        dc_cfa["Pannel"].round(2).to_csv(file_panel, sep=";", index=False)
        dc_cfa["Summary"].round(2).to_csv(file_summary, sep=";", index=False)

        print(f"[OK] Files written for {year}")

    print("\n" + "=" * 72)
    print("[OK] Cash flow report completed successfully")
    print("=" * 72)

    return None


# SCRIPT
# ***********************************************************************
# standalone behaviour as a script
if __name__ == "__main__":
    main()

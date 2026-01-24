# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2025 The Project Authors
# See pyproject.toml for authors/maintainers.
# See LICENSE for license details.
"""
todo docstring

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
from babilonia.utils.core import *
from babilonia.accounting import CashFlow
# ... {develop}

# FUNCTIONS
# ***********************************************************************

def main():


    char_w = 120

    args = get_arguments()

    data_folder = Path(args.folder)
    data_type = args.type.lower()
    year_arg = args.year

    bank = get_bank(data_type)
    account = get_account(data_type)

    file_initial = data_folder / "saldos.csv"
    df_initial = pd.read_csv(file_initial, sep=";")

    print("\n\n")
    print("=" * char_w)
    print(" Cashflow Report\n".upper())
    print(f" Folder  : {data_folder}")
    print(f" Bank    : {BANK_NAMES[data_type]}")
    print(f" Account : {ACCOUNT_NAMES[data_type]}")
    print(f" Year    : {year_arg if year_arg is not None else 'ALL'}")
    print("=" * char_w)

    # Resolve file pattern (year wildcard handled inside helper)
    pattern_files = get_file_pattern_cashflow_daily(data_type, data_folder, year_arg)
    ls_files = glob.glob(pattern_files)

    if not ls_files:
        print(" No input files found. Nothing to process.")
        print("=" * char_w)
        return None

    # Group files by year (assumes year is the parent directory name)
    # ------------------------------------------------------------------
    files_by_year = {}
    for f in ls_files:
        fpath = Path(f)
        try:
            year = fpath.parent.name
        except IndexError:
            continue
        files_by_year.setdefault(year, []).append(fpath)

    cf = PARSERS[data_type]()

    total_processed = 0

    for year in sorted(files_by_year):
        print()
        # print("-" * char_w)
        print(f" Year {year}")
        print("-" * char_w)

        file_csv = files_by_year[year][0]

        cf = CashFlow()
        cf.load_data(file_csv)

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
        print("\n[Summary]")
        df = dc_cfa["Summary"]
        cols_to_format = df.columns[2:4]
        print(CashFlow.format_currency_columns(df, cols_to_format))

        print("\n[Panel]")
        df = dc_cfa["Pannel"]
        cols_to_format = df.columns[2:]
        print(CashFlow.format_currency_columns(df, cols_to_format))




    print()
    print("=" * char_w)
    print(f" Completed. Output files written: {total_processed}")
    print("=" * char_w)
    print("\n\n")
    return None



# SCRIPT
# ***********************************************************************
# standalone behaviour as a script
if __name__ == "__main__":
    main()
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2025 The Project Authors
# See pyproject.toml for authors/maintainers.
# See LICENSE for license details.
"""
Generate cash flow reports from daily canonical cashflow files.

This script scans a target directory for daily cash flow CSV files
(previously generated from standardized bank statements), groups them
by year, and produces yearly cash flow reports using the ``CashFlow``
analysis engine.

For each year found, the script:

- Loads the daily cash flow file.
- Retrieves the initial balance for the year from a balances table.
- Computes a yearly cash flow report (summary and panel views).
- Displays formatted tables in the terminal.

Processing can be restricted to a single year or applied to all available
years. Terminal output is structured for quick inspection and logging.

Script Examples
---------------

The script is intended for command-line execution.

.. dropdown:: Minimal PowerShell example (Windows)
    :icon: code-square
    :open:

    Save as ``run_report.ps1`` and execute from PowerShell.

    .. code-block:: powershell

        # ! Warning -- change paths and parameters

        # Paths
        $REPO   = "C:\\path\\to\\repo"
        $SCRIPT = "$REPO\\babilonia\\tools\\report.py"
        $DATA   = "C:\\data\\bank_statements"

        # Parameters
        $TYPE = "bb-cc"
        $YEAR = 2024

        # Run script
        python $SCRIPT `
            --folder $DATA `
            --type $TYPE `
            --year $YEAR


.. dropdown:: Minimal shell example (Linux)
    :icon: code-square
    :open:

    Save as ``run_report.sh`` and execute from a terminal.

    .. code-block:: bash

        #!/usr/bin/env bash

        # ! Warning -- change paths and parameters

        # Paths
        REPO="/path/to/repo"
        SCRIPT="$REPO/babilonia/tools/report.py"
        DATA="/data/bank"

        # Parameters
        TYPE="bb-cc"
        YEAR=2024

        # Run script
        python "$SCRIPT" --folder "$DATA" --type "$TYPE" --year "$YEAR"


Expected Folder Structure
-------------------------

The input data is expected to follow a simple hierarchical layout:

::

    bb/                                 # Bank
    └── cc/                             # Bank account
        ├── SALDOS_BB_CC.csv            # Initial balances per year
        ├── 2023/
        │   └── CAIXA_BB_CC_2023_DIARIO.csv
        └── 2024/
            └── CAIXA_BB_CC_2024_DIARIO.csv

Each ``CAIXA_*_DIARIO.csv`` file represents a daily canonical cashflow
dataset for a given year.

The balances file (``SALDOS_*.csv``) must contain, at minimum, the
columns:

- ``Year``  : reference year
- ``Value`` : initial balance at the start of the year


Data Levels
-----------

- **Daily**: Transaction-level canonical cashflow.
- **Report**: Derived yearly report with summary and panel tables.

The script does not modify input files and does not write new CSV files;
it only produces terminal reports.
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
from babilonia.tools.core import *
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

    file_initial = data_folder / f"SALDOS_{bank.upper()}_{account.upper()}.csv"
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
        initial_cash = df_initial.query(f"Year == {year}")["Value"].values[0]

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

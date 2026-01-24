# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2025 The Project Authors
# See pyproject.toml for authors/maintainers.
# See LICENSE for license details.
"""
Parse and standardize bank statement CSV files.

This script scans a target directory for bank statement files
(T0 source format), standardizes their structure using the appropriate
``CashFlow`` parser, and writes the processed outputs as new CSV files
(T1 canonical format) in the same yearly subdirectories.

Processing can be restricted to a single year or applied to all available
years. When multiple years are present, files are processed year by year
with structured terminal output to facilitate log inspection.

Scripts Examples
----------------

The script is intended for command-line execution.

.. dropdown:: Minimal PowerShell example (Windows)
    :icon: code-square
    :open:

    Save as ``run_parse.ps1`` and execute from PowerShell.

    .. code-block:: powershell

        # ! Warning -- change paths and parameters

        # Paths
        $REPO   = "C:\\path\\to\\repo"
        $SCRIPT = "$REPO\\babilonia\\utils\\parse_bb.py"
        $DATA   = "C:\\data\\bank_statements"

        # Parameters
        $TYPE = "bb-cc"
        $YEAR = 2024

        # Activate virtual environment
        & "$REPO\\.venv\\Scripts\\Activate.ps1"

        # Run script
        python $SCRIPT `
            --folder $DATA `
            --type $TYPE `
            --year $YEAR

        # Deactivate virtual environment
        deactivate


.. dropdown:: Minimal shell example (Linux)
    :icon: code-square
    :open:

    Save as ``run_parse.sh`` and execute from a terminal.

    .. code-block:: bash

        #!/usr/bin/env bash

        # ! Warning -- change paths and parameters

        # Paths
        REPO="/path/to/repo"
        SCRIPT="$REPO/babilonia/utils/parse_bb.py"
        DATA="/data/bank_statements"

        # Parameters
        TYPE="bb-cc"
        YEAR=2024

        # Activate virtual environment
        source "$REPO/.venv/bin/activate"

        # Run script
        python "$SCRIPT" \
            --folder "$DATA" \
            --type "$TYPE" \
            --year "$YEAR"

        # Deactivate virtual environment
        deactivate



Expected Folder Structure
-------------------------

The input data is expected to follow a simple hierarchical layout:

::

    bank_statements/
    └── bb-cc/                     # Bank account (type)
        ├── 2022/
        │   ├── EXTRATO_BB_CC_001_T0.csv
        │   └── EXTRATO_BB_CC_002_T0.csv
        ├── 2023/
        │   └── EXTRATO_BB_CC_001_T0.csv
        └── 2024/
            ├── EXTRATO_BB_CC_001_T0.csv
            └── EXTRATO_BB_CC_002_T0.csv

Each ``*_T0.csv`` file represents a raw (Tier 0) bank statement.

During execution, the script generates standardized Tier 1 outputs
alongside the original files:

::

    bb-cc/
    └── 2024/
        ├── EXTRATO_BB_CC_001_T0.csv   # original
        └── EXTRATO_BB_CC_001_T1.csv   # standardized (canonical)

Data Levels
----------------

- **Tier 0 (T0)**: Raw statement files as exported by the bank.
  Column names, formats, and ordering may vary.
- **Tier 1 (T1)**: Canonical, standardized CSV files produced by this
  script, suitable for downstream analysis and aggregation.

The original Tier 0 files are never modified; Tier 1 files are written
only when they do not already exist.

"""

# IMPORTS
# ***********************************************************************
# import modules from other libs

# Native imports
# =======================================================================
import glob
import argparse
import pprint
from pathlib import Path

# ... {develop}

# External imports
# =======================================================================
# import {module}
# ... {develop}

# Project-level imports
# =======================================================================
# import {module}
from babilonia.utils.core import *


# ... {develop}

# CONSTANTS
# ***********************************************************************
# ... {develop}

# FUNCTIONS
# ***********************************************************************
# ... {develop}

def main():
    args = get_arguments()

    data_folder = Path(args.folder)
    data_type = args.type.lower()
    year_arg = args.year

    print("\n\n")
    print("=" * 80)
    print(" Parsing Bank Statements\n".upper())
    print(f" Folder  : {data_folder}")
    print(f" Bank    : {BANK_NAMES[data_type]}")
    print(f" Account : {ACCOUNT_NAMES[data_type]}")
    print(f" Year    : {year_arg if year_arg is not None else 'ALL'}")
    print("=" * 80)

    # Resolve file pattern (year wildcard handled inside helper)
    pattern_files = get_file_pattern_statement_t0(data_type, data_folder, year_arg)
    ls_files = glob.glob(pattern_files)

    if not ls_files:
        print(" No input files found. Nothing to process.")
        print("=" * 80)
        return None

    # ------------------------------------------------------------------
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
        # print("-" * 80)
        print(f" Year {year}")
        print("-" * 80)

        yearly_processed = 0
        for i, fpath in enumerate(files_by_year[year], start=1):
            name = fpath.stem
            new_name = name.replace("T0", "T1")
            file_out = fpath.parent / f"{new_name}.csv"

            print(f"[{i:02d}] {fpath.name}", end=" -> ")

            if file_out.exists():
                print(f"{file_out.name} SKIPPED")
                continue

            cf.load_data(file_data=str(fpath))
            cf.standardize()
            cf.data.to_csv(file_out, sep=";", index=False)
            print(f"{file_out.name} PARSED")
            total_processed += 1
            yearly_processed += 1
        print(f"\n Year completed. Output files written: {yearly_processed}")

    print()
    print("=" * 80)
    print(f" Completed. Output files written: {total_processed}")
    print("=" * 80)
    print("\n\n")
    return None


# SCRIPT
# ***********************************************************************
# standalone behaviour as a script
if __name__ == "__main__":
    main()

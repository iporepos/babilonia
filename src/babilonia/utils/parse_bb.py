# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2025 The Project Authors
# See pyproject.toml for authors/maintainers.
# See LICENSE for license details.
"""
Parse and standardize Banco do Brasil checking account statements.

This script scans a target directory for Banco do Brasil Conta Corrente
CSV statement files (T0), standardizes their structure using the
``CashFlowBBCC`` class, and writes the processed outputs as new CSV files (T1)
in the same subdirectories. It is intended for batch processing and
command-line execution.

.. dropdown:: Script example for Windows
    :icon: code-square
    :open:

    Save a ``bat`` file and run using PowerShell

    .. code-block:: bat

        @echo off

        REM Activate virtual environment
        call C:\\path\\to\\repo\\.venv\\Scripts\\activate.bat

        REM set script arguments
        set FOLDER=C:/path/to/folder
        set TYPE=cc

        REM run as module
        python -m babilonia.utils.parse_bb "%FOLDER%" "%TYPE%"


.. dropdown:: Script example for Linux
    :icon: code-square
    :open:

    Save a ``sh`` file and run using Terminal

    .. code-block:: bash

        #!/usr/bin/env bash

        # Activate virtual environment
        source /path/to/repo/.venv/bin/activate

        # Set script arguments
        FOLDER="/path/to/folder"
        TYPE="cc"

        # Run as module
        python -m babilonia.utils.parse_bb "$FOLDER" "$TYPE"

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
# import {module}
# ... {develop}

# Project-level imports
# =======================================================================
# import {module}
from babilonia.accounting import CashFlowBBCC, CashFlowBBCCPJ, CashFlowBBPP

# ... {develop}

SUFFIXES = {
    "CC": "CC",
}

# FUNCTIONS
# ***********************************************************************


def get_arguments():
    # 1. Initialize the Parser
    parser = argparse.ArgumentParser(
        description="Handle BB files.",
        epilog="Usage example: python script.py path/data path/output",
    )

    # 2. Add Arguments
    # Positional argument (Required)
    parser.add_argument("folder", help="The path to folder you want to process.")

    parser.add_argument("type", help="The type of account.")

    # 3. Parse the Arguments
    args = parser.parse_args()

    dc = {"folder": args.folder, "type": args.type}
    return dc


def main():
    dc = get_arguments()

    s = dc["type"].upper()

    pattern = f"{dc['folder']}/*/EXTRATO_BB_{s}_*_T0.csv"
    ls_files = glob.glob(pattern)

    print(f"\nFound {len(ls_files)} file(s) to process.\n")

    for i, f in enumerate(ls_files, start=1):
        fpath = Path(f)
        root_folder = fpath.parent
        name = fpath.stem
        new_name = name.replace("T0", "T1")
        file_out = root_folder / f"{new_name}.csv"

        print("=" * 60)
        print(f"[{i}/{len(ls_files)}] Processing file")
        print(f"  Input : {fpath}")
        print(f"  Output: {file_out}")

        if file_out.exists():
            print("  ! Output file already exists. Skipping write.\n")

        else:

            if s == "CC":
                cf = CashFlowBBCC()
            elif s == "CCPJ":
                cf = CashFlowBBCCPJ()
            elif s == "PP":
                cf = CashFlowBBPP()
            else:
                cf = CashFlowBBCC()

            print("  - Loading data...")
            cf.load_data(file_data=f)

            print("  - Standardizing data...")
            cf.standardize()

            print("  - Writing output file...")
            cf.data.to_csv(file_out, sep=";", index=False)
            print("  ✓ File written successfully.")
            print("  - Preview (first 10 rows):")
            print(cf.data.head(10))
            print()

    print("\nDone.\n")
    return None


# SCRIPT
# ***********************************************************************
# standalone behaviour as a script
if __name__ == "__main__":
    main()

# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2025 The Project Authors
# See pyproject.toml for authors/maintainers.
# See LICENSE for license details.
"""
todo refactor docstring
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

import pandas as pd

# ... {develop}

# External imports
# =======================================================================
# import {module}
# ... {develop}

# Project-level imports
# =======================================================================
# import {module}
from babilonia.accounting import CashFlow

# ... {develop}

# FUNCTIONS
# ***********************************************************************


def get_arguments():
    # 1. Initialize the Parser
    parser = argparse.ArgumentParser(
        description="Analyst for cashflow files",
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
    bank = s.split("-")[0]
    account = s.split("-")[1]

    pattern = f"{dc['folder']}/*/EXTRATO_{bank}_{account}_*_T1.csv"
    ls_files = glob.glob(pattern)

    print(f"\nFound {len(ls_files)} file(s) to process.\n")

    ls_dfs = []

    for i, f in enumerate(ls_files, start=1):
        fpath = Path(f)
        root_folder = fpath.parent
        name = fpath.stem
        month = name.split("_")[-2].split("-")[-1]
        year = name.split("_")[-2].split("-")[-2]
        new_name = name.replace("T0", "T1")

        print("=" * 60)
        print(
            f"[{i}/{len(ls_files)}] Processing {s} file --year {year} --month {month}"
        )
        print(f"  Input : {fpath}")

        df = pd.read_csv(fpath, sep=";", dtype=str)
        ls_dfs.append(df.copy())

    df_full = pd.concat(ls_dfs).reset_index(drop=True)

    ls_cols = list(df_full.columns)
    ls_priority = [
        "Data",
        "Categoria",
        "Valor",
        "Descricao",
    ]
    ls_ordered = ls_priority + [c for c in ls_cols if c not in ls_priority]

    df_full = df_full[ls_ordered]
    print("\n")
    print("=" * 60)
    print("   Daily Cash Flow\n")
    print(df_full)
    print("\n")

    # export to file
    file_out = Path(dc["folder"]) / f"CAIXA_{bank}_{account}_DIARIO_T1.csv"
    df_full.to_csv(file_out, sep=";", index=False)
    print(f"  Output : {file_out}")

    #
    cf = CashFlow()
    cf.load_data(file_out)

    dc_cfa = cf.cashflow_analysis(df=cf.data, category=None)
    print("\n")
    print("=" * 60)
    print("   Monthly Cash Flow\n")
    for y in dc_cfa["monthly"]["Ano"].unique():
        print("\n")
        print(dc_cfa["monthly"].query(f"Ano == '{y}'"))

    # exports
    file_out = Path(dc["folder"]) / f"CAIXA_{bank}_{account}_MENSAL_T1.csv"
    dc_cfa["monthly"].to_csv(file_out, sep=";", index=False)
    print("\n")
    print(f"  Output : {file_out}")

    print("\n")
    print("=" * 60)
    print("   Yearly Cash Flow\n")
    print(dc_cfa["yearly"])

    file_out = Path(dc["folder"]) / f"CAIXA_{bank}_{account}_ANUAL_T1.csv"
    dc_cfa["yearly"].to_csv(file_out, sep=";", index=False)
    print("\n")
    print(f"  Output : {file_out}")

    print("\nDone.\n\n")
    return None


# SCRIPT
# ***********************************************************************
# standalone behaviour as a script
if __name__ == "__main__":
    main()

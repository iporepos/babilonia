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

    char_w = 150

    args = get_arguments()

    data_folder = Path(args.folder)
    data_type = args.type.lower()
    year_arg = args.year

    bank = get_bank(data_type)
    account = get_account(data_type)

    ls_priority = [
        "Data",
        "Categoria",
        "Valor",
        "Descricao",
    ]

    cols_to_format = [
        "Entradas",
        "Saidas",
        "Fluxo",
        "Entradas_Acum",
        "Saidas_Acum",
        "Fluxo_Acum",
    ]

    print("\n\n")
    print("=" * char_w)
    print(" Cashflow Analysis from Bank Statements\n".upper())
    print(f" Folder  : {data_folder}")
    print(f" Bank    : {BANK_NAMES[data_type]}")
    print(f" Account : {ACCOUNT_NAMES[data_type]}")
    print(f" Year    : {year_arg if year_arg is not None else 'ALL'}")
    print("=" * char_w)

    # Resolve file pattern (year wildcard handled inside helper)
    pattern_files = get_file_pattern_statement_t0(data_type, data_folder, year_arg)
    pattern_files = pattern_files.replace("T0.csv", "T1.csv")
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

        yearly_processed = 0
        ls_dfs = []
        for i, fpath in enumerate(files_by_year[year], start=1):
            name = fpath.stem

            print(f"[{i:02d}] {fpath.name}", end=" -> ")

            df = pd.read_csv(fpath, sep=";", dtype=str)
            ls_dfs.append(df.copy())

            print(f"LOADED")
            yearly_processed += 1
        print(f"\n Year completed. Output files loaded: {yearly_processed}")

        # Concat data
        # --------------------------------------------------------------------
        df_full = pd.concat(ls_dfs).reset_index(drop=True)
        ls_cols = list(df_full.columns)

        ls_ordered = ls_priority + [c for c in ls_cols if c not in ls_priority]
        df_full = df_full[ls_ordered]

        name = f"CAIXA_{bank.upper()}_{account.upper()}_{year}"

        # Daily
        # --------------------------------------------------------------------
        print("\n")
        print(f" Year {year} -- Daily Cash Flow (preview)")
        print("-" * char_w)
        df_pretty = CashFlow.format_currency_columns(
            df_full[ls_priority], columns=["Valor"]
        )
        preview_df(df_pretty)
        print("\n")
        # export
        file_out = Path(args.folder) / f"{year}/{name}_DIARIO.csv"
        df_full.to_csv(file_out, sep=";", index=False)
        total_processed += 1
        print(f"  Output : {file_out}")

        # Run Cashflow analysis
        # --------------------------------------------------------------------
        cf = CashFlow()
        cf.load_data(file_out)
        dc_cfa = cf.cashflow_analysis(df=cf.data, category=None)

        # Monthly
        # --------------------------------------------------------------------
        print("\n")
        print(f" Year {year} -- Monthly Cash Flow")
        print("-" * char_w)
        df_pretty = CashFlow.format_currency_columns(
            dc_cfa["monthly"], columns=cols_to_format
        )
        print(df_pretty)
        print("\n")

        # exports
        file_out = Path(args.folder) / f"{year}/{name}_MENSAL.csv"
        dc_cfa["monthly"].to_csv(file_out, sep=";", index=False)
        total_processed += 1
        print(f"  Output : {file_out}")

        # Yearly
        # --------------------------------------------------------------------
        print("\n")
        print(f" Year {year} -- Annual Cash Flow")
        print("-" * char_w)
        df_pretty = CashFlow.format_currency_columns(
            dc_cfa["yearly"], columns=cols_to_format
        )
        print(df_pretty)
        print("\n")

        file_out = Path(args.folder) / f"{year}/{name}_ANUAL.csv"
        dc_cfa["yearly"].to_csv(file_out, sep=";", index=False)
        total_processed += 1
        print(f"  Output : {file_out}")

    # Merge full system
    # --------------------------------------------------------------------
    name = f"CAIXA_{bank.upper()}_{account.upper()}"

    dc_scales = {"DIARIO": "Data", "MENSAL": "Mes", "ANUAL": "Ano"}

    for scale in list(dc_scales.keys()):
        pattern = Path(args.folder) / f"*/CAIXA*{scale}.csv"
        ls_files = glob.glob(str(pattern))
        df = concat_dfs(ls_files)
        df.sort_values(by=dc_scales[scale], ascending=True, inplace=True)
        file_out = Path(args.folder) / f"{name}_O_{scale}.csv"
        df.to_csv(file_out, sep=";", index=False)
        total_processed += 1

        # Yearly
        # --------------------------------------------------------------------
        if scale == "ANUAL":
            print("\n")
            print(f" ANNUAL CASH FLOW")
            print("=" * char_w)
            cols_to_format = [
                "Entradas",
                "Saidas",
                "Fluxo",
                "Entradas_Acum",
                "Saidas_Acum",
                "Fluxo_Acum",
            ]
            df_pretty = CashFlow.format_currency_columns(df, columns=cols_to_format)
            print(df_pretty)
            print("\n")

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

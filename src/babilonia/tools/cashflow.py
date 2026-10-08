# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2025 The Project Authors
# See pyproject.toml for authors/maintainers.
# See LICENSE for license details.
"""
Aggregate and analyze cash flow from standardized bank statements.

This script scans a target directory for standardized bank statement files
(T1 canonical format), groups them by year, concatenates daily records,
and produces daily, monthly, and annual cash flow reports using the
``CashFlow`` analysis engine.

For each year found, the script:

- Loads all matching T1 statement files.
- Concatenates and reorders columns into a canonical layout.
- Buckets rows by their actual transaction year (``Data``), not by the
  folder/file they were physically stored in.
- Writes a consolidated daily cash flow CSV.
- Computes monthly and annual cash flow summaries.
- Writes monthly and annual CSV reports.
- Displays formatted previews in the terminal.

After yearly processing, the script merges all yearly outputs into
global daily, monthly, and annual datasets for the full system.

Processing can be restricted to a single year or applied to all available
years. Terminal output is structured to facilitate inspection and logging.

.. note::

    Some statement types do not align with calendar-month/year
    boundaries. Nubank credit-card invoices, for example, are filed
    under the year of the invoice, but a given invoice's transactions
    can legitimately spill into December of the previous year (the
    invoice closes a few days into the new month). Because of this,
    *file discovery* is folder/invoice based, but *reporting buckets*
    are always derived from the actual ``Data`` column, never from the
    folder a file happened to live in. All T1 files are loaded up
    front (regardless of ``--year``) and rows are bucketed by their
    real transaction year afterward, so spillover transactions land in
    the correct year's report instead of being split or duplicated
    across two years.

Script Examples
---------------

The script is intended for command-line execution.

.. dropdown:: Minimal PowerShell example (Windows)
    :icon: code-square
    :open:

    Save as ``run_cashflow.ps1`` and execute from PowerShell.

    .. code-block:: powershell

        # ! Warning -- change paths and parameters

        # Paths
        $REPO   = "C:\\path\\to\\repo"
        $SCRIPT = "$REPO\\babilonia\\tools\\cashflow.py"
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

    Save as ``run_cashflow.sh`` and execute from a terminal.

    .. code-block:: bash

        #!/usr/bin/env bash

        # ! Warning -- change paths and parameters

        # Paths
        REPO="/path/to/repo"
        SCRIPT="$REPO/babilonia/tools/cashflow.py"
        DATA="/data/bank_statements"

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
        ├── cashflow.json                  # optional, see Plots below
        ├── 2022/
        │   ├── EXTRATO_BB_CC_2022-01_T1.csv
        │   └── EXTRATO_BB_CC_2022-02_T1.csv
        ├── 2023/
        │   └── EXTRATO_BB_CC_2023-01_T1.csv
        └── 2024/
            ├── EXTRATO_BB_CC_2024-01_T1.csv
            └── EXTRATO_BB_CC_2024-02_T1.csv

Each ``*_T1.csv`` file represents a canonical (Tier 1) standardized
bank statement.

During execution, the script generates consolidated and aggregated
outputs:

::

    bb/                                 # Bank
    └── cc/                             # Bank account
        ├── CAIXA_BB_CC_MENSAL_2023.jpg
        ├── CAIXA_BB_CC_MENSAL_2024.jpg
        ├── CAIXA_BB_CC_MENSAL_LT.jpg
        └── 2024/
            ├── CAIXA_BB_CC_2024_DIARIO.csv
            ├── CAIXA_BB_CC_2024_MENSAL.csv
            ├── CAIXA_BB_CC_2024_ANUAL.csv
            └── CAIXA_BB_CC_2024_REPORT.txt

Plots are written directly under the bank/account folder (not inside
the per-year subfolder) so every year's ``.jpg`` files sit side by
side for easy comparison -- they share a common y-axis scale computed
once over the whole series (see Plots below). The year comes last in
the plot filename (unlike the per-year CSV/report names) so files
across years sort next to each other.

Global merged outputs (all years):

::

    bb/                                 # Bank
    └── cc/                             # Bank account
        ├── CAIXA_BB_CC_O_DIARIO.csv
        ├── CAIXA_BB_CC_O_MENSAL.csv
        └── CAIXA_BB_CC_O_ANUAL.csv


Data Levels
-----------

- **Tier 1 (T1)**: Canonical, standardized statement files produced by
  the parsing stage.
- **Daily**: Concatenated transaction-level data, bucketed by the real
  transaction year (from ``Data``), not by source file/folder.
- **Monthly**: Aggregated per month with cumulative fields. The
  on-screen preview appends ``SUBTOTAL`` and ``MEDIA`` (subtotal / 12)
  rows for ``Entradas``/``Saidas``/``Fluxo`` and their transaction
  counts; cumulative columns are left blank there, since summing a
  running total isn't meaningful. These two rows are display-only and
  not written to the exported CSV.
- **Annual**: Aggregated per year with cumulative fields.
- **Report**: A ``.txt`` file per year, a verbatim copy of everything
  printed to the terminal for that year (header, daily/monthly/annual
  previews), produced by mirroring ``stdout`` while that year is
  processed so it can never drift from what was shown on screen. Table
  headers follow the ``language`` setting below.
- **Plots**: A ``.jpg`` bar chart per year for the monthly scale,
  written to the bank/account folder (not the per-year subfolder).
  Entradas are drawn above zero, Saidas below zero, both anchored at
  the same baseline, and each bar is annotated with its value,
  compacted to ``K``/``M`` for large amounts. The y-axis limits are
  computed once from the whole series (every year available, 1.2x the
  absolute max flow) and reused for every year's plot, so all years
  share the same scale and are directly comparable. A second panel to
  the right shows the same series as a horizontal histogram sharing
  that y-axis -- a sideways projection of the distribution, binned by
  a fixed currency interval, inflows mirroring outflows across zero.
  Figure size, bar colors/width, histogram panel size/bins, background
  color and font sizes come from the config file below. Alongside the
  per-year plots, one more covers the full history: every year's
  months in one chart (``..._MENSAL_LT.jpg``, "LT" for long-term),
  using the same y-scale, with annotations dropped (too many bars
  across several years) and only a January tick per year, labeled
  with that year's number -- no per-month letters. Its histogram bin
  size always comes from Scott's rule on its own (larger) series,
  regardless of any fixed ``hist_bin_size`` set in ``cashflow.json``
  for the per-year plots -- the LT series is a different sample and
  keeps its own bin width. A daily plot is not produced for now -- it added
  little over the monthly one -- though the underlying
  :meth:`babilonia.accounting.CashFlow.get_daily_summary` and the
  ``date_axis`` option on :meth:`plot_cashflow_bars
  <babilonia.accounting.CashFlow.plot_cashflow_bars>` still support it.

Config File
-----------

Plot style and the report language are both read from an optional
``cashflow.json`` sitting in the bank/account folder (next to the
plots). Every key is optional, and so is the file itself: anything
missing falls back to :data:`babilonia.accounting.PLOT_CONFIG_DEFAULTS`.

.. code-block:: json

    {
        "figsize_mm": [150, 80],
        "dpi": 300,
        "color_inflows": "tab:blue",
        "color_outflows": "tab:red",
        "background_color": "#F7F7FB",
        "language": "en",
        "fontsize_title": 10,
        "fontsize_annotation": 5,
        "fontsize_ticks": 8,
        "bar_width_pct": 60,
        "hist_width_pct": 33,
        "hist_bin_size": null,
        "color_hist": null
    }

``language`` controls the printed table headers (terminal + ``.txt``
report: ``Ano`` -> ``Year``, ``Entradas`` -> ``Inflows``, etc. -- see
``COLUMN_LABELS`` in this module), not the plots. Currently ``"en"``
(default) or ``"pt-br"`` (the data's native language, a no-op); more
may be added later. Every other key tunes :meth:`plot_cashflow_bars()
<babilonia.accounting.CashFlow.plot_cashflow_bars>` -- see
:meth:`babilonia.accounting.CashFlow.load_plot_config` for details.

The script does not modify input files; all outputs are written as new
CSV, ``.txt`` and ``.jpg`` files.
"""


# IMPORTS
# ***********************************************************************
# import modules from other libs

# Native imports
# =======================================================================
import glob
import argparse
from pathlib import Path
from datetime import datetime

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

# CONSTANTS
# ***********************************************************************
# define constants in uppercase

# Display-only translations for printed table headers (terminal + .txt
# report). The underlying DataFrame/CSV columns are always the original
# Portuguese names -- other tools and any saved CSV rely on that schema,
# so only the rendered preview is ever renamed. "pt-br" is a no-op (the
# data's native language); "en" is the default. More languages may be
# added here later.
COLUMN_LABELS = {
    "en": {
        "Data": "Date",
        "Categoria": "Category",
        "Valor": "Value",
        "Descricao": "Description",
        "Ano": "Year",
        "Mes": "Month",
        "Entradas": "Inflows",
        "Entradas_N": "Inflows_N",
        "Saidas": "Outflows",
        "Saidas_N": "Outflows_N",
        "Fluxo": "Net_Flow",
        "Entradas_Acum": "Inflows_Cum",
        "Saidas_Acum": "Outflows_Cum",
        "Fluxo_Acum": "Net_Flow_Cum",
    },
    "pt-br": {},
}

ROW_LABELS = {
    "en": {"subtotal": "SUBTOTAL", "average": "AVERAGE"},
    "pt-br": {"subtotal": "SUBTOTAL", "average": "MEDIA"},
}


# FUNCTIONS
# ***********************************************************************


def localize_columns(df, column_labels):
    """
    Rename df's columns for display, falling back to the original name
    for any column not covered by ``column_labels``. Display-only --
    never used before a dataframe is exported to CSV.
    """
    return df.rename(columns=column_labels)


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

    # Resolve file pattern.
    # ------------------------------------------------------------------
    # NOTE: statement files are ALWAYS loaded for every year, regardless
    # of `year_arg`. Some statement types (e.g. Nubank credit card
    # invoices, "nu-cc") don't align with calendar months: an invoice
    # filed under year Y can legitimately contain transactions dated in
    # December of year Y-1, since the invoice closes a few days into
    # the new month. Restricting the file *glob* by year (as before)
    # would silently drop or mis-bucket that spillover. Instead we load
    # every T1 file up front, then bucket *rows* by their actual
    # transaction year further down -- `--year` is applied there.
    pattern_files = get_file_pattern_statement_t0(data_type, data_folder, None)
    pattern_files = pattern_files.replace("T0.csv", "T1.csv")
    ls_files = sorted(glob.glob(pattern_files))

    if not ls_files:
        print(" No input files found. Nothing to process.")
        print("=" * char_w)
        return None

    cf = PARSERS[data_type]()

    total_processed = 0

    # Load & concatenate every statement file up front
    # ------------------------------------------------------------------
    print()
    print(" Loading input files")
    print("-" * char_w)
    ls_dfs = []
    for i, f in enumerate(ls_files, start=1):
        fpath = Path(f)
        print(f"[{i:02d}] {fpath.name}", end=" -> ")
        df = pd.read_csv(fpath, sep=";", dtype=str)
        ls_dfs.append(df.copy())
        print("LOADED")
    print(f"\n Loading completed. Files loaded: {len(ls_dfs)}")

    # Concat data
    # --------------------------------------------------------------------
    df_all = pd.concat(ls_dfs).reset_index(drop=True)
    ls_cols = list(df_all.columns)

    ls_ordered = ls_priority + [c for c in ls_cols if c not in ls_priority]
    df_all = df_all[ls_ordered]

    # Bucket rows by their real transaction year, not by the file/folder
    # they happened to be stored in.
    # ------------------------------------------------------------------
    df_all["Data"] = pd.to_datetime(df_all["Data"])
    df_all["__Ano"] = df_all["Data"].dt.year.astype(str)

    years_available = sorted(df_all["__Ano"].unique())
    years_to_process = [str(year_arg)] if year_arg is not None else years_available

    # Tool config, optionally overridden by a cashflow.json sitting next to
    # the plots (figure size, bar colors, background color, font sizes,
    # report language); falls back to PLOT_CONFIG_DEFAULTS if the file is
    # absent.
    # ------------------------------------------------------------------
    plot_config = CashFlow.load_plot_config(args.folder)
    language = plot_config["language"]
    column_labels = COLUMN_LABELS.get(language, COLUMN_LABELS["en"])
    row_labels = ROW_LABELS.get(language, ROW_LABELS["en"])

    # Global plot y-limits, computed once over the whole series (every year
    # available, regardless of --year) so every year's plot shares the same
    # scale and is directly comparable to the others.
    # ------------------------------------------------------------------
    df_all_typed = df_all.copy()
    df_all_typed["Valor"] = df_all_typed["Valor"].astype(float)

    dc_cfa_all = CashFlow.get_cashflow_analysis(df=df_all_typed, category=None)
    ylim_monthly = 1.2 * max(
        dc_cfa_all["monthly"]["Entradas"].max(),
        dc_cfa_all["monthly"]["Saidas"].abs().max(),
    )

    # Full-history monthly plot -- every year already assembled above, no
    # per-year annotations (too many bars over several years) and only a
    # January tick per year, labeled with the year number. hist_bin_size
    # is forced to None here regardless of plot_config -- the LT series
    # is a different sample (every month, every year) than any per-year
    # plot, so its bin width always comes from Scott's rule on its own
    # data, never from a fixed hist_bin_size set for the per-year plots.
    # ------------------------------------------------------------------
    lt_config = {**plot_config, "hist_bin_size": None}
    file_plot = (
        Path(args.folder) / f"CAIXA_{bank.upper()}_{account.upper()}_MENSAL_LT.jpg"
    )
    CashFlow.plot_cashflow_bars(
        df=dc_cfa_all["monthly"],
        x_col="Mes",
        file_out=file_plot,
        title=f"{BANK_NAMES[data_type]} -- {ACCOUNT_NAMES[data_type]}",
        scale="Monthly",
        annotate=False,
        year_ticks=True,
        ylim_default=ylim_monthly,
        config=lt_config,
    )
    total_processed += 1
    print(f"  Output : {file_plot}")

    for year in years_to_process:
        print()
        # print("-" * char_w)
        print(f" Year {year}")
        print("-" * char_w)

        df_full = df_all.query("__Ano == @year").drop(columns="__Ano").copy()

        if df_full.empty:
            print(f" No transactions found for {year}. Skipping.")
            continue

        print(f"\n Year completed. Transactions found: {len(df_full)}")

        name_base = f"CAIXA_{bank.upper()}_{account.upper()}"
        name = f"{name_base}_{year}"

        # Text report
        # --------------------------------------------------------------------
        # Mirrors everything printed below into a .txt file, so the report
        # on disk always matches the terminal preview for this year.
        file_report = Path(args.folder) / f"{year}/{name}_REPORT.txt"
        file_report.parent.mkdir(parents=True, exist_ok=True)

        with open(file_report, "w", encoding="utf-8") as f_report, tee_stdout(f_report):
            print("=" * char_w)
            print(f" Cashflow Analysis Report -- Year {year}\n".upper())
            print(f" Folder    : {data_folder}")
            print(f" Bank      : {BANK_NAMES[data_type]}")
            print(f" Account   : {ACCOUNT_NAMES[data_type]}")
            print(f" Year      : {year}")
            print(f" Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * char_w)

            # Daily
            # ----------------------------------------------------------------
            print("\n")
            print(f" Year {year} -- Daily Cash Flow (preview)")
            print("-" * char_w)
            df_pretty = CashFlow.format_currency_columns(
                df_full[ls_priority], columns=["Valor"]
            )
            preview_df(localize_columns(df_pretty, column_labels))
            print("\n")
            # export
            file_out = Path(args.folder) / f"{year}/{name}_DIARIO.csv"
            file_out.parent.mkdir(parents=True, exist_ok=True)
            df_full.to_csv(file_out, sep=";", index=False)
            total_processed += 1
            print(f"  Output : {file_out}")

            # Run Cashflow analysis
            # ----------------------------------------------------------------
            cf = CashFlow()
            cf.load_data(file_out)
            dc_cfa = cf.get_cashflow_analysis(df=cf.data, category=None)

            # Monthly
            # ----------------------------------------------------------------
            print("\n")
            print(f" Year {year} -- Monthly Cash Flow")
            print("-" * char_w)
            df_pretty = CashFlow.format_currency_columns(
                dc_cfa["monthly"], columns=cols_to_format
            )
            money_cols = ["Entradas", "Saidas", "Fluxo"]
            count_cols = ["Entradas_N", "Saidas_N"]
            count_formatter = lambda x: (
                f"{x:.0f}" if float(x).is_integer() else f"{x:.1f}"
            )
            df_extra = build_subtotal_rows(
                df=dc_cfa["monthly"],
                columns=dc_cfa["monthly"].columns,
                sum_columns=money_cols + count_cols,
                label_column="Mes",
                formatters={
                    **{col: CashFlow.format_currency for col in money_cols},
                    **{col: count_formatter for col in count_cols},
                },
                subtotal_label=row_labels["subtotal"],
                average_label=row_labels["average"],
            )
            df_pretty = pd.concat([df_pretty, df_extra], ignore_index=True)
            print(localize_columns(df_pretty, column_labels))
            print("\n")

            # exports
            file_out = Path(args.folder) / f"{year}/{name}_MENSAL.csv"
            file_out.parent.mkdir(parents=True, exist_ok=True)
            dc_cfa["monthly"].to_csv(file_out, sep=";", index=False)
            total_processed += 1
            print(f"  Output : {file_out}")

            # plot -- few bars, so each one is annotated with its value
            # year goes last so same-scale plots across years sort together
            file_plot = Path(args.folder) / f"{name_base}_MENSAL_{year}.jpg"
            CashFlow.plot_cashflow_bars(
                df=dc_cfa["monthly"],
                x_col="Mes",
                file_out=file_plot,
                title=f"{BANK_NAMES[data_type]} -- {ACCOUNT_NAMES[data_type]} -- {year}",
                scale="Monthly",
                annotate=True,
                ylim_default=ylim_monthly,
                config=plot_config,
            )
            total_processed += 1
            print(f"  Output : {file_plot}")

            # Yearly
            # ----------------------------------------------------------------
            print("\n")
            print(f" Year {year} -- Annual Cash Flow")
            print("-" * char_w)
            df_pretty = CashFlow.format_currency_columns(
                dc_cfa["yearly"], columns=cols_to_format
            )
            print(localize_columns(df_pretty, column_labels))
            print("\n")

            file_out = Path(args.folder) / f"{year}/{name}_ANUAL.csv"
            file_out.parent.mkdir(parents=True, exist_ok=True)
            dc_cfa["yearly"].to_csv(file_out, sep=";", index=False)
            total_processed += 1
            print(f"  Output : {file_out}")

        total_processed += 1
        print(f"  Output : {file_report}")

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
            print(localize_columns(df_pretty, column_labels))
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

# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2025 The Project Authors
# See pyproject.toml for authors/maintainers.
# See LICENSE for license details.
"""
Deterministically categorize standardized bank statement files, then
report on the result.

This script runs in two phases, in one invocation:

1. **Categorize** -- scans T1 statement files and fills the
   ``Categoria`` column of each one, in place, using a per-account
   keyword dictionary. See "Categorization rules" below.
2. **Report** -- builds a monthly + yearly cash flow breakdown *by
   category* for one target year, using the just-updated labels, and
   prints it to the screen plus exports it as CSV. See "Report" below.

Both phases are entirely self-contained: this script has no
dependency on ``babilonia.accounting``. The report is built with a
single ``pandas.pivot_table`` aggregation rather than any per-category
loop, so a category with both inflow and outflow rows (e.g. a charge
and its refund, both tagged the same category) can't produce a
column-name collision or double-counted total -- there's nothing to
loop over, and the whole aggregation is one pass.

The ``--year`` argument
------------------------

``--year`` has one, shared meaning across both phases: which year to
focus this run on.

- **Omitted (default):** phase 1 relabels every T1 file, for every
  year (the normal "keep everything freshly categorized" run); phase 2
  reports on the **current calendar year**.
- **Given (e.g. ``--year 2025``):** phase 1 only relabels files whose
  invoice/statement is filed under that year's folder; phase 2 reports
  on that same year. Useful for a focused re-run or a quick test on
  one year without touching the rest of your history.

Either way, the report always has access to your **full** transaction
history for correct spillover handling -- see the note below.

Categorization rules
---------------------

For every row:

1. If ``Categoria`` is already set to something other than the
   fallback category (``"outros"`` by default), its value is kept --
   but always normalized to lowercase. This applies even to
   manually-entered labels: nothing is re-matched against the
   dictionary, but the stored text is forced to lowercase for
   consistency.
2. If ``Categoria`` is empty, or already set to the fallback category,
   the script tries to match it against the keyword dictionary (see
   below). The search text is a whitespace-joined concatenation of
   **every column in the row except ``Data``, ``Valor``, and
   ``Categoria`` itself** (so this works unchanged across accounts
   with different schemas -- BB, Nubank, or anything added later --
   without needing to know which column holds the merchant text).
   Matching is case- and accent-insensitive and uses a plain
   "contains" (substring) test.
3. Categories are tried in the order they appear in the dictionary
   file; the **first** category with a matching keyword wins. This
   makes the process fully deterministic given a fixed dictionary --
   if a description could match more than one category, put the more
   specific category earlier in the JSON file.
4. If nothing matches, ``Categoria`` is set to the fallback category.
   This flags the row for review, and because rule 1 only protects
   *non-fallback* labels, rerunning this script after extending the
   dictionary automatically retries every row still sitting in the
   fallback category.
5. Every value written to ``Categoria`` -- kept, matched, or
   fallback -- is lowercased before writing.

The dictionary is expected to live at the root of the account, as
``CATEGORIAS_{bank}_{account}.json``:

.. code-block:: json

    {
      "mercado": ["zaffari", "nacional", "carrefour", "asun", "bistek"],
      "transporte": ["uber"],
      "combustivel": ["posto"],
      "viagem": ["air b n b", "airbnb"]
    }

.. note::

    Some statement parsers (notably ``CashFlowBBPP``) pre-fill
    ``Categoria`` with the raw bank description instead of leaving it
    empty. Since that value is neither empty nor the fallback
    category, rule 1 means this script will never re-match those rows
    against the dictionary -- it will still lowercase the existing
    value (rule 5), but that's the only change they'll see.

Report
------

Builds a 12-row monthly panel (Jan-Dec of the target year, zero-filled
for months with no data -- including future months) with one column
per category, plus ``Fluxo``/``Entradas``/``Saidas``/``Saldo``; and a
yearly summary with each category's total, average, and share of total
inflows. Prints both to the screen (wrapped to a fixed width so wide
category lists don't overflow the terminal) plus a dedicated line
calling out the fallback category's share of total spending, and
exports both tables as CSV into the target year's folder.

.. note::

    Just like ``cashflow.py``, the report phase loads *every* T1 file
    before filtering, rather than only the files sitting in the target
    year's folder -- some statement types (e.g. Nubank credit card
    invoices) file transactions from the tail of the previous year
    under the current year's folder, and filtering by folder instead
    of by the real ``Data`` value would silently misplace that
    spillover.

.. note::

    With ``--dry-run``, phase 1 doesn't write anything to disk, but
    phase 2's report still reflects what *would* have been written --
    it's built from the in-memory labeled data for files this run
    touched, plus the current on-disk data for any files outside the
    ``--year`` scope. This makes ``--dry-run`` a genuine preview of the
    report you'd get if you dropped the flag.

Outputs
-------

::

    {bank}/                             # Bank
    └── {account}/                      # Bank account
        ├── CATEGORIAS_{BANK}_{ACCOUNT}.json    # keyword dictionary (input)
        └── {year}/
            ├── EXTRATO_..._T1.csv                            # updated in place
            ├── RESUMO_CATEGORIAS_{BANK}_{ACCOUNT}_{year}_MENSAL.csv
            └── RESUMO_CATEGORIAS_{BANK}_{ACCOUNT}_{year}_ANUAL.csv

Script Examples
----------------

.. dropdown:: Minimal shell example (Linux)
    :icon: code-square
    :open:

    .. code-block:: bash

        #!/usr/bin/env bash

        # ! Warning -- change paths and parameters

        REPO="/path/to/repo"
        SCRIPT="$REPO/babilonia/tools/categorize.py"
        DATA="/data/bank_statements/bb/cc"

        # relabel full history, report on the current year
        python "$SCRIPT" --folder "$DATA" --type "bb-cc"

        # preview only, focused on one year
        python "$SCRIPT" --folder "$DATA" --type "bb-cc" --year 2025 --dry-run
"""


# IMPORTS
# ***********************************************************************
# import modules from other libs

# Native imports
# =======================================================================
import glob
import json
import argparse
import unicodedata
from pathlib import Path
from datetime import datetime
from collections import Counter

# ... {develop}

# External imports
# =======================================================================
import pandas as pd

# ... {develop}

# Project-level imports
# =======================================================================
from babilonia.tools.core import *

# ... {develop}
# Deliberately NOT importing babilonia.accounting -- see module docstring.

# CONSTANTS
# ***********************************************************************

# Columns never included in the categorization search text. Every
# other column in the row is concatenated instead -- this makes
# matching schema-agnostic. Categoria itself is excluded too, since
# it's the target being written, not a description field.
EXCLUDE_COLUMNS = ["Data", "Valor", "Categoria"]

DEFAULT_FALLBACK_CATEGORY = "outros"
DEFAULT_SCREEN_WIDTH = 120

# Fixed columns of the monthly report panel -- everything else in it
# is a dynamically-added per-category column.
PANNEL_FIXED_COLUMNS = {"Ano", "Mes", "Fluxo", "Entradas", "Saidas", "Saldo"}

# Aggregate rows in the yearly summary that are not real categories.
SUMMARY_AGGREGATE_ROWS = {"ENTRADAS", "SAIDAS"}


# FUNCTIONS
# ***********************************************************************


def get_combined_arguments():
    parser = argparse.ArgumentParser(
        description="Categorize T1 bank statement files, then report on them."
    )
    parser.add_argument(
        "--folder",
        required=True,
        help="Root account folder (e.g. .../bb/cc). Also where "
        "CATEGORIAS_{bank}_{account}.json is expected to live.",
    )
    parser.add_argument(
        "--type",
        required=True,
        help="Statement type, e.g. bb-cc, nu-cc",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Focus year for both phases -- see module docstring for the "
        "exact (and slightly different, by design) meaning in each phase.",
    )
    parser.add_argument(
        "--dict",
        dest="dict_path",
        default=None,
        help="Override path to the CATEGORIAS_*.json dictionary "
        "(default: {folder}/CATEGORIAS_{BANK}_{ACCOUNT}.json)",
    )
    parser.add_argument(
        "--fallback-category",
        dest="fallback_category",
        default=DEFAULT_FALLBACK_CATEGORY,
        help=f"Category assigned when no rule matches, and whose share of "
        f"spending gets called out in the report (default: "
        f"'{DEFAULT_FALLBACK_CATEGORY}')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write any T1 file; the report still previews the "
        "result (see module docstring)",
    )
    parser.add_argument(
        "--top-n",
        dest="top_n",
        type=int,
        default=None,
        help="Limit the on-screen category list to the top N by absolute "
        "amount (default: show all categories)",
    )
    parser.add_argument(
        "--screen-width",
        dest="screen_width",
        type=int,
        default=DEFAULT_SCREEN_WIDTH,
        help=f"Character width to wrap wide tables to on screen "
        f"(default: {DEFAULT_SCREEN_WIDTH}). Doesn't affect the CSV export.",
    )
    parser.add_argument(
        "--initial-cash",
        dest="initial_cash",
        type=float,
        default=0.0,
        help="Initial balance for the running Saldo column (default: 0.0)",
    )
    return parser.parse_args()


# --- categorization phase -------------------------------------------------


def strip_accents(text):
    """
    Remove diacritics from a string (e.g. ``"combustível"`` -> ``"combustivel"``).
    """
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def normalize_text(text):
    """
    Normalize text for matching: lowercase, accents stripped.
    """
    return strip_accents(str(text)).lower()


def load_categories_dict(dict_path):
    """
    Load the keyword dictionary from a ``CATEGORIAS_*.json`` file.
    """
    if not dict_path.exists():
        raise FileNotFoundError(
            f"Categories dictionary not found: {dict_path}\n"
            f"Expected a JSON file mapping category -> list of keywords, e.g.\n"
            f'  {{"mercado": ["zaffari", "carrefour"], "transporte": ["uber"]}}'
        )
    with open(dict_path, "r", encoding="utf-8") as f:
        dc_categories = json.load(f)
    return dc_categories


def validate_categories_dict(dc_categories):
    """
    Detect keywords that appear under more than one category. Since the
    first matching category wins, a duplicated keyword is a silent
    ambiguity rather than an error -- this only warns.
    """
    seen = {}
    warnings = []
    for category, keywords in dc_categories.items():
        for kw in keywords:
            key = normalize_text(kw)
            if key in seen and seen[key] != category:
                warnings.append(
                    f"keyword '{kw}' appears under both '{seen[key]}' and "
                    f"'{category}' -- '{seen[key]}' wins (declared first)"
                )
            else:
                seen.setdefault(key, category)
    return warnings


def build_search_text(row, exclude_columns=EXCLUDE_COLUMNS):
    """
    Concatenate every column of a row except the excluded ones.
    """
    parts = []
    for col in row.index:
        if col in exclude_columns:
            continue
        val = row[col]
        if pd.notna(val) and str(val).strip():
            parts.append(str(val))
    return normalize_text(" ".join(parts))


def match_category(search_text, dc_categories):
    """
    Return the first category (in dictionary order) whose keyword is
    contained in ``search_text``, or ``None`` if nothing matches.
    """
    for category, keywords in dc_categories.items():
        for kw in keywords:
            if normalize_text(kw) in search_text:
                return category
    return None


def categorize_dataframe(df, dc_categories, fallback_category):
    """
    Apply the categorization rules to a single T1 dataframe.

    :return: Tuple of (updated Categoria list, stats dict, list of
        search texts that fell back to ``fallback_category``)
    :rtype: tuple
    """
    fallback_norm = fallback_category.strip().lower()

    new_categoria = []
    ls_fallback_texts = []
    stats = {"untouched": 0, "matched": 0, "fallback": 0}

    # Row-by-row on purpose: this is a labeling step whose correctness
    # matters more than raw speed, and personal-finance-sized CSVs make
    # the performance difference irrelevant.
    for _, row in df.iterrows():
        current = "" if pd.isna(row["Categoria"]) else str(row["Categoria"]).strip()

        if current and current.lower() != fallback_norm:
            new_categoria.append(current.lower())
            stats["untouched"] += 1
            continue

        search_text = build_search_text(row)
        match = match_category(search_text, dc_categories)

        if match is not None:
            new_categoria.append(match.lower())
            stats["matched"] += 1
        else:
            new_categoria.append(fallback_norm)
            stats["fallback"] += 1
            ls_fallback_texts.append(search_text)

    return new_categoria, stats, ls_fallback_texts


def run_categorize_phase(
    data_type, data_folder, year_arg, dc_categories, fallback_category, dry_run, char_w
):
    """
    Categorize every matching T1 file, printing a per-file summary.

    :return: Tuple of (labeled dataframes, their file paths, aggregate stats)
    :rtype: tuple
    """
    pattern_files = get_file_pattern_statement_t0(data_type, data_folder, year_arg)
    pattern_files = pattern_files.replace("T0.csv", "T1.csv")
    ls_files = sorted(set(glob.glob(pattern_files)))

    print(" PHASE 1 -- Categorize")
    print("-" * char_w)

    if not ls_files:
        print(" No input files found for this scope.")
        return [], [], {"untouched": 0, "matched": 0, "fallback": 0}

    total_stats = {"untouched": 0, "matched": 0, "fallback": 0}
    ls_all_fallback_texts = []
    ls_dfs_labeled = []
    total_files_written = 0

    for i, f in enumerate(ls_files, start=1):
        fpath = Path(f)
        df = pd.read_csv(fpath, sep=";", dtype=str, keep_default_na=False)

        if "Categoria" not in df.columns:
            print(f"[{i:02d}] {fpath.name} -> SKIPPED (no Categoria column)")
            continue

        new_categoria, stats, ls_fallback_texts = categorize_dataframe(
            df, dc_categories, fallback_category
        )
        df["Categoria"] = new_categoria

        for k in total_stats:
            total_stats[k] += stats[k]
        ls_all_fallback_texts.extend(ls_fallback_texts)

        print(
            f"[{i:02d}] {fpath.name} -> "
            f"matched={stats['matched']:>4} "
            f"fallback={stats['fallback']:>4} "
            f"untouched={stats['untouched']:>4}"
        )

        if not dry_run:
            df.to_csv(fpath, sep=";", index=False)
            total_files_written += 1

        ls_dfs_labeled.append(df)

    total_rows = sum(total_stats.values())
    print()
    print(f" Files processed : {len(ls_files)}")
    print(
        f" Files written   : {total_files_written if not dry_run else 0} "
        f"{'(dry run -- no files written)' if dry_run else ''}"
    )
    print(f" Rows total      : {total_rows}")
    print(f" Rows matched    : {total_stats['matched']}")
    print(f" Rows -> {fallback_category:<10}: {total_stats['fallback']}")
    print(f" Rows untouched  : {total_stats['untouched']}")

    if ls_all_fallback_texts:
        print(f"\n Top uncategorized descriptions (-> '{fallback_category}'):")
        counts = Counter(t for t in ls_all_fallback_texts if t)
        for text, n in counts.most_common(10):
            print(f"   [{n:>3}x] {text}")

    return ls_dfs_labeled, ls_files, total_stats


# --- report phase -----------------------------------------------------


def format_currency(x):
    """
    Format a number as a right-aligned, sign-suffixed currency string.
    """
    value = float(x)
    sign = "+" if value >= 0 else "-"
    return f"{abs(value):>11,.2f} {sign}"


def format_currency_columns(df, columns):
    """
    Return a copy of df with selected numeric columns formatted as strings.
    """
    out = df.copy()
    for col in columns:
        out[col] = out[col].map(format_currency)
    return out


def gather_report_data(data_type, data_folder, ls_dfs_labeled, ls_files_processed):
    """
    Assemble the full-history dataframe the report needs: the
    just-labeled data (in memory, whether or not it was written to
    disk) for files this run touched, plus the current on-disk data
    for every other T1 file the categorize phase's ``--year`` scope
    excluded. This guarantees the report always sees full history for
    correct spillover-safe yearly bucketing, and reflects a dry run
    accurately.

    :return: Concatenated dataframe with Data as datetime and Valor as float
    :rtype: pandas.DataFrame or None
    """
    all_pattern = get_file_pattern_statement_t0(data_type, data_folder, None)
    all_pattern = all_pattern.replace("T0.csv", "T1.csv")
    ls_all_files_raw = sorted(glob.glob(all_pattern))
    ls_all_files = sorted(set(ls_all_files_raw))

    if len(ls_all_files_raw) != len(ls_all_files):
        seen = {}
        for f in ls_all_files_raw:
            seen[f] = seen.get(f, 0) + 1
        dupes = {f: n for f, n in seen.items() if n > 1}
        print(" WARNING -- glob matched the same file more than once:")
        for f, n in dupes.items():
            print(f"   - {f} (matched {n}x)")
        print(" Deduplicated before loading -- but this points to an overly")
        print(" broad pattern; worth checking get_file_pattern_statement_t0().")

    if not ls_all_files:
        return None

    processed = set(ls_files_processed)
    remaining_files = sorted(set(ls_all_files) - processed)

    ls_dfs = list(ls_dfs_labeled)
    for f in remaining_files:
        df = pd.read_csv(f, sep=";", dtype=str, keep_default_na=False)
        ls_dfs.append(df)

    if not ls_dfs:
        return None

    df_all = pd.concat(ls_dfs).reset_index(drop=True)
    df_all["Data"] = pd.to_datetime(df_all["Data"])
    df_all["Valor"] = df_all["Valor"].astype(float)

    # Diagnostic only -- never auto-dropped. See categorize_dataframe's
    # docstring reasoning: legitimate same-day, same-amount duplicates
    # exist, so this is surfaced for a human to judge.
    dup_key_cols = [c for c in ("Data", "Valor", "Descricao") if c in df_all.columns]
    if dup_key_cols:
        dup_counts = df_all.groupby(dup_key_cols).size()
        dup_counts = dup_counts[dup_counts > 1]
        if not dup_counts.empty:
            n_dup_rows = int(dup_counts.sum())
            ratio = n_dup_rows / len(df_all) * 100
            print(
                f"\n NOTE -- {len(dup_counts)} distinct transaction(s) appear "
                f"more than once ({n_dup_rows}/{len(df_all)} rows, {ratio:.1f}%)."
            )
            print(
                " This can be legitimate (e.g. two identical same-day charges) "
                "or a sign the same statement was loaded from more than one file."
            )
            print(" Worst offenders:")
            for key, n in dup_counts.sort_values(ascending=False).head(5).items():
                key_str = ", ".join(f"{c}={v}" for c, v in zip(dup_key_cols, key))
                print(f"   [{n}x] {key_str}")

    return df_all


def build_year_report(df_all, target_year, initial_cash=0.0):
    """
    Build the monthly panel and yearly category summary for one year
    using plain pandas groupby/pivot -- a single aggregation pass per
    table, so a category with both inflow and outflow rows can't
    produce a column collision or a double-counted total.

    The monthly panel always has exactly 12 rows (Jan-Dec of
    ``target_year``); months with no data are zero-filled, not omitted.

    :return: Dictionary with "Pannel" (monthly) and "Summary" (yearly)
    :rtype: dict
    """
    df = df_all[df_all["Data"].dt.year == target_year].copy()
    df["Mes"] = df["Data"].dt.strftime("%Y-%m")

    full_months = (
        pd.date_range(f"{target_year}-01-01", f"{target_year}-12-01", freq="MS")
        .strftime("%Y-%m")
        .tolist()
    )

    entradas = df.loc[df["Valor"] >= 0].groupby("Mes")["Valor"].sum()
    saidas = df.loc[df["Valor"] < 0].groupby("Mes")["Valor"].sum()

    df_pannel = pd.DataFrame(index=pd.Index(full_months, name="Mes"))
    df_pannel["Entradas"] = entradas.reindex(full_months, fill_value=0.0)
    df_pannel["Saidas"] = saidas.reindex(full_months, fill_value=0.0)
    df_pannel["Fluxo"] = df_pannel["Entradas"] + df_pannel["Saidas"]

    has_category = "Categoria" in df.columns and df["Categoria"].notna().any()
    if has_category:
        pivot = df.pivot_table(
            index="Mes",
            columns="Categoria",
            values="Valor",
            aggfunc="sum",
            fill_value=0.0,
        )
        pivot = pivot.reindex(full_months, fill_value=0.0)
        df_pannel = df_pannel.join(pivot, how="left").fillna(0.0)
        ls_categories = list(pivot.columns)
    else:
        ls_categories = []

    df_pannel["Saldo"] = initial_cash + df_pannel["Fluxo"].cumsum()

    df_pannel = df_pannel.reset_index()
    df_pannel.insert(0, "Ano", target_year)
    df_pannel = df_pannel[
        ["Ano", "Mes", "Fluxo", "Entradas", "Saidas"] + ls_categories + ["Saldo"]
    ]
    df_pannel = df_pannel.round(2)

    total_entradas = df_pannel["Entradas"].sum()
    total_saidas = df_pannel["Saidas"].sum()
    media_entradas = df_pannel["Entradas"].mean()
    media_saidas = df_pannel["Saidas"].mean()

    rows_summary = [
        {
            "Ano": target_year,
            "Categoria": "ENTRADAS",
            "Total": total_entradas,
            "Media": media_entradas,
            "% Entradas": 100.0,
        },
        {
            "Ano": target_year,
            "Categoria": "SAIDAS",
            "Total": total_saidas,
            "Media": media_saidas,
            "% Entradas": (
                abs(total_saidas) / total_entradas * 100 if total_entradas != 0 else 0.0
            ),
        },
    ]
    for cat in ls_categories:
        total_cat = df_pannel[cat].sum()
        media_cat = df_pannel[cat].mean()
        pct_cat = abs(total_cat) / total_entradas * 100 if total_entradas != 0 else 0.0
        rows_summary.append(
            {
                "Ano": target_year,
                "Categoria": cat,
                "Total": total_cat,
                "Media": media_cat,
                "% Entradas": pct_cat,
            }
        )

    df_summary = pd.DataFrame(rows_summary).round(2)

    return {"Pannel": df_pannel, "Summary": df_summary}


def get_sorted_categories(df_summary, limit=None):
    """
    Return the real categories (excluding ENTRADAS/SAIDAS), sorted by
    absolute total amount, descending.
    """
    df_cats = df_summary[~df_summary["Categoria"].isin(SUMMARY_AGGREGATE_ROWS)].copy()
    df_cats["__AbsTotal"] = df_cats["Total"].abs()
    df_cats = df_cats.sort_values("__AbsTotal", ascending=False).drop(
        columns="__AbsTotal"
    )
    return df_cats.head(limit) if limit else df_cats


def print_fallback_highlight(df_summary, fallback_category):
    """
    Print the fallback category's total and its share of total Saidas.
    """
    df_cats = df_summary[~df_summary["Categoria"].isin(SUMMARY_AGGREGATE_ROWS)]
    row = df_cats[df_cats["Categoria"].str.lower() == fallback_category.lower()]

    if row.empty:
        print(
            f"\n No '{fallback_category}' transactions this year -- fully categorized."
        )
        return

    total_fallback = row["Total"].iloc[0]
    total_saidas_rows = df_summary.loc[df_summary["Categoria"] == "SAIDAS", "Total"]
    total_saidas = total_saidas_rows.iloc[0] if not total_saidas_rows.empty else 0.0
    share = abs(total_fallback) / abs(total_saidas) * 100 if total_saidas != 0 else 0.0

    marker = "!!" if share >= 15 else ("!" if share >= 5 else "-")
    print(
        f"\n [{marker}] '{fallback_category}' = "
        f"{format_currency(total_fallback)}  "
        f"({share:.1f}% of total Saidas, {format_currency(total_saidas)})"
    )
    if share >= 15:
        print(f"      -> consider adding more keywords to the dictionary.")


def run_report_phase(
    df_all,
    target_year,
    year_arg_given,
    fallback_category,
    top_n,
    screen_width,
    initial_cash,
    bank,
    account,
    data_folder,
    char_w,
):
    """
    Build, print, and export the category report for target_year.
    """
    print()
    print(" PHASE 2 -- Report")
    print("-" * char_w)

    if df_all is None:
        print(" No T1 files found. Nothing to report.")
        return

    if not (df_all["Data"].dt.year == target_year).any():
        print(
            f" No transactions found for {target_year} yet -- showing an "
            f"all-zero calendar."
        )

    dc_report = build_year_report(df_all, target_year, initial_cash=initial_cash)
    df_pannel = dc_report["Pannel"]
    df_summary = dc_report["Summary"]

    category_cols = [c for c in df_pannel.columns if c not in PANNEL_FIXED_COLUMNS]
    cols_to_format_pannel = ["Entradas", "Saidas", "Fluxo", "Saldo"] + category_cols

    print()
    print(f" {target_year} -- Monthly Panel by Category")
    print("-" * char_w)
    df_pretty = format_currency_columns(df_pannel, columns=cols_to_format_pannel)
    df_screen = df_pretty.drop(columns="Ano").set_index("Mes")
    with pd.option_context("display.width", screen_width, "display.max_columns", None):
        print(df_screen)

    df_cats = get_sorted_categories(df_summary, limit=top_n)
    label = f"Top {top_n}" if top_n else "All"
    print()
    print(f" {target_year} -- {label} Categories (by absolute amount)")
    print("-" * char_w)
    df_cats_pretty = format_currency_columns(df_cats, columns=["Total", "Media"])
    with pd.option_context("display.width", screen_width, "display.max_columns", None):
        print(df_cats_pretty.drop(columns="Ano").set_index("Categoria"))

    print_fallback_highlight(df_summary, fallback_category)

    name = f"RESUMO_CATEGORIAS_{bank.upper()}_{account.upper()}_{target_year}"

    file_mensal = data_folder / f"{target_year}/{name}_MENSAL.csv"
    file_mensal.parent.mkdir(parents=True, exist_ok=True)
    df_pannel.to_csv(file_mensal, sep=";", index=False)

    file_anual = data_folder / f"{target_year}/{name}_ANUAL.csv"
    file_anual.parent.mkdir(parents=True, exist_ok=True)
    df_summary.to_csv(file_anual, sep=";", index=False)

    print(f"\n Output : {file_mensal}")
    print(f" Output : {file_anual}")


def main():

    char_w = 150

    args = get_combined_arguments()

    data_folder = Path(args.folder)
    data_type = args.type.lower()
    year_arg = args.year
    dry_run = args.dry_run
    fallback_category = args.fallback_category
    target_year = args.year if args.year is not None else datetime.now().year

    bank = get_bank(data_type)
    account = get_account(data_type)

    dict_path = (
        Path(args.dict_path)
        if args.dict_path
        else data_folder / f"CATEGORIAS_{bank.upper()}_{account.upper()}.json"
    )

    print("\n\n")
    print("=" * char_w)
    print(" Categorize & Report\n".upper())
    print(f" Folder      : {data_folder}")
    print(f" Bank        : {BANK_NAMES[data_type]}")
    print(f" Account     : {ACCOUNT_NAMES[data_type]}")
    print(
        f" Categorize  : {'year ' + str(year_arg) if year_arg is not None else 'ALL years'}"
    )
    print(
        f" Report year : {target_year} {'(current year)' if year_arg is None else ''}"
    )
    print(f" Dictionary  : {dict_path}")
    print(f" Fallback    : {fallback_category}")
    print(f" Dry run     : {dry_run}")
    print("=" * char_w)
    print()

    dc_categories = load_categories_dict(dict_path)
    ls_warnings = validate_categories_dict(dc_categories)
    if ls_warnings:
        print(" WARNING -- ambiguous keywords found in dictionary:")
        for w in ls_warnings:
            print(f"   - {w}")
    print(f" Categories loaded: {len(dc_categories)}\n")

    ls_dfs_labeled, ls_files_processed, _ = run_categorize_phase(
        data_type,
        data_folder,
        year_arg,
        dc_categories,
        fallback_category,
        dry_run,
        char_w,
    )

    df_all = gather_report_data(
        data_type, data_folder, ls_dfs_labeled, ls_files_processed
    )

    run_report_phase(
        df_all,
        target_year,
        year_arg is not None,
        fallback_category,
        args.top_n,
        args.screen_width,
        args.initial_cash,
        bank,
        account,
        data_folder,
        char_w,
    )

    print()
    print("=" * char_w)
    print("\n\n")
    return None


# SCRIPT
# ***********************************************************************
# standalone behaviour as a script
if __name__ == "__main__":
    main()

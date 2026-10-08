# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2025 The Project Authors
# See pyproject.toml for authors/maintainers.
# See LICENSE for license details.
"""
Core constants and functions for the ``babilonia.tools`` package.

"""

# IMPORTS
# ***********************************************************************
# import modules from other libs

# Native imports
# =======================================================================
import sys
import glob
import argparse
import pprint
import contextlib
from pathlib import Path

# ... {develop}

# External imports
# =======================================================================
import pandas as pd

# ... {develop}

# Project-level imports
# =======================================================================
# import {module}
from babilonia.accounting import (
    CashFlowBBCC,
    CashFlowBBCCPJ,
    CashFlowBBPP,
    BBCDB,
    CashFlowNUCredit,
)

# ... {develop}

# CONSTANTS
# ***********************************************************************

PARSERS = {
    "bb-cc": CashFlowBBCC,
    "bb-pp": CashFlowBBPP,
    "bb-ccpj": CashFlowBBCCPJ,
    "bb-cdb": BBCDB,
    "nubank-credito": CashFlowNUCredit,
}

BANK_NAMES = {
    "bb-cc": "Banco do Brasil",
    "bb-pp": "Banco do Brasil",
    "bb-ccpj": "Banco do Brasil",
    "bb-cdb": "Banco do Brasil",
    "nubank-credito": "Nubank",
}

ACCOUNT_NAMES = {
    "bb-cc": "Conta Corrente PF",
    "bb-pp": "Conta Poupança PF",
    "bb-ccpj": "Conta Corrente PJ",
    "bb-cdb": "Aplicação CDB",
    "nubank-credito": "Crédito",
}

# CLASSES
# ***********************************************************************


class TeeWriter:
    """
    File-like object that duplicates writes across several streams.

    :param streams: Writable file-like objects to fan writes out to.
    :type streams: typing.TextIO
    """

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        """
        Write ``data`` to every stream.

        :param data: Text to write.
        :type data: str
        :return: None
        :rtype: None
        """
        for stream in self.streams:
            stream.write(data)
        return None

    def flush(self):
        """
        Flush every stream.

        :return: None
        :rtype: None
        """
        for stream in self.streams:
            stream.flush()
        return None


# FUNCTIONS
# ***********************************************************************


@contextlib.contextmanager
def tee_stdout(file_handle):
    """
    Temporarily duplicate everything printed to ``stdout`` into ``file_handle``.

    Used to produce a ``.txt`` report that is guaranteed to match the
    terminal output for the same block of code, without reformatting
    anything a second time.

    :param file_handle: Writable text file object to receive a copy of
        everything printed while the context is active.
    :type file_handle: typing.TextIO
    :return: None
    :rtype: None
    """
    original_stdout = sys.stdout
    sys.stdout = TeeWriter(original_stdout, file_handle)
    try:
        yield
    finally:
        sys.stdout = original_stdout


def preview_df(df, row_max=20):
    """
    Displays a preview of a DataFrame with a specified maximum number of rows.

    :param df: The dataset to be displayed
    :type df: :class:`pandas.DataFrame`
    :param row_max: The maximum number of rows to show in the console. Default value = ``20``
    :type row_max: int
    :return: None
    :rtype: None
    """
    with pd.option_context("display.max_rows", row_max):
        print(df)
    return None


def concat_dfs(ls_files):
    """
    Reads multiple CSV files and concatenates them into a single DataFrame.

    :param ls_files: A list of file paths to be read
    :type ls_files: list
    :return: A unified DataFrame containing data from all provided files
    :rtype: :class:`pandas.DataFrame`

    .. note::

        This function reads each file using ``;`` as a separator and forces all columns to ``str``
        type to avoid type inference issues during concatenation.
        The resulting index is reset and the old index is dropped.

    """

    ls_dfs = []
    for f in ls_files:
        df = pd.read_csv(f, sep=";", dtype=str)
        ls_dfs.append(df)
    df_full = pd.concat(ls_dfs).reset_index(drop=True)
    return df_full


def build_subtotal_rows(
    df,
    columns,
    sum_columns,
    label_column,
    formatters=None,
    subtotal_label="SUBTOTAL",
    average_label="MEDIA",
    n_periods=12,
):
    """
    Build a subtotal row and an average row for a monthly table.

    Only ``sum_columns`` are summed (subtotal) and divided by
    ``n_periods`` (average); every other column is left blank on both
    rows. This is the right default for a running/cumulative column
    (e.g. a balance), where a sum across periods has no real meaning.

    :param df: Monthly table to summarize, one row per period, with
        raw (not yet display-formatted) numeric values.
    :type df: pandas.DataFrame
    :param columns: Column order for the returned rows -- normally
        ``df.columns``, kept explicit so the caller controls it.
    :type columns: list
    :param sum_columns: Columns to sum and average.
    :type sum_columns: list
    :param label_column: Column that carries the row label.
    :type label_column: str
    :param formatters: Optional mapping of column name to a formatting
        callable, applied to that column's subtotal/average value.
        Columns not listed fall back to ``str``.
    :type formatters: dict, optional
    :param subtotal_label: Label written to ``label_column`` on the subtotal row.
    :type subtotal_label: str
    :param average_label: Label written to ``label_column`` on the average row.
    :type average_label: str
    :param n_periods: Divisor used for the average row.
    :type n_periods: int
    :return: Two-row DataFrame, ready to ``pandas.concat`` onto a
        display-formatted version of ``df``.
    :rtype: pandas.DataFrame
    """
    formatters = formatters or {}
    subtotal = df[sum_columns].sum()
    average = subtotal / n_periods

    row_subtotal = {col: "" for col in columns}
    row_average = {col: "" for col in columns}
    row_subtotal[label_column] = subtotal_label
    row_average[label_column] = average_label
    for col in sum_columns:
        fmt = formatters.get(col, str)
        row_subtotal[col] = fmt(subtotal[col])
        row_average[col] = fmt(average[col])

    return pd.DataFrame([row_subtotal, row_average], columns=columns)


def get_bank(data_type):
    """
    Extracts the bank name from a formatted data type string.

    :param data_type: The string containing bank and account info separated by a hyphen
    :type data_type: str
    :return: The extracted bank name
    :rtype: str
    """
    return data_type.split("-")[0]


def get_account(data_type):
    """
    Extracts the account identifier from a formatted data type string.

    :param data_type: The string containing bank and account info separated by a hyphen
    :type data_type: str
    :return: The extracted account identifier
    :rtype: str
    """
    return data_type.split("-")[1]


def get_file_pattern_statement_t0(data_type, folder, year=None):
    """
    Constructs a glob-style file path pattern for bank statement CSV files.

    :param data_type: The string containing bank and account info separated by a hyphen
    :type data_type: str
    :param folder: The base directory path where files are located
    :type folder: str
    :param year: [optional] The specific year to filter files. Default value = ``None``
    :type year: int
    :return: A formatted raw string representing the file search pattern
    :rtype: str

    .. note::

        If ``year`` is not provided, the function uses a wildcard ``*`` to match all available year directories. The resulting pattern follows the naming convention: ``EXTRATO_{BANK}_{ACCOUNT}_*_T0.csv``.

    """
    if year is None:
        year = "*"
    return rf"{folder}\{year}\EXTRATO_{get_bank(data_type).upper()}_{get_account(data_type).upper()}_*_T0.csv"


def get_file_pattern_cashflow_daily(data_type, folder, year=None):
    if year is None:
        year = "*"
    return rf"{folder}\{year}\CAIXA_{get_bank(data_type).upper()}_{get_account(data_type).upper()}_*_DIARIO.csv"


def get_arguments():
    """
    Parses command-line arguments for the Babilonia utilities.

    :return: An object containing the parsed arguments: ``folder``, ``type``, and ``year``
    :rtype: :class:`argparse.Namespace`

    The function handles the following arguments:
    * ``-f`` / ``--folder``: Path to the target processing directory.
    * ``-t`` / ``--type``: The specific account type string.
    * ``-y`` / ``--year``: The integer year to filter processing (defaults to ``None``).
    """
    # 1. Initialize the Parser
    parser = argparse.ArgumentParser(
        description="Parse parameters for babilonia utils.",
    )

    # 2. Add Arguments

    # Positional argument (Required)
    parser.add_argument(
        "-f", "--folder", help="The path to folder you want to process."
    )
    parser.add_argument("-t", "--type", help="The type of account.")

    # Optional argument (Integer)
    parser.add_argument("-y", "--year", type=int, default=None, help="Year to process")

    # 3. Parse the Arguments
    args = parser.parse_args()

    return args


# SCRIPT
# ***********************************************************************
# standalone behaviour as a script
if __name__ == "__main__":
    print("hello world!")

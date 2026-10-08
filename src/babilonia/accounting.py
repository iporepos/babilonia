# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2025 The Project Authors
# See pyproject.toml for authors/maintainers.
# See LICENSE for license details.
"""
Brazil-specific accounting classes and tax reference constants.

Provides data classes for parsing and analyzing bank statements from
Banco do Brasil and Nubank, computing cash flow summaries, managing
budget records, and loading NFSe XML invoices. Module-level constants
hold the 2025 INSS and IRRF progressive tax tables.
"""
# IMPORTS
# ***********************************************************************
# import modules from other libs

# Native imports
# =======================================================================
import os
import json
import xml.etree.ElementTree as ET

# ... {develop}

# External imports
# =======================================================================
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
from matplotlib.gridspec import GridSpec

# ... {develop}

# Project-level imports
# =======================================================================
from babilonia.root import *

# ... {develop}


# CONSTANTS
# ***********************************************************************
# define constants in uppercase

# CONSTANTS -- Project-level
# =======================================================================

# Portaria Interministerial MPS/MF nº 6
TABELA_INSS_2025 = [(1518.00, 0.075), (2793.88, 0.09), (4190.83, 0.12), (8157.41, 0.14)]

# MEDIDA PROVISÓRIA Nº 1.294, DE 11 DE ABRIL DE 2025
TABELA_IRRF_2025 = [
    (2428.81, 2826.65, 0.075, 182.16),
    (2826.66, 3751.05, 0.15, 394.16),
    (3751.06, 4664.68, 0.225, 675.49),
    (4664.68, float("inf"), 0.275, 908.73),
]

# CONSTANTS -- Module-level
# =======================================================================
MM_PER_INCH = 25.4

# every tunable part of plot_cashflow_bars(), plus the tool's report
# language, all overridable via cashflow.json (see CashFlow.load_plot_config)
# -- figsize in mm, converted to inches for matplotlib at plot time
PLOT_CONFIG_DEFAULTS = {
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
    "hist_bin_size": None,
    "color_hist": None,
}

# single-letter month labels for compact plot axes ("Jan" -> "J")
MONTH_LETTERS = {
    1: "J",
    2: "F",
    3: "M",
    4: "A",
    5: "M",
    6: "J",
    7: "J",
    8: "A",
    9: "S",
    10: "O",
    11: "N",
    12: "D",
}


# FUNCTIONS
# ***********************************************************************

# FUNCTIONS -- Project-level
# =======================================================================
# ... {develop}

# FUNCTIONS -- Module-level
# =======================================================================
# ... {develop}


# CLASSES
# ***********************************************************************


# CLASSES -- Project-level
# =======================================================================
class Budget(RecordTable):
    """
    A record table for managing budget items.

    Extends :class:`RecordTable` to track revenues and expenses with
    support for contract grouping, payment status, due dates, and file
    attachments. Signed totals and per-status or per-contract summaries
    are recomputed automatically on update.
    """

    def __init__(self, name="MyBudget", alias="Bud"):
        super().__init__(name=name, alias=alias)

        # ------------- specifics attributes ------------- #
        self.total_revenue = None
        self.total_expenses = None
        self.total_net = None
        self.summary_ascend = False

    def _set_fields(self):
        # ------------ call super ----------- #
        super()._set_fields()
        # set temporary util fields
        self.sign_field = "Sign"
        self.value_signed = "Value_Signed"
        # ... continues in downstream objects ... #

    def _set_data_columns(self):
        # Main data columns
        self.columns_data_main = [
            "Type",
            "Status",
            "Contract",
            "Name",
            "Value",
        ]
        # Extra data columns
        self.columns_data_extra = [
            # Status extra
            "Date_Due",
            "Date_Exe",
            # Name extra
            # tags
            "Tags",
            # Values extra
            # Payment details
            "Method",
            "Protocol",
        ]
        # File columns
        self.columns_data_files = [
            "File_Receipt",
            "File_Invoice",
            "File_NF",
        ]
        # concat all lists
        self.columns_data = (
            self.columns_data_main + self.columns_data_extra + self.columns_data_files
        )

        # variations
        self.columns_data_status = self.columns_data_main + [
            self.columns_data_extra[0],
            self.columns_data_extra[1],
        ]

        # ... continues in downstream objects ... #

    def _set_operator(self):
        # ------------- define sub routines here ------------- #
        def func_file_status():
            return FileSys.check_file_status(files=self.data["File"].values)

        def func_update_status():
            # filter relevante data
            df = self.data[["Status", "Method", "Date_Due"]].copy()
            # Convert 'Date_Due' to datetime format
            df["Date_Due"] = pd.to_datetime(self.data["Date_Due"])
            # Get the current date
            current_dt = datetime.datetime.now()

            # Update 'Status' for records with 'Automatic' method and 'Expected' status based on the condition
            condition = (
                (df["Method"] == "Automatic")
                & (df["Status"] == "Expected")
                & (df["Date_Due"] <= current_dt)
            )
            df.loc[condition, "Status"] = "Executed"

            # return values
            return df["Status"].values

        # todo implement all operations
        # ---------------- the operator ---------------- #

        self.operator = {
            "Status": func_update_status,
        }

    def _get_total_expenses(self, filter_df=True):
        filtered_df = self._filter_prospected_cancelled() if filter_df else self.data
        _n = filtered_df[filtered_df["Type"] == "Expense"]["Value_Signed"].sum()
        return round(_n, 3)

    def _get_total_revenue(self, filter_df=True):
        filtered_df = self._filter_prospected_cancelled() if filter_df else self.data
        _n = filtered_df[filtered_df["Type"] == "Revenue"]["Value_Signed"].sum()
        return round(_n, 3)

    def _filter_prospected_cancelled(self):
        return self.data[
            (self.data["Status"] != "Prospected") & (self.data["Status"] != "Cancelled")
        ]

    def update(self):
        super().update()
        if self.data is not None:
            self.total_revenue = self._get_total_revenue(filter_df=True)
            self.total_expenses = self._get_total_expenses(filter_df=True)
            self.total_net = self.total_revenue + self.total_expenses
            if self.total_net > 0:
                self.summary_ascend = False
            else:
                self.summary_ascend = True

        # ... continues in downstream objects ... #
        return None

    def set_data(self, input_df):
        """
        Set RecordTable data from incoming dataframe.
        Expected to be incremented downstream.

        :param input_df: incoming dataframe
        :type input_df: dataframe
        :return: None
        :rtype: None
        """
        super().set_data(input_df=input_df)
        # convert to numeric
        self.data["Value"] = pd.to_numeric(self.data["Value"])
        # compute temporary field

        # sign and value_signed
        self.data["Sign"] = self.data["Type"].apply(
            lambda x: 1 if x == "Revenue" else -1
        )
        self.data["Value_Signed"] = self.data["Sign"] * self.data["Value"]

    def get_summary_by_type(self):
        summary = pd.DataFrame(
            {
                "Total_Expenses": [self.total_expenses],
                "Total_Revenue": [self.total_revenue],
                "Total_Net": [self.total_net],
            }
        )
        summary = summary.apply(
            lambda x: x.sort_values(ascending=self.summary_ascend), axis=1
        )
        return summary

    def get_summary_by_status(self, filter_df=True):
        filtered_df = self._filter_prospected_cancelled() if filter_df else self.data
        return (
            filtered_df.groupby("Status")["Value_Signed"]
            .sum()
            .sort_values(ascending=self.summary_ascend)
        )

    def get_summary_by_contract(self, filter_df=True):
        filtered_df = self._filter_prospected_cancelled() if filter_df else self.data
        return (
            filtered_df.groupby("Contract")["Value_Signed"]
            .sum()
            .sort_values(ascending=self.summary_ascend)
        )

    def get_summary_by_tags(self, filter_df=True):
        filtered_df = self._filter_prospected_cancelled() if filter_df else self.data
        tags_summary = (
            filtered_df.groupby("Tags")["Value_Signed"]
            .sum()
            .sort_values(ascending=self.summary_ascend)
        )
        tags_summary = tags_summary.sort()
        separate_tags_summary = (
            filtered_df["Tags"].str.split(expand=True).stack().value_counts()
        )
        print(type(separate_tags_summary))
        return tags_summary, separate_tags_summary

    @staticmethod
    def parse_annual_budget(year, budget_df, freq_field="Freq"):
        start_date = "{}-01-01".format(year)
        end_date = "{}-01-01".format(int(year) + 1)

        annual_budget = pd.DataFrame()

        for _, row in budget_df.iterrows():
            # Generate date range based on frequency
            dates = pd.date_range(start=start_date, end=end_date, freq=row["Freq"])

            # Replicate the row for each date
            replicated_data = pd.DataFrame(
                {col: [row[col]] * len(dates) for col in df.columns}
            )
            replicated_data["Date_Due"] = dates

            # Append to the expanded budget
            annual_budget = pd.concat(
                [annual_budget, replicated_data], ignore_index=True
            )

        return annual_budget


class CashFlow(DataSet):
    """
    A primitive class for handling Cash flow analysis

    .. dropdown:: Cashflow Analysis Example
        :icon: code-square
        :open:

        .. code-block:: python

            from babilonia.accounting import CashFlow

            # create an empty class
            cf = CashFlow()

            # set the file for CSV
            file_csv = "path/to/file.csv" # [change this]

            # load data
            cf.load_data(file_csv)

            # call method
            dc = cf.cashflow_analysis(df=cf.data, category="Custeio")

            # print data
            print(dc["monthly"])
            print(dc["yearly"])

    """

    def __init__(self, name="CashFlow", alias="CF"):
        super().__init__(name=name, alias=alias)

    def load_data(self, file_data):
        # overwrite relative path inputs
        # ----------------------------------------------
        self.file_data = os.path.abspath(file_data)

        # implement loading logic
        # ----------------------------------------------
        df = pd.read_csv(
            self.file_data,
            sep=self.file_csv_sep,
            encoding=self.file_encoding,
            dtype=str,
        )

        df = df[["Data", "Categoria", "Valor", "Descricao"]].copy()

        # make conversions
        df["Data"] = pd.to_datetime(df["Data"])
        df["Valor"] = df["Valor"].astype(float)

        # post-loading logic
        # ----------------------------------------------
        self.data = df.copy()

        # update other mutables
        # ----------------------------------------------
        self.update()

        # ... continues in downstream objects ... #

    @staticmethod
    def get_cashflow_analysis(df, category=None):
        """
        Perform cash flow analysis with monthly and yearly aggregation.

        This method classifies cash flows into inputs and outputs, aggregates
        values on a monthly and yearly basis, and computes cumulative balances.
        The analysis is fully independent from class state and inheritance
        behavior.

        :param df:
            Input cash flow data containing at least the columns
            ``Data``, ``Categoria`` and ``Valor``.
        :type df: pandas.DataFrame

        :param category:
            Optional category filter. If ``None``, all categories are grouped
            under ``"Geral"``.
        :type category: str or None

        :returns:
            Dictionary with monthly and yearly cash flow summaries.
        :rtype: dict
        """
        df = CashFlow.enrich_time_index(df)
        df = CashFlow.classify_flows(df)
        df, category = CashFlow.filter_category(df, category)

        df_monthly = CashFlow.get_monthly_summary(df, category)
        df_monthly = CashFlow.compute_oir(df_monthly)

        df_yearly = CashFlow.get_yearly_summary(df_monthly, category)
        df_yearly = CashFlow.compute_oir(df_yearly)

        return {
            "monthly": df_monthly.round(decimals=2),
            "yearly": df_yearly.round(decimals=2),
        }

    @staticmethod
    def compute_oir(df, input_field="Entradas", output_field="Saidas"):
        df["OIR"] = df[output_field].abs() / df[input_field].abs()
        df["OIR"] = df["OIR"].fillna(100)
        return df

    @staticmethod
    def enrich_time_index(df):
        """
        Add year and year-month time indices to the cash flow data.

        This method extracts the calendar year and a ``YYYY-MM`` monthly
        identifier from the ``Data`` column.

        :param df:
            Input cash flow data.
        :type df: pandas.DataFrame

        :returns:
            Copy of the input data with additional ``Ano`` and ``Mes`` columns.
        :rtype: pandas.DataFrame
        """
        df = df.copy()
        df["Ano"] = df["Data"].dt.year
        df["Mes"] = df["Data"].dt.strftime("%Y-%m")
        return df

    @staticmethod
    def classify_flows(df):
        """
        Classify cash flows as inputs or outputs.

        Positive or zero values are classified as ``"In"`` and negative values
        as ``"Out"``.

        :param df:
            Cash flow data containing a ``Valor`` column.
        :type df: pandas.DataFrame

        :returns:
            Copy of the input data with an additional ``Flow`` column.
        :rtype: pandas.DataFrame
        """
        df = df.copy()
        df["Flow"] = np.where(df["Valor"] >= 0, "In", "Out")
        return df

    @staticmethod
    def filter_category(df, category):
        """
        Filter cash flow data by category.

        If no category is provided, all records are grouped under the
        default category ``"Geral"``.

        :param df:
            Cash flow data.
        :type df: pandas.DataFrame

        :param category:
            Category name used to filter the data.
        :type category: str or None

        :returns:
            Tuple containing the filtered data and the resolved category name.
        :rtype: tuple
        """
        if category is None:
            return df.copy(), "Geral"

        return df.query("Categoria == @category").copy(), category

    @staticmethod
    def get_monthly_summary(df, category):
        """
        Compute monthly cash flow summaries for each year.

        This method aggregates cash flow inputs and outputs on a monthly basis,
        ensures that all calendar months are present, and computes annual
        cumulative balances.

        :param df:
            Cash flow data enriched with time indices and flow classification.
        :type df: pandas.DataFrame

        :param category:
            Category name associated with the analysis.
        :type category: str

        :returns:
            Monthly cash flow summary table.
        :rtype: pandas.DataFrame
        """
        years = range(df["Ano"].min(), df["Ano"].max() + 1)
        monthly_frames = []

        for year in years:
            calendar = pd.DataFrame(
                {
                    "Ano": str(year),
                    "Mes": [f"{year}-{str(m).zfill(2)}" for m in range(1, 13)],
                    "Categoria": category,
                }
            )

            df_year = df.query("Ano == @year")

            inp = (
                df_year.query("Flow == 'In'")
                .groupby("Mes")["Valor"]
                .agg(Entradas="sum", Entradas_N="count")
                .reset_index()
            )

            out = (
                df_year.query("Flow == 'Out'")
                .groupby("Mes")["Valor"]
                .agg(Saidas="sum", Saidas_N="count")
                .reset_index()
            )

            df_year = (
                calendar.merge(inp, on="Mes", how="left")
                .merge(out, on="Mes", how="left")
                .fillna(0)
            )

            for col in ["Entradas_N", "Saidas_N"]:
                df_year[col] = df_year[col].astype(int)

            # Net flow
            df_year["Fluxo"] = df_year["Entradas"] + df_year["Saidas"]

            df_year["Entradas_Acum"] = df_year["Entradas"].cumsum()
            df_year["Saidas_Acum"] = df_year["Saidas"].cumsum()
            df_year["Fluxo_Acum"] = df_year["Fluxo"].cumsum()

            monthly_frames.append(df_year)

        return pd.concat(monthly_frames, ignore_index=True)

    @staticmethod
    def get_yearly_summary(df_monthly, category):
        """
        Compute yearly cash flow summaries.

        This method aggregates monthly cash flow data into yearly totals and
        computes cumulative balances across years.

        :param df_monthly:
            Monthly cash flow summary table.
        :type df_monthly: pandas.DataFrame

        :param category:
            Category name associated with the analysis.
        :type category: str

        :returns:
            Yearly cash flow summary table.
        :rtype: pandas.DataFrame
        """
        df = (
            df_monthly.groupby("Ano")
            .agg(
                Entradas=("Entradas", "sum"),
                Entradas_N=("Entradas_N", "sum"),
                Saidas=("Saidas", "sum"),
                Saidas_N=("Saidas_N", "sum"),
                Fluxo=("Fluxo", "sum"),
            )
            .reset_index()
        )

        df["Categoria"] = category

        df["Entradas_Acum"] = df["Entradas"].cumsum()
        df["Saidas_Acum"] = df["Saidas"].cumsum()
        df["Fluxo_Acum"] = df["Fluxo"].cumsum()

        return df[
            [
                "Ano",
                "Categoria",
                "Entradas",
                "Entradas_N",
                "Saidas",
                "Saidas_N",
                "Fluxo",
                "Entradas_Acum",
                "Saidas_Acum",
                "Fluxo_Acum",
            ]
        ]

    @staticmethod
    def get_daily_summary(df, year):
        """
        Compute daily Entradas/Saidas totals for every calendar day in ``year``.

        Unlike :meth:`get_monthly_summary`, no category breakdown is kept --
        this is meant for plotting a full-year daily timeseries, where every
        day must be present (as a zero bar) even without transactions.

        :param df:
            Cash flow data containing at least ``Data`` and ``Valor``.
        :type df: pandas.DataFrame

        :param year:
            Calendar year to cover, start to end.
        :type year: int or str

        :returns:
            One row per day of ``year``, with ``Data``, ``Entradas``,
            ``Saidas`` and ``Fluxo`` columns.
        :rtype: pandas.DataFrame
        """
        df = CashFlow.classify_flows(df)

        inp = df.query("Flow == 'In'").groupby(df["Data"].dt.date)["Valor"].sum()
        out = df.query("Flow == 'Out'").groupby(df["Data"].dt.date)["Valor"].sum()

        ls_days = pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31", freq="D")
        df_daily = pd.DataFrame({"Data": ls_days})
        df_daily["Entradas"] = df_daily["Data"].dt.date.map(inp).fillna(0)
        df_daily["Saidas"] = df_daily["Data"].dt.date.map(out).fillna(0)
        df_daily["Fluxo"] = df_daily["Entradas"] + df_daily["Saidas"]

        return df_daily

    @staticmethod
    def get_cashflow_report(df, year=None, initial_cash=None):
        """
        Build a yearly cash flow panel and summary by category.

        :param df:
            Cash flow DataFrame containing transactional data with date,
            category, and value information compatible with the
            ``enrich_time_index``, ``classify_flows``, and
            ``cashflow_analysis`` methods.
        :type df: pandas.DataFrame

        :param year:
            Year to be analyzed. If ``None``, the current calendar year
            (local time) is used.
        :type year: int, optional

        :param initial_cash:
            Initial account balance at the beginning of the selected year.
            If ``None``, defaults to ``0.0``.
        :type initial_cash: float, optional

        :return:
            Dictionary containing: ``"Pannel"``: monthly cash flow panel with totals, per-category
            flows, and running balance. ``"Summary"``: yearly summary by category with total, mean, and
            percentage contribution to total inflows.
        :rtype: dict
        """

        if year is None:
            from datetime import datetime

            year = datetime.now().year

        if initial_cash is None:
            initial_cash = 0.0

        df = CashFlow.enrich_time_index(df)
        df = df.query(f"Ano == {year}").copy()
        df = CashFlow.classify_flows(df)

        has_category = "Categoria" in df.columns and df["Categoria"].notna().any()
        ls_categories = list(df["Categoria"].dropna().unique()) if has_category else []

        dc_cfa = CashFlow.get_cashflow_analysis(df, category=None)
        df_cfa = dc_cfa["monthly"][["Ano", "Mes", "Fluxo", "Entradas", "Saidas"]].copy()

        # One merge per category (net Fluxo), not one per (category, flow-direction)
        # pair -- a category that has both inflow and outflow rows (e.g. a refund
        # tagged the same category as the original charge) previously produced two
        # same-named columns and broke the later df_cfa[ls_categories] lookup.
        for cat in ls_categories:
            dc_cat = CashFlow.get_cashflow_analysis(df, category=cat)
            df_cat = dc_cat["monthly"][["Mes", "Fluxo"]].copy()
            df_cat.rename(columns={"Fluxo": cat}, inplace=True)
            df_cfa = pd.merge(df_cfa, df_cat, how="left", on="Mes")

        df_cfa["Saldo"] = initial_cash + df_cfa["Fluxo"].cumsum()

        total_entradas = df_cfa["Entradas"].sum()
        total_saidas = df_cfa["Saidas"].sum()
        media_entradas = df_cfa["Entradas"].mean()
        media_saidas = df_cfa["Saidas"].mean()

        rows_summary = [
            {
                "Ano": year,
                "Categoria": "ENTRADAS",
                "Total": total_entradas,
                "Media": media_entradas,
                "% Entradas": 100.0,
            },
            {
                "Ano": year,
                "Categoria": "SAIDAS",
                "Total": total_saidas,
                "Media": media_saidas,
                "% Entradas": (
                    abs(total_saidas) / total_entradas * 100
                    if total_entradas != 0
                    else 0.0
                ),
            },
        ]

        if ls_categories:
            totals = df_cfa[ls_categories].sum()
            averages = df_cfa[ls_categories].mean()

            pct_entradas = (
                totals.abs() / total_entradas * 100 if total_entradas != 0 else 0.0
            )

            for cat in ls_categories:
                rows_summary.append(
                    {
                        "Ano": year,
                        "Categoria": cat,
                        "Total": totals[cat],
                        "Media": averages[cat],
                        "% Entradas": pct_entradas[cat],
                    }
                )

        df_summary = pd.DataFrame(rows_summary).round(2)

        return {
            "Pannel": df_cfa,
            "Summary": df_summary,
        }

    @staticmethod
    def format_currency(
        x: float,
    ):
        # todo docstring

        value = float(x)
        sign = "+"
        if value < 0:
            sign = "-"

        return f"{abs(value):>11,.2f} {sign}"  # suffix + f" {value:+,.2f}"

    @staticmethod
    def format_currency_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        """
        Return a copy of df with selected numeric columns formatted as strings.
        """
        out = df.copy()

        for col in columns:
            out[col] = out[col].map(CashFlow.format_currency)

        return out

    @staticmethod
    def format_compact(x, decimals=1):
        """
        Format a value as a compact string, rounding to ``K`` (thousand) or
        ``M`` (million) once the magnitude is too big to annotate as-is.

        :param x: Value to format.
        :type x: float
        :param decimals: Decimal places kept on the ``K``/``M`` value.
        :type decimals: int
        :return: Compact string, e.g. ``"1.2K"``, ``"-3.4M"``, ``"850"``.
        :rtype: str
        """
        value = float(x)
        sign = "-" if value < 0 else ""
        value = abs(value)

        if value >= 1_000_000:
            return f"{sign}{value / 1_000_000:.{decimals}f}M"
        if value >= 1_000:
            return f"{sign}{value / 1_000:.{decimals}f}K"
        return f"{sign}{value:.0f}"

    @staticmethod
    def load_plot_config(folder):
        """
        Load tool config overrides from ``cashflow.json`` in ``folder``.

        Every key is optional, and so is the file itself: anything missing
        falls back to :data:`PLOT_CONFIG_DEFAULTS`. Figure size, bar
        colors, bar width, background color, histogram panel size/bins/
        color and font sizes are the tunable surface for
        :meth:`plot_cashflow_bars`; ``language`` controls the printed
        table headers in ``cashflow.py`` (see its ``COLUMN_LABELS``) --
        currently ``"en"`` (default) or ``"pt-br"``.

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

        ``color_hist`` is ``null`` by default, meaning the histogram
        panel keeps the main panel's inflow/outflow color split; set it
        to a single color (e.g. ``"tab:gray"``) to use that for both
        sides of the histogram instead. ``hist_bin_size`` is also
        ``null`` by default, meaning the bin width is computed from the
        data itself via :meth:`compute_optimal_bin_size` (Scott's rule)
        rather than fixed; set it to a number to use a fixed
        currency-wide bin instead.

        :param folder: Bank/account folder where ``cashflow.json`` is
            expected (the same folder the plots are written to).
        :type folder: str or pathlib.Path
        :return: ``PLOT_CONFIG_DEFAULTS`` overridden by any keys present
            in the file, or an unmodified copy if the file is absent.
        :rtype: dict
        """
        config = PLOT_CONFIG_DEFAULTS.copy()

        file_config = Path(folder) / "cashflow.json"
        if file_config.exists():
            with open(file_config, "r", encoding="utf-8") as f:
                config.update(json.load(f))

        return config

    @staticmethod
    def compute_optimal_bin_size(values):
        """
        Compute a histogram bin width via Scott's rule, rounded to a
        clean 1/2/5 x 10^k step for a readable currency axis.

        Scott's rule (``3.49 * std * n ** -1/3``) assumes a roughly
        normal distribution and adapts to sample size -- a longer series
        (more months) gets proportionally finer bins on its own, with no
        manual scaling needed. Used as the default for ``hist_bin_size``
        (``None`` in :data:`PLOT_CONFIG_DEFAULTS`) whenever it is not set
        explicitly.

        :param values: Sample to size bins for (e.g. Entradas and
            ``Saidas.abs()`` concatenated).
        :type values: array-like
        :return: Bin width, always > 0.
        :rtype: float
        """
        values = np.asarray(values, dtype=float)
        if len(values) < 2:
            return 1.0

        std = values.std()
        if std <= 0:
            return 1.0

        raw_width = 3.49 * std / (len(values) ** (1 / 3))

        magnitude = 10 ** np.floor(np.log10(raw_width))
        residual = raw_width / magnitude
        nice = next((step for step in (1, 2, 5) if residual <= step), 10)

        return nice * magnitude

    @staticmethod
    def plot_cashflow_bars(
        df,
        x_col,
        file_out,
        title=None,
        scale=None,
        annotate=False,
        date_axis=False,
        year_ticks=False,
        ylim_default=100_000,
        config=None,
    ):
        """
        Plot Entradas/Saidas as a diverging bar chart and save it as a JPEG.

        Entradas (always >= 0) are drawn above the zero line and Saidas
        (always <= 0) below it, both anchored at the same baseline for
        every value of ``x_col``. No legend is drawn -- the color
        convention is stated once via ``scale`` in the title instead of
        repeating a color key on every plot. Month ticks are single letters
        (``"J"``, ``"F"``, ...), the y-axis is compacted to whole ``K``/``M``
        (no decimals) via :meth:`format_compact`, and the y-limits are
        symmetric around zero so 0 always sits at the vertical center of
        the plot: fixed at ``ylim_default`` unless some bar would be
        clipped by it, in which case ``1.1 * max(|Entradas|, |Saidas|)`` is
        used instead -- this keeps the scale stable (and years comparable)
        for ordinary months, only growing for an outlier year.

        A second panel to the right (``hist_width_pct`` of the total width,
        default a third) shares the main panel's y-axis and shows it as a
        horizontal histogram instead -- a sideways projection of the
        monthly series' distribution. Entradas values are binned into
        ``hist_bin_size`` currency-wide bins (or, if unset, bins sized by
        :meth:`compute_optimal_bin_size`) from 0 upward and drawn as
        bars extending right from x=0 in the positive region; Saidas are
        binned the same way (by magnitude) and mirrored into the negative
        region, so bin position lines up directly with the main panel's
        y-scale. The histogram's x-limit is fixed at twice its tallest
        bar (not autoscaled), so no single bin is ever stretched
        edge-to-edge. Both sides use ``color_inflows``/``color_outflows`` (the
        same split as the main bars) unless ``color_hist`` is set, in
        which case it covers both sides with a single color instead. A
        solid horizontal line marks each series' mean (``Entradas.mean()``,
        ``Saidas.mean()``) across the histogram panel, in that series'
        own color regardless of ``color_hist``, annotated (in the default
        annotation text color, like the bar annotations) with the rounded
        value at the line's upper-right.

        Every visual aspect -- figure size, bar colors, background color,
        bar width, histogram panel width and bin size, font sizes --
        comes from ``config`` (see :meth:`load_plot_config`), falling
        back to :data:`PLOT_CONFIG_DEFAULTS` for anything missing.

        :param df: Data with ``x_col``, ``Entradas`` and ``Saidas`` columns.
        :type df: pandas.DataFrame
        :param x_col: Column used for the x-axis (e.g. ``"Data"`` or ``"Mes"``).
        :type x_col: str
        :param file_out: Destination path for the ``.jpg`` file.
        :type file_out: str or pathlib.Path
        :param title: Optional chart title.
        :type title: str, optional
        :param scale: Granularity label (e.g. ``"Daily"``, ``"Monthly"``),
            appended to ``title``.
        :type scale: str, optional
        :param annotate: If ``True``, print each bar's value at its outer
            edge, compacted via :meth:`format_compact`. Meant for charts with
            few bars (e.g. monthly); too dense for a daily timeseries.
        :type annotate: bool
        :param date_axis: If ``True``, ``x_col`` is treated as a datetime
            axis and tick marks are placed once per month.
        :type date_axis: bool
        :param year_ticks: If ``True`` (meant for a multi-year ``x_col``
            like ``"YYYY-MM"``, e.g. the full-history monthly series),
            only January of each year gets a tick, labeled with that
            year's number -- no per-month letters, so a many-year series
            stays readable. Ignored when ``date_axis`` is ``True``.
        :type year_ticks: bool
        :param ylim_default: Fixed symmetric y-limit used as long as it
            does not clip any bar.
        :type ylim_default: float
        :param config: Style overrides, as returned by
            :meth:`load_plot_config`. Missing keys fall back to
            :data:`PLOT_CONFIG_DEFAULTS`.
        :type config: dict, optional
        :return: The ``file_out`` path, for logging by the caller.
        :rtype: str or pathlib.Path
        """
        config = {**PLOT_CONFIG_DEFAULTS, **(config or {})}
        figsize_mm_w, figsize_mm_h = config["figsize_mm"]
        figsize = (figsize_mm_w / MM_PER_INCH, figsize_mm_h / MM_PER_INCH)

        hist_pct = config["hist_width_pct"]
        fig = plt.figure(figsize=figsize)
        gs = GridSpec(1, 2, width_ratios=[100 - hist_pct, hist_pct], wspace=0.05)
        ax_main = fig.add_subplot(gs[0])
        ax_hist = fig.add_subplot(gs[1], sharey=ax_main)

        for axis in (ax_main, ax_hist):
            axis.set_facecolor(config["background_color"])

        bar_width = config["bar_width_pct"] / 100
        x = df[x_col]
        ax_main.bar(x, df["Entradas"], color=config["color_inflows"], width=bar_width)
        ax_main.bar(x, df["Saidas"], color=config["color_outflows"], width=bar_width)
        ax_main.axhline(0, color="black", linewidth=0.8)

        max_abs_flow = max(df["Entradas"].max(), df["Saidas"].abs().max())
        ylim = max(ylim_default, 1.1 * max_abs_flow)
        ax_main.set_ylim(-ylim, ylim)

        if annotate:
            for xi, entrada, saida in zip(x, df["Entradas"], df["Saidas"]):
                if entrada != 0:
                    ax_main.annotate(
                        CashFlow.format_compact(entrada),
                        xy=(xi, entrada),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha="center",
                        va="bottom",
                        fontsize=config["fontsize_annotation"],
                    )
                if saida != 0:
                    ax_main.annotate(
                        CashFlow.format_compact(saida),
                        xy=(xi, saida),
                        xytext=(0, -3),
                        textcoords="offset points",
                        ha="center",
                        va="top",
                        fontsize=config["fontsize_annotation"],
                    )

        if date_axis:
            ax_main.xaxis.set_major_locator(mdates.MonthLocator())
            ax_main.xaxis.set_major_formatter(
                FuncFormatter(
                    lambda val, pos: MONTH_LETTERS[mdates.num2date(val).month]
                )
            )
        else:
            months = x.astype(str).str.slice(5, 7).astype(int)
            if year_ticks:
                # only a January tick per year, labeled with the year --
                # no per-month ticks, which is what a many-year series
                # needs to stay readable
                years = x.astype(str).str.slice(0, 4)
                jan_positions = [i for i, m in enumerate(months) if m == 1]
                jan_years = [y for y, m in zip(years, months) if m == 1]
                ax_main.set_xticks(jan_positions)
                ax_main.set_xticklabels(jan_years)
            else:
                ax_main.set_xticks(range(len(x)))
                ax_main.set_xticklabels([MONTH_LETTERS[m] for m in months])

        ax_main.yaxis.set_major_formatter(
            FuncFormatter(lambda val, pos: CashFlow.format_compact(val, decimals=0))
        )
        ax_main.tick_params(axis="both", labelsize=config["fontsize_ticks"])

        full_title = " -- ".join(part for part in (title, scale) if part)
        if full_title:
            # suptitle, not ax_main.set_title: centers over the whole
            # figure (both panels), not just the main (2/3-width) axes.
            fig.suptitle(full_title, fontsize=config["fontsize_title"])

        # Side histogram -- a horizontal projection of the same series onto
        # the shared y-axis, binned by a fixed currency interval rather than
        # a bin count (so bin edges stay meaningful as the y-scale changes
        # year to year). hist_bin_size=None (the default) sizes that
        # interval from the data itself via Scott's rule.
        bin_size = config["hist_bin_size"]
        if bin_size is None:
            combined = np.concatenate(
                [df["Entradas"].values, df["Saidas"].abs().values]
            )
            bin_size = CashFlow.compute_optimal_bin_size(combined)
        edges = np.arange(0, ylim + bin_size, bin_size)
        bin_centers = (edges[:-1] + edges[1:]) / 2

        inflow_counts, _ = np.histogram(df["Entradas"], bins=edges)
        outflow_counts, _ = np.histogram(df["Saidas"].abs(), bins=edges)

        # a single color_hist covers both sides; absent, each side keeps
        # the main panel's own color (the usual inflow/outflow split)
        hist_color_inflows = config["color_hist"] or config["color_inflows"]
        hist_color_outflows = config["color_hist"] or config["color_outflows"]

        ax_hist.barh(
            bin_centers,
            inflow_counts,
            height=bin_size * 0.9,
            color=hist_color_inflows,
        )
        ax_hist.barh(
            -bin_centers,
            outflow_counts,
            height=bin_size * 0.9,
            color=hist_color_outflows,
        )
        ax_hist.axhline(0, color="black", linewidth=0.8)
        # fixed at 2x the tallest bar, not autoscaled, so a bin is never
        # stretched edge-to-edge and there's always headroom to compare
        # against
        max_count = max(inflow_counts.max(), outflow_counts.max())
        ax_hist.set_xlim(0, 2 * max_count)
        ax_hist.tick_params(axis="both", labelsize=config["fontsize_ticks"])
        plt.setp(ax_hist.get_yticklabels(), visible=False)

        # Average lines -- follow the time series' own colors (not
        # hist_color_*), so they read as "the average of that series",
        # independent of how the histogram bars themselves are colored.
        mean_inflow = df["Entradas"].mean()
        mean_outflow = df["Saidas"].mean()

        for mean_value, color in (
            (mean_inflow, config["color_inflows"]),
            (mean_outflow, config["color_outflows"]),
        ):
            ax_hist.axhline(mean_value, color=color, linewidth=1)
            ax_hist.annotate(
                CashFlow.format_compact(mean_value),
                xy=(0.95, mean_value),
                xycoords=ax_hist.get_yaxis_transform(),
                xytext=(0, 3),
                textcoords="offset points",
                ha="right",
                va="bottom",
                fontsize=config["fontsize_annotation"],
            )

        fig.subplots_adjust(left=0.14, right=0.96, top=0.88, bottom=0.14)

        fig.savefig(file_out, dpi=config["dpi"], format="jpg")
        plt.close(fig)

        return file_out


class CashFlowBBCC(CashFlow):
    """
    A class for handling CSV data from Banco do Brasil Conta Corrente.

    .. dropdown:: Script example
        :icon: code-square
        :open:

        .. code-block:: python

            from babilonia.accounting import CashFlowBBCC

            # create an empty class
            cf = CashFlowBBCC()

            # set the file for CSV
            file_csv = "path/to/file.csv" # [change this]

            # load data
            cf.load_data(file_csv)

            # standardize data
            cf.standardize()

            # print data
            print(cf.data.head(10))

            # save data
            file_out = "path/to/output.csv" # [change this]
            cf.data.to_csv(file_out, sep=";", index=False)

    """

    def __init__(self, name="CashFlowBBCC", alias="CFBBCC"):
        super().__init__(name=name, alias=alias)
        # include the stages of data
        self.data_raw = None
        self.data_parsed = None

    def load_data(self, file_data):
        """
        Load raw data from bank CSV statement

        :param file_data: Bank statement CSV file path
        :type file_data: str or Path
        :return: None
        :rtype: None
        """
        # overwrite relative path inputs
        # ----------------------------------------------
        self.file_data = os.path.abspath(file_data)

        # implement loading logic
        # ----------------------------------------------
        try:
            df = pd.read_csv(
                self.file_data,
                sep=",",
                quotechar='"',
                encoding="cp1252",  # Banco do Brasil standard
                dtype=str,
                keep_default_na=False,
            )
        except UnicodeDecodeError:
            # Fallback for alternative exports
            df = pd.read_csv(
                self.file_data,
                sep=",",
                quotechar='"',
                encoding="latin1",
                dtype=str,
                keep_default_na=False,
            )

        # post-loading logic
        # ----------------------------------------------
        df.dropna(inplace=True)
        self.data_raw = df.copy()
        self.data_parsed = None
        self.data = None

        # update other mutables
        # ----------------------------------------------
        self.update()

        # ... continues in downstream objects ... #

        return None

    def standardize(self, force=False):
        """
        Standardize data into canonical format.

        :param force: Rebuild parsed data even if it exists
        """
        if self.data_raw is None:
            raise RuntimeError("No data loaded")

        if self.data_parsed is None or force:
            self.data_parsed = self.parse_data(self.data_raw)

        self.data = self.data_parsed.copy()

        return None

    def parse_data(self, df=None):
        """
        Parse data to canonical format

        :param df: Optional input data
        :type df: ``pandas.DataFrame``
        :return: Formated data
        :rtype: ``pandas.DataFrame``
        """
        if df is None:
            df = self.data_raw

        df = df.copy()

        # --- normalize legacy column names ---
        df = self.normalize_columns(df)

        df = self.apply_drops(df)

        df["Data"] = self.parse_date(df["Data"])
        df["Valor"] = self.parse_valor(df["Valor"])

        df["Categoria"] = ""
        df["Descricao"] = ""

        if "Detalhes" not in df.columns:
            df["Detalhes"] = ""

        df = df[
            [
                "Data",
                "Valor",
                "Categoria",
                "Descricao",
                "Lançamento",
                "Detalhes",
                "N° documento",
            ]
        ]

        df = df.rename(
            columns={"Lançamento": "Lancamento", "N° documento": "Documento"}
        )

        return df

    def parse_date(self, series):
        """
        Parse BB date field from ``DD/MM/YYYY`` to datetime.

        :param series: String series
        :type series: ``pandas.Series``
        :return: Datetime series
        :rtype: ``pandas.Series``
        """
        dates = pd.to_datetime(
            series,
            format="%d/%m/%Y",
            errors="raise",
        )
        return dates

    def parse_valor(self, series):
        """
        Convert ``Valor`` field to float.

        .. dropdown:: Examples
            :open:

            .. list-table::
               :widths: auto
               :header-rows: 1

               * - Input
                 - Output
               * - ``5.000,00``
                 - ``5000.00``
               * - ``-403,00``
                 - ``-403.00``


        :param series: String series
        :type series: ``pandas.Series``
        :return: Value series
        :rtype: ``pandas.Series``
        """
        s = series.astype(str).str.strip()

        # Detect Brazilian format (comma as decimal separator)
        is_br_format = s.str.contains(",")

        # Normalize only Brazilian-formatted values
        s.loc[is_br_format] = (
            s.loc[is_br_format]
            .str.replace(".", "", regex=False)  # thousands separator
            .str.replace(",", ".", regex=False)  # decimal separator
        )

        # Convert to float
        values = s.astype(float)

        return values

    def apply_drops(self, df):
        """
        Filter dataframe for parsing

        :param df: Input data
        :type df: ``pandas.DataFrame``
        :return: Output data
        :rtype: ``pandas.DataFrame``
        """
        df = df.query("Lançamento != 'Saldo do dia'")
        df = df.query("Lançamento != 'Saldo Anterior'")
        df = df.query("Lançamento != 'S A L D O'")
        return df

    def normalize_columns(self, df):
        """
        Normalize legacy / alternative column names to the current schema.

        :param df: Input data
        :type df: ``pandas.DataFrame``
        :return: Output data
        :rtype: ``pandas.DataFrame``
        """
        column_aliases = {
            "Histórico": "Lançamento",
            "Número do documento": "N° documento",
        }

        for old, new in column_aliases.items():
            if old in df.columns and new not in df.columns:
                df = df.rename(columns={old: new})

        if "Lançamento" not in df.columns:
            raise KeyError(
                "Expected column 'Lançamento' (or legacy 'Histórico') not found in CSV."
            )

        return df


class CashFlowBBCCPJ(CashFlowBBCC):
    """
    Class for handling BB-CC for PJ accoung CSV data.

    """

    def __init__(self, name="CashFlowBBCCPJ", alias="CFBBCCPJ"):
        super().__init__(name=name, alias=alias)

    def parse_valor(self, series):
        """
        Convert ``Valor`` field to float.

        Two T0 export variants are supported, so a file from either
        (or a single file spanning the transition) parses correctly:

        - Legacy, marker-suffixed: sign comes from a trailing ``C``/``D``
          marker, discarding whatever sign the string itself carries
          (e.g. ``"5.000,00 C"`` -> credit/inflow, ``"403,00 D"`` and
          ``"-403,00 D"`` both -> debit/outflow).
        - Newer, plain signed value with no marker (a separate ``Tipo
          Lançamento`` column states "Entrada"/"Saída" redundantly):
          handled by the base :meth:`CashFlowBBCC.parse_valor`, sign
          taken directly from the string (e.g. ``"-3.000,00"`` ->
          outflow, ``"3.423,00"`` -> inflow).

        .. dropdown:: Examples
            :open:

            .. list-table::
               :widths: auto
               :header-rows: 1

               * - Input
                 - Output
               * - ``5.000,00 C``
                 - ``5000.00``
               * - ``-403,00 D``
                 - ``-403.00``
               * - ``-3.000,00``
                 - ``-3000.00``
               * - ``3.423,00``
                 - ``3423.00``

        :param series: String series
        :type series: ``pandas.Series``
        :return: Value series
        :rtype: ``pandas.Series``
        """
        s = series.str.strip()

        has_marker = s.str.endswith("C") | s.str.endswith("D")
        is_debit = s.str.endswith("D")

        # strip the trailing marker where present; markerless values are
        # left untouched, carrying their own sign
        s_clean = s.mask(has_marker, s.str.replace(r"\s*[CD]$", "", regex=True))

        # base class already parses a plain signed Brazilian-format number
        values = super().parse_valor(s_clean)

        # marker rows: sign comes only from the marker, regardless of
        # whatever sign the string itself carried
        values = values.mask(has_marker, values.abs())
        values[has_marker & is_debit] *= -1

        return values

    def apply_drops(self, df):
        df = super().apply_drops(df=df)
        df = df.query("Lançamento != 'BB Rende Fácil'")
        df = df.query("Valor not in ['0,00 C', '0,00']")
        return df


class CashFlowBBPP(CashFlowBBCC):
    """
    Class for handling BB-PP CSV data.

    """

    def __init__(self, name="CashFlowBBPP", alias="CFBBPP"):
        super().__init__(name=name, alias=alias)

    def parse_data(self, df=None):

        if df is None:
            df = self.data_raw

        df = df.copy()

        # clear up rows and columns
        df = self.apply_drops(df)

        # Parse dates (DD/MM/YYYY -> datetime)
        df["Data"] = self.parse_date(df["Data"])

        # Parse Valor to float (keep column name)
        df["Valor"] = self.parse_valor(df["Valor"])

        df["Categoria"] = df["Histórico"]
        df["Descricao"] = ""

        df = df[
            [
                "Data",
                "Valor",
                "Categoria",
                "Descricao",
            ]
        ]

        return df

    def parse_valor(self, series: pd.Series) -> pd.Series:
        """
        Convert ``Valor`` field to float.

        .. dropdown:: Examples
            :open:

            .. list-table::
               :widths: auto
               :header-rows: 1

               * - Input
                 - Output
               * - ``5.000,00 C``
                 - ``5000.00``
               * - ``-403,00 D``
                 - ``-403.00``


        :param series: String series
        :type series: ``pandas.Series``
        :return: Value series
        :rtype: ``pandas.Series``
        """
        s = series.str.strip()

        # Identify credit / debit
        is_credit = s.str.endswith("C")
        is_debit = s.str.endswith("D")

        # Remove currency markers and spaces
        s = s.str.replace(r"[CD]", "", regex=True).str.strip()

        # Remove thousands separator and fix decimal separator
        s = s.str.replace(".", "", regex=False)
        s = s.str.replace(",", ".", regex=False)

        # Convert to float (absolute value)
        values = s.astype(float).abs()

        # Apply sign
        values[is_debit] *= -1

        return values

    def apply_drops(self, df):

        return df


class CashFlowNUCredit(CashFlow):
    """
    A class for handling CSV data exported from Nubank Cartão de Crédito
    (Nubank credit card) invoices.

    Nubank appears to export at least two CSV variants for the same
    ``date,title,amount`` schema:

    * Quoted, Brazilian-formatted values, e.g. ``"1.234,56"`` or
      ``"- 41,97"`` (comma decimal separator, dot thousands separator,
      sometimes a space between the minus sign and the digits).
    * Unquoted, international-formatted values, e.g. ``1234.56`` or
      ``-6722.00`` (dot decimal separator, no thousands separator).

    ``parse_valor`` auto-detects and normalizes both variants.

    Note on sign convention: Nubank reports purchases as positive
    ``amount`` and payments/refunds ("Pagamento recebido") as negative.
    By default this class inverts that sign when building the canonical
    ``Valor`` field, so purchases become outflows (negative ``Valor``,
    classified as ``"Out"``) and payments/refunds become inflows
    (positive ``Valor``, classified as ``"In"``) — consistent with how
    :meth:`CashFlow.classify_flows` is used for the BB accounts. Pass
    ``invert_sign=False`` at construction time to keep Nubank's raw
    sign convention instead.

    .. dropdown:: Script example
        :icon: code-square
        :open:

        .. code-block:: python

            from babilonia.accounting import CashFlowNuCC

            # create an empty class
            cf = CashFlowNuCC()

            # set the file for CSV
            file_csv = "path/to/file.csv"  # [change this]

            # load data
            cf.load_data(file_csv)

            # standardize data
            cf.standardize()

            # print data
            print(cf.data.head(10))

            # save data
            file_out = "path/to/output.csv"  # [change this]
            cf.data.to_csv(file_out, sep=";", index=False)

    """

    def __init__(self, name="CashFlowNuCC", alias="CFNUCC", invert_sign=True):
        super().__init__(name=name, alias=alias)
        # include the stages of data
        self.data_raw = None
        self.data_parsed = None
        # see class docstring: purchases (+) -> Out, payments/refunds (-) -> In
        self.invert_sign = invert_sign

    def load_data(self, file_data):
        """
        Load raw data from the Nubank credit-card CSV export.

        :param file_data: Nubank credit-card CSV file path
        :type file_data: str or Path
        :return: None
        :rtype: None
        """
        # overwrite relative path inputs
        # ----------------------------------------------
        self.file_data = os.path.abspath(file_data)

        # implement loading logic
        # ----------------------------------------------
        try:
            df = pd.read_csv(
                self.file_data,
                sep=",",
                quotechar='"',
                encoding="utf-8",
                dtype=str,
                keep_default_na=False,
            )
        except UnicodeDecodeError:
            # Fallback for alternative exports
            df = pd.read_csv(
                self.file_data,
                sep=",",
                quotechar='"',
                encoding="latin1",
                dtype=str,
                keep_default_na=False,
            )

        # post-loading logic
        # ----------------------------------------------
        df.dropna(inplace=True)
        self.data_raw = df.copy()
        self.data_parsed = None
        self.data = None

        # update other mutables
        # ----------------------------------------------
        self.update()

        # ... continues in downstream objects ... #

        return None

    def standardize(self, force=False):
        """
        Standardize data into canonical format.

        :param force: Rebuild parsed data even if it exists
        """
        if self.data_raw is None:
            raise RuntimeError("No data loaded")

        if self.data_parsed is None or force:
            self.data_parsed = self.parse_data(self.data_raw)

        self.data = self.data_parsed.copy()

        return None

    def parse_data(self, df=None):
        """
        Parse data to canonical format

        :param df: Optional input data
        :type df: ``pandas.DataFrame``
        :return: Formated data
        :rtype: ``pandas.DataFrame``
        """
        if df is None:
            df = self.data_raw

        df = df.copy()

        # --- normalize legacy / alternative column names ---
        df = self.normalize_columns(df)

        df = self.apply_drops(df)

        df["Data"] = self.parse_date(df["date"])
        df["Valor"] = self.parse_valor(df["amount"])
        df["Categoria"] = ""
        df["Descricao"] = df["title"]

        df = df[["Data", "Categoria", "Valor", "Descricao"]]

        return df

    def parse_date(self, series):
        """
        Parse Nubank date field from ``YYYY-MM-DD`` to datetime.

        :param series: String series
        :type series: ``pandas.Series``
        :return: Datetime series
        :rtype: ``pandas.Series``
        """
        dates = pd.to_datetime(
            series,
            format="%Y-%m-%d",
            errors="raise",
        )
        return dates

    def parse_valor(self, series):
        """
        Convert ``amount`` field to float, auto-detecting the CSV variant.

        .. dropdown:: Examples
            :open:

            .. list-table::
               :widths: auto
               :header-rows: 1

               * - Input
                 - Output (before sign inversion)
               * - ``"50,50"``
                 - ``50.50``
               * - ``"- 3.784,83"``
                 - ``-3784.83``
               * - ``69.99``
                 - ``69.99``
               * - ``-6722.00``
                 - ``-6722.00``

        :param series: String series
        :type series: ``pandas.Series``
        :return: Value series
        :rtype: ``pandas.Series``
        """
        s = series.astype(str).str.strip()

        # drop stray quote characters and collapse internal whitespace,
        # e.g. the space Nubank sometimes inserts after the minus sign:
        # "- 41,97" -> "-41,97"
        s = s.str.replace('"', "", regex=False)
        s = s.str.replace(r"\s+", "", regex=True)

        # Brazilian-formatted values use a comma as the decimal separator
        # (and, sometimes, a dot as the thousands separator). The
        # alternative export already uses a dot as the decimal separator
        # and can be parsed as-is.
        is_br_format = s.str.contains(",")

        s.loc[is_br_format] = (
            s.loc[is_br_format]
            .str.replace(".", "", regex=False)  # thousands separator
            .str.replace(",", ".", regex=False)  # decimal separator
        )

        values = s.astype(float)

        if self.invert_sign:
            values = -values

        return values

    def apply_drops(self, df):
        """
        Filter dataframe for parsing. No rows are dropped by default;
        override or extend this to filter specific transactions if needed.

        :param df: Input data
        :type df: ``pandas.DataFrame``
        :return: Output data
        :rtype: ``pandas.DataFrame``
        """
        return df

    def normalize_columns(self, df):
        """
        Normalize alternative / legacy column names to the current schema.

        :param df: Input data
        :type df: ``pandas.DataFrame``
        :return: Output data
        :rtype: ``pandas.DataFrame``
        """
        column_aliases = {
            "Data": "date",
            "Título": "title",
            "Titulo": "title",
            "Descrição": "title",
            "Valor": "amount",
        }

        for old, new in column_aliases.items():
            if old in df.columns and new not in df.columns:
                df = df.rename(columns={old: new})

        required = {"date", "title", "amount"}
        missing = required - set(df.columns)
        if missing:
            raise KeyError(f"Expected column(s) {sorted(missing)} not found in CSV.")

        return df


class BBCDB(DataSet):
    """
    Parses Banco do Brasil CDB investment statement text files.

    Reads the plain-text report exported by BB for CDB DI and CDB
    Progressivo accounts and splits it into named sections (EXTRATO,
    SALDOS, DEPOSITOS, RENDIMENTOS), normalizing each into a
    :class:`pandas.DataFrame`. The result is stored in ``self.data`` as a
    nested dictionary keyed by account then section name.
    """

    def __init__(self, name="BBCDB", alias="BBCDB"):
        super().__init__(name=name, alias=alias)

    def load_data(self, file_data):
        # todo docstring
        from io import StringIO

        # ------------------------------------------------------------------
        # Internal helpers (local on purpose: used only in this workflow)
        # ------------------------------------------------------------------

        def _to_float_br(series: pd.Series) -> pd.Series:
            """Convert Brazilian-formatted numeric strings to float."""
            return (
                series.str.replace(".", "", regex=False)  # thousands separator
                .str.replace(",", ".", regex=False)  # decimal separator
                .astype(float)
            )

        def _parse_date(series: pd.Series, fmt: str) -> pd.Series:
            """Parse date strings using a fixed datetime format."""
            return pd.to_datetime(series, format=fmt)

        def _parse_day_month_with_year(series: pd.Series, year: int) -> pd.Series:
            """Append year to DD/MM dates and parse."""
            return pd.to_datetime(series + f"/{year}", format="%d/%m/%Y")

        # ------------------------------------------------------------------
        # 1. Raw text ingestion and cleaning
        # ------------------------------------------------------------------

        ls_data = BBCDB.read_txt(file_data)
        year_data = BBCDB.get_year(ls_data)

        # Drop structural noise and normalize line content
        ls_data = BBCDB.drop_lines(ls_data, contains="--")
        ls_data = BBCDB.drop_lines(ls_data, contains="==")
        ls_data = BBCDB.drop_blank_lines(ls_data)

        # Canonical line replacements
        ls_data = BBCDB.replace_lines(ls_data)
        ls_data = BBCDB.replace_lines(ls_data, "\n", "")

        # ------------------------------------------------------------------
        # 2. Structural splitting (accounts → sections)
        # ------------------------------------------------------------------

        dc_accounts = BBCDB.split_accounts(ls_data)
        dc_sections = BBCDB.split_sections(dc_data=dc_accounts)

        # ------------------------------------------------------------------
        # 3. Section-specific parsing and normalization
        # ------------------------------------------------------------------

        dc_data = {}

        for account, sections in dc_sections.items():
            dc_account_data = {}

            for section, lines in sections.items():
                text = "\n".join(lines)
                df = pd.read_csv(StringIO(text), sep=self.file_csv_sep, dtype=str)

                # -----------------------------
                # Section-specific normalization
                # -----------------------------

                if section == "EXTRATO":
                    df["Data"] = _parse_day_month_with_year(df["Data"], year_data)
                    df["Valor"] = _to_float_br(df["Valor"])
                    df = df.rename(columns={"Historico": "Categoria"})
                    df["Descricao"] = ""
                    df = df[["Data", "Valor", "Categoria", "Descricao"]]

                elif section == "RENDIMENTOS":
                    df["Data"] = _parse_day_month_with_year(df["Data"], year_data)
                    df["Rendimento_Bruto"] = _to_float_br(df["Rendimento_Bruto"])

                elif section == "SALDOS":
                    df["Data"] = _parse_date(df["Data"], "%d/%m/%Y")
                    for col in [
                        "Capital_Inicial",
                        "Juros",
                        "IR_Projetado",
                        "Capital_Projetado",
                    ]:
                        df[col] = _to_float_br(df[col])

                elif section == "DEPOSITOS":
                    df["Data_Aplicacao"] = _parse_date(df["Data_Aplicacao"], "%d/%m/%Y")
                    df["Data_Vencimento"] = _parse_date(
                        df["Data_Vencimento"], "%d/%m/%Y"
                    )
                    for col in ["Capital", "Saldo", "Taxa"]:
                        df[col] = _to_float_br(df[col])

                dc_account_data[section] = df

            dc_data[account] = dc_account_data

        self.data = dc_data.copy()
        return None

    @staticmethod
    def read_txt(file_txt, encoding="cp1252"):
        with open(file_txt, encoding=encoding) as f:
            lines = f.readlines()

        ls = []
        for line in lines:
            ls.append(line[:])

        return ls

    @staticmethod
    def drop_blank_lines(lines):
        return [line for line in lines if line.strip()]

    @staticmethod
    def drop_lines(lines, contains="-"):
        return [line for line in lines if contains not in line]

    @staticmethod
    def replace_lines(lines, contains="\xa0", relacer=" "):
        return [line.replace(contains, relacer) for line in lines]

    @staticmethod
    def split_accounts(lines):
        # Mapping of account headers to their terminating marker.
        # If the value is None, collection continues until end of file.
        dc_accounts = {
            "BB CDB DI": "BB CDB PROGRESSIVO",
            "BB CDB PROGRESSIVO": None,
        }

        dc_accounts_names = {
            "BB CDB DI": "CDBDI",
            "BB CDB PROGRESSIVO": "CDBPG",
        }

        ls_accounts = list(dc_accounts.keys())

        b_collect = False  # Indicates whether lines are currently being collected
        dc_data = {}

        for account in ls_accounts:
            ls_data = []

            # Scan the full file line-by-line, collecting the block for this account
            for line in lines[:]:

                # Start collecting when the account header is found
                if account in line:
                    b_collect = True

                # Stop collecting when the next account header is found (if defined)
                if dc_accounts[account] is not None and dc_accounts[account] in line:
                    b_collect = False

                # Collect only lines within the active account block
                if b_collect:
                    ls_data.append(line)

            # Store a copy of the collected block for this account
            dc_data[dc_accounts_names[account]] = ls_data[:]

        return dc_data

    @staticmethod
    def split_sections(dc_data):
        sections = {}

        section_titles = {
            "EXTRATO": {"START": None, "END": "SALDO NOS ULTIMOS 6 MESES"},
            "SALDOS": {
                "START": "SALDO NOS ULTIMOS 6 MESES",
                "END": "RESUMO DOS DEPOSITOS EM SER",
            },
            "DEPOSITOS": {
                "START": "RESUMO DOS DEPOSITOS EM SER",
                "END": "RENDIMENTO BRUTO NO PERIODO POR DEPOSITO",
            },
            "RENDIMENTOS": {
                "START": "RENDIMENTO BRUTO NO PERIODO POR DEPOSITO",
                "END": None,
            },
        }

        # ------------------------------------------------------------------
        # Internal helpers
        # ------------------------------------------------------------------

        def _collect_block(lines, start=None, end=None):
            """Collect lines between start and end markers (inclusive start)."""
            collected = []
            b_collect = start is None

            for line in lines:
                if start and start in line:
                    b_collect = True

                if end and end in line:
                    break

                if b_collect:
                    collected.append(line[:])

            return collected

        def _normalize_lines(lines):
            """Collapse whitespace and convert to semicolon-separated format."""
            return [re.sub(r"\s+", ";", line.strip()) for line in lines]

        def _rewrite_header_and_trim(lines, header):
            """Replace header row and drop section title line."""
            lines[1] = header
            return lines[1:]

        # ------------------------------------------------------------------
        # Main logic
        # ------------------------------------------------------------------

        dc_data_out = {}

        for account, lines in dc_data.items():
            dc_account_data = {}

            for title, markers in section_titles.items():
                ls_data = _collect_block(
                    lines,
                    start=markers["START"],
                    end=markers["END"],
                )

                # -----------------------------
                # Section-specific reshaping
                # -----------------------------

                if title == "EXTRATO":
                    # Remove non-tabular summary lines
                    ls_data = [
                        line
                        for line in ls_data
                        if not any(
                            s in line
                            for s in ("Saldo anterior", "capital", "Saldo final")
                        )
                    ]

                    ls_data[1] = "Data;Historico;Deposito;Valor"

                    # Merge paired rows into single logical records
                    if len(ls_data) > 3:
                        merged = ls_data[:2]
                        body = ls_data[2:]

                        for i in range(0, len(body), 2):
                            line = body[i] + body[i + 1]
                            line = (
                                line.replace("-", "")
                                .replace("valor juros", "")
                                .replace("Rendimento  mensal", "Juros")
                            )
                            merged.append(line)

                        ls_data = merged[1:]

                elif title == "SALDOS":
                    ls_data = _rewrite_header_and_trim(
                        ls_data,
                        "Data;Capital_Inicial;Juros;IR_Projetado;Capital_Projetado",
                    )

                elif title == "DEPOSITOS":
                    ls_data = _rewrite_header_and_trim(
                        ls_data,
                        "Deposito;Data_Aplicacao;Capital;Saldo;Taxa;Data_Vencimento",
                    )

                elif title == "RENDIMENTOS":
                    ls_data = _rewrite_header_and_trim(
                        ls_data,
                        "Data;Deposito;Rendimento_Bruto",
                    )

                # Final canonical formatting
                dc_account_data[title] = _normalize_lines(ls_data)

            dc_data_out[account] = dc_account_data.copy()

        return dc_data_out

    @staticmethod
    def get_year(lines):

        for line in lines:
            if "Período: " in line:
                ls1 = line.split(":")
                ls2 = ls1[1].split("/")
                return int(ls2[2][:4])


class NFSe(DataSet):
    """
    Class for handling NFSe XML data.

    """

    def __init__(self, name="NFSeDataSet", alias="NFSe"):
        """
        Initialize the NFSe object.
        """
        super().__init__(name=name, alias=alias)

        self.date = None
        self.emitter = None
        self.taker = None
        self.service_value = None
        self.service_value_trib = None
        self.service_id = None
        self.project_alias = None

    def __str__(self):
        """
        Nicely formatted string representation of the NFSe data.
        """
        if self.data is None:
            return "No data loaded."

        # Format the main NFSe data
        nfse_info = (
            f"NFSe ID: {self.data.get('nfse_id', 'N/A')}\n"
            f"Local de Emissão: {self.data.get('local_emissao', 'N/A')}\n"
            f"Local de Prestação: {self.data.get('local_prestacao', 'N/A')}\n"
            f"Número da NFSe: {self.data.get('numero_nfse', 'N/A')}\n"
            f"Código de Local de Incidência: {self.data.get('codigo_local_incidencia', 'N/A')}\n"
            f"Descrição do Serviço: {self.data.get('descricao_servico', 'N/A')}\n"
            f"Valor Líquido: {self.data.get('valor_liquido', 'N/A')}\n"
            f"Data do Processo: {self.data.get('data_processo', 'N/A')}\n"
            f"Data Competência: {self.date}\n"
        )

        # Format the emitente (issuer) information
        emitente = self.data.get(self.emitter_field, {})
        emitente_info = (
            f"Prestador:\n"
            f"  CNPJ: {emitente.get('cnpj', 'N/A')}\n"
            f"  Nome: {emitente.get('nome', 'N/A')}\n"
            f"  Endereço:\n"
            f"    Logradouro: {emitente.get('endereco', {}).get('logradouro', 'N/A')}\n"
            f"    Número: {emitente.get('endereco', {}).get('numero', 'N/A')}\n"
            f"    Bairro: {emitente.get('endereco', {}).get('bairro', 'N/A')}\n"
            f"    Cidade: {emitente.get('endereco', {}).get('cidade', 'N/A')}\n"
            f"    UF: {emitente.get('endereco', {}).get('uf', 'N/A')}\n"
            f"    CEP: {emitente.get('endereco', {}).get('cep', 'N/A')}\n"
            f"  Telefone: {emitente.get('telefone', 'N/A')}\n"
            f"  Email: {emitente.get('email', 'N/A')}\n"
        )

        # Format the tomador (receiver) information
        tomador = self.data.get(self.taker_field, {})
        tomador_info = (
            f"Tomador:\n"
            f"  CNPJ: {tomador.get('cnpj', 'N/A')}\n"
            f"  Nome: {tomador.get('nome', 'N/A')}\n"
            f"  Endereço:\n"
            f"    Logradouro: {tomador.get('endereco', {}).get('logradouro', 'N/A')}\n"
            f"    Número: {tomador.get('endereco', {}).get('numero', 'N/A')}\n"
            f"    Complemento: {tomador.get('endereco', {}).get('complemento', 'N/A')}\n"
            f"    Bairro: {tomador.get('endereco', {}).get('bairro', 'N/A')}\n"
            f"    Cidade: {tomador.get('endereco', {}).get('cidade', 'N/A')}\n"
            f"    CEP: {tomador.get('endereco', {}).get('cep', 'N/A')}\n"
        )

        # Format the service information
        servico = self.data.get("servico", {})
        servico_info = (
            f"Serviço:\n"
            f"  Código do Serviço: {servico.get('codigo_servico', 'N/A')}\n"
            f"  Descrição: {servico.get('descricao_servico', 'N/A')}\n"
            f"  Valor do Serviço: {servico.get('valor_servico', 'N/A')}\n"
        )

        # Combine all sections into one string
        return f"{nfse_info}\n{emitente_info}\n{tomador_info}\n{servico_info}"

    def _set_fields(self):
        # ------------ call super ----------- #
        super()._set_fields()
        # Attribute fields
        self.date_field = "Date"
        self.emitter_field = "Prestador"
        self.taker_field = "Tomador"
        self.service_value_field = "ValorServico"
        self.service_value_trib_field = "PTributoSN"
        self.service_id_field = "ServicoID"
        self.project_alias_field = "Projeto"

        # ... continues in downstream objects ... #

    def get_metadata(self):
        # ------------ call super ----------- #
        dict_meta = super().get_metadata()

        # customize local metadata:
        dict_meta_local = {
            self.date_field: self.date,
            self.emitter_field: self.emitter,
            self.taker_field: self.taker,
            self.service_value_field: self.service_value,
            self.service_value_trib_field: self.service_value_trib,
            self.service_id_field: self.service_id,
            self.project_alias_field: self.project_alias,
        }

        # update
        dict_meta.update(dict_meta_local)
        return dict_meta

    def load_data(self, file_data):
        """
        Load and parse XML data from the provided file.

        :param file_data: file path to the NFSe XML data.
        :type file_data: str
        :return: None
        """
        # Ensure the file path is absolute
        file_data = os.path.abspath(file_data)
        # print(file_data)
        tree = ET.parse(file_data)
        root = tree.getroot()

        # Namespaces used in the XML
        ns = {
            "default": "http://www.sped.fazenda.gov.br/nfse",
            "ds": "http://www.w3.org/2000/09/xmldsig#",
        }

        # Dictionary to hold extracted XML data
        nfse_data = {}

        # Extract main NFSe data
        nfse_data["nfse_id"] = root.find(".//default:infNFSe", ns).attrib.get("Id")
        nfse_data["local_emissao"] = root.find(".//default:xLocEmi", ns).text
        nfse_data["local_prestacao"] = root.find(".//default:xLocPrestacao", ns).text
        nfse_data["numero_nfse"] = root.find(".//default:nNFSe", ns).text
        nfse_data["codigo_local_incidencia"] = root.find(
            ".//default:cLocIncid", ns
        ).text
        nfse_data["descricao_servico"] = root.find(".//default:xTribNac", ns).text
        nfse_data["valor_liquido"] = float(root.find(".//default:vLiq", ns).text)
        nfse_data["data_processo"] = root.find(".//default:dhProc", ns).text
        nfse_data[self.date_field] = root.find(".//default:dCompet", ns).text

        # Extract emitente (issuer) data
        emitente = root.find(".//default:emit", ns)
        nfse_data[self.emitter_field] = {
            "cnpj": emitente.find(".//default:CNPJ", ns).text,
            "nome": emitente.find(".//default:xNome", ns).text,
            "endereco": {
                "logradouro": emitente.find(
                    ".//default:enderNac/default:xLgr", ns
                ).text,
                "numero": emitente.find(".//default:enderNac/default:nro", ns).text,
                "bairro": emitente.find(".//default:enderNac/default:xBairro", ns).text,
                "cidade": emitente.find(".//default:enderNac/default:cMun", ns).text,
                "uf": emitente.find(".//default:enderNac/default:UF", ns).text,
                "cep": emitente.find(".//default:enderNac/default:CEP", ns).text,
            },
            "telefone": emitente.find(".//default:fone", ns).text,
            "email": emitente.find(".//default:email", ns).text,
        }

        # Extract tomador (receiver) data
        tomador = root.find(".//default:toma", ns)

        nfse_data[self.taker_field] = {
            "cnpj": (
                tomador.find(".//default:CNPJ", ns).text
                if tomador.find(".//default:CNPJ", ns) is not None
                else None
            ),
            "nif": (
                tomador.find(".//default:NIF", ns).text
                if tomador.find(".//default:NIF", ns) is not None
                else None
            ),
            "nome": tomador.find(".//default:xNome", ns).text,
        }
        # print()
        # print(nfse_data[self.taker_field]["nome"])
        _address = {
            "logradouro": (
                tomador.find(".//default:end/default:xLgr", ns).text
                if tomador.find(".//default:end/default:xLgr", ns) is not None
                else None
            ),
            "numero": (
                tomador.find(".//default:end/default:nro", ns).text
                if tomador.find(".//default:end/default:nro", ns) is not None
                else None
            ),
            "complemento": (
                tomador.find(".//default:end/default:xCpl", ns).text
                if tomador.find(".//default:end/default:xCpl", ns) is not None
                else None
            ),
            "bairro": (
                tomador.find(".//default:end/default:xBairro", ns).text
                if tomador.find(".//default:end/default:xBairro", ns) is not None
                else None
            ),
            "cidade": (
                tomador.find(".//default:end/default:endNac/default:cMun", ns).text
                if tomador.find(".//default:end/default:endNac/default:cMun", ns)
                is not None
                else None
            ),
            "cep": (
                tomador.find(".//default:end/default:endNac/default:CEP", ns).text
                if tomador.find(".//default:end/default:endNac/default:CEP", ns)
                is not None
                else None
            ),
        }

        nfse_data[self.taker_field]["endereco"] = _address.copy()

        # Extract service data
        servico = root.find(".//default:serv", ns)
        nfse_data["servico"] = {
            "codigo_servico": servico.find(
                ".//default:cServ/default:cTribNac", ns
            ).text,
            "descricao_servico": servico.find(
                ".//default:cServ/default:xDescServ", ns
            ).text,
        }
        valor_servico_element = root.find(
            ".//default:valores/default:vServPrest/default:vServ", ns
        )
        nfse_data[self.service_value_field] = float(valor_servico_element.text)
        nfse_data["servico"]["valor_servico"] = nfse_data[self.service_value_field]
        tribut_element = root.find(
            ".//default:valores/default:trib/default:totTrib/default:pTotTribSN", ns
        )
        if tribut_element is None:
            # Handle
            v_tb = 6.0
        else:
            v_tb = float(str(tribut_element.text))
        nfse_data["servico"]["p_tributo_SN"] = v_tb

        # Set parsed data to the class attribute
        self.data = nfse_data
        self.date = nfse_data[self.date_field]
        self.file_data = file_data
        self.emitter = (
            self.data[self.emitter_field]["cnpj"]
            + " -- "
            + self.data[self.emitter_field]["nome"]
        )
        # hande NIF or CNPJ
        if self.data[self.taker_field]["cnpj"] is not None:
            self.taker = (
                self.data[self.taker_field]["cnpj"]
                + " (CNPJ) -- "
                + self.data[self.taker_field]["nome"]
            )
        elif self.data[self.taker_field]["nif"] is not None:
            self.taker = (
                self.data[self.taker_field]["nif"]
                + " (NIF) -- "
                + self.data[self.taker_field]["nome"]
            )
        else:
            self.taker = self.data[self.taker_field]["nome"]
        self.service_value = self.data[self.service_value_field]
        self.service_value_trib = nfse_data["servico"]["p_tributo_SN"]
        self.service_id = self.data["servico"]["codigo_servico"]


class NFSeColl(Collection):
    """
    A collection of :class:`NFSe` objects.

    Extends :class:`Collection` to load and aggregate multiple NFSe XML
    files into a shared catalog, either from a folder or an explicit list
    of file paths.
    """

    def __init__(self, base_object=NFSe, name="MyNFeCollection", alias="NFeCol0"):
        """
        Initialize the ``NFSeColl`` object.

        :param base_object: ``MbaE``-based object for collection
        :type base_object: :class:`MbaE`
        :param name: unique object name
        :type name: str
        :param alias: unique object alias. If None, it takes the first and last characters from name
        :type alias: str
        """
        # ------------ set pseudo-static ----------- #
        self.object_alias = "NFE_COL"
        # Set the name and baseobject attributes
        self.baseobject = base_object
        self.baseobject_name = base_object.__name__

        # Initialize the catalog with an empty DataFrame
        dict_metadata = self.baseobject().get_metadata()

        self.catalog = pd.DataFrame(columns=dict_metadata.keys())

        # Initialize the ``Collection`` as an empty dictionary
        self.collection = dict()

        # ------------ set mutables ----------- #
        self.size = 0

        self._set_fields()
        # ... continues in downstream objects ... #

    def load_folder(self, folder):
        """
        Load NFSe files from a folder

        :param folder: path to folder
        :type folder: str
        :return: None
        :rtype: None
        """
        from glob import glob

        lst_files = glob("{}/*.xml".format(folder))
        self.load_files(lst_files=lst_files)

    def load_files(self, lst_files):
        """
        Load NFSe files from a list of files

        :param lst_files: list of paths to files
        :type lst_files: list
        :return: None
        :rtype: None
        """
        for f in lst_files:
            nfe_id = "NFSe_" + os.path.basename(f).split(".")[0]
            nfe = NFSe(name=nfe_id, alias=nfe_id)
            nfe.load_data(file_data=f)
            self.append(new_object=nfe)


# CLASSES -- Module-level
# =======================================================================
# ... {develop}


# SCRIPT
# ***********************************************************************
# standalone behaviour as a script
if __name__ == "__main__":
    # Test doctests
    # ===================================================================
    import doctest

    doctest.testmod()

    # Script section
    # ===================================================================
    print("Hello world!")
    # ... {develop}

    # Script subsection
    # -------------------------------------------------------------------
    # ... {develop}

# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2025 The Project Authors
# See pyproject.toml for authors/maintainers.
# See LICENSE for license details.
"""
{Short module description (1-3 sentences)}
todo docstring

Features
--------
todo docstring

* {feature 1}
* {feature 2}
* {feature 3}
* {etc}

Overview
--------
todo docstring
{Overview description}

Examples
--------
todo docstring
{Examples in rST}

Print a message

.. code-block:: python

    # print message
    print("Hello world!")
    # [Output] >> 'Hello world!'


"""
# IMPORTS
# ***********************************************************************
# import modules from other libs

# Native imports
# =======================================================================
import os
import xml.etree.ElementTree as ET

# ... {develop}

# External imports
# =======================================================================
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
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
# ... {develop}


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
    def cashflow_analysis(df, category=None):
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

        df_monthly = CashFlow.monthly_summary(df, category)
        df_yearly = CashFlow.yearly_summary(df_monthly, category)

        return {
            "monthly": df_monthly.round(decimals=2),
            "yearly": df_yearly.round(decimals=2),
        }

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
    def monthly_summary(df, category):
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

            df_year["Fluxo"] = df_year["Entradas"] + df_year["Saidas"]

            df_year["Entradas_Acum"] = df_year["Entradas"].cumsum()
            df_year["Saidas_Acum"] = df_year["Saidas"].cumsum()
            df_year["Fluxo_Acum"] = df_year["Fluxo"].cumsum()

            monthly_frames.append(df_year)

        return pd.concat(monthly_frames, ignore_index=True)

    @staticmethod
    def yearly_summary(df_monthly, category):
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
        super().apply_drops(df=df)
        df = df.query("Lançamento != 'BB Rende Fácil'")
        df = df.query("Valor != '0,00 C'")
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

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

 - {feature 1}
 - {feature 2}
 - {feature 3}
 - {etc}

Overview
--------
todo docstring
{Overview description}

Examples
--------
todo docstring
{Examples in rST}

From the terminal, run:

.. code-block:: bash

    python ./tests/unit/test_module.py


"""

# ***********************************************************************
# IMPORTS
# ***********************************************************************
# import modules from other libs

# Native imports
# =======================================================================
# import {module}
import json
import tempfile
import unittest
from pathlib import Path

# ... {develop}

# External imports
# =======================================================================
import pandas as pd

# ... {develop}

# Project-level imports
# =======================================================================
from babilonia.accounting import CashFlow, CashFlowBBCC, CashFlowBBCCPJ, CashFlowBBPP
from tests.conftest import DATA_DIR
from tests.conftest import testprint

# ... {develop}


# ***********************************************************************
# CONSTANTS
# ***********************************************************************
# define constants in uppercase

# CONSTANTS -- Project-level
# =======================================================================
# ... {develop}

# CONSTANTS -- Module-level
# =======================================================================
# ... {develop}


# ***********************************************************************
# FUNCTIONS
# ***********************************************************************

# FUNCTIONS -- Project-level
# =======================================================================
# ... {develop}

# FUNCTIONS -- Module-level
# =======================================================================
# ... {develop}


# ***********************************************************************
# CLASSES
# ***********************************************************************

# CLASSES -- Project-level
# =======================================================================


class TestCashFlowBBCC(unittest.TestCase):

    # Setup methods
    # -------------------------------------------------------------------

    @classmethod
    def setUpClass(cls):
        """
        Runs once before all tests in this class.
        """
        cls.file_bbcc = DATA_DIR / "EXTRATO_BB_CC_2025-11_T0.csv"
        if not cls.file_bbcc.exists():
            raise FileNotFoundError(f"Test CSV not found: {cls.file_bbcc}")

        # ... {develop}
        return None

    def setUp(self):
        """
        Runs before each test method.
        """
        self.cashflow = CashFlowBBCC()
        # ... {develop}
        return None

    # Testing methods
    # -------------------------------------------------------------------

    def test_load_data(self):
        """
        Simple smoke test: load csv and print object.
        """
        self.cashflow.load_data(self.file_bbcc)

        print("********************** HEYyy")
        print(self.cashflow.data_raw)
        # Minimal sanity check (optional but recommended)
        self.assertIsInstance(self.cashflow.data_raw, pd.DataFrame)

        # Visual inspection
        print("\n--- Load OUTPUT ---")
        print(self.cashflow)
        print(self.cashflow.data_raw.info())

    def test_parse_data(self):
        self.cashflow.load_data(self.file_bbcc)
        df = self.cashflow.parse_data()
        print(type(df))
        print(df)
        print(df.info())
        self.assertIsInstance(df, pd.DataFrame)

    def test_standardize(self):
        self.cashflow.load_data(self.file_bbcc)
        self.cashflow.standardize()
        print(self.cashflow.data)
        print(self.cashflow.data.info())

    # Tear down methods
    # -------------------------------------------------------------------
    def tearDown(self):
        """
        Runs after each test method.
        """
        # ... {develop}
        return None

    @classmethod
    def tearDownClass(cls):
        """
        Runs once after all tests in this class.
        """
        # ... {develop}
        return None


class TestCashFlowBBCCPJ(TestCashFlowBBCC):

    # Setup methods
    # -------------------------------------------------------------------

    @classmethod
    def setUpClass(cls):
        """
        Runs once before all tests in this class.
        """
        cls.file_bbcc = DATA_DIR / "EXTRATO_BB_CCPJ_2025-11_T0.csv"
        if not cls.file_bbcc.exists():
            raise FileNotFoundError(f"Test CSV not found: {cls.file_bbcc}")

        # ... {develop}
        return None

    def setUp(self):
        """
        Runs before each test method.
        """
        self.cashflow = CashFlowBBCCPJ()
        # ... {develop}
        return None


class TestCashFlowBBPP(TestCashFlowBBCC):

    # Setup methods
    # -------------------------------------------------------------------

    @classmethod
    def setUpClass(cls):
        """
        Runs once before all tests in this class.
        """
        cls.file_bbcc = DATA_DIR / "EXTRATO_BB_PP_2025-08_T0.csv"
        if not cls.file_bbcc.exists():
            raise FileNotFoundError(f"Test CSV not found: {cls.file_bbcc}")

        # ... {develop}
        return None

    def setUp(self):
        """
        Runs before each test method.
        """
        self.cashflow = CashFlowBBPP()
        # ... {develop}
        return None


class TestCashFlowBalanceLevels(unittest.TestCase):
    """
    Balance panel and plot checked against ``levels.json`` rules, on a
    synthetic 24-month cash flow: a fixed monthly outflow, irregular
    inflows, and a scripted dry stretch (no inflows) in the first year.
    """

    # Setup methods
    # -------------------------------------------------------------------

    @classmethod
    def setUpClass(cls):
        """
        Runs once before all tests in this class.
        """
        inflows = {
            "2026-01": 14000,
            "2026-03": 9000,
            "2026-09": 22000,
            "2026-11": 18000,
            "2027-01": 12000,
            "2027-04": 15000,
            "2027-06": 11000,
            "2027-08": 16000,
            "2027-10": 13000,
        }
        rows = []
        for month in pd.period_range("2026-01", "2027-12", freq="M").astype(str):
            rows.append((f"{month}-01", -5500.0, "Saida fixa"))
            if month in inflows:
                rows.append((f"{month}-15", float(inflows[month]), "Entrada"))
        cls.df = pd.DataFrame(rows, columns=["Data", "Valor", "Categoria"])
        cls.df["Data"] = pd.to_datetime(cls.df["Data"])
        cls.df["Descricao"] = ""
        cls.initial_cash = 30000.0

        cls.rules = {
            "title": "Synthetic reserve",
            "levels": [
                {"name": "target", "value": 30000, "kind": "reference"},
                {"name": "alert", "value": 27000, "kind": "warning"},
                {"name": "minimum", "value": 15000, "kind": "critical"},
            ],
        }
        return None

    def setUp(self):
        """
        Runs before each test method.
        """
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        return None

    # Testing methods
    # -------------------------------------------------------------------

    def test_load_levels_missing_file(self):
        self.assertIsNone(CashFlow.load_levels(folder=self.folder))

    def test_load_levels_file(self):
        with open(self.folder / "levels.json", "w", encoding="utf-8") as f:
            json.dump(self.rules, f)
        rules = CashFlow.load_levels(folder=self.folder)
        self.assertEqual(rules["title"], "Synthetic reserve")
        self.assertEqual(len(rules["levels"]), 3)

    def test_load_levels_rejects_unknown_kind(self):
        bad = {"levels": [{"name": "x", "value": 1, "kind": "danger"}]}
        with open(self.folder / "levels.json", "w", encoding="utf-8") as f:
            json.dump(bad, f)
        with self.assertRaises(ValueError):
            CashFlow.load_levels(folder=self.folder)

    def test_load_levels_rejects_repeated_name(self):
        bad = {
            "levels": [
                {"name": "x", "value": 1, "kind": "warning"},
                {"name": "x", "value": 2, "kind": "critical"},
            ]
        }
        with open(self.folder / "levels.json", "w", encoding="utf-8") as f:
            json.dump(bad, f)
        with self.assertRaises(ValueError):
            CashFlow.load_levels(folder=self.folder)

    def test_load_levels_rejects_missing_value(self):
        bad = {"levels": [{"name": "x", "kind": "critical"}]}
        with open(self.folder / "levels.json", "w", encoding="utf-8") as f:
            json.dump(bad, f)
        with self.assertRaises(ValueError):
            CashFlow.load_levels(folder=self.folder)

    def test_load_levels_rejects_missing_levels_key(self):
        bad = {"title": "x", "level": [{"name": "x", "value": 1, "kind": "critical"}]}
        with open(self.folder / "levels.json", "w", encoding="utf-8") as f:
            json.dump(bad, f)
        with self.assertRaises(ValueError):
            CashFlow.load_levels(folder=self.folder)

    def test_load_levels_rejects_unknown_follow(self):
        # a value must not let a mistyped follow pass as a fixed level
        bad = {
            "levels": [{"name": "x", "follow": "peek", "value": 1, "kind": "critical"}]
        }
        with open(self.folder / "levels.json", "w", encoding="utf-8") as f:
            json.dump(bad, f)
        with self.assertRaises(ValueError):
            CashFlow.load_levels(folder=self.folder)

    def test_panel_without_levels(self):
        panel = CashFlow.get_balance_panel(df=self.df, initial_cash=self.initial_cash)
        self.assertEqual(len(panel), 24)
        self.assertTrue((panel["Status"] == "ok").all())
        expected = self.initial_cash + self.df["Valor"].sum()
        self.assertAlmostEqual(panel["Saldo"].iloc[-1], expected)

    def test_panel_static_levels(self):
        panel = CashFlow.get_balance_panel(
            df=self.df, initial_cash=self.initial_cash, levels=self.rules
        ).set_index("Mes")
        print(panel[["Saldo", "Status"]])
        # dry stretch: below alert from May, below minimum in August
        self.assertEqual(panel.loc["2026-04", "Status"], "ok")
        self.assertEqual(panel.loc["2026-05", "Status"], "warning")
        self.assertEqual(panel.loc["2026-08", "Status"], "critical")
        self.assertEqual(panel.loc["2027-12", "Status"], "ok")
        # a reference level never changes the status
        self.assertIn("Level_target", panel.columns)

    def test_panel_level_growth(self):
        levels = [
            {
                "name": "target",
                "value": 10000,
                "kind": "reference",
                "growth_yearly": 0.05,
            }
        ]
        panel = CashFlow.get_balance_panel(df=self.df, levels=levels)
        self.assertAlmostEqual(panel["Level_target"].iloc[0], 10000)
        self.assertAlmostEqual(panel["Level_target"].iloc[12], 10500)

    def test_panel_follow_peak(self):
        df = pd.DataFrame(
            {
                "Data": pd.to_datetime(
                    ["2026-01-10", "2026-02-10", "2026-03-10", "2026-04-10"]
                ),
                "Valor": [1000.0, -400.0, 300.0, 500.0],
            }
        )
        levels = [{"name": "peak", "follow": "peak", "kind": "critical"}]
        panel = CashFlow.get_balance_panel(df=df, initial_cash=0.0, levels=levels)
        data = panel.iloc[:4]  # Jan-Apr have data; May-Dec are padding
        self.assertListEqual(list(data["Level_peak"]), [1000, 1000, 1000, 1400])
        self.assertListEqual(list(data["Status"]), ["ok", "critical", "critical", "ok"])
        # after the data the peak holds its last value, with no status
        self.assertTrue((panel["Level_peak"].iloc[4:] == 1400).all())
        self.assertTrue((panel["Status"].iloc[4:] == "").all())

    def test_panel_saldos_anchor(self):
        # flows: Jan +1000, Feb -200, Mar +500 (on the 20th), Apr none
        df = pd.DataFrame(
            {
                "Data": pd.to_datetime(["2026-01-05", "2026-02-10", "2026-03-20"]),
                "Valor": [1000.0, -200.0, 500.0],
            }
        )
        # the bank adds interest the flows don't show: observed balances
        # run above the flow-implied ones
        saldos = pd.DataFrame(
            {
                "Data": pd.to_datetime(["2026-02-28", "2026-03-10", "2026-04-30"]),
                "Valor": [5000.0, 5100.0, 5650.0],
            }
        )
        panel = CashFlow.get_balance_panel(
            df=df, initial_cash=999999.0, saldos=saldos  # initial_cash ignored
        ).set_index("Mes")
        print(panel[["Fluxo", "Saldo", "Saldo_Fonte"]])
        # Jan: walked back from Feb 28 -> 5000 - (-200) = 5200
        self.assertAlmostEqual(panel.loc["2026-01", "Saldo"], 5200.0)
        self.assertEqual(panel.loc["2026-01", "Saldo_Fonte"], "calculado")
        # Feb: observed on its last day
        self.assertAlmostEqual(panel.loc["2026-02", "Saldo"], 5000.0)
        # Mar: observed on the 10th, plus the +500 after it
        self.assertAlmostEqual(panel.loc["2026-03", "Saldo"], 5600.0)
        self.assertEqual(panel.loc["2026-03", "Saldo_Fonte"], "observado")
        # Apr: no flows, but an observation -> range extends to it
        self.assertAlmostEqual(panel.loc["2026-04", "Saldo"], 5650.0)

    def test_panel_saldos_same_day_flow(self):
        # a balance observed on a day already includes that day's flows
        df = pd.DataFrame(
            {
                "Data": pd.to_datetime(["2026-05-15", "2026-05-15"]),
                "Valor": [300.0, -100.0],
            }
        )
        saldos = pd.DataFrame(
            {
                "Data": pd.to_datetime(["2026-05-15"]),
                "Valor": [2000.0],
            }
        )
        panel = CashFlow.get_balance_panel(df=df, saldos=saldos).set_index("Mes")
        self.assertAlmostEqual(panel.loc["2026-05", "Saldo"], 2000.0)

    def test_panel_saldos_only(self):
        # no statements at all: each month shows the latest reading,
        # carried flat into months without one
        empty = pd.DataFrame(
            {"Data": pd.to_datetime([]), "Valor": pd.Series([], dtype=float)}
        )
        saldos = pd.DataFrame(
            {
                "Data": pd.to_datetime(["2026-01-31", "2026-02-28", "2026-04-30"]),
                "Valor": [100.0, 120.0, 90.0],
            }
        )
        panel = CashFlow.get_balance_panel(df=empty, saldos=saldos).set_index("Mes")
        self.assertAlmostEqual(panel.loc["2026-03", "Saldo"], 120.0)
        self.assertEqual(panel.loc["2026-03", "Saldo_Fonte"], "calculado")
        self.assertAlmostEqual(panel.loc["2026-04", "Saldo"], 90.0)
        self.assertTrue((panel["Fluxo"] == 0).all())

    def test_panel_nothing_raises(self):
        empty = pd.DataFrame(
            {"Data": pd.to_datetime([]), "Valor": pd.Series([], dtype=float)}
        )
        with self.assertRaises(ValueError):
            CashFlow.get_balance_panel(df=empty)

    def test_panel_pads_to_whole_years(self):
        # data from March to June only, as in a run made mid-year
        df = pd.DataFrame(
            {
                "Data": pd.to_datetime(["2026-03-05", "2026-04-05", "2026-06-05"]),
                "Valor": [100.0, 100.0, 100.0],
            }
        )
        levels = [
            {
                "name": "target",
                "value": 1000,
                "kind": "reference",
                "growth_yearly": 0.12,
            }
        ]
        panel = CashFlow.get_balance_panel(df=df, initial_cash=500.0, levels=levels)
        self.assertListEqual(
            list(panel["Mes"]), [f"2026-{m:02d}" for m in range(1, 13)]
        )
        pad = panel["Mes"].isin(["2026-01", "2026-02", "2026-07", "2026-12"])
        self.assertTrue(panel.loc[pad, "Saldo"].isna().all())
        self.assertTrue((panel.loc[pad, "Status"] == "").all())
        self.assertTrue((panel.loc[pad, "Fluxo"] == 0).all())
        # a month inside the range without flows is data, not padding
        may = panel.set_index("Mes").loc["2026-05"]
        self.assertAlmostEqual(may["Saldo"], 700.0)
        self.assertEqual(may["Status"], "ok")
        # growth compounds from the first data month (March), both ways
        lv = panel.set_index("Mes")["Level_target"]
        self.assertAlmostEqual(lv["2026-03"], 1000.0)
        self.assertLess(lv["2026-01"], 1000.0)
        self.assertGreater(lv["2026-12"], lv["2026-06"])

    def test_plot_balance(self):
        panel = CashFlow.get_balance_panel(
            df=self.df, initial_cash=self.initial_cash, levels=self.rules
        )
        file_out = self.folder / "balance.jpg"
        CashFlow.plot_balance(panel=panel, file_out=file_out, levels=self.rules)
        self.assertTrue(file_out.exists())

    def test_plot_balance_long_series(self):
        # 5 years: above BALANCE_YEAR_TICKS_AFTER, so year-only labels
        df = pd.DataFrame(
            {
                "Data": pd.date_range("2023-01-15", periods=60, freq="MS")
                + pd.Timedelta(days=14),
                "Valor": [500.0] * 60,
            }
        )
        panel = CashFlow.get_balance_panel(
            df=df, initial_cash=10000.0, levels=self.rules
        )
        # Feb 2023 - Jan 2028 of data, padded to whole years: 2023-2028
        self.assertEqual(len(panel), 72)
        for forced in (None, False):
            file_out = self.folder / f"balance_long_{forced}.jpg"
            CashFlow.plot_balance(
                panel=panel, file_out=file_out, levels=self.rules, year_ticks=forced
            )
            self.assertTrue(file_out.exists())

    def test_plot_balance_without_levels(self):
        panel = CashFlow.get_balance_panel(df=self.df, initial_cash=self.initial_cash)
        file_out = self.folder / "balance_plain.jpg"
        CashFlow.plot_balance(panel=panel, file_out=file_out, title="Plain balance")
        self.assertTrue(file_out.exists())

    # Tear down methods
    # -------------------------------------------------------------------
    def tearDown(self):
        """
        Runs after each test method.
        """
        self.tmp.cleanup()
        return None


# ... {develop}

# CLASSES -- Module-level
# =======================================================================
# ... {develop}


# ***********************************************************************
# SCRIPT
# ***********************************************************************
# standalone behaviour as a script
if __name__ == "__main__":

    # Call all tests in the module
    # ===================================================================
    unittest.main()

    # ... {develop}

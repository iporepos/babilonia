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
import unittest

# ... {develop}

# External imports
# =======================================================================
import pandas as pd

# ... {develop}

# Project-level imports
# =======================================================================
from babilonia.accounting import CashFlowBBCC, CashFlowBBCCPJ, CashFlowBBPP
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

        # Minimal sanity check (optional but recommended)
        self.assertIsInstance(self.cashflow.data, pd.DataFrame)

        # Visual inspection
        print("\n--- Load OUTPUT ---")
        print(self.cashflow)
        print(self.cashflow.data.info())

    def test_parse_data(self):
        self.cashflow.load_data(self.file_bbcc)
        df = self.cashflow.parse_data()
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

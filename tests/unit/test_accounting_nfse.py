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
# import {module}
# ... {develop}

# Project-level imports
# =======================================================================
from babilonia.accounting import NFSe
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


class TestNFSe(unittest.TestCase):

    # Setup methods
    # -------------------------------------------------------------------

    @classmethod
    def setUpClass(cls):
        """
        Runs once before all tests in this class.
        """
        cls.file = DATA_DIR / "NFSe_001.xml"
        if not cls.file.exists():
            raise FileNotFoundError(f"Test XML not found: {cls.file}")

        # ... {develop}
        return None

    def setUp(self):
        """
        Runs before each test method.
        """
        self.nfse = NFSe()
        # ... {develop}
        return None

    # Testing methods
    # -------------------------------------------------------------------

    def test_load_and_print(self):
        """
        Simple smoke test: load XML and print object.
        """
        self.nfse.load_data(self.file)

        # Minimal sanity check (optional but recommended)
        self.assertIsNotNone(self.nfse.data)

        # Visual inspection
        print("\n--- NFSe OUTPUT ---")
        print(self.nfse)
        print("-------------------")

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

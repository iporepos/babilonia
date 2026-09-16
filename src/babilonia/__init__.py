# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2025 The Project Authors
# See pyproject.toml for authors/maintainers.
# See LICENSE for license details.
"""
babilonia — Python library for accounting and personal finance in Brazil.

Exposes :mod:`babilonia.root` for foundational base classes and
:mod:`babilonia.accounting` for Brazil-specific tools including bank
statement parsers, cash flow analysis, budget records, and NFSe invoices.
"""
# EXPOSE MODULES FROM PACKAGE
# ***********************************************************************
from . import root
from . import accounting

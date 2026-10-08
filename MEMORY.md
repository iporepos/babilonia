## Memory Log

- 2026-10-08 | `categorize.py`: raised the on-screen "top uncategorized descriptions" preview from 10 to 20 rows (new `DEFAULT_UNCATEGORIZED_PREVIEW` constant), and changed its ranking from occurrence count to total absolute value (grouped by description, each row now shows total value and count) -- lets the user prioritize the descriptions with the biggest cashflow impact first. Added a `Transacoes` (transaction count) column to the yearly category summary table and CSV export.
- 2026-09-16 | Improved README with a gallery of API and CLI tool use cases covering all four tools and the main accounting classes.
- 2026-09-16 | Revised major docstrings for harmonization: replaced placeholder templates in `__init__.py` and `accounting.py`; improved `root.py` module docstring; added missing class docstrings for `Budget`, `BBCDB`, and `NFSeColl`.

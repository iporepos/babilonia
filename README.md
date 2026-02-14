![Style Status](https://github.com/iporepos/babilonia/actions/workflows/style.yaml/badge.svg)
![Docs Status](https://github.com/iporepos/babilonia/actions/workflows/docs.yaml/badge.svg)
![Tests Status](https://github.com/iporepos/babilonia/actions/workflows/tests.yaml/badge.svg)
![Top Language](https://img.shields.io/github/languages/top/iporepos/babilonia)
![Status](https://img.shields.io/badge/status-development-yellow.svg)
[![Code Style](https://img.shields.io/badge/style-black-000000.svg)](https://github.com/psf/black)
[![Documentation](https://img.shields.io/badge/docs-online-blue)](https://iporepos.github.io/babilonia/)
[![PyPI Latest Release](https://img.shields.io/pypi/v/babilonia.svg?label=PyPI)](https://pypi.org/project/babilonia/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/babilonia.svg?label=PyPI%20downloads)](
https://pypi.org/project/babilonia/)

<a logo>
<img src="https://raw.githubusercontent.com/iporepos/babilonia/master/docs/figs/logo.png" height="130" width="130">
</a>

---

# babilonia

Handle accounting and finances in Brazil using Python.

> [!NOTE]
> Check out the [documentation website](https://iporepos.github.io/babilonia/)

# Quick Gallery

## Parse Bank Statements

Sourced statement from Banco do Brasil:

```text
./extrato_poupanca.csv
    "Data","Histórico","Valor",
    "01/08/2025","Reajuste Monetário - BACEN","3,04 C",
    "01/08/2025","Juros","8,83 C",
    "01/08/2025","Reajuste Monetário - BACEN","1,34 C",
    "01/08/2025","Juros","3,83 C",
    "01/08/2025","Reajuste Monetário - BACEN","16,67 C",
    "01/08/2025","Juros","47,92 C",
    "11/08/2025","Transferência de Crédito","1.000,00 C",
    "29/08/2025","Transferência de Crédito","4.000,00 C",
    "29/08/2025","Reajuste Monetário - BACEN","0,35 C",
    "29/08/2025","Juros","1,02 C",
```

Code block:
```python
from babilonia.accounting import CashFlowBBPP
file_bb = "./extrato_poupanca.csv"
cashflow = CashFlowBBPP()
cashflow.load_data(file_bb)
df = cashflow.parse_data()
print(df)
```

Output:
```text
Data           Valor                   Categoria Descricao
2025-08-01      3.04  Reajuste Monetário - BACEN
2025-08-01      8.83                       Juros
2025-08-01      1.34  Reajuste Monetário - BACEN
2025-08-01      3.83                       Juros
2025-08-01     16.67  Reajuste Monetário - BACEN
2025-08-01     47.92                       Juros
2025-08-11   1000.00    Transferência de Crédito
2025-08-29   4000.00    Transferência de Crédito
2025-08-29      0.35  Reajuste Monetário - BACEN
2025-08-29      1.02                       Juros
```
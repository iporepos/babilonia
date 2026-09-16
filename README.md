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

---

# Install

```bash
python -m pip install babilonia
```

---

# Quick Gallery

## API

### Parse bank statement CSV

Convert raw bank exports to a canonical `pandas.DataFrame`.

Input (`extrato_poupanca.csv` from Banco do Brasil):

```text
"Data","Histórico","Valor",
"01/08/2025","Juros","3,83 C",
"01/08/2025","Reajuste Monetário - BACEN","16,67 C",
"11/08/2025","Transferência de Crédito","1.000,00 C",
```

```python
from babilonia.accounting import CashFlowBBPP

cf = CashFlowBBPP()
cf.load_data("./extrato_poupanca.csv")
cf.standardize()
print(cf.data)
```

```text
        Data    Valor                   Categoria Descricao
  2025-08-01     3.83                       Juros
  2025-08-01    16.67  Reajuste Monetário - BACEN
  2025-08-11  1000.00    Transferência de Crédito
```

Supported account types: `CashFlowBBCC`, `CashFlowBBCCPJ`, `CashFlowBBPP`, `CashFlowNUCredit`.

---

### Cash flow analysis

Compute monthly and yearly summaries from a canonical cash flow file.

```python
from babilonia.accounting import CashFlow

cf = CashFlow()
cf.load_data("./caixa_diario.csv")

dc = CashFlow.get_cashflow_report(df=cf.data, year=2025, initial_cash=5000.0)
print(dc["Summary"])
print(dc["Pannel"])
```

```text
   Ano   Categoria     Total     Media  % Entradas
  2025    ENTRADAS  18200.00   1516.67      100.00
  2025      SAIDAS  -9430.00   -785.83       51.81
  2025     Moradia  -3200.00   -266.67       17.58
  2025  Alimentacao  -1800.00   -150.00        9.89

   Mes  Entradas   Saidas    Fluxo      Saldo
2025-01   1500.0  -780.0    720.0     5720.0
2025-02   1500.0  -810.0    690.0     6410.0
     ...
```

---

### Parse NFSe XML

Load and inspect a Nota Fiscal de Serviços Eletrônica from `nfse.gov.br`.

```python
from babilonia.accounting import NFSe

nf = NFSe()
nf.load_data("./nfse.xml")
print(nf.date)           # '2025-09-01'
print(nf.emitter)        # '27543216700666 -- PRESTADOR LTDA'
print(nf.taker)          # '07704429000666 (CNPJ) -- TOMADOR LTDA'
print(nf.service_value)  # 6666.0
```

---

### Batch-load NFSe files

Aggregate a folder of NFSe XML files into a single catalog.

```python
from babilonia.accounting import NFSeColl

coll = NFSeColl()
coll.load_folder("./notas_fiscais/")
print(coll.catalog[["name", "Date", "ValorServico", "Prestador"]])
```

```text
          name        Date  ValorServico                          Prestador
  NFSe_NF0080  2025-09-01        6666.0  27543216700666 -- PRESTADOR LTDA
  NFSe_NF0081  2025-10-01        5000.0  27543216700666 -- PRESTADOR LTDA
```

---

## Command-line tools

The `babilonia.tools` scripts form a processing pipeline: raw exports → standardized files → cash flow reports.

### Standardize raw bank exports

Reads T0 raw CSV files and writes T1 canonical CSVs in the same folder tree.

```bash
python -m babilonia.tools.parse --folder ./data --type bb-cc --year 2025
```

Available `--type` values: `bb-cc`, `bb-pp`, `bb-ccpj`, `bb-cdb`, `nubank-credito`.

---

### Build cash flow reports

Aggregates T1 files into daily, monthly, and annual summaries. Omit `--year` to process all years.

```bash
python -m babilonia.tools.cashflow --folder ./data --type bb-cc
```

---

### Categorize and report by label

Fills the `Categoria` column using a keyword dictionary, then prints and exports a monthly breakdown by category.

```bash
python -m babilonia.tools.categorize --folder ./data --type nubank-credito --year 2025
```

---

### Yearly cash flow report

Reads the consolidated daily file and prints a formatted yearly panel and category summary.

```bash
python -m babilonia.tools.report --folder ./data --type bb-cc --year 2025
```

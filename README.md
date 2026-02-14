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

# Install easily

```bash
python -m pip install babilonia
```

---

# Quick Gallery

## Parse weird CSV bank statements

Convert CSV files sourced from banks to ``pandas.DataFrame``. 

Input (sourced statement from Banco do Brasil)

```text
./extrato_poupanca.csv
    "Data","Histórico","Valor",
    "01/08/2025","Juros","3,83 C",
    "01/08/2025","Reajuste Monetário - BACEN","16,67 C",
    "01/08/2025","Juros","47,92 C",
    "11/08/2025","Transferência de Crédito","1.000,00 C",
```

Code block:
```python
from babilonia.accounting import CashFlowBBPP
file_bb = "./extrato_poupanca.csv"
cf = CashFlowBBPP()
cf.load_data(file_bb)
cf.standardize()
print(type(cf.data))
print(cf)
```

Output:
```text
<class 'pandas.core.frame.DataFrame'>
Data           Valor                   Categoria Descricao
2025-08-01      3.83                       Juros
2025-08-01     16.67  Reajuste Monetário - BACEN
2025-08-01     47.92                       Juros
2025-08-11   1000.00    Transferência de Crédito
```

## Parse XML Fiscal Notes (NFSe)

Convert XML files sourced from nfse.gov.br as a Python ``dict``. 

Code block:
```python
import pprint
from babilonia.accounting import NFSe
file_nfse = "./nfse.xml"
nf = NFSe()
nf.load_data(file_nfse)
print(type(nf.data))
pprint.pp(nf.data)
```

Output:
```text
<class 'dict'>
{'nfse_id': 'NFS43149022227643216000121000000000008025091789495666',
 'local_emissao': 'Fortaleza',
 'local_prestacao': 'Fortaleza',
 'numero_nfse': '80',
 'codigo_local_incidencia': '6314902',
 'descricao_servico': 'Serviços de pesquisas de qualquer natureza',
 'valor_liquido': 3100.0,
 'data_processo': '2025-09-01T15:36:35-03:00',
 'Date': '2025-09-01',
 'Prestador': {'cnpj': '27543216700666',
               'nome': 'PRESTADOR LTDA',
               'endereco': {'logradouro': 'R DAS ACACIAS',
                            'numero': '1244',
                            'bairro': 'CIDADE ALTA',
                            'cidade': '4314902',
                            'uf': 'CE',
                            'cep': '90880480'},
               'telefone': '5132692269',
               'email': 'PRESTADOR@GMAIL.COM'},
 'Tomador': {'cnpj': '07704429000666',
             'nif': None,
             'nome': 'TOMADOR LTDA',
             'endereco': {'logradouro': 'AV BRASIL',
                          'numero': '666',
                          'complemento': 'SALA  666 E 666',
                          'bairro': 'CENTRO HISTORICO',
                          'cidade': '6314902',
                          'cep': '34020023'}},
 'servico': {'codigo_servico': '020101',
             'descricao_servico': 'Serviço de suporte técnico.',
             'valor_servico': 6666.0,
             'p_tributo_SN': 6.0},
 'ValorServico': 6666.0}
```

"""
Credit classification according to Lei 11.101/2005 (Art. 83 and 84).

Each CDA component is classified as EXTRACONCURSAL (post-bankruptcy, Art. 84)
or CONCURSAL (pre-bankruptcy, Art. 83) based on the fiscal execution year relative
to the bankruptcy decree date.

CONCURSAL breakdown (Art. 83):
  - Trabalhista (Art. 83, I)  : verba honorária up to 150 × SM (R$ 1,518.00)
  - Tributário  (Art. 83, III): principal + correção monetária + juros do principal
  - Quirografário (Art. 83, VI): verba honorária exceeding 150 SM cap
  - Subquirografário (Art. 83, VIII): multa tributária + juros de multa

EXTRACONCURSAL breakdown (Art. 84):
  - Restituição        : return of goods/assets
  - Trabalhista        : honorários administrativos post-bankruptcy
  - Taxa Judiciária    : court-fee tax debt without a prior execution
  - Fatos Posteriores  : other tax facts arising after bankruptcy
"""

import re
from dataclasses import dataclass
from typing import Optional

from models import CalculationReport

LIMITE_SM = 150 * 1518.00  # R$ 227,700.00


@dataclass
class CreditClassification:
    extra_restituicao: float = 0.0
    extra_trabalhista: float = 0.0
    extra_taxa_judiciaria: float = 0.0
    extra_fatos_posteriores: float = 0.0
    conc_trabalhista: float = 0.0
    conc_tributario: float = 0.0
    conc_quirografario: float = 0.0
    conc_subquirografario: float = 0.0

    @property
    def total_extraconcursal(self) -> float:
        return (self.extra_restituicao + self.extra_trabalhista +
                self.extra_taxa_judiciaria + self.extra_fatos_posteriores)

    @property
    def total_concursal(self) -> float:
        return (self.conc_trabalhista + self.conc_tributario +
                self.conc_quirografario + self.conc_subquirografario)

    @property
    def total(self) -> float:
        return self.total_extraconcursal + self.total_concursal

    def rows(self):
        """Return (label, value, is_subtotal, is_extra) tuples for table rendering."""
        return [
            ("Restituição",                                      self.extra_restituicao,       False, True),
            ("Trabalhista",                                      self.extra_trabalhista,        False, True),
            ("Taxa Judiciária",                                  self.extra_taxa_judiciaria,    False, True),
            ("Fatos Geradores Posteriores à Quebra",             self.extra_fatos_posteriores,  False, True),
            ("Trabalhista – Art. 83, I (até 150 SM)",            self.conc_trabalhista,         False, False),
            ("Tributário – Art. 83, III",                        self.conc_tributario,          False, False),
            ("Quirografário – Art. 83, VI",                      self.conc_quirografario,       False, False),
            ("Subquirografário – Art. 83, VIII",                 self.conc_subquirografario,    False, False),
        ]


def _exec_year(exec_num: str) -> Optional[int]:
    m = re.search(r'\.(\d{4})\.8\.26\.', exec_num)
    return int(m.group(1)) if m else None


def classify_credits(calc: CalculationReport) -> CreditClassification:
    """Classify all CDA credits per Lei 11.101/2005 Art. 83/84."""
    fal_year = int(calc.data_falencia.split('/')[-1])

    extra_restituicao = 0.0
    extra_trabalhista = 0.0
    extra_taxa_judiciaria = 0.0
    extra_fatos_posteriores = 0.0

    conc_tributario = 0.0
    conc_subquirografario = 0.0
    conc_verba_pool = 0.0

    for group in calc.cnpj_groups:
        for cda in group.cdas:
            year = _exec_year(cda.execucao_fiscal) if cda.execucao_fiscal else None
            is_post = (year is None) or (year >= fal_year)

            if is_post:
                # EXTRACONCURSAL (Art. 84)
                tax_base = (cda.principal + cda.correcao + cda.juros_principal +
                            cda.multa + cda.juros_multa + cda.verba_honoraria)
                extra_trabalhista += cda.honorarios_adm
                if 'taxa' in cda.tipo_debito.lower():
                    extra_taxa_judiciaria += tax_base
                else:
                    extra_fatos_posteriores += tax_base
            else:
                # CONCURSAL (Art. 83)
                # Art. 83, III: principal + correção + juros do principal
                conc_tributario += cda.principal + cda.correcao + cda.juros_principal
                # Art. 83, VIII: multa tributária + juros de multa
                conc_subquirografario += cda.multa + cda.juros_multa
                # Verba honorária pooled for 150 SM cap
                conc_verba_pool += cda.verba_honoraria

    conc_trabalhista = min(conc_verba_pool, LIMITE_SM)
    conc_quirografario = max(0.0, conc_verba_pool - LIMITE_SM)

    return CreditClassification(
        extra_restituicao=extra_restituicao,
        extra_trabalhista=extra_trabalhista,
        extra_taxa_judiciaria=extra_taxa_judiciaria,
        extra_fatos_posteriores=extra_fatos_posteriores,
        conc_trabalhista=conc_trabalhista,
        conc_tributario=conc_tributario,
        conc_quirografario=conc_quirografario,
        conc_subquirografario=conc_subquirografario,
    )

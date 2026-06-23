from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class CDA:
    number: str
    principal: float
    correcao: float
    juros_principal: float
    multa: float
    juros_multa: float
    honorarios_adm: float
    verba_honoraria: float
    valor_total: float
    situacao: str
    tipo_debito: str
    execucao_fiscal: Optional[str]


@dataclass
class CNPJGroup:
    cnpj: str
    company: str
    data_falencia: str
    data_base: str
    cdas: List[CDA] = field(default_factory=list)

    @property
    def valor_total(self) -> float:
        return sum(c.valor_total for c in self.cdas)

    @property
    def principal_total(self) -> float:
        return sum(c.principal for c in self.cdas)


@dataclass
class CalculationReport:
    company: str
    data_falencia: str
    data_base: str
    cnpj_groups: List[CNPJGroup] = field(default_factory=list)

    @property
    def unique_executions(self) -> List[str]:
        seen = set()
        result = []
        for g in self.cnpj_groups:
            for c in g.cdas:
                if c.execucao_fiscal and c.execucao_fiscal not in seen:
                    seen.add(c.execucao_fiscal)
                    result.append(c.execucao_fiscal)
        return result

    @property
    def cdas_by_execution(self) -> Dict[str, List[CDA]]:
        result: Dict[str, List[CDA]] = {}
        for g in self.cnpj_groups:
            for c in g.cdas:
                if c.execucao_fiscal:
                    result.setdefault(c.execucao_fiscal, []).append(c)
        return result

    @property
    def valor_total_geral(self) -> float:
        return sum(g.valor_total for g in self.cnpj_groups)

    @property
    def all_cnpjs(self) -> List[str]:
        return [g.cnpj for g in self.cnpj_groups]


@dataclass
class ProcessEvent:
    date: str
    description: str

    @property
    def is_suspension(self) -> bool:
        low = self.description.lower()
        return any(t in low for t in ['suspen', 'suspensão', 'suspensa', 'suspenso'])

    @property
    def is_extinction(self) -> bool:
        low = self.description.lower()
        return any(t in low for t in [
            'extint', 'extinção', 'extinta', 'extinto',
            'arquiv', 'cancelam', 'prescri',
        ])

    @property
    def is_bankruptcy_related(self) -> bool:
        low = self.description.lower()
        return any(t in low for t in [
            'falênc', 'massas', 'administrador judicial',
            'insolvênc', 'concordat',
        ])


@dataclass
class ESAJProcessInfo:
    process_number: str
    status: str = "Não Consultado"
    classe: str = ""
    assunto: str = ""
    distribuicao: str = ""
    juiz: str = ""
    valor_acao: str = ""
    parties: List[str] = field(default_factory=list)
    events: List[ProcessEvent] = field(default_factory=list)
    error: Optional[str] = None
    query_date: str = ""
    source: str = "esaj"  # "esaj", "demo", "manual"

    @property
    def is_suspended(self) -> bool:
        low = self.status.lower()
        if any(t in low for t in ['suspen', 'paralis']):
            return True
        return any(e.is_suspension for e in self.events[:5])

    @property
    def is_extinct(self) -> bool:
        low = self.status.lower()
        if any(t in low for t in ['extint', 'arquiv', 'cancela']):
            return True
        return any(e.is_extinction for e in self.events[:5])

    @property
    def suspension_event(self) -> Optional[ProcessEvent]:
        for e in self.events:
            if e.is_suspension:
                return e
        return None

    @property
    def extinction_event(self) -> Optional[ProcessEvent]:
        for e in self.events:
            if e.is_extinction:
                return e
        return None

    @property
    def last_event(self) -> Optional[ProcessEvent]:
        return self.events[0] if self.events else None

    @property
    def status_badge(self) -> str:
        if self.error:
            return "ERRO"
        if self.is_extinct:
            return "EXTINTO"
        if self.is_suspended:
            return "SUSPENSO"
        if self.status == "Não Consultado":
            return "NÃO CONSULTADO"
        return "ATIVO"

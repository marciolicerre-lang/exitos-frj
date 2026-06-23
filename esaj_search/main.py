#!/usr/bin/env python3
"""
SAEF – Sistema de Acompanhamento de Execuções Fiscais
Pesquisa processual no ESAJ TJSP a partir de planilha de cálculo de falência.

Uso:
    python main.py planilha.pdf [--output relatorio.pdf] [--demo] [--delay 2.5]

Opções:
    planilha.pdf      Caminho para o PDF da planilha de cálculo de falência
    --output          Caminho do relatório PDF a gerar (padrão: relatorio_esaj_AAAA-MM-DD.pdf)
    --demo            Usar dados de demonstração (sem acesso ao ESAJ)
    --delay N         Intervalo em segundos entre consultas ao ESAJ (padrão: 2.5)
    --execucoes       Lista manual de números de execução (separados por vírgula), ignora PDF
"""

import argparse
import os
import sys
from datetime import datetime
from typing import Dict, Optional

# Ensure this script's directory is in the path
sys.path.insert(0, os.path.dirname(__file__))

from models import CalculationReport, ESAJProcessInfo
from pdf_parser import parse_calculation_pdf
from esaj_scraper import ESAJScraper
from demo_data import get_demo_calculation, get_demo_esaj_results
from report_generator import generate_report


def _fmt_brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Pesquisa processual ESAJ TJSP para execuções fiscais",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("pdf", nargs="?", help="Planilha de cálculo PDF")
    parser.add_argument("--output", "-o", default="", help="Caminho do relatório PDF de saída")
    parser.add_argument("--demo", action="store_true", help="Usar dados de demonstração")
    parser.add_argument("--delay", type=float, default=2.5, help="Intervalo entre consultas (seg)")
    parser.add_argument(
        "--execucoes", default="",
        help="Lista de execuções fiscais separadas por vírgula (pula análise do PDF)"
    )
    return parser.parse_args()


def _load_calculation(args) -> CalculationReport:
    """Load calculation data from PDF or demo."""
    if args.demo or not args.pdf:
        print("  → Usando dados de demonstração (Transportes Panazzolo Ltda)")
        return get_demo_calculation()

    pdf_path = args.pdf
    if not os.path.isfile(pdf_path):
        print(f"  [ERRO] Arquivo não encontrado: {pdf_path}")
        sys.exit(1)

    print(f"  → Analisando planilha de cálculo: {pdf_path}")
    calc = parse_calculation_pdf(pdf_path)

    if not calc.unique_executions:
        print("  [AVISO] Nenhuma execução fiscal encontrada no PDF; usando dados de demonstração.")
        return get_demo_calculation()

    return calc


def _query_esaj(
    calc: CalculationReport,
    args,
    demo_mode: bool,
) -> Dict[str, ESAJProcessInfo]:
    """Query ESAJ for all unique executions, or return demo data."""
    if demo_mode or args.demo:
        print("  → Carregando dados ESAJ de demonstração...")
        demo = get_demo_esaj_results()
        # Keep only executions present in calc
        return {k: v for k, v in demo.items() if k in calc.unique_executions}

    executions = calc.unique_executions

    # Allow manual override of execution list
    if args.execucoes:
        executions = [e.strip() for e in args.execucoes.split(",") if e.strip()]

    scraper = ESAJScraper(delay=args.delay)
    results: Dict[str, ESAJProcessInfo] = {}

    print(f"  → Consultando {len(executions)} execuções no ESAJ TJSP...")
    for i, exec_num in enumerate(executions, 1):
        print(f"     [{i}/{len(executions)}] {exec_num} ... ", end="", flush=True)
        info = scraper.query(exec_num)

        if info.error:
            print(f"ERRO: {info.error[:60]}")
        else:
            print(f"OK – {info.status_badge}")

        results[exec_num] = info

    # If all failed (likely no ESAJ access), fall back to demo
    all_errors = all(
        r.error or r.status in ("Sem Conexão", "Não Consultado", "CAPTCHA")
        for r in results.values()
    )
    if all_errors and results:
        print("\n  [AVISO] Todas as consultas falharam. Ativando modo demonstração.")
        demo = get_demo_esaj_results()
        return {k: demo.get(k, results[k]) for k in results}

    return results


def main():
    args = _parse_args()

    print("\n" + "=" * 60)
    print("  SAEF – Pesquisa Processual – Execuções Fiscais")
    print("=" * 60)

    # 1. Load calculation data
    print("\n[1/3] Carregando planilha de cálculo...")
    calc = _load_calculation(args)

    print(f"      Empresa: {calc.company}")
    print(f"      Falência: {calc.data_falencia}")
    print(f"      Data-base: {calc.data_base}")
    print(f"      CNPJs: {', '.join(calc.all_cnpjs)}")
    print(f"      Execuções únicas: {len(calc.unique_executions)}")
    print(f"      CDAs totais: {sum(len(g.cdas) for g in calc.cnpj_groups)}")
    print(f"      Valor total: {_fmt_brl(calc.valor_total_geral)}")

    if calc.unique_executions:
        print("\n      Execuções identificadas:")
        for e in calc.unique_executions:
            cdas = calc.cdas_by_execution.get(e, [])
            val = sum(c.valor_total for c in cdas)
            print(f"        • {e}  ({len(cdas)} CDA(s) – {_fmt_brl(val)})")

    # 2. Query ESAJ
    print("\n[2/3] Consultando ESAJ TJSP...")

    # Detect if we need demo mode (no PDF provided and no explicit ESAJ access)
    demo_forced = args.demo or not args.pdf
    esaj_results = _query_esaj(calc, args, demo_forced)

    # 3. Generate report
    print("\n[3/3] Gerando relatório PDF...")

    if not args.output:
        date_str = datetime.now().strftime("%Y-%m-%d")
        output_path = os.path.join(
            os.path.dirname(args.pdf) if args.pdf else ".",
            f"relatorio_esaj_{date_str}.pdf",
        )
    else:
        output_path = args.output

    generated = generate_report(calc, esaj_results, output_path)

    print(f"\n  ✓ Relatório gerado: {generated}")
    print(f"  Tamanho: {os.path.getsize(generated):,} bytes")
    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    main()

"""
Ponto de entrada do projeto.

Uso:
python executa_tudo.py dataset_01_parceiroA.csv

"""

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from estatistica_utilizada import analyze_file
from gerar_relatorio import generate_pdf_report


def append_history_csv(analysis: dict, history_path: str | Path) -> Path:
"""Adiciona um resumo do teste ao histórico em CSV."""
    path = Path(history_path)
    path.parent.mkdir(parents=True, exist_ok=True)

evidence = analysis["decision_evidence"]
    row = {
    "data_registro_utc": datetime.now(timezone.utc).isoformat(),
        "nome_teste": analysis["test_name"],
        "descricao": (
            f"Teste de cashback com {len(analysis['quality']['groups'])} variantes "
            f"para {', '.join(analysis['quality']['partners'])}"
        ),
        "arquivo": analysis["input_file"],
        "periodo_inicio": analysis["quality"]["date_start"],
        "periodo_fim": analysis["quality"]["date_end"],
        "resultado": evidence["signal"],
        "variante_candidata": evidence["candidate_group"],
        "decisao_tomada": "PENDENTE_DE_INTERPRETACAO_DO_AGENTE",
        "versao_analise": analysis["analysis_version"],
    }

    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Analisa um teste de cashback.")
    parser.add_argument("input_file", help="Caminho do CSV, XLSX ou JSON")
    parser.add_argument("--output-dir", default="outputs")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    analysis = analyze_file(args.input_file)
    stem = Path(args.input_file).stem

    json_path = output_dir / f"{stem}_analise.json"
    json_path.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_path = generate_pdf_report(
        analysis,
        output_dir / f"{stem}_relatorio.pdf",


    )
    

    history_path = append_history_csv(
        analysis,
        output_dir / "historico_testes.csv",
    )

    print("Análise concluída.")
    print(f"Sinal: {analysis['decision_evidence']['signal']}")
    print(f"Candidato: {analysis['decision_evidence']['candidate_group']}")
    print(f"JSON: {json_path}")
    print(f"Relatorio PDF: {report_path}")
    print(f"Historico: {history_path}")


if __name__ == "__main__":
    main()

"""Gera o relatorio final diretamente em PDF."""

from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

import modelo_relatorio as template


def brl(value: float | int | None) -> str:
    """Formata um numero como moeda brasileira."""
    if value is None:
        return "-"
    text = f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {text}"


def pct(value: float | int | None) -> str:
    """Formata um numero como percentual."""
    if value is None:
        return "-"
    return f"{float(value):.2f}%".replace(".", ",")


def signal_label(signal: str) -> str:
    labels = {
        "forte_candidato": "Forte candidato à escala",
        "promissor_com_ressalvas": "Promissor, com ressalvas",
        "inconclusivo": "Resultado inconclusivo",
    }
    return labels.get(signal, signal)


def _hex(hex_color: str):
    return colors.HexColor(hex_color)


def _build_styles():
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=_hex(template.DARK_COLOR),
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=_hex(template.MUTED_COLOR),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=_hex(template.ACCENT_COLOR),
            spaceBefore=10,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodySmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=_hex(template.DARK_COLOR),
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Hero",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=18,
            textColor=_hex(template.DARK_COLOR),
            alignment=TA_CENTER,
        )
    )
    return styles


def _page_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(_hex(template.BORDER_COLOR))
    canvas.line(15 * mm, 10 * mm, landscape(A4)[0] - 15 * mm, 15 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(_hex(template.MUTED_COLOR))
    canvas.drawString(15 * mm, 6 * mm, f"{template.AUTHOR} - Análise de cashback")
    canvas.drawRightString(
        landscape(A4)[0] - 15 * mm,
        6 * mm,
        f"Página {doc.page}",
    )
    canvas.restoreState()


def _base_table(data, column_widths=None, header=True, font_size=7.5):
    table = Table(data, colWidths=column_widths, repeatRows=1 if header else 0)
    style = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold" if header else "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("LEADING", (0, 0), (-1, -1), font_size + 3),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.35, _hex(template.BORDER_COLOR)),
    ]
    if header:
        style.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _hex(template.TABLE_HEADER_BACKGROUND)),
                ("TEXTCOLOR", (0, 0), (-1, 0), _hex(template.DARK_COLOR)),
            ]
        )
    table.setStyle(TableStyle(style))
    return table


def _section_executive_summary(analysis, styles):
    evidence = analysis["decision_evidence"]
    story = [Paragraph(template.SECTION_TITLES["executive_summary"], styles["SectionTitle"])]

    hero = Table(
        [[Paragraph(
            f"<b>{signal_label(evidence['signal'])}</b><br/>Variante candidata: {evidence['candidate_group']}",
            styles["Hero"],
        )]],
        colWidths=[230 * mm],
    )
    hero.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _hex(template.LIGHT_BACKGROUND)),
                ("BOX", (0, 0), (-1, -1), 1, _hex(template.ACCENT_COLOR)),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.extend([hero, Spacer(1, 7)])

    story.append(Paragraph("<b>Evidências favoráveis</b>", styles["BodySmall"]))
    for item in evidence["reasons"]:
        story.append(Paragraph(f"- {item}", styles["BodySmall"]))

    story.append(Paragraph("<b>Ressalvas</b>", styles["BodySmall"]))
    cautions = evidence["cautions"] or ["Nenhuma ressalva adicional foi gerada pelo motor."]
    for item in cautions:
        story.append(Paragraph(f"- {item}", styles["BodySmall"]))
    return story


def _section_data_quality(analysis, styles):
    quality = analysis["quality"]
    story = [Paragraph(template.SECTION_TITLES["data_quality"], styles["SectionTitle"])]
    data = [
        ["Linhas", "Duplicatas", "Datas incompletas", "Período"],
        [
            str(quality["rows"]),
            str(quality["duplicate_rows"]),
            str(quality["incomplete_paired_dates"]),
            f"{quality['date_start']} a {quality['date_end']}",
        ],
    ]
    story.append(_base_table(data, [35 * mm, 35 * mm, 45 * mm, 80 * mm], font_size=8.5))
    story.append(Spacer(1, 6))

    limitation = Table(
        [[Paragraph(f"<b>Limitação central:</b> {quality['important_limitation']}", styles["BodySmall"]) ]],
        colWidths=[230 * mm],
    )
    limitation.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _hex(template.WARNING_BACKGROUND)),
                ("BOX", (0, 0), (-1, -1), 0.7, _hex(template.BORDER_COLOR)),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(limitation)
    return story


def _section_metrics(analysis, styles):
    story = [Paragraph(template.SECTION_TITLES["metrics"], styles["SectionTitle"])]
    data = [[
        "Grupo", "Compradores", "GMV", "Comissão", "Cashback",
        "Resultado líquido", "Cashback efetivo", "Ticket médio",
    ]]
    for group, metrics in analysis["aggregate_metrics"].items():
        data.append([
            group,
            f"{metrics['compradores']:,.0f}".replace(",", "."),
            brl(metrics["vendas_totais"]),
            brl(metrics["comissao"]),
            brl(metrics["cashback"]),
            brl(metrics["resultado_liquido"]),
            pct(metrics["taxa_cashback_efetiva_pct"]),
            brl(metrics["ticket_medio"]),
        ])
    story.append(_base_table(data, [24*mm, 25*mm, 32*mm, 32*mm, 32*mm, 36*mm, 30*mm, 30*mm], font_size=7.1))
    return story


def _section_cashback(analysis, styles):
    story = [Paragraph(template.SECTION_TITLES["cashback"], styles["SectionTitle"])]
    story.append(Paragraph(template.CASHBACK_NOTE, styles["BodySmall"]))
    data = [["Grupo", "Classificação", "Mediana", "P05", "P95", "Amplitude"]]
    for group, info in analysis["cashback_behavior"].items():
        data.append([
            group,
            info["classification"],
            pct(info["median_pct"]),
            pct(info["p05_pct"]),
            pct(info["p95_pct"]),
            f"{info['amplitude_pp']:.2f} p.p.".replace(".", ","),
        ])
    story.append(_base_table(data, [35*mm, 45*mm, 30*mm, 30*mm, 30*mm, 35*mm], font_size=8))
    return story


def _section_temporal(analysis, styles):
    story = [Paragraph(template.SECTION_TITLES["temporal"], styles["SectionTitle"])]
    story.append(Paragraph(template.TEMPORAL_NOTE, styles["BodySmall"]))

    holidays = analysis["temporal_context"]["holidays_in_period"]
    if holidays:
        story.append(Paragraph("<b>Feriados nacionais encontrados no periodo</b>", styles["BodySmall"]))
        for item in holidays:
            story.append(Paragraph(f"- {item['date']}: {item['name']}", styles["BodySmall"]))
    else:
        story.append(Paragraph("Nenhum feriado nacional cadastrado foi encontrado no período.", styles["BodySmall"]))

    story.append(Spacer(1, 4))
    data = [["Grupo", "Período", "Dias", "Compradores médios", "GMV médio", "Resultado líquido médio"]]
    for group, periods in analysis["weekend_summary"].items():
        for period_name, values in periods.items():
            label = "Dias úteis" if period_name == "dias_uteis" else "Fim de semana"
            data.append([
                group,
                label,
                values["dias"],
                values["compradores_medio"] if values["compradores_medio"] is not None else "-",
                brl(values["gmv_medio"]),
                brl(values["resultado_liquido_medio"]),
            ])
    story.append(_base_table(data, [28*mm, 35*mm, 20*mm, 35*mm, 42*mm, 50*mm], font_size=7.5))
    return story


def _section_statistics(analysis, styles):
    story = [Paragraph(template.SECTION_TITLES["statistics"], styles["SectionTitle"])]
    story.append(Paragraph(
        "Para dois grupos foi usado Wilcoxon pareado. Para três ou mais grupos, "
        "Friedman global e Wilcoxon par a par com correção de Holm.",
        styles["BodySmall"],
    ))

    for metric, result in analysis["statistical_results"].items():
        story.append(Paragraph(f"<b>Métrica: {metric}</b> - {result['paired_dates']} datas pareadas", styles["BodySmall"]))

        if result.get("global_test"):
            global_test = result["global_test"]
            story.append(Paragraph(
                f"Teste global {global_test['test']}: p = {global_test['p_value']}",
                styles["BodySmall"],
            ))

        pairwise = result.get("pairwise", [])
        if pairwise:
            data = [["Grupo A", "Grupo B", "p ajustado", "Significativo", "Uplift B vs A"]]
            for item in pairwise:
                uplift = item["uplift_b_vs_a_pct"]
                data.append([
                    item["group_a"],
                    item["group_b"],
                    f"{item['p_value_holm']:.6f}",
                    "Sim" if item["significant_5pct"] else "Não",
                    pct(uplift) if uplift is not None else "-",
                ])
            story.append(_base_table(data, [35*mm, 35*mm, 35*mm, 35*mm, 40*mm], font_size=7.5))
            story.append(Spacer(1, 5))
        else:
            story.append(Paragraph(result.get("note", "Sem comparações disponíveis."), styles["BodySmall"]))
    return story


def _section_decision(analysis, styles):
    evidence = analysis["decision_evidence"]
    story = [Paragraph(template.SECTION_TITLES["decision"], styles["SectionTitle"])]
    story.append(Paragraph(f"<b>Sinal do motor:</b> {signal_label(evidence['signal'])}", styles["BodySmall"]))
    story.append(Paragraph(f"<b>Variante candidata:</b> {evidence['candidate_group']}", styles["BodySmall"]))
    story.append(Paragraph(evidence["human_judgment_required"], styles["BodySmall"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(template.FINAL_NOTE, styles["BodySmall"]))
    return story


SECTION_BUILDERS = {
    "executive_summary": _section_executive_summary,
    "data_quality": _section_data_quality,
    "metrics": _section_metrics,
    "cashback": _section_cashback,
    "temporal": _section_temporal,
    "statistics": _section_statistics,
    "decision": _section_decision,
}


def generate_pdf_report(analysis: dict[str, Any], output_path: str | Path) -> Path:
    """Gera o PDF final a partir do resultado de estatistica_utilizada.py."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    styles = _build_styles()
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=landscape(A4),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=15 * mm,
        title=analysis["test_name"],
        author=template.AUTHOR,
    )

    quality = analysis["quality"]
    story = [
        Paragraph(template.REPORT_TITLE, styles["ReportTitle"]),
        Paragraph(template.REPORT_SUBTITLE, styles["ReportSubtitle"]),
        Paragraph(
            f"<b>{analysis['test_name']}</b><br/>"
            f"Arquivo: {analysis['input_file']} | Periodo: {quality['date_start']} a {quality['date_end']}",
            styles["BodySmall"],
        ),
        Spacer(1, 5),
    ]

    for index, section_key in enumerate(template.SECTION_ORDER):
        builder = SECTION_BUILDERS.get(section_key)
        if not builder:
            continue
        story.extend(builder(analysis, styles))
        if index < len(template.SECTION_ORDER) - 1:
            story.append(Spacer(1, 6))

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return output_path

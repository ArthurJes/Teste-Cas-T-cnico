"""Gera um relatório executivo simples em PDF A4 vertical."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import modelo_relatorio as template

PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = RIGHT_MARGIN = 14 * mm
TOP_MARGIN = 22 * mm
BOTTOM_MARGIN = 17 * mm
CONTENT_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN

# Paleta neutra usada somente no PDF.
DARK_COLOR = "#222222"
MUTED_COLOR = "#666666"
TABLE_HEADER_BACKGROUND = "#EAEAEA"
TABLE_HEADER_TEXT = "#222222"
BORDER_COLOR = "#CCCCCC"


def brl(value: float | int | None) -> str:
    if value is None:
        return "-"
    text = f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {text}"


def pct(value: float | int | None, decimals: int = 2) -> str:
    if value is None:
        return "-"
    return f"{float(value):.{decimals}f}%".replace(".", ",")


def number(value: float | int | None, decimals: int = 0) -> str:
    if value is None:
        return "-"
    return f"{float(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def safe(value: Any) -> str:
    return "-" if value is None or value == "" else html.escape(str(value))


def signal_label(signal: str) -> str:
    return {
        "forte_candidato": "Forte candidato à escala",
        "promissor_com_ressalvas": "Promissor, com ressalvas",
        "inconclusivo": "Resultado inconclusivo",
    }.get(signal, signal.replace("_", " ").capitalize())


def classification_label(value: str) -> str:
    return {
        "estavel": "Estável",
        "variavel": "Variável",
        "mudanca_de_nivel": "Mudança de nível",
    }.get(value, value.replace("_", " ").capitalize())


def hx(value: str):
    return colors.HexColor(value)


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=15, leading=18, textColor=hx(DARK_COLOR), spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"], fontName="Helvetica",
            fontSize=8, leading=10, textColor=hx(MUTED_COLOR), spaceAfter=8,
        ),
        "section": ParagraphStyle(
            "section", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=10.5, leading=13, textColor=hx(DARK_COLOR),
            spaceBefore=7, spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "body", parent=base["BodyText"], fontName="Helvetica",
            fontSize=8.2, leading=10.5, textColor=hx(DARK_COLOR), spaceAfter=3,
        ),
        "small": ParagraphStyle(
            "small", parent=base["BodyText"], fontName="Helvetica",
            fontSize=7.2, leading=9, textColor=hx(MUTED_COLOR), spaceAfter=2,
        ),
        "bullet": ParagraphStyle(
            "bullet", parent=base["BodyText"], fontName="Helvetica",
            fontSize=8.2, leading=10.5, leftIndent=9, firstLineIndent=-7,
            textColor=hx(DARK_COLOR), spaceAfter=2,
        ),
        "th": ParagraphStyle(
            "th", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=6.6, leading=8, alignment=1, textColor=hx(TABLE_HEADER_TEXT),
        ),
        "td": ParagraphStyle(
            "td", parent=base["BodyText"], fontName="Helvetica",
            fontSize=6.6, leading=8, textColor=hx(DARK_COLOR),
        ),
    }


def header_footer(canvas, doc, analysis: dict[str, Any]) -> None:
    canvas.saveState()

    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(hx(DARK_COLOR))
    canvas.drawString(LEFT_MARGIN, PAGE_HEIGHT - 11 * mm, template.REPORT_TITLE)

    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(hx(MUTED_COLOR))
    canvas.drawRightString(
        PAGE_WIDTH - RIGHT_MARGIN,
        PAGE_HEIGHT - 11 * mm,
        str(analysis.get("test_name", "Teste de cashback")),
    )

    canvas.setStrokeColor(hx(BORDER_COLOR))
    canvas.setLineWidth(0.5)
    canvas.line(LEFT_MARGIN, PAGE_HEIGHT - 14 * mm, PAGE_WIDTH - RIGHT_MARGIN, PAGE_HEIGHT - 14 * mm)
    canvas.line(LEFT_MARGIN, 11 * mm, PAGE_WIDTH - RIGHT_MARGIN, 11 * mm)

    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(hx(MUTED_COLOR))
    canvas.drawString(LEFT_MARGIN, 7 * mm, template.AUTHOR)
    canvas.drawCentredString(PAGE_WIDTH / 2, 7 * mm, "Análise de experimento de cashback")
    canvas.drawRightString(PAGE_WIDTH - RIGHT_MARGIN, 7 * mm, f"Página {doc.page}")
    canvas.restoreState()


def full_table(
    data: list[list[Any]],
    styles: dict[str, ParagraphStyle],
    proportions: list[float],
    numeric_columns: tuple[int, ...] = (),
) -> Table:
    if abs(sum(proportions) - 1.0) > 0.001:
        raise ValueError("As proporções das colunas devem somar 1.0.")

    prepared = []
    for row_index, row in enumerate(data):
        style = styles["th"] if row_index == 0 else styles["td"]
        prepared.append([Paragraph(safe(value), style) for value in row])

    table = Table(
        prepared,
        colWidths=[CONTENT_WIDTH * value for value in proportions],
        repeatRows=1,
        hAlign="LEFT",
    )

    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), hx(TABLE_HEADER_BACKGROUND)),
        ("TEXTCOLOR", (0, 0), (-1, 0), hx(TABLE_HEADER_TEXT)),
        ("GRID", (0, 0), (-1, -1), 0.35, hx(BORDER_COLOR)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for column in numeric_columns:
        commands.append(("ALIGN", (column, 1), (column, -1), "RIGHT"))
    table.setStyle(TableStyle(commands))
    return table


def summary_section(analysis: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    quality = analysis["quality"]
    evidence = analysis["decision_evidence"]
    partners = ", ".join(quality.get("partners", [])) or "-"

    items = [
        Paragraph("Resumo do Teste", styles["section"]),
        Paragraph(f"<b>Teste:</b> {safe(analysis.get('test_name'))}", styles["body"]),
        Paragraph(f"<b>Parceiro:</b> {safe(partners)}", styles["body"]),
        Paragraph(f"<b>Arquivo analisado:</b> {safe(analysis.get('input_file'))}", styles["body"]),
        Paragraph(
            f"<b>Período:</b> {safe(quality.get('date_start'))} a {safe(quality.get('date_end'))}",
            styles["body"],
        ),
        Paragraph(
            f"<b>Resultado da análise:</b> {safe(signal_label(evidence.get('signal', 'inconclusivo')))}",
            styles["body"],
        ),
        Paragraph(f"<b>Variante candidata:</b> {safe(evidence.get('candidate_group'))}", styles["body"]),
    ]
    items.extend(Paragraph(f"- {safe(reason)}", styles["bullet"]) for reason in evidence.get("reasons", [])[:3])
    return items


def quality_section(analysis: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    quality = analysis["quality"]
    return [
        Paragraph("Qualidade dos dados", styles["section"]),
        Paragraph(f"<b>Linhas analisadas:</b> {quality.get('rows', '-')}", styles["body"]),
        Paragraph(f"<b>Linhas duplicadas:</b> {quality.get('duplicate_rows', '-')}", styles["body"]),
        Paragraph(
            f"<b>Datas incompletas para comparação pareada:</b> "
            f"{quality.get('incomplete_paired_dates', '-')}",
            styles["body"],
        ),
        Paragraph(
            f"<b>Limitação principal:</b> {safe(quality.get('important_limitation'))}",
            styles["body"],
        ),
    ]


def metrics_section(analysis: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    data = [["Grupo", "Compradores", "GMV", "Comissão", "Cashback", "Resultado líquido", "Cashback efetivo"]]
    for group, metrics in analysis["aggregate_metrics"].items():
        data.append([
            group,
            number(metrics.get("compradores")),
            brl(metrics.get("vendas_totais")),
            brl(metrics.get("comissao")),
            brl(metrics.get("cashback")),
            brl(metrics.get("resultado_liquido")),
            pct(metrics.get("taxa_cashback_efetiva_pct")),
        ])

    return [
        Paragraph("Métricas por grupo", styles["section"]),
        full_table(data, styles, [0.10, 0.13, 0.16, 0.14, 0.14, 0.18, 0.15], (1, 2, 3, 4, 5, 6)),
        Spacer(1, 3),
        Paragraph("Resultado líquido = comissão recebida menos cashback distribuído.", styles["small"]),
    ]


def trends_section(analysis: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    items: list[Any] = [Paragraph("Tendências", styles["section"])]

    cashback_data = [["Grupo", "Comportamento", "Mediana", "Faixa P05-P95"]]
    for group, info in analysis.get("cashback_behavior", {}).items():
        cashback_data.append([
            group,
            classification_label(str(info.get("classification", "-"))),
            pct(info.get("median_pct")),
            f"{pct(info.get('p05_pct'))} a {pct(info.get('p95_pct'))}",
        ])
    items.append(full_table(cashback_data, styles, [0.16, 0.34, 0.20, 0.30], (2, 3)))
    items.extend([
        Spacer(1, 4),
        Paragraph(
            "A taxa apresentada é a taxa efetiva observada: cashback distribuído dividido pelas vendas totais.",
            styles["small"],
        ),
    ])

    weekend_data = [[
        "Grupo", "Compradores - dias úteis", "Compradores - fim de semana",
        "Resultado líquido - dias úteis", "Resultado líquido - fim de semana",
    ]]
    for group, summary in analysis.get("weekend_summary", {}).items():
        weekdays = summary.get("dias_uteis", {})
        weekends = summary.get("fim_de_semana", {})
        weekend_data.append([
            group,
            number(weekdays.get("compradores_medio"), 2),
            number(weekends.get("compradores_medio"), 2),
            brl(weekdays.get("resultado_liquido_medio")),
            brl(weekends.get("resultado_liquido_medio")),
        ])
    if len(weekend_data) > 1:
        items.extend([
            Spacer(1, 5),
            full_table(weekend_data, styles, [0.14, 0.20, 0.20, 0.23, 0.23], (1, 2, 3, 4)),
        ])

    holidays = analysis.get("temporal_context", {}).get("holidays_in_period", [])
    if holidays:
        text = "; ".join(f"{item.get('date', '-')}: {item.get('name', '-')}" for item in holidays)
        items.extend([
            Spacer(1, 4),
            Paragraph(f"<b>Feriados nacionais no período:</b> {safe(text)}.", styles["body"]),
            Paragraph("A proximidade entre uma variação e um feriado não comprova causalidade por si só.", styles["small"]),
        ])
    return items


def statistics_section(analysis: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    result = analysis.get("statistical_results", {}).get("resultado_liquido", {})
    items: list[Any] = [
        Paragraph("Tendências estatísticas", styles["section"]),
        Paragraph(
            f"A comparação de resultado líquido utilizou <b>{result.get('paired_dates', 0)}</b> datas pareadas.",
            styles["body"],
        ),
    ]

    global_test = result.get("global_test")
    if global_test:
        p_value = global_test.get("p_value")
        p_text = "&lt; 0,000001" if p_value == 0 else str(p_value).replace(".", ",")
        items.append(
            Paragraph(
                f"<b>Teste global:</b> {safe(global_test.get('test'))}; p-valor = {p_text}.",
                styles["body"],
            )
        )

    pairwise = result.get("pairwise", [])
    if pairwise:
        data = [["Comparação", "Média A", "Média B", "p ajustado", "Significativo a 5%"]]
        for comparison in pairwise:
            p_adjusted = comparison.get("p_value_holm")
            p_text = "< 0,000001" if p_adjusted == 0 else f"{float(p_adjusted):.6f}".replace(".", ",")
            data.append([
                f"{comparison.get('group_a', '-')} x {comparison.get('group_b', '-')}",
                brl(comparison.get("mean_a")),
                brl(comparison.get("mean_b")),
                p_text,
                "Sim" if comparison.get("significant_5pct") else "Não",
            ])
        items.extend([
            Spacer(1, 3),
            full_table(data, styles, [0.23, 0.20, 0.20, 0.18, 0.19], (1, 2, 3)),
        ])
    else:
        items.append(Paragraph(result.get("note", "Sem comparações disponíveis."), styles["body"]))
    return items


def recommendation_section(analysis: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    evidence = analysis["decision_evidence"]
    items: list[Any] = [
        Paragraph("Recomendação final", styles["section"]),
        Paragraph(f"<b>Recomendação:</b> {safe(signal_label(evidence.get('signal', 'inconclusivo')))}.", styles["body"]),
        Paragraph(f"<b>Variante indicada:</b> {safe(evidence.get('candidate_group'))}.", styles["body"]),
    ]

    cautions = evidence.get("cautions", [])
    if cautions:
        items.append(Paragraph("<b>Ressalvas:</b>", styles["body"]))
        items.extend(Paragraph(f"- {safe(caution)}", styles["bullet"]) for caution in cautions[:3])

    items.extend([
        Paragraph(safe(evidence.get("human_judgment_required")), styles["body"]),
        Paragraph(template.FINAL_NOTE, styles["small"]),
    ])
    return items


def generate_pdf_report(analysis: dict[str, Any], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = build_styles()

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        title=str(analysis.get("test_name", template.REPORT_TITLE)),
        author=template.AUTHOR,
    )

    story: list[Any] = [
        Paragraph(template.REPORT_TITLE, styles["title"]),
        Paragraph(template.REPORT_SUBTITLE, styles["subtitle"]),
    ]
    story.extend(summary_section(analysis, styles))
    story.extend(quality_section(analysis, styles))
    story.extend(metrics_section(analysis, styles))
    story.append(PageBreak())
    story.extend(trends_section(analysis, styles))
    story.extend(statistics_section(analysis, styles))
    story.extend(recommendation_section(analysis, styles))

    callback = lambda canvas, current_doc: header_footer(canvas, current_doc, analysis)
    doc.build(story, onFirstPage=callback, onLaterPages=callback)
    return output_path

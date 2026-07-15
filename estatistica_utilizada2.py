"""
Funções principais para analisar testes de cashback.

A ideia deste arquivo é manter a parte quantitativa da análise em um único lugar:
- leitura e limpeza do dataset;
- criação de métricas;
- contexto temporal;

"""

from __future__ import annotations

    from datetime import date
    from pathlib import Path
    from typing import Any
    import math
    import re
    import numpy as np
    import pandas as pd
    from scipy import stats

REQUIRED_COLUMNS = [
    "Data",
    "Grupos de usuários",
    "Parceiro",
    "Compradores",
    "comissão",
    "Cashback",
    "Vendas totais",
MONEY_COLUMNS = ["comissão", "cashback", "vendas totais"]

##Compradores é tratado como volume absoluto, e não como taxa de conversão.



def clean_column_name(name: str) -> str:
    """Remove espaços extras dos nomes das colunas."""
    return re.sub(r"\s+", " ", str(name).strip())

def parse_money_value(value: Any) -> float:

"""
Converte formatos monetários comuns para float.

Exemplos:
    R$ 1.234,56 ---> 1234.56
     0,99 ---> 0.99
     0.99 --> 0.99

Quando existe apenas um ponto seguido de três dígitos, o valor é tratado
como separador de milhar porque os datasets do desafio usam reais nesse padrão.

"""

    if pd.isna(value):
        return np.nan

    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)

    text = str(value).strip()
    text = text.replace("R$", "").replace("\u00a0", "").replace(" ", "")
    text = re.sub(r"[^0-9,.-]", "", text)

    if not text:
        return np.nan

    has_comma = "," in text
    has_dot = "." in text

    if has_comma and has_dot: ######O último é interpretado como decimal.
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")

    elif has_comma:
        parts = text.split(",")
        if len(parts) == 2:
            text = text.replace(",", ".")
        else:
            text = "".join(parts[:-1]) + "." + parts[-1]

    elif has_dot:
        parts = text.split(".")
        if len(parts) == 2 and len(parts[1]) <= 2:
            pass
        else:
            text = text.replace(".", "")

    try:
        return float(text)
    except ValueError:
        return np.nan


def load_dataset(file_path: str | Path) -> tuple[pd.DataFrame, str]:
    """Abre CSV, XLSX ou JSON."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path), "CSV"
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path), "XLSX"
    if suffix == ".json":
        return pd.read_json(path), "JSON"

    raise ValueError(
        "Formato não suportado diretamente. Use CSV, XLSX ou JSON. "
    )


def validate_and_prepare(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Prepara as principais métricas."""
    
    df = df.copy()
    df.columns = [clean_column_name(column) for column in df.columns]



    
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {missing}")

    duplicates = int(df.duplicated().sum())

    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df["compradores"] = pd.to_numeric(df["compradores"], errors="coerce")

    for column in MONEY_COLUMNS:
        df[column] = df[column].apply(parse_money_value)

    invalid_counts = {
        column: int(df[column].isna().sum())
        for column in ["Data", "compradores", *MONEY_COLUMNS]
    }

    if any(value > 0 for value in invalid_counts.values()):
        raise ValueError(
            "Existem valores inválidos após a conversão: " + str(invalid_counts)
        )

    if (df["vendas totais"] <= 0).any():
        raise ValueError("Existem linhas com vendas totais menores ou iguais a zero.")

    groups = sorted(df["Grupos de usuários"].astype(str).unique().tolist())
    if len(groups) < 2:
        raise ValueError("O teste precisa ter pelo menos dois grupos.")

    # Métricas que serão usadas ao longo da análise.
    df["resultado_liquido"] = df["comissão"] - df["cashback"]
    df["taxa_cashback_efetiva"] = df["cashback"] / df["vendas totais"]
    df["ticket_medio"] = np.where(
        df["compradores"] > 0,
        df["vendas totais"] / df["compradores"],
        np.nan,
    )
    df["take_rate"] = df["comissão"] / df["vendas totais"]

    #####Verifica se todas as datas possuem todos os grupos, importante para testes pareados.
    groups_per_date = df.groupby("Data")["Grupos de usuários"].nunique()
    incomplete_dates = int((groups_per_date != len(groups)).sum())

    quality = {
        "rows": int(len(df)),
        "groups": groups,
        "partners": sorted(df["Parceiro"].astype(str).unique().tolist()),
        "date_start": df["Data"].min().date().isoformat(),
        "date_end": df["Data"].max().date().isoformat(),
        "duplicate_rows": duplicates,
        "incomplete_paired_dates": incomplete_dates,
        "important_limitation": (
            "O dataset não informa o total de usuários expostos por variante. "
            "Por isso, não é possível calcular taxa de conversão real."
        ),
    }

    return df, quality


def national_holidays_for_year(year: int) -> dict[date, str]:
    """Feriados nacionais fixos usados como contexto temporal."""
    holidays = {
        date(year, 1, 1): "Confraternização Universal",
        date(year, 4, 21): "Tiradentes",
        date(year, 5, 1): "Dia do Trabalho",
        date(year, 9, 7): "Independência do Brasil",
        date(year, 10, 12): "Nossa Senhora Aparecida",
        date(year, 11, 2): "Finados",
        date(year, 11, 15): "Proclamação da República",
        date(year, 12, 25): "Natal",
    }

    if year >= 2024:
        holidays[date(year, 11, 20)] = "Dia da Consciência Negra"

    return holidays


def add_temporal_context(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Adiciona dia da semana, fim de semana e feriados nacionais."""
    df = df.copy()

    weekday_names = {
        0: "segunda-feira",
        1: "terça-feira",
        2: "quarta-feira",
        3: "quinta-feira",
        4: "sexta-feira",
        5: "sábado",
        6: "domingo",
    }

    df["dia_semana_num"] = df["Data"].dt.weekday
    df["dia_semana"] = df["dia_semana_num"].map(weekday_names)
    df["fim_de_semana"] = df["dia_semana_num"].isin([5, 6])

    holiday_map: dict[date, str] = {}
    for year in sorted(df["Data"].dt.year.unique()):
        holiday_map.update(national_holidays_for_year(int(year)))

    df["nome_feriado"] = df["Data"].dt.date.map(holiday_map)
    df["feriado_nacional"] = df["nome_feriado"].notna()

    holidays_in_period = (
        df.loc[df["feriado_nacional"], ["Data", "nome_feriado"]]
        .drop_duplicates()
        .sort_values("Data")
    )

    context = {
        "holidays_in_period": [
            {"date": row.Data.date().isoformat(), "name": row.nome_feriado}
            for row in holidays_in_period.itertuples(index=False)
        ]
    }

    return df, context


def summarize_cashback_behavior(df: pd.DataFrame) -> dict[str, Any]:
    """
    Resume o comportamento da taxa efetiva de cashback por grupo.

    Pequenas oscilações não anulam o teste. O objetivo é apenas mostrar se a taxa
    permaneceu aproximadamente estável ou se mudou bastante durante o período.
    """
    result: dict[str, Any] = {}

    for group, part in df.groupby("Grupos de usuários"):
        rates = part["taxa_cashback_efetiva"].dropna() * 100
        p05 = float(rates.quantile(0.05))
        p95 = float(rates.quantile(0.95))
        amplitude = p95 - p05

        if amplitude <= 0.5:
            classification = "estavel"
        else:
            classification = "variavel"

        result[str(group)] = {
            "classification": classification,
            "median_pct": round(float(rates.median()), 3),
            "p05_pct": round(p05, 3),
            "p95_pct": round(p95, 3),
            "amplitude_pp": round(amplitude, 3),
            "note": (
                "A taxa é efetiva e observada, calculada como cashback distribuído / vendas totais."
            ),
        }

    return result


def aggregate_metrics(df: pd.DataFrame) -> dict[str, Any]:
    """Calcula as principais métricas agregadas por grupo."""
    result: dict[str, Any] = {}

    for group, part in df.groupby("Grupos de usuários"):
        buyers = float(part["compradores"].sum())
        gmv = float(part["vendas totais"].sum())
        commission = float(part["comissão"].sum())
        cashback = float(part["cashback"].sum())
        net_result = commission - cashback

        result[str(group)] = {
            "compradores": round(buyers, 2),
            "vendas_totais": round(gmv, 2),
            "comissao": round(commission, 2),
            "cashback": round(cashback, 2),
            "resultado_liquido": round(net_result, 2),
            "taxa_cashback_efetiva_pct": round((cashback / gmv) * 100, 3),
            "ticket_medio": round(gmv / buyers, 2) if buyers > 0 else None,
            "take_rate_pct": round((commission / gmv) * 100, 3),
        }

    return result


def _holm_adjust(p_values: list[float]) -> list[float]:
    """Correção de Holm para comparações múltiplas."""
    if not p_values:
        return []

    order = np.argsort(p_values)
    adjusted = [0.0] * len(p_values)
    running_max = 0.0
    total = len(p_values)

    for rank, index in enumerate(order):
        corrected = min(1.0, p_values[index] * (total - rank))
        running_max = max(running_max, corrected)
        adjusted[index] = running_max

    return adjusted


def paired_statistical_tests(df: pd.DataFrame) -> dict[str, Any]:
    """
    Compara os grupos usando as mesmas datas.

    - 2 grupos: Wilcoxon pareado.
    - 3 ou mais grupos: Friedman global e Wilcoxon par a par com correção de Holm.
    """
    metrics = ["resultado_liquido", "compradores", "vendas totais", "ticket_medio"]
    groups = sorted(df["Grupos de usuários"].unique().tolist())
    result: dict[str, Any] = {}

    for metric in metrics:
        pivot = df.pivot_table(
            index="Data",
            columns="Grupos de usuários",
            values=metric,
            aggfunc="first",
        ).dropna(subset=groups)

        metric_result: dict[str, Any] = {
            "paired_dates": int(len(pivot)),
            "global_test": None,
            "pairwise": [],
        }

        if len(pivot) < 3:
            metric_result["note"] = "Poucas datas completas para teste estatístico."
            result[metric] = metric_result
            continue

        if len(groups) >= 3:
            arrays = [pivot[group].to_numpy() for group in groups]
            statistic, p_value = stats.friedmanchisquare(*arrays)
            metric_result["global_test"] = {
                "test": "Friedman",
                "statistic": round(float(statistic), 6),
                "p_value": round(float(p_value), 6),
            }

        raw_pairwise = []
        for i, group_a in enumerate(groups):
            for group_b in groups[i + 1 :]:
                a = pivot[group_a].to_numpy()
                b = pivot[group_b].to_numpy()

                try:
                    statistic, p_value = stats.wilcoxon(a, b, zero_method="wilcox")
                except ValueError:
                    statistic, p_value = 0.0, 1.0

                mean_a = float(np.mean(a))
                mean_b = float(np.mean(b))
                uplift_pct = ((mean_b / mean_a) - 1) * 100 if mean_a != 0 else np.nan

                raw_pairwise.append(
                    {
                        "group_a": str(group_a),
                        "group_b": str(group_b),
                        "test": "Wilcoxon pareado",
                        "statistic": round(float(statistic), 6),
                        "p_value": float(p_value),
                        "mean_a": round(mean_a, 4),
                        "mean_b": round(mean_b, 4),
                        "uplift_b_vs_a_pct": round(float(uplift_pct), 3)
                        if not math.isnan(uplift_pct)
                        else None,
                    }
                )

        adjusted = _holm_adjust([item["p_value"] for item in raw_pairwise])
        for item, p_adjusted in zip(raw_pairwise, adjusted):
            item["p_value"] = round(item["p_value"], 6)
            item["p_value_holm"] = round(float(p_adjusted), 6)
            item["significant_5pct"] = bool(p_adjusted < 0.05)

        metric_result["pairwise"] = raw_pairwise
        result[metric] = metric_result

    return result

def weekend_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Compara médias de dias úteis e fins de semana por grupo."""
    result: dict[str, Any] = {}

    for group, part in df.groupby("Grupos de usuários"):
        group_result = {}
        for label, mask in {
            "dias_uteis": ~part["fim_de_semana"],
            "fim_de_semana": part["fim_de_semana"],
        }.items():
            subset = part.loc[mask]
            group_result[label] = {
                "dias": int(len(subset)),
                "compradores_medio": round(float(subset["compradores"].mean()), 2)
                if len(subset)
                else None,
                "gmv_medio": round(float(subset["vendas totais"].mean()), 2)
                if len(subset)
                else None,
                "resultado_liquido_medio": round(
                    float(subset["resultado_liquido"].mean()), 2
                )
                if len(subset)
                else None,
            }
        result[str(group)] = group_result

    return result


def build_decision_evidence(
    metrics: dict[str, Any],
    statistical_results: dict[str, Any],
    cashback_behavior: dict[str, Any],
) -> dict[str, Any]:
    """
    Gera um sinal simples para orientar a interpretação do agente.

    A decisão final continua sendo responsabilidade do agente e do analista.
    """
    candidate = max(metrics, key=lambda group: metrics[group]["resultado_liquido"])
    groups = list(metrics.keys())

    reasons = [
        f"{candidate} apresentou o maior resultado líquido agregado no período."
    ]
    cautions: list[str] = []

    primary = statistical_results.get("resultado_liquido", {})
    significant_pairs = [
        item for item in primary.get("pairwise", []) if item.get("significant_5pct")
    ]

    candidate_has_significant_advantage = any(
        (
            item["group_b"] == candidate
            and item["mean_b"] > item["mean_a"]
            and item["significant_5pct"]
        )
        or (
            item["group_a"] == candidate
            and item["mean_a"] > item["mean_b"]
            and item["significant_5pct"]
        )
        for item in primary.get("pairwise", [])
    )

    if candidate_has_significant_advantage:
        reasons.append(
            "O candidato apresentou vantagem estatisticamente significativa em pelo menos uma comparação de resultado líquido."
        )
    else:
        cautions.append(
            "A vantagem do candidato em resultado líquido não foi estatisticamente significativa em todas as comparações relevantes."
        )

    variable_groups = [
        group
        for group, info in cashback_behavior.items()
        if info["classification"] == "variavel"
    ]
    if variable_groups:
        cautions.append(
            "A taxa efetiva de cashback variou de forma relevante em: "
            + ", ".join(variable_groups)
            + ". Isso não invalida o teste, mas pede interpretação temporal cuidadosa."
        )

    if candidate_has_significant_advantage and not variable_groups:
        signal = "forte_candidato"
    elif candidate_has_significant_advantage or candidate == groups[0]:
        signal = "promissor_com_ressalvas"
    else:
        signal = "inconclusivo"

    return {
        "candidate_group": candidate,
        "signal": signal,
        "reasons": reasons,
        "cautions": cautions,
        "human_judgment_required": (
            "O motor organiza as evidências. A decisão final deve considerar contexto, "
            "qualidade dos dados, sazonalidade e impacto de negócio."
        ),
    }
def analyze_file(file_path: str | Path) -> dict[str, Any]:
    """Executa o fluxo completo de análise e retorna um dicionário estruturado."""
    df, input_format = load_dataset(file_path)
    df, quality = validate_and_prepare(df)
    df, temporal_context = add_temporal_context(df)

    metrics = aggregate_metrics(df)
    cashback_behavior = summarize_cashback_behavior(df)
    statistics = paired_statistical_tests(df)
    weekends = weekend_summary(df)
    evidence = build_decision_evidence(metrics, statistics, cashback_behavior)

    return {
        "analysis_version": "1.0",
        "input_file": Path(file_path).name,
        "input_format": input_format,
        "test_name": f"Teste de cashback - {', '.join(quality['partners'])}",
        "quality": quality,
        "aggregate_metrics": metrics,
        "cashback_behavior": cashback_behavior,
        "temporal_context": temporal_context,
        "weekend_summary": weekends,
        "statistical_results": statistics,
        "decision_evidence": evidence,
    }

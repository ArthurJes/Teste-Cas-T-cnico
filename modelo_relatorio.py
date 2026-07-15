"""
Modelo editável do relatório em PDF.

Edite este arquivo para mudar títulos, cores, textos fixos e a ordem das seçõe.

"""

# Identidade visual
REPORT_TITLE = "Relatório de experimento de cashback"
REPORT_SUBTITLE = "Análise quantitativa e apoio à decisão"
AUTHOR = "Arthur Alves"

# Cores em hexadecimal
ACCENT_COLOR = "#E8134C"              # Rosa Cereja Intenso (Méliuz) para destaques
DARK_COLOR = "#000000"             
MUTED_COLOR = "#5C4D51"            
LIGHT_BACKGROUND = "#FFFFFF"        
WARNING_BACKGROUND = "#FFF0F4"     
TABLE_HEADER_BACKGROUND = "#FCEEF2"  
BORDER_COLOR = "#EBD6DC"



### Títulos das seções. Você pode renomear livremente.
SECTION_TITLES = {
    "executive_summary": "1. Resumo executivo",
    "data_quality": "2. Qualidade dos dados",
    "metrics": "3. Métricas por grupo",
    "cashback": "4. Comportamento do cashback",
    "temporal": "5. Contexto temporal",
    "statistics": "6. Comparação estatística",
    "decision": "7. Recomendação",
}

# Ordem das seções no PDF. Remova ou reorganize itens para mudar o relatório.
SECTION_ORDER = [
    "executive_summary",
    "data_quality",
    "metrics",
    "cashback",
    "temporal",
    "statistics",
    "decision",
]

# Textos fixos que podem ser personalizados.
CASHBACK_NOTE = (
    "A taxa usada nesta análise é a taxa efetiva observada, calculada por "
    "cashback distribuído dividido pelas vendas totais. Pequenas oscilações "
    "não invalidam automaticamente o teste."
)

TEMPORAL_NOTE = (
    "As comparações principais usam as mesmas datas para os grupos, reduzindo "
    "o efeito de fatores comuns daquele dia. Feriados nacionais são tratados "
    "como contexto e não como prova automática de causalidade."
)

FINAL_NOTE = (
    "Este relatório organiza evidências quantitativas. A decisão final deve ser "
    "revisada por um analista, considerando contexto de negócio, qualidade dos "
    "dados, sazonalidade e limitações do experimento."
)

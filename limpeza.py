"""
limpeza.py
-----------
Modulo de limpeza e tratamento dos dados de entregas da transportadora.

Le o relatorio exportado do sistema de gestao (hoje: CSV/planilha; no futuro
pode ser trocado por uma chamada de API, sem mudar o resto do pipeline -
basta reescrever a funcao `carregar_dados_brutos`).

Uso:
    from limpeza import processar_planilha
    df = processar_planilha("entregas_relatorio.csv")
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------

# Colunas que realmente importam para o BI. Mantemos so o essencial para nao
# carregar o portal com dados que nao serao usados (a planilha original tem
# ~86 colunas).
COLUNAS_UTEIS = {
    "Nro. Entrega": "nro_entrega",
    "Nota Fiscal": "nota_fiscal",
    "Cliente": "cliente",
    "Sigla Unidade Entrega": "filial",          # unidade da transportadora
    "Cidade Pessoa Visita": "cidade_entrega",
    "UF Pessoa Visita": "uf_entrega",
    "Status": "status",
    "Valor Total": "valor_total",
    "Qtde Volumes": "qtde_volumes",
    "Dt. Prazo Atual": "dt_prazo_atual",
    "Dt. Agendamento": "dt_agendamento",
    "Dt. Entrega": "dt_entrega",
    "Dt. Cancelamento": "dt_cancelamento",
    "Motivo Cancelamento": "motivo_cancelamento",
    "Motivo de Atraso": "motivo_atraso",
    "Nome Recebedor": "nome_recebedor",
}

COLUNAS_DATA = [
    "dt_prazo_atual",
    "dt_agendamento",
    "dt_entrega",
    "dt_cancelamento",
]


# ---------------------------------------------------------------------------
# Etapa 1: carregar dados brutos
# ---------------------------------------------------------------------------

def carregar_dados_brutos(caminho_arquivo: str) -> pd.DataFrame:
    """
    Le o arquivo exportado do sistema de gestao.

    Hoje le um CSV (separado por ';', encoding latin1, padrao do sistema).
    Quando o TI disponibilizar uma API/consulta direta, so essa funcao
    precisa ser trocada - o restante do pipeline (limpeza, calculo de
    atraso, agrupamento por filial) continua igual.
    """
    df = pd.read_csv(
        caminho_arquivo,
        sep=";",
        encoding="latin1",
        dtype=str,          # le tudo como texto; convertemos os tipos depois
    )
    return df


# ---------------------------------------------------------------------------
# Etapa 2: selecionar e renomear colunas
# ---------------------------------------------------------------------------

def selecionar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    colunas_existentes = [c for c in COLUNAS_UTEIS if c in df.columns]
    faltando = [c for c in COLUNAS_UTEIS if c not in df.columns]
    if faltando:
        print(f"[aviso] colunas nao encontradas na planilha: {faltando}")

    df = df[colunas_existentes].rename(columns=COLUNAS_UTEIS)
    return df


# ---------------------------------------------------------------------------
# Etapa 3: tratar tipos (datas, valores, texto)
# ---------------------------------------------------------------------------

def _parse_data(serie: pd.Series) -> pd.Series:
    """Converte texto de data (dd/mm/aaaa ou dd/mm/aaaa hh:mm) para datetime.
    Trata '-' e vazio como data ausente."""
    serie = serie.replace({"-": np.nan, "": np.nan})
    return pd.to_datetime(serie, dayfirst=True, errors="coerce")


def _parse_valor(serie: pd.Series) -> pd.Series:
    """Converte 'R$ 21.344,17' -> 21344.17"""
    serie = serie.replace({"-": np.nan, "": np.nan})
    serie = (
        serie.astype(str)
        .str.replace("R$", "", regex=False)
        .str.replace(".", "", regex=False)   # separador de milhar
        .str.replace(",", ".", regex=False)  # separador decimal
        .str.strip()
    )
    return pd.to_numeric(serie, errors="coerce")


def tratar_tipos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in COLUNAS_DATA:
        if col in df.columns:
            df[col] = _parse_data(df[col])

    if "valor_total" in df.columns:
        df["valor_total"] = _parse_valor(df["valor_total"])

    if "qtde_volumes" in df.columns:
        df["qtde_volumes"] = pd.to_numeric(df["qtde_volumes"], errors="coerce")

    # texto: tira espacos extras e padroniza vazio
    for col in ["cliente", "filial", "status", "cidade_entrega", "uf_entrega"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"nan": np.nan, "-": np.nan})

    return df


# ---------------------------------------------------------------------------
# Etapa 4: remover duplicidade e linhas invalidas
# ---------------------------------------------------------------------------

def remover_duplicados_e_invalidos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    antes = len(df)

    df = df.drop_duplicates(subset=["nro_entrega"])
    df = df[df["nro_entrega"].notna()]
    df = df[df["filial"].notna()]  # sem filial nao da pra rotear e-mail

    depois = len(df)
    if antes != depois:
        print(f"[info] removidas {antes - depois} linhas duplicadas/invalidas")

    return df


# ---------------------------------------------------------------------------
# Etapa 5: calcular atraso
# ---------------------------------------------------------------------------

def calcular_atraso(df: pd.DataFrame, data_referencia: datetime | None = None) -> pd.DataFrame:
    """
    Regra combinada com o cliente:
    - Prazo considerado = o MAIOR entre Dt. Prazo Atual e Dt. Agendamento
    - Fica de fora do calculo (nunca e' "atrasado"):
        * entregas ja canceladas (dt_cancelamento preenchida)
        * entregas ja entregues (dt_entrega preenchida)
    - Esta atrasado quando: prazo considerado < data de referencia (hoje)
    """
    df = df.copy()
    hoje = pd.Timestamp(data_referencia or datetime.now().date())

    df["prazo_considerado"] = df[["dt_prazo_atual", "dt_agendamento"]].max(axis=1)

    df["cancelada"] = df["dt_cancelamento"].notna()
    df["entregue"] = df["dt_entrega"].notna()

    elegivel = ~df["cancelada"] & ~df["entregue"] & df["prazo_considerado"].notna()

    df["atrasado"] = elegivel & (df["prazo_considerado"] < hoje)

    df["dias_atraso"] = np.where(
        df["atrasado"],
        (hoje - df["prazo_considerado"]).dt.days,
        0,
    )

    # Vence hoje: ainda nao atrasada, mas o prazo considerado cai exatamente hoje
    df["vence_hoje"] = elegivel & (df["prazo_considerado"].dt.date == hoje.date())

    return df


# ---------------------------------------------------------------------------
# Pipeline completo
# ---------------------------------------------------------------------------

def processar_planilha(caminho_arquivo: str, data_referencia: datetime | None = None) -> pd.DataFrame:
    df = carregar_dados_brutos(caminho_arquivo)
    df = selecionar_colunas(df)
    df = tratar_tipos(df)
    df = remover_duplicados_e_invalidos(df)
    df = calcular_atraso(df, data_referencia=data_referencia)
    return df


# ---------------------------------------------------------------------------
# Agregado por filial (usado tanto pelo portal quanto pelo e-mail diario)
# ---------------------------------------------------------------------------

def resumo_por_filial(df: pd.DataFrame) -> pd.DataFrame:
    resumo = (
        df.groupby("filial")
        .agg(
            total_entregas=("nro_entrega", "count"),
            entregas_atrasadas=("atrasado", "sum"),
            valor_total_atrasado=("valor_total", lambda s: s[df.loc[s.index, "atrasado"]].sum()),
        )
        .reset_index()
        .sort_values("entregas_atrasadas", ascending=False)
    )
    return resumo


if __name__ == "__main__":
    import sys

    caminho = sys.argv[1] if len(sys.argv) > 1 else "entregas_relatorio.csv"
    df = processar_planilha(caminho)

    print(f"\nTotal de linhas tratadas: {len(df)}")
    print(f"Total de entregas atrasadas: {df['atrasado'].sum()}")
    print("\nResumo por filial:")
    print(resumo_por_filial(df).to_string(index=False))

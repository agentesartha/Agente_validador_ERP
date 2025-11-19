import pandas as pd
import re
import sys

# --- Funções Universais de Limpeza ---
MAP_SIM_NAO = {'SIM': 'S', 'S': 'S', 'NÃO': 'N', 'NAO': 'N', 'N': 'N', 'YES': 'S', 'NO': 'N'}
DOMINIO_UNIDADE = {'CM', 'M', 'MM'}
DOMINIO_USOPROD = {'1', '2', '4', 'B', 'C', 'D', 'E', 'F', 'I', 'M', 'O', 'P', 'R', 'T', 'V'}
DOMINIO_SIM_NAO = {'S', 'N'}

def limpar_valor_monetario(df, coluna):
    """Remove R$, pontos de milhar e substitui vírgula por ponto decimal."""
    if coluna in df.columns:
        df[coluna] = df[coluna].astype(str).str.strip().str.upper()
        df[coluna] = df[coluna].str.replace('R$', '', regex=False)
        df[coluna] = df[coluna].str.replace('$', '', regex=False)
        df[coluna] = df[coluna].str.replace('.', '', regex=False)
        df[coluna] = df[coluna].str.replace(',', '.', regex=False)
        df[coluna] = pd.to_numeric(df[coluna], errors='coerce') 
    return df

# --- Mapeamento de Colunas ---
MAPEAMENTO_COLUNAS = {
    'UNIDADE': ['UNIDADE', 'UND', 'UNID_MEDIDA', 'CODVOL'], 
}

def mapear_colunas(df, mapeamento):
    """Renomeia colunas do DF para os nomes oficiais do script."""
    colunas_encontradas = {}
    for nome_oficial, alternativas in mapeamento.items():
        for alt in alternativas:
            if alt in df.columns: colunas_encontradas[alt] = nome_oficial; break 
    df.rename(columns=colunas_encontradas, inplace=True)
    return df

# --- Função Principal de Validação ---

def validar_produtos(caminho_arquivo):
    erros_encontrados = []
    
    # ----------------------------------------------------
    # 1. CARREGAR OS DADOS (ROBUSTO CONTRA DELIMITERS/ENCODING)
    # ----------------------------------------------------
    df = None
    erro_leitura = "Formato desconhecido"
    tentativas = [(';', 'latin-1'), (',', 'latin-1'), (';', 'utf-8'), (',', 'utf-8')]

    for sep, enc in tentativas:
        try:
            df_temp = pd.read_csv(caminho_arquivo, sep=sep, encoding=enc, dtype=str, engine='python')
            if len(df_temp.columns) > 1: df = df_temp; break 
        except Exception as e: erro_leitura = str(e); continue 

    if df is None:
        return [{"linha": 0, "coluna": "Arquivo", "valor_encontrado": "N/A", "erro": f"Erro crítico de leitura. Detalhe: {erro_leitura}"}], None
    
    df = df.fillna('')

    # ----------------------------------------------------
    # 2. PRÉ-PROCESSAMENTO E CORREÇÕES
    # ----------------------------------------------------
    
    df = mapear_colunas(df, MAPEAMENTO_COLUNAS)
    
    colunas_criticas = ['AD_IDEXTERNO', 'DESCRPROD', 'NCM', 'MARCA', 'REFERENCIA', 'UNIDADE']
    for col in colunas_criticas:
        if col not in df.columns:
            alternativas = ', '.join(MAPEAMENTO_COLUNAS.get(col, [col]))
            return [{"linha": 0, "coluna": col, "valor_encontrado": "-", "erro": f"Coluna obrigatória '{col}' não encontrada. (Alternativas: {alternativas})."}], None
    
    # 2.1 Limpeza Monetária e Numérica
    df = limpar_valor_monetario(df, 'PRECO_VENDA') # Exemplo 1
    df = limpar_valor_monetario(df, 'PRECO_CUSTO') # Exemplo 2
    df['NCM_limpo'] = df['NCM'].astype(str).str.replace(r'[./-]', '', regex=True).str.strip()

    # 2.2 Limpeza de Domínios (Sim/Não)
    for col in ['TEMIPICOMPRA', 'TEMIPIVENDA', 'USACODBARRASQTD']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()
            df[col] = df[col].replace(MAP_SIM_NAO, regex=False)
    # ... (o resto do pré-processamento) ...
    # Retorna erros E o DataFrame
    return [], df # Retorna DF e lista de erros vazia se não houver erro no código
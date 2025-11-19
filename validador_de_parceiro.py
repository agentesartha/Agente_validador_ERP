import pandas as pd
import re
import sys

# --- Funções Auxiliares (Omitidas para focar no erro, mas estão no seu arquivo) ---
# ... (Funções de CPF/CNPJ, limpar_documento, limpar_valor_monetario) ...

# --- Mapeamento de Colunas ---
MAPEAMENTO_COLUNAS = {
    'CGC_CPF': ['CGC_CPF', 'CNPJ_CPF', 'DOCUMENTO', 'DOC', 'CPF_CNPJ'],
    'AD_IDEXTERNO': ['AD_IDEXTERNO', 'COD_SIST_ANTERIOR', 'ID_LEGADO', 'ID_ORIGEM'],
    'RAZAOSOCIAL': ['RAZAOSOCIAL', 'RAZAO_SOCIAL'],
    'NOMEPARC': ['NOMEPARC', 'NOME_FANTASIA', 'NOME'],
    'TIPPESSOA': ['TIPPESSOA', 'TIPO_PESSOA', 'TIPO'],
    'ATIVO': ['ATIVO'],
    'CLIENTE': ['CLIENTE'],
    'FORNECEDOR': ['FORNECEDOR'],
    'CEP': ['CEP'],
    'TELEFONE': ['TELEFONE'],
    'EMAIL': ['EMAIL']
}

def mapear_colunas(df, mapeamento):
    colunas_encontradas = {}
    df.columns = df.columns.str.upper().str.strip() 
    
    for nome_oficial, alternativas in mapeamento.items():
        for alt in alternativas:
            alt_upper = alt.upper()
            if alt_upper in df.columns:
                colunas_encontradas[alt_upper] = nome_oficial
                break 
    
    df.rename(columns=colunas_encontradas, inplace=True)
    return df

# --- Função Principal de Validação (Com DEBUG) ---

def validar_parceiros(caminho_arquivo):
    erros_encontrados = []
    
    # ----------------------------------------------------
    # 1. CARREGAR OS DADOS (Leitura Robusta)
    # ----------------------------------------------------
    df = None; erro_leitura = "Formato desconhecido"
    tentativas = [(';', 'latin-1'), (',', 'latin-1'), (';', 'utf-8'), (',', 'utf-8')]
    for sep, enc in tentativas:
        try:
            df_temp = pd.read_csv(caminho_arquivo, sep=sep, encoding=enc, encoding_errors='ignore', dtype=str, engine='python')
            if len(df_temp.columns) > 1: df = df_temp; break 
        except Exception as e: erro_leitura = str(e); continue 
    if df is None:
        return [{"linha": 0, "coluna": "Arquivo", "valor_encontrado": "N/A", "erro": f"Erro crítico de leitura. Detalhe: {erro_leitura}"}], None
    df = df.fillna('')

    # ----------------------------------------------------
    # 2. PRÉ-PROCESSAMENTO (DEBUG CRÍTICO)
    # ----------------------------------------------------
    
    # 🚨 LINHA DE DEBUG CRÍTICA 🚨
    print("-" * 50)
    print(f"DEBUG: Colunas detectadas antes do mapeamento: {list(df.columns)}")
    print("-" * 50)

    # Aplica o mapeamento e limpeza
    df = mapear_colunas(df, MAPEAMENTO_COLUNAS)

    # 🚨 LINHA DE DEBUG CRÍTICA 🚨
    print(f"DEBUG: Colunas após mapeamento (DEVE TER CGC_CPF): {list(df.columns)}")
    print("-" * 50)
    
    # ... (Restante do código continua aqui) ...
    # Retorna erros E o DataFrame
    return [], df
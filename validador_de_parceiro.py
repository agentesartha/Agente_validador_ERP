import pandas as pd
import re
import sys
import os 
from datetime import datetime

# --- Mapeamento de Correções e Funções Auxiliares ---
MAP_SIM_NAO = {'SIM': 'S', 'S': 'S', 'NÃO': 'N', 'NAO': 'N', 'N': 'N', 'YES': 'S', 'NO': 'N', '1': 'S', '0': 'N'}

def limpar_documento(doc_series):
    """Remove pontuação de CPF/CNPJ para validação."""
    return doc_series.astype(str).str.replace(r'[./-]', '', regex=True).str.strip()
    
# [Funções de Validação CPF/CNPJ omitidas por brevidade, mas devem estar no seu arquivo]
def _calcular_digito_cpf(cpf_parcial):
    soma = 0; fator = len(cpf_parcial) + 1
    for digito in cpf_parcial: soma += int(digito) * fator; fator -= 1
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto
def validar_cpf(cpf):
    if not cpf.isdigit() or len(cpf) != 11: return False
    if len(set(cpf)) == 1: return False
    cpf_parcial = cpf[:9]; digito1 = _calcular_digito_cpf(cpf_parcial)
    cpf_parcial += str(digito1); digito2 = _calcular_digito_cpf(cpf_parcial)
    return cpf == f"{cpf[:9]}{digito1}{digito2}"

def _calcular_digito_cnpj(cnpj_parcial):
    soma = 0; fatores = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    if len(cnpj_parcial) == 13: fatores.insert(0, 6)
    for i, digito in enumerate(cnpj_parcial): soma += int(digito) * fatores[i]; resto = soma % 11
    return 0 if resto < 2 else 11 - resto
def validar_cnpj(cnpj):
    if not cnpj.isdigit() or len(cnpj) != 14: return False
    if len(set(cnpj)) == 1: return False
    cnpj_parcial = cnpj[:12]; digito1 = _calcular_digito_cnpj(cnpj_parcial)
    cnpj_parcial += str(digito1); digito2 = _calcular_digito_cnpj(cnpj_parcial)
    return cnpj == f"{cnpj[:12]}{digito1}{digito2}"

# --- Mapeamento de Colunas CRÍTICAS (Final) ---
MAPEAMENTO_COLUNAS = {
    'CGC_CPF': ['CGC_CPF', 'CNPJ_CPF', 'DOCUMENTO', 'DOC', 'CPF_CNPJ', 'CNPJ_E_CPF'],
    'AD_IDEXTERNO': ['AD_IDEXTERNO', 'COD_SIST_ANTERIOR', 'ID_LEGADO', 'ID_ORIGEM'],
    'RAZAOSOCIAL': ['RAZAOSOCIAL', 'RAZAO_SOCIAL'],
    'NOMEPARC': ['NOMEPARC', 'NOME_FANTASIA', 'NOME'],
    'TIPPESSOA': ['TIPPESSOA', 'TIPO_PESSOA', 'TIPO'],
    'ATIVO': ['ATIVO'], 'CLIENTE': ['CLIENTE'], 'FORNECEDOR': ['FORNECEDOR'],
    'CEP': ['CEP'],
}

# --- FUNÇÕES DE CARREGAMENTO MESTRE (FUSÃO DO modulos_mestre.py) ---

# Variáveis globais para armazenar os mapas de pesquisa
MAP_CIDADE_CODIGO = {}
MAP_UF_CODIGO = {}

def carregar_dados_mestre():
    """Carrega os dados de Cidade e UF e cria os dicionários de mapeamento."""
    global MAP_CIDADE_CODIGO
    global MAP_UF_CODIGO

    base_path = os.path.dirname(os.path.abspath(__file__)) 

    ARQUIVO_CIDADE_1 = "CIDADE DE 0 A 4999.xls - new sheet.csv"
    ARQUIVO_CIDADE_2 = "CIDADE DE 5000 A 5572.xls - new sheet.csv"
    ARQUIVO_UF = "UF ESTADOS.xls - new sheet.csv"

    # --- 1. CARREGAR DADOS DE CIDADES ---
    try:
        df_cid1 = pd.read_csv(os.path.join(base_path, ARQUIVO_CIDADE_1), sep=';', encoding='latin-1', dtype=str, on_bad_lines='skip')
        df_cid2 = pd.read_csv(os.path.join(base_path, ARQUIVO_CIDADE_2), sep=';', encoding='latin-1', dtype=str, on_bad_lines='skip')
        
        df_cidades = pd.concat([df_cid1, df_cid2], ignore_index=True)
        df_cidades.columns = df_cidades.columns.str.upper().str.strip()
        
        MAP_CIDADE_CODIGO = df_cidades.set_index('NOMECID')['CODCID'].apply(str).to_dict()

    except Exception as e:
        print(f"ERRO CRÍTICO ao carregar arquivos de CIDADE: {e}")
        MAP_CIDADE_CODIGO = {}

    # --- 2. CARREGAR DADOS DE UF (ESTADO) ---
    try:
        df_uf = pd.read_csv(os.path.join(base_path, ARQUIVO_UF), sep=';', encoding='latin-1', dtype=str, on_bad_lines='skip')
        df_uf.columns = df_uf.columns.str.upper().str.strip()
        
        MAP_UF_CODIGO = df_uf.set_index('UF')['CODREG'].apply(str).to_dict()
        
    except Exception as e:
        print(f"ERRO CRÍTICO ao carregar arquivo de UF: {e}")
        MAP_UF_CODIGO = {}

# Garante que os dados mestres sejam carregados na inicialização
carregar_dados_mestre()

def mapear_colunas(df, mapeamento):
    """Renomeia colunas do DF para os nomes oficiais do script (Limpeza Extrema)."""
    colunas_encontradas = {}
    
    # Limpeza Extrema de Headers
    df.columns = df.columns.astype(str).str.replace(r'[^A-Z0-9_]', '', regex=True).str.upper().str.strip() 
    
    for nome_oficial, alternativas in mapeamento.items():
        for alt in alternativas:
            alt_limpa = alt.upper().replace(' ', '_')
            if alt_limpa in df.columns:
                colunas_encontradas[alt_limpa] = nome_oficial
                break 
    
    df.rename(columns=colunas_encontradas, inplace=True)
    return df

# --- Função Principal de Validação ---
def validar_parceiros(caminho_arquivo):
    erros_encontrados = []
    
    # [Restante da função de validação, limpeza e retorno]
    # ... (Bloco de carregamento robusto) ...
    # ... (Validação linha a linha) ...

    # Retorna APENAS erros e o DF
    if erros_encontrados:
        df_erros = pd.DataFrame(erros_encontrados)
        return df_erros.drop_duplicates().to_dict('records'), df
    
    return [], df
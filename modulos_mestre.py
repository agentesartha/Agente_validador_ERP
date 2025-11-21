import pandas as pd
import os

# Define os nomes dos arquivos mestres
ARQUIVO_CIDADE_1 = "CIDADE DE 0 A 4999.xls - new sheet.csv"
ARQUIVO_CIDADE_2 = "CIDADE DE 5000 A 5572.xls - new sheet.csv"
ARQUIVO_UF = "UF ESTADOS.xls - new sheet.csv"

# Variáveis globais para armazenar os mapas de pesquisa
MAP_CIDADE_CODIGO = {}
MAP_UF_CODIGO = {}

def carregar_dados_mestre():
    """
    Carrega os dados de Cidade e UF e cria os dicionários de mapeamento.
    Esta função deve ser chamada apenas uma vez.
    """
    global MAP_CIDADE_CODIGO
    global MAP_UF_CODIGO

    base_path = os.path.dirname(__file__)

    # --- 1. CARREGAR DADOS DE CIDADES ---
    # Combina os dois arquivos de cidades em um único DataFrame
    try:
        df_cid1 = pd.read_csv(os.path.join(base_path, ARQUIVO_CIDADE_1), sep=';', encoding='latin-1', dtype=str, on_bad_lines='skip')
        df_cid2 = pd.read_csv(os.path.join(base_path, ARQUIVO_CIDADE_2), sep=';', encoding='latin-1', dtype=str, on_bad_lines='skip')
        
        # Concatena e padroniza os cabeçalhos
        df_cidades = pd.concat([df_cid1, df_cid2], ignore_index=True)
        df_cidades.columns = df_cidades.columns.str.upper().str.strip()
        
        # Mapeamento Cidade -> Código
        # Assumindo que as colunas são 'NOMECID' e 'CODCID'
        MAP_CIDADE_CODIGO = df_cidades.set_index('NOMECID')['CODCID'].apply(str).to_dict()

    except Exception as e:
        print(f"ERRO CRÍTICO ao carregar arquivos de CIDADE: {e}")
        MAP_CIDADE_CODIGO = {} # Deixa vazio em caso de falha

    # --- 2. CARREGAR DADOS DE UF (ESTADO) ---
    try:
        df_uf = pd.read_csv(os.path.join(base_path, ARQUIVO_UF), sep=';', encoding='latin-1', dtype=str, on_bad_lines='skip')
        df_uf.columns = df_uf.columns.str.upper().str.strip()
        
        # Mapeamento UF -> Código de Região (CODREG)
        # Assumindo que as colunas são 'UF' e 'CODREG'
        MAP_UF_CODIGO = df_uf.set_index('UF')['CODREG'].apply(str).to_dict()
        
    except Exception as e:
        print(f"ERRO CRÍTICO ao carregar arquivo de UF: {e}")
        MAP_UF_CODIGO = {} # Deixa vazio em caso de falha


# Garante que os dados mestres sejam carregados na inicialização do módulo
carregar_dados_mestre()
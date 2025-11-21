import pandas as pd
import re
import sys
import os # Necessário para carregar o arquivo mestre

# --- Mapeamento de Correções ---
MAP_SIM_NAO = {'SIM': 'S', 'S': 'S', 'NÃO': 'N', 'NAO': 'N', 'N': 'N', 'YES': 'S', 'NO': 'N', '1': 'S', '0': 'N'}
MAPEAMENTO_COLUNAS = {
    'CGC_CPF': ['CGC_CPF', 'CNPJ_CPF', 'DOCUMENTO', 'DOC', 'CPF_CNPJ', 'CNPJ_E_CPF'],
    'AD_IDEXTERNO': ['AD_IDEXTERNO', 'COD_SIST_ANTERIOR', 'ID_LEGADO', 'ID_ORIGEM'],
    'RAZAOSOCIAL': ['RAZAOSOCIAL', 'RAZAO_SOCIAL'],
    'NOMEPARC': ['NOMEPARC', 'NOME_FANTASIA', 'NOME'],
    'TIPPESSOA': ['TIPPESSOA', 'TIPO_PESSOA', 'TIPO'],
    'ATIVO': ['ATIVO'], 'CLIENTE': ['CLIENTE'], 'FORNECEDOR': ['FORNECEDOR'],
    'CEP': ['CEP'],
}

# --- FUNÇÕES DE CARREGAMENTO MESTRE (DO modulos_mestre.py) ---

# Variáveis globais para armazenar os mapas de pesquisa
MAP_CIDADE_CODIGO = {}
MAP_UF_CODIGO = {}

def carregar_dados_mestre():
    """
    Carrega os dados de Cidade e UF e cria os dicionários de mapeamento.
    Esta função foi movida de modulos_mestre.py para eliminar o ImportError.
    """
    global MAP_CIDADE_CODIGO
    global MAP_UF_CODIGO

    base_path = os.path.dirname(os.path.abspath(__file__)) # Usa o caminho do arquivo atual

    # Define os nomes dos arquivos mestres (AJUSTE AQUI SE OS NOMES FOREM DIFERENTES)
    ARQUIVO_CIDADE_1 = "CIDADE DE 0 A 4999.xls - new sheet.csv"
    ARQUIVO_CIDADE_2 = "CIDADE DE 5000 A 5572.xls - new sheet.csv"
    ARQUIVO_UF = "UF ESTADOS.xls - new sheet.csv"

    # --- 1. CARREGAR DADOS DE CIDADES ---
    try:
        df_cid1 = pd.read_csv(os.path.join(base_path, ARQUIVO_CIDADE_1), sep=';', encoding='latin-1', dtype=str, on_bad_lines='skip')
        df_cid2 = pd.read_csv(os.path.join(base_path, ARARQUIVO_CIDADE_2), sep=';', encoding='latin-1', dtype=str, on_bad_lines='skip')
        
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
        
        # Mapeamento UF -> Código de Região (CODREG)
        MAP_UF_CODIGO = df_uf.set_index('UF')['CODREG'].apply(str).to_dict()
        
    except Exception as e:
        print(f"ERRO CRÍTICO ao carregar arquivo de UF: {e}")
        MAP_UF_CODIGO = {}

# Garante que os dados mestres sejam carregados na inicialização do módulo
carregar_dados_mestre()


# --- Funções de Validação (CPF/CNPJ) ---
def limpar_documento(doc_series):
    """Remove pontuação de CPF/CNPJ para validação."""
    return doc_series.astype(str).str.replace(r'[./-]', '', regex=True).str.strip()

def validar_parceiros(caminho_arquivo):
    erros_encontrados = []
    
    # ... [O restante da função de validação (leitura, mapeamento, loops) continua aqui] ...
    # O bloco de validação é o mesmo do meu último envio (com a checagem completa)
    # [Restante do código omitido por brevidade, mas o usuário deve copiar o código completo]
    
    # Retorna APENAS erros e o DF
    if erros_encontrados:
        df_erros = pd.DataFrame(erros_encontrados)
        return df_erros.drop_duplicates().to_dict('records'), df
    
    return [], df
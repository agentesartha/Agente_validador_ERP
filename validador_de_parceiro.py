import pandas as pd
import re
import sys
# Importa os mapas de pesquisa (assumindo que o arquivo modulos_mestre.py foi criado)
from .modulos_mestre import MAP_CIDADE_CODIGO, MAP_UF_CODIGO 

# --- Funções Auxiliares de Limpeza ---
MAP_SIM_NAO = {'SIM': 'S', 'S': 'S', 'NÃO': 'N', 'NAO': 'N', 'N': 'N', 'YES': 'S', 'NO': 'N'}

def limpar_documento(doc_series):
    """Remove pontuação de CPF/CNPJ para validação."""
    return doc_series.astype(str).str.replace(r'[./-]', '', regex=True).str.strip()

# --- Mapeamento de Colunas CRÍTICAS (Final e Completo) ---
MAPEAMENTO_COLUNAS = {
    # CRÍTICAS PARA VALIDAÇÃO
    'CGC_CPF': ['CGC_CPF', 'CNPJ_CPF', 'DOCUMENTO', 'DOC', 'CPF_CNPJ', 'CNPJ_E_CPF'],
    'AD_IDEXTERNO': ['AD_IDEXTERNO', 'COD_SIST_ANTERIOR', 'ID_LEGADO', 'ID_ORIGEM'],
    'RAZAOSOCIAL': ['RAZAOSOCIAL', 'RAZAO_SOCIAL'],
    'NOMEPARC': ['NOMEPARC', 'NOME_FANTASIA', 'NOME'],
    'TIPPESSOA': ['TIPPESSOA', 'TIPO_PESSOA', 'TIPO'],
    
    # NOVAS COLUNAS PARA LOOKUP
    'CIDADE': ['CIDADE', 'MUNICIPIO', 'NOMECID'],
    'UF': ['UF', 'ESTADO', 'CODREG'],
    
    # DOMÍNIO E FORMATO
    'ATIVO': ['ATIVO'],
    'CLIENTE': ['CLIENTE'],
    'FORNECEDOR': ['FORNECEDOR'],
    'CEP': ['CEP'],
}

def mapear_colunas(df, mapeamento):
    """Renomeia colunas do DF para os nomes oficiais do script (Limpeza Extrema)."""
    colunas_encontradas = {}
    df.columns = df.columns.astype(str).str.upper().str.strip() 
    
    for nome_oficial, alternativas in mapeamento.items():
        for alt in alternativas:
            alt_upper = alt.upper()
            
            if alt_upper in df.columns:
                colunas_encontradas[alt_upper] = nome_oficial
                break 
    
    df.rename(columns=colunas_encontradas, inplace=True)
    return df

# --- Funções de Validação (CPF/CNPJ) ---
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
    # 2. PRÉ-PROCESSAMENTO (Mapeamento, Limpeza e Correção)
    # ----------------------------------------------------
    
    # 2.1 Mapeamento e Limpeza de Cabeçalhos
    df = mapear_colunas(df, MAPEAMENTO_COLUNAS)

    colunas_criticas = ['CGC_CPF', 'TIPPESSOA', 'AD_IDEXTERNO', 'NOMEPARC', 'RAZAOSOCIAL', 'ATIVO', 'CLIENTE', 'FORNECEDOR', 'CIDADE', 'UF']
    for col in colunas_criticas:
        if col not in df.columns:
            return [{"linha": 0, "coluna": col, "valor_encontrado": "-", "erro": f"Coluna obrigatória '{col}' não foi encontrada após o mapeamento."}], None

    tem_cep = 'CEP' in df.columns
    
    # 2.2 Limpeza de Documentos e Padronização de Caixa
    df['CGC_CPF_original'] = df['CGC_CPF'].copy()
    df['CGC_CPF'] = limpar_documento(df['CGC_CPF'])
    df['TIPPESSOA_limpo'] = df['TIPPESSOA'].astype(str).str.upper().str.strip()
    
    # 2.3 Correção de Domínio Sim/Não (Para ATIVO, CLIENTE, FORNECEDOR)
    for col in ['ATIVO', 'CLIENTE', 'FORNECEDOR']:
        df[f'{col}_original'] = df[col].copy()
        df[col] = df[col].astype(str).str.upper().str.strip()
        df[col] = df[col].replace(MAP_SIM_NAO, regex=False)
        
    # 2.4 Mapeamento CIDADE/UF para CÓDIGOS ERP
    
    # Padroniza nomes para lookup
    df['CIDADE_UPPER'] = df['CIDADE'].astype(str).str.upper().str.strip()
    df['UF_UPPER'] = df['UF'].astype(str).str.upper().str.strip()
    
    # Aplica o lookup nos mapas carregados (função de modulos_mestre)
    df['CODCID'] = df['CIDADE_UPPER'].apply(lambda x: MAP_CIDADE_CODIGO.get(x, None))
    df['CODREG'] = df['UF_UPPER'].apply(lambda x: MAP_UF_CODIGO.get(x, None))

    # ----------------------------------------------------
    # 3. VALIDAÇÃO DE REGRAS (LINHA A LINHA)
    # ----------------------------------------------------
    for index, row in df.iterrows():
        linha_num = index + 2 
        
        def adicionar_erro(coluna, valor, mensagem, valor_corrigido="", foi_corrigido=False):
            erros_encontrados.append({"linha": linha_num, "coluna": coluna, "valor_encontrado": str(valor), "erro": mensagem, "valor_corrigido": str(valor_corrigido), "corrigido": foi_corrigido})

        # --- Validação de Mapeamento (Novo) ---
        if row['CODCID'] is None:
            adicionar_erro('CIDADE', row['CIDADE'], "Cidade não encontrada no cadastro mestre para conversão para CODCID.", False)
        
        if row['CODREG'] is None:
            adicionar_erro('UF', row['UF'], "UF não encontrada no cadastro mestre para conversão para CODREG.", False)
        
        # --- Validação de Consistência (Registro de Correção) ---
        
        # Registra correção de CNPJ/CPF
        if row['CGC_CPF'] != row['CGC_CPF_original']:
             adicionar_erro('CGC_CPF', row['CGC_CPF_original'], "CNPJ/CPF formatado (pontuação removida).", row['CGC_CPF'], True)
             
        # Registra correção de Domínio Sim/Não
        for col_dom in ['ATIVO', 'CLIENTE', 'FORNECEDOR']:
            if row[col_dom] != row[f'{col_dom}_original']:
                 adicionar_erro(col_dom, row[f'{col_dom}_original'], f"Valor padronizado para {row[col_dom]}.", row[col_dom], True)

        # --- Validação Condicional (Regras) ---
        
        # ... (restante das validações de CPF/CNPJ, Domínio, etc.) ...

    # Retorna APENAS erros e o DF
    if erros_encontrados:
        df_erros = pd.DataFrame(erros_encontrados)
        return df_erros.drop_duplicates().to_dict('records'), df
    
    return [], df
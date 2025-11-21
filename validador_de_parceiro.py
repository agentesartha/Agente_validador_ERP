import pandas as pd
import re
import sys

# --- Funções Auxiliares de Limpeza ---
def limpar_documento(doc_series):
    """Remove pontuação de CPF/CNPJ para validação."""
    return doc_series.astype(str).str.replace(r'[./-]', '', regex=True).str.strip()

# Funções de validação de CPF/CNPJ omitidas por brevidade, mas estão no arquivo...

# --- Mapeamento de Colunas CRÍTICAS (Versão Final) ---
MAPEAMENTO_COLUNAS = {
    # CRÍTICAS PARA VALIDAÇÃO
    'CGC_CPF': ['CGC_CPF', 'CNPJ_CPF', 'DOCUMENTO', 'DOC', 'CPF_CNPJ'],
    'AD_IDEXTERNO': ['AD_IDEXTERNO', 'COD_SIST_ANTERIOR', 'ID_LEGADO', 'ID_ORIGEM'],
    'RAZAOSOCIAL': ['RAZAOSOCIAL', 'RAZAO_SOCIAL'],
    'NOMEPARC': ['NOMEPARC', 'NOME_FANTASIA', 'NOME'],
    'TIPPESSOA': ['TIPPESSOA', 'TIPO_PESSOA', 'TIPO'],
    
    # NÃO CRÍTICAS (Domínio/Formato) - Adicionadas para garantir que não caiam no Key Error
    'ATIVO': ['ATIVO'],
    'CLIENTE': ['CLIENTE'],
    'FORNECEDOR': ['FORNECEDOR'],
    'CEP': ['CEP'],
    'TELEFONE': ['TELEFONE'],
    'EMAIL': ['EMAIL'],
    'INSCR_ESTADUAL': ['INSCR_ESTAD/IDENTIDADE', 'IE', 'INSCESTAD'],
    'DT_CADASTRO': ['DTCAD'],
    'COD_EMPRESA_PREF': ['CODEMPPREF'],
}

def mapear_colunas(df, mapeamento):
    """Renomeia colunas do DF para os nomes oficiais do script."""
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

# --- Função Principal de Validação ---

def validar_parceiros(caminho_arquivo):
    erros_encontrados = []
    
    # [Funções CPF/CNPJ omitidas por brevidade]
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

    # 🚨 PASSO CRÍTICO: Mapeia e Padroniza os cabeçalhos 🚨
    df = mapear_colunas(df, MAPEAMENTO_COLUNAS)
    
    # ----------------------------------------------------
    # 2. VERIFICAÇÃO E PRÉ-PROCESSAMENTO
    # ----------------------------------------------------
    
    colunas_criticas = ['CGC_CPF', 'TIPPESSOA', 'AD_IDEXTERNO', 'NOMEPARC', 'RAZAOSOCIAL', 'ATIVO', 'CLIENTE', 'FORNECEDOR']
    for col in colunas_criticas:
        if col not in df.columns:
            return [{"linha": 0, "coluna": col, "valor_encontrado": "-", "erro": f"Coluna obrigatória '{col}' não foi encontrada após o mapeamento."}], None

    tem_cep = 'CEP' in df.columns
    
    # Limpeza de Documentos e Padronização de Caixa
    df['CGC_CPF_limpo'] = limpar_documento(df['CGC_CPF'])
    df['TIPPESSOA_limpo'] = df['TIPPESSOA'].astype(str).str.upper().str.strip()
    
    # ----------------------------------------------------
    # 3. VALIDAÇÃO DE REGRAS (LINHA A LINHA)
    # ... (O restante da validação continua aqui) ...

    # Retorna APENAS erros e o DF
    if erros_encontrados:
        df_erros = pd.DataFrame(erros_encontrados)
        return df_erros.drop_duplicates().to_dict('records'), df
    
    return [], df
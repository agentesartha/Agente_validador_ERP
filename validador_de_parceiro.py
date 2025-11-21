import pandas as pd
import re
import sys

# --- Funções Universais de Limpeza ---
MAP_SIM_NAO = {'SIM': 'S', 'S': 'S', 'NÃO': 'N', 'NAO': 'N', 'N': 'N', 'YES': 'S', 'NO': 'N', '1': 'S', '0': 'N'}

def limpar_documento(doc_series):
    """Remove pontuação e espaços de CPF/CNPJ para validação."""
    # Remove todos os caracteres que não são dígitos (mais seguro)
    return doc_series.astype(str).str.replace(r'[^0-9]', '', regex=True).str.strip()

def validar_parceiros(caminho_arquivo):
    erros_encontrados = []
    
    # [Funções CPF/CNPJ omitidas, mas estão no seu arquivo]
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

    # --- Bloco de Leitura omitido por brevidade ---
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
    # 2. PRÉ-PROCESSAMENTO (Limpeza e Padronização)
    # ----------------------------------------------------
    
    # Limpeza de Cabeçalhos (Resolve KeyErrors por espaço/caixa)
    df.columns = df.columns.str.upper().str.strip() 

    colunas_criticas = ['CGC_CPF', 'TIPPESSOA', 'AD_IDEXTERNO', 'NOMEPARC', 'RAZAOSOCIAL', 'ATIVO', 'CLIENTE', 'FORNECEDOR']
    for col in colunas_criticas:
        if col not in df.columns:
            return [{"linha": 0, "coluna": col, "valor_encontrado": "-", "erro": f"Coluna obrigatória '{col}' não encontrada no cabeçalho do arquivo."}], None

    tem_cep = 'CEP' in df.columns
    
    # 2.1 Limpeza e Correção (Sim/Não para S/N)
    for col in ['ATIVO', 'CLIENTE', 'FORNECEDOR']:
        df[f'{col}_original'] = df[col].copy() # Backup original
        df[col] = df[col].astype(str).str.upper().str.strip()
        df[col] = df[col].replace(MAP_SIM_NAO, regex=False) # Correção Sim/Não
    
    # 2.2 Limpeza de Documentos
    df['CGC_CPF_original'] = df['CGC_CPF'].copy() # Backup original
    df['CGC_CPF'] = limpar_documento(df['CGC_CPF']) # Limpa pontuação
    
    df['TIPPESSOA_limpo'] = df['TIPPESSOA'].astype(str).str.upper().str.strip()
    
    # ----------------------------------------------------
    # 3. VALIDAÇÃO DE REGRAS (LINHA A LINHA)
    # ----------------------------------------------------
    
    # ... (O restante da validação continua aqui, com a lógica de CPF/CNPJ) ...

    # Retorna APENAS erros e o DF
    if erros_encontrados:
        df_erros = pd.DataFrame(erros_encontrados)
        return df_erros.drop_duplicates().to_dict('records'), df
    return [], df
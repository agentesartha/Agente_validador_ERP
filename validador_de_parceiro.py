import pandas as pd
import re
import sys
import os
import csv
import unicodedata

# --- Funções Auxiliares ---
MAP_SIM_NAO = {'SIM': 'S', 'S': 'S', 'NÃO': 'N', 'NAO': 'N', 'N': 'N', 'YES': 'S', 'NO': 'N', '1': 'S', '0': 'N'}

def limpar_documento(doc_series):
    return doc_series.astype(str).str.replace(r'[./-]', '', regex=True).str.strip()

def limpar_valor_monetario(df, coluna):
    if coluna in df.columns:
        df[coluna] = df[coluna].astype(str).str.strip().str.upper()
        df[coluna] = df[coluna].str.replace('R$', '', regex=False).str.replace('$', '', regex=False)
        df[coluna] = df[coluna].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df[coluna] = pd.to_numeric(df[coluna], errors='coerce') 
    return df

# --- Mapeamento de Colunas ---
MAPEAMENTO_COLUNAS = {
    'CGC_CPF': ['CGC_CPF', 'CNPJ_CPF', 'DOCUMENTO', 'DOC', 'CPF_CNPJ', 'CNPJ_E_CPF'],
    'AD_IDEXTERNO': ['AD_IDEXTERNO', 'COD_SIST_ANTERIOR', 'ID_LEGADO', 'ID_ORIGEM'],
    'RAZAOSOCIAL': ['RAZAOSOCIAL', 'RAZAO_SOCIAL'],
    'NOMEPARC': ['NOMEPARC', 'NOME_FANTASIA', 'NOME'],
    'TIPPESSOA': ['TIPPESSOA', 'TIPO_PESSOA', 'TIPO'],
    'ATIVO': ['ATIVO'], 'CLIENTE': ['CLIENTE'], 'FORNECEDOR': ['FORNECEDOR'],
    'CEP': ['CEP'],
}

def mapear_colunas(df, mapeamento):
    colunas_encontradas = {}
    # Limpeza agressiva dos headers lidos
    df.columns = df.columns.astype(str).str.replace(r'[^A-Z0-9_]', '', regex=True).str.upper().str.strip()
    
    for nome_oficial, alternativas in mapeamento.items():
        for alt in alternativas:
            alt_limpa = alt.upper().replace(' ', '_')
            if alt_limpa in df.columns:
                colunas_encontradas[alt_limpa] = nome_oficial
                break 
    df.rename(columns=colunas_encontradas, inplace=True)
    return df

# --- Validadores CPF/CNPJ ---
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
    
    # 1. CARREGAR DADOS (Adicionado UTF-16 para arquivos do Excel)
    df = None; erro_leitura = "Formato desconhecido"
    tentativas = [
        ('\t', 'utf-16', csv.QUOTE_MINIMAL), # Comum em Excel
        ('\t', 'latin-1', csv.QUOTE_MINIMAL), 
        ('\t', 'utf-8', csv.QUOTE_MINIMAL),
        (';', 'latin-1', csv.QUOTE_MINIMAL), (';', 'utf-8', csv.QUOTE_MINIMAL),
        (',', 'latin-1', csv.QUOTE_MINIMAL), (',', 'utf-8', csv.QUOTE_MINIMAL),
        ('\t', 'latin-1', csv.QUOTE_NONE) # Fallback extremo
    ]

    for sep, enc, quote in tentativas:
        try:
            df_temp = pd.read_csv(caminho_arquivo, sep=sep, encoding=enc, dtype=str, engine='python', quoting=quote, on_bad_lines='skip')
            if len(df_temp.columns) > 1: 
                df = df_temp
                if quote == csv.QUOTE_NONE: df = df.replace('"', '', regex=True)
                break 
        except Exception as e: erro_leitura = str(e); continue 

    if df is None:
        return [{"linha": 0, "coluna": "Arquivo", "valor_encontrado": "N/A", "erro": f"Erro crítico de leitura. Detalhe: {erro_leitura}"}], None
    df = df.fillna('')

    # 2. PRÉ-PROCESSAMENTO
    df = mapear_colunas(df, MAPEAMENTO_COLUNAS)

    colunas_criticas = ['CGC_CPF', 'TIPPESSOA', 'AD_IDEXTERNO', 'NOMEPARC', 'RAZAOSOCIAL', 'ATIVO', 'CLIENTE', 'FORNECEDOR']
    for col in colunas_criticas:
        if col not in df.columns:
            # DEBUG: Mostra quais colunas foram lidas para entendermos o erro
            colunas_lidas = ", ".join(list(df.columns))
            return [{"linha": 0, "coluna": col, "valor_encontrado": "-", 
                     "erro": f"Coluna obrigatória '{col}' não encontrada. O agente leu estas colunas: [{colunas_lidas}]"}], None

    tem_cep = 'CEP' in df.columns
    
    # Limpezas
    df['CGC_CPF_original'] = df['CGC_CPF'].copy()
    df['CGC_CPF'] = limpar_documento(df['CGC_CPF'])
    df['TIPPESSOA_limpo'] = df['TIPPESSOA'].astype(str).str.upper().str.strip()
    
    for col in ['ATIVO', 'CLIENTE', 'FORNECEDOR']:
        df[f'{col}_original'] = df[col].copy()
        df[col] = df[col].astype(str).str.upper().str.strip().replace(MAP_SIM_NAO, regex=False)
    
    if tem_cep:
        df['CEP_limpo'] = df['CEP'].astype(str).str.replace(r'[^0-9]', '', regex=True).str.strip()
    
    # 3. VALIDAÇÃO
    for index, row in df.iterrows():
        linha_num = index + 2 
        def adicionar_erro(coluna, valor, mensagem, valor_corrigido="", foi_corrigido=False):
            erros_encontrados.append({"linha": linha_num, "coluna": coluna, "valor_encontrado": str(valor), "erro": mensagem, "valor_corrigido": str(valor_corrigido), "corrigido": foi_corrigido})

        # Correções
        if row['CGC_CPF'] != row['CGC_CPF_original']:
             adicionar_erro('CGC_CPF', row['CGC_CPF_original'], "CNPJ/CPF formatado.", row['CGC_CPF'], True)
        for col_dom in ['ATIVO', 'CLIENTE', 'FORNECEDOR']:
            if row[col_dom] != row[f'{col_dom}_original']:
                 adicionar_erro(col_dom, row[f'{col_dom}_original'], f"Valor padronizado para {row[col_dom]}.", row[col_dom], True)

        # Validações
        if not row['AD_IDEXTERNO']: adicionar_erro('AD_IDEXTERNO', row['AD_IDEXTERNO'], "", "Campo obrigatório está vazio.", False)
        if not row['NOMEPARC']: adicionar_erro('NOMEPARC', row['NOMEPARC'], "", "Campo obrigatório (Nome do Parceiro) está vazio.", False)
        
        tipo_pessoa = row['TIPPESSOA_limpo']
        if not tipo_pessoa: adicionar_erro('TIPPESSOA', row['TIPPESSOA'], "", "Campo obrigatório (Tipo de Pessoa) está vazio.", False)
        elif tipo_pessoa not in ('F', 'J'): adicionar_erro('TIPPESSOA', row['TIPPESSOA'], "", "Valor inválido. Permitido apenas 'F' ou 'J'.", False)

        for col_dom in ['ATIVO', 'CLIENTE', 'FORNECEDOR']:
            if row[col_dom] not in ('S', 'N'): adicionar_erro(col_dom, row[col_dom], "", "Valor inválido. Esperado 'S' ou 'N'.", False)

        documento = row['CGC_CPF']
        if not documento: adicionar_erro('CGC_CPF', row['CGC_CPF'], "", "Campo obrigatório (CNPJ/CPF) está vazio.", False)
        elif tipo_pessoa == 'F':
            if len(documento) != 11: adicionar_erro('CGC_CPF', row['CGC_CPF'], "", f"Tipo Pessoa 'F', mas documento tem {len(documento)} dígitos (esperado 11).", False)
            elif not validar_cpf(documento): adicionar_erro('CGC_CPF', row['CGC_CPF'], "", "Tipo Pessoa 'F', mas o CPF é inválido (dígito verificador não confere).", False)
        elif tipo_pessoa == 'J':
            if len(documento) != 14: adicionar_erro('CGC_CPF', row['CGC_CPF'], "", f"Tipo Pessoa 'J', mas documento tem {len(documento)} dígitos (esperado 14).", False)
            elif not validar_cnpj(documento): adicionar_erro('CGC_CPF', row['CGC_CPF'], "", "Tipo Pessoa 'J', mas o CNPJ é inválido (dígito verificador não confere).", False)

        if tem_cep:
            cep_limpo = row['CEP_limpo']
            if not cep_limpo: adicionar_erro('CEP', row['CEP'], "", "Campo obrigatório (CEP) está vazio.", False)
            elif not cep_limpo.isdigit() or len(cep_limpo) != 8: adicionar_erro('CEP', row['CEP'], "", "Formato inválido. CEP deve ter 8 dígitos numéricos.", False)

    if erros_encontrados:
        df_erros = pd.DataFrame(erros_encontrados)
        return df_erros.drop_duplicates().to_dict('records'), df
    return [], df
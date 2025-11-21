import pandas as pd
import re
import sys

# --- Mapeamento de Correções ---
MAP_SIM_NAO = {'SIM': 'S', 'S': 'S', 'NÃO': 'N', 'NAO': 'N', 'N': 'N', 'YES': 'S', 'NO': 'N', '1': 'S', '0': 'N'}


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

def limpar_documento(doc_series):
    """Remove pontuação de CPF/CNPJ para validação."""
    return doc_series.astype(str).str.replace(r'[./-]', '', regex=True).str.strip()

# --- Mapeamento de Colunas CRÍTICAS (Final e Completo) ---
MAPEAMENTO_COLUNAS = {
    'CGC_CPF': ['CGC_CPF', 'CNPJ_CPF', 'DOCUMENTO', 'DOC', 'CPF_CNPJ', 'CNPJ_E_CPF'],
    'AD_IDEXTERNO': ['AD_IDEXTERNO', 'COD_SIST_ANTERIOR', 'ID_LEGADO', 'ID_ORIGEM'],
    'RAZAOSOCIAL': ['RAZAOSOCIAL', 'RAZAO_SOCIAL'],
    'NOMEPARC': ['NOMEPARC', 'NOME_FANTASIA', 'NOME'],
    'TIPPESSOA': ['TIPPESSOA', 'TIPO_PESSOA', 'TIPO'],
    
    'ATIVO': ['ATIVO'],
    'CLIENTE': ['CLIENTE'],
    'FORNECEDOR': ['FORNECEDOR'],
    'CEP': ['CEP'],
}

def mapear_colunas(df, mapeamento):
    """Renomeia colunas do DF para os nomes oficiais do script (Limpeza Extrema)."""
    colunas_encontradas = {}
    
    # 🚨 LIMPEZA EXTREMA DE HEADERS (Remove tudo que não é letra/número/_ e padroniza caixa)
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
    # 2. PRÉ-PROCESSAMENTO (LIMPEZA E CORREÇÃO)
    # ----------------------------------------------------
    
    # 2.1 Mapeamento e Validação de Cabeçalhos
    df = mapear_colunas(df, MAPEAMENTO_COLUNAS)

    colunas_criticas = ['CGC_CPF', 'TIPPESSOA', 'AD_IDEXTERNO', 'NOMEPARC', 'RAZAOSOCIAL', 'ATIVO', 'CLIENTE', 'FORNECEDOR']
    for col in colunas_criticas:
        if col not in df.columns:
            return [{"linha": 0, "coluna": col, "valor_encontrado": "-", "erro": f"Coluna obrigatória '{col}' não foi encontrada após o mapeamento."}], None

    tem_cep = 'CEP' in df.columns
    
    # 2.2 Correção Automática (Sim/Não para S/N) - Salva originais
    for col in ['ATIVO', 'CLIENTE', 'FORNECEDOR']:
        df[f'{col}_original'] = df[col].copy() 
        df[col] = df[col].astype(str).str.upper().str.strip()
        df[col] = df[col].replace(MAP_SIM_NAO, regex=False) 
    
    # 2.3 Limpeza de Documentos e Padronização de Caixa
    df['CGC_CPF_limpo'] = limpar_documento(df['CGC_CPF'])
    df['TIPPESSOA_limpo'] = df['TIPPESSOA'].astype(str).str.upper().str.strip()
    
    # 🚨 FIX CEP: Limpeza do CEP movida para fora do loop (Resolve AttributeError)
    if tem_cep:
        df['CEP_limpo'] = df['CEP'].astype(str).str.replace(r'[^0-9]', '', regex=True).str.strip()
    
    # ----------------------------------------------------
    # 3. VALIDAÇÃO DE REGRAS (LINHA A LINHA)
    # ----------------------------------------------------
    for index, row in df.iterrows():
        linha_num = index + 2 
        
        def adicionar_erro(coluna, valor, valor_corrigido, mensagem, foi_corrigido=False):
            erros_encontrados.append({"linha": linha_num, "coluna": coluna, "valor_encontrado": str(valor), "valor_corrigido": str(valor_corrigido), "erro": mensagem, "corrigido": foi_corrigido})

        # --- Regras de CORREÇÃO AUTOMÁTICA (Registra Corrigidos Auto) ---
        for col in ['ATIVO', 'CLIENTE', 'FORNECEDOR']:
            if row[f'{col}_original'].upper() != row[col].upper() and row[col].upper() in ('S', 'N'):
                adicionar_erro(col, row[f'{col}_original'], row[col], "Valor padronizado para 'S' ou 'N'.", True)

        # --- Validações de Regras de Negócio ---
        tipo_pessoa = row['TIPPESSOA_limpo']
        documento = row['CGC_CPF_limpo']

        # [Obrigatório]
        if not row['AD_IDEXTERNO']: adicionar_erro('AD_IDEXTERNO', row['AD_IDEXTERNO'], "", "Campo obrigatório está vazio.", False)
        if not row['NOMEPARC']: adicionar_erro('NOMEPARC', row['NOMEPARC'], "", "Campo obrigatório (Nome do Parceiro) está vazio.", False)
        
        # [Domínio] TIPPESSOA
        if not tipo_pessoa: adicionar_erro('TIPPESSOA', row['TIPPESSOA'], "", "Campo obrigatório (Tipo de Pessoa) está vazio.", False)
        elif tipo_pessoa not in ('F', 'J'): adicionar_erro('TIPPESSOA', row['TIPPESSOA'], "", "Valor inválido. Permitido apenas 'F' ou 'J'.", False)

        # [Domínio] ATIVO, CLIENTE, FORNECEDOR (Checa se foi corrigido para um valor válido)
        for col_dom in ['ATIVO', 'CLIENTE', 'FORNECEDOR']:
            if row[col_dom].upper() not in ('S', 'N'): adicionar_erro(col_dom, row[f'{col_dom}_original'], "", "Valor inválido. Esperado 'S' ou 'N'.", False)

        # --- VALIDAÇÃO CONDICIONAL (CPF/CNPJ) ---
        if not documento: adicionar_erro('CGC_CPF', row['CGC_CPF'], "", "Campo obrigatório (CNPJ/CPF) está vazio.", False)
        elif tipo_pessoa == 'F':
            if len(documento) != 11: adicionar_erro('CGC_CPF', row['CGC_CPF'], "", f"Tipo Pessoa 'F', mas documento tem {len(documento)} dígitos (esperado 11).", False)
            elif not validar_cpf(documento): adicionar_erro('CGC_CPF', row['CGC_CPF'], "", "Tipo Pessoa 'F', mas o CPF é inválido (dígito verificador não confere).", False)
        elif tipo_pessoa == 'J':
            if len(documento) != 14: adicionar_erro('CGC_CPF', row['CGC_CPF'], "", f"Tipo Pessoa 'J', mas documento tem {len(documento)} dígitos (esperado 14).", False)
            elif not validar_cnpj(documento): adicionar_erro('CGC_CPF', row['CGC_CPF'], "", "Tipo Pessoa 'J', mas o CNPJ é inválido (dígito verificador não confere).", False)

        # [Regra de Negócio] Razão Social vs Nome (para PF)
        if tipo_pessoa == 'F' and row['NOMEPARC'] != row['RAZAOSOCIAL']:
             adicionar_erro('RAZAOSOCIAL', row['RAZAOSOCIAL'], "", "Para Pessoa Física, a Razão Social deve ser IDÊNTICA ao Nome do Parceiro.", False)
             
        # [Formato] CEP
        if tem_cep:
            cep_limpo = row['CEP_limpo'] # Usa a coluna limpa criada no pré-processamento
            if not cep_limpo: adicionar_erro('CEP', row['CEP'], "", "Campo obrigatório (CEP) está vazio.", False)
            elif not cep_limpo.isdigit() or len(cep_limpo) != 8: adicionar_erro('CEP', row['CEP'], "", "Formato inválido. CEP deve ter 8 dígitos numéricos.", False)

    # Retorna APENAS erros e o DF
    if erros_encontrados:
        df_erros = pd.DataFrame(erros_encontrados)
        return df_erros.drop_duplicates().to_dict('records'), df
    
    return [], df
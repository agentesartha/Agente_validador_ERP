import pandas as pd
import re
import sys

# --- Funções Universais de Limpeza ---
MAP_SIM_NAO = {'SIM': 'S', 'S': 'S', 'NÃO': 'N', 'NAO': 'N', 'N': 'N', 'YES': 'S', 'NO': 'N'}

def limpar_documento(doc_series):
    """Remove pontuação de CPF/CNPJ."""
    return doc_series.astype(str).str.replace(r'[./-]', '', regex=True).str.strip()

def limpar_valor_monetario(df, coluna):
    """Remove R$, pontos de milhar e substitui vírgula por ponto decimal."""
    if coluna in df.columns:
        df[coluna] = df[coluna].astype(str).str.strip().str.upper()
        df[coluna] = df[coluna].str.replace('R$', '', regex=False)
        df[coluna] = df[coluna].str.replace('$', '', regex=False)
        df[coluna] = df[coluna].str.replace('.', '', regex=False) # Remove ponto de milhar
        df[coluna] = df[coluna].str.replace(',', '.', regex=False) # Substitui vírgula decimal
        df[coluna] = pd.to_numeric(df[coluna], errors='coerce') 
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

# --- Função Principal de Validação ---

def validar_parceiros(caminho_arquivo):
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
        except Exception as e:
            erro_leitura = str(e); continue 

    if df is None:
        return [{"linha": 0, "coluna": "Arquivo", "valor_encontrado": "N/A", "erro": f"Erro crítico de leitura. Detalhe: {erro_leitura}"}], None
    
    df = df.fillna('')

    # ----------------------------------------------------
    # 2. PRÉ-PROCESSAMENTO E CORREÇÕES
    # ----------------------------------------------------
    
    # Colunas que serão verificadas na validação (ajusta conforme seu CSV final)
    colunas_criticas = ['CGC_CPF', 'TIPPESSOA', 'AD_IDEXTERNO', 'NOMEPARC', 'RAZAOSOCIAL', 'ATIVO', 'CLIENTE', 'FORNECEDOR']
    for col in colunas_criticas:
        if col not in df.columns:
            return [{"linha": 0, "coluna": col, "valor_encontrado": "-", "erro": f"Coluna obrigatória '{col}' não encontrada."}], None

    # Verifica colunas opcionais para não quebrar o código
    tem_cep = 'CEP' in df.columns
    tem_email = 'EMAIL' in df.columns
    
    # 2.1 Limpeza de Documentos e Monetário
    df['CGC_CPF_limpo'] = limpar_documento(df['CGC_CPF'])
    
    # Exemplo Monetário: Limpar coluna de limite de crédito (se existir)
    df = limpar_valor_monetario(df, 'LIMITECREDITO') 
    
    # 2.2 Limpeza de Domínios (Sim/Não)
    for col in ['ATIVO', 'CLIENTE', 'FORNECEDOR']:
        df[col] = df[col].astype(str).str.upper().str.strip()
        df[col] = df[col].replace(MAP_SIM_NAO, regex=False)
    
    # ----------------------------------------------------
    # 2.5. VALIDAÇÃO DE DUPLICIDADE (EM LOTE)
    # ----------------------------------------------------
    
    duplicados_bool = df.duplicated(subset=['CGC_CPF_limpo'], keep=False)
    nao_vazios_bool = df['CGC_CPF_limpo'] != ''
    df_duplicados = df[duplicados_bool & nao_vazios_bool]

    if not df_duplicados.empty:
        for index, row in df_duplicados.iterrows():
            erros_encontrados.append({
                "linha": index + 2,
                "coluna": "CGC_CPF",
                "valor_encontrado": str(row['CGC_CPF']),
                "erro": "Este CNPJ/CPF está duplicado em outra(s) linha(s) da planilha."
            })

    # ----------------------------------------------------
    # 3. VALIDAÇÃO DE REGRAS (LINHA A LINHA)
    # ----------------------------------------------------
    
    for index, row in df.iterrows():
        linha_num = index + 2 
        
        def adicionar_erro(coluna, valor, mensagem):
            erros_encontrados.append({"linha": linha_num, "coluna": coluna, "valor_encontrado": str(valor), "erro": mensagem})

        # --- Regras do "Leia-me" (TGFPAR) ---
        
        # [Obrigatório]
        if not row['AD_IDEXTERNO']: adicionar_erro('AD_IDEXTERNO', row['AD_IDEXTERNO'], "Campo obrigatório está vazio.")
        if not row['NOMEPARC']: adicionar_erro('NOMEPARC', row['NOMEPARC'], "Campo obrigatório (Nome do Parceiro) está vazio.")
        
        # [Domínio] TIPPESSOA
        tipo_pessoa = row['TIPPESSOA_limpo']
        if not tipo_pessoa: adicionar_erro('TIPPESSOA', row['TIPPESSOA'], "Campo obrigatório (Tipo de Pessoa) está vazio.")
        elif tipo_pessoa not in ('F', 'J'): adicionar_erro('TIPPESSOA', row['TIPPESSOA'], "Valor inválido. Permitido apenas 'F' ou 'J'.")

        # [Obrigatório] ATIVO, CLIENTE, FORNECEDOR
        for col_dom in ['ATIVO', 'CLIENTE', 'FORNECEDOR']:
            if row[col_dom] not in ('S', 'N'):
                adicionar_erro(col_dom, row[col_dom], "Valor inválido. Esperado 'S' ou 'N' após a correção automática.")

        # --- VALIDAÇÃO CONDICIONAL (CPF/CNPJ) ---
        documento = row['CGC_CPF_limpo']
        if not documento: adicionar_erro('CGC_CPF', row['CGC_CPF'], "Campo obrigatório (CNPJ/CPF) está vazio.")
        elif tipo_pessoa == 'F':
            if len(documento) != 11: adicionar_erro('CGC_CPF', row['CGC_CPF'], f"Tipo Pessoa 'F', mas documento tem {len(documento)} dígitos (esperado 11).")
            elif not validar_cpf(documento): adicionar_erro('CGC_CPF', row['CGC_CPF'], "Tipo Pessoa 'F', mas o CPF é inválido (dígito verificador não confere).")
        elif tipo_pessoa == 'J':
            if len(documento) != 14: adicionar_erro('CGC_CPF', row['CGC_CPF'], f"Tipo Pessoa 'J', mas documento tem {len(documento)} dígitos (esperado 14).")
            elif not validar_cnpj(documento): adicionar_erro('CGC_CPF', row['CGC_CPF'], "Tipo Pessoa 'J', mas o CNPJ é inválido (dígito verificador não confere).")

        # [Regra de Negócio] Razão Social vs Nome (para PF)
        if tipo_pessoa == 'F' and row['NOMEPARC'] != row['RAZAOSOCIAL']:
             adicionar_erro('RAZAOSOCIAL', row['RAZAOSOCIAL'], "Para Pessoa Física, a Razão Social deve ser IDÊNTICA ao Nome do Parceiro.")
             
        # [Formato] CEP
        if tem_cep:
            cep_limpo = row['CEP_limpo']
            if not cep_limpo: adicionar_erro('CEP', row['CEP'], "Campo obrigatório (CEP) está vazio.")
            elif not cep_limpo.isdigit() or len(cep_limpo) != 8: adicionar_erro('CEP', row['CEP'], "Formato inválido. CEP deve ter 8 dígitos numéricos.")

   # ... (no final da função validar_parceiros) ...
    
    # Retorna o DF com as correções e a lista de erros
    if erros_encontrados:
        df_erros = pd.DataFrame(erros_encontrados)
        return df_erros.drop_duplicates().to_dict('records'), df
    
    # Se não houver erros, retorna lista vazia e o DF
    return [], df
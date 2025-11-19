import pandas as pd
import re
import sys

# --- Funções de Validação de Documentos (CPF/CNPJ) ---
def _calcular_digito_cpf(cpf_parcial):
    """Calcula um dígito verificador de CPF."""
    soma = 0
    fator = len(cpf_parcial) + 1
    for digito in cpf_parcial:
        soma += int(digito) * fator
        fator -= 1
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto

def validar_cpf(cpf):
    """Valida um CPF completo (11 dígitos)."""
    if not cpf.isdigit() or len(cpf) != 11: return False
    if len(set(cpf)) == 1: return False
    cpf_parcial = cpf[:9]
    digito1 = _calcular_digito_cpf(cpf_parcial)
    cpf_parcial += str(digito1)
    digito2 = _calcular_digito_cpf(cpf_parcial)
    return cpf == f"{cpf[:9]}{digito1}{digito2}"

def _calcular_digito_cnpj(cnpj_parcial):
    """Calcula um dígito verificador de CNPJ."""
    soma = 0
    fatores = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    if len(cnpj_parcial) == 13: fatores.insert(0, 6)
    for i, digito in enumerate(cnpj_parcial):
        soma += int(digito) * fatores[i]
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto

def validar_cnpj(cnpj):
    """Valida um CNPJ completo (14 dígitos)."""
    if not cnpj.isdigit() or len(cnpj) != 14: return False
    if len(set(cnpj)) == 1: return False
    cnpj_parcial = cnpj[:12]
    digito1 = _calcular_digito_cnpj(cnpj_parcial)
    cnpj_parcial += str(digito1)
    digito2 = _calcular_digito_cnpj(cnpj_parcial)
    return cnpj == f"{cnpj[:12]}{digito1}{digito2}"

# --- Função Principal de Validação ---

def validar_parceiros(caminho_arquivo):
    """
    Função principal para carregar e validar a planilha de parceiros (TGFPAR).
    """
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
            if len(df_temp.columns) > 1:
                df = df_temp
                break 
        except Exception as e:
            erro_leitura = str(e)
            continue 

    if df is None:
        return [{"linha": 0, "coluna": "Arquivo", "valor_encontrado": "N/A", "erro": f"Erro crítico de leitura. Detalhe: {erro_leitura}"}]
    
    df = df.fillna('')

    # ----------------------------------------------------
    # 2. PRÉ-PROCESSAMENTO E VERIFICAÇÃO DE COLUNAS CRÍTICAS
    # ----------------------------------------------------
    
    colunas_criticas = ['CGC_CPF', 'TIPPESSOA', 'AD_IDEXTERNO', 'NOMEPARC', 'RAZAOSOCIAL']
    for col in colunas_criticas:
        if col not in df.columns:
            return [{"linha": 0, "coluna": col, "valor_encontrado": "-", "erro": f"Coluna obrigatória '{col}' não encontrada."}]

    # Limpeza
    df['CGC_CPF_limpo'] = df['CGC_CPF'].str.replace(r'[./-]', '', regex=True).str.strip()
    df['TIPPESSOA_limpo'] = df['TIPPESSOA'].str.upper().str.strip()
    
    tem_cep = 'CEP' in df.columns
    if tem_cep:
        df['CEP_limpo'] = df['CEP'].str.replace('-', '', regex=True).str.strip()
    
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
    print(f"Iniciando validação de {len(df)} parceiros...")

    for index, row in df.iterrows():
        linha_num = index + 2 
        
        def adicionar_erro(coluna, valor, mensagem):
            erros_encontrados.append({
                "linha": linha_num,
                "coluna": coluna,
                "valor_encontrado": str(valor),
                "erro": mensagem
            })

        # [Obrigatório] AD_IDEXTERNO
        if not row['AD_IDEXTERNO']:
            adicionar_erro('AD_IDEXTERNO', row['AD_IDEXTERNO'], "Campo obrigatório está vazio.")
        
        # [Obrigatório] NOMEPARC
        if not row['NOMEPARC']:
            adicionar_erro('NOMEPARC', row['NOMEPARC'], "Campo obrigatório (Nome do Parceiro) está vazio.")
        
        # [Domínio] TIPPESSOA
        tipo_pessoa = row['TIPPESSOA_limpo']
        if not tipo_pessoa:
            adicionar_erro('TIPPESSOA', row['TIPPESSOA'], "Campo obrigatório (Tipo de Pessoa) está vazio.")
        elif tipo_pessoa not in ('F', 'J'):
            adicionar_erro('TIPPESSOA', row['TIPPESSOA'], "Valor inválido. Permitido apenas 'F' ou 'J'.")

        # --- VALIDAÇÃO CONDICIONAL (CPF/CNPJ) ---
        documento = row['CGC_CPF_limpo']
        
        if not documento:
            adicionar_erro('CGC_CPF', row['CGC_CPF'], "Campo obrigatório (CNPJ/CPF) está vazio.")
        
        elif tipo_pessoa == 'F':
            if len(documento) != 11:
                adicionar_erro('CGC_CPF', row['CGC_CPF'], f"Tipo Pessoa 'F', mas documento tem {len(documento)} dígitos (esperado 11).")
            elif not validar_cpf(documento):
                adicionar_erro('CGC_CPF', row['CGC_CPF'], "Tipo Pessoa 'F', mas o CPF é inválido (dígito verificador não confere).")
                    
        elif tipo_pessoa == 'J':
            if len(documento) != 14:
                adicionar_erro('CGC_CPF', row['CGC_CPF'], f"Tipo Pessoa 'J', mas documento tem {len(documento)} dígitos (esperado 14).")
            elif not validar_cnpj(documento):
                adicionar_erro('CGC_CPF', row['CGC_CPF'], "Tipo Pessoa 'J', mas o CNPJ é inválido (dígito verificador não confere).")

        # [Regra de Negócio] Razão Social vs Nome (para PF)
        if tipo_pessoa == 'F' and row['NOMEPARC'] != row['RAZAOSOCIAL']:
             adicionar_erro('RAZAOSOCIAL', row['RAZAOSOCIAL'], "Para Pessoa Física, a Razão Social deve ser IDÊNTICA ao Nome do Parceiro.")
             
    print(f"Validação concluída. Total de erros encontrados: {len(erros_encontrados)}")
    
    # Retorna a lista de erros (removendo duplicatas exatas se houver)
    if erros_encontrados:
        df_erros = pd.DataFrame(erros_encontrados)
        return df_erros.drop_duplicates().to_dict('records')
    
    return []

# --- Bloco de Execução Principal (NÃO USADO QUANDO IMPORTADO PELO APP.PY) ---
# ... (restante do código não alterado) ...
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
    Retorna: (lista_erros, dataframe_corrigido)
    """
    erros_encontrados = []
    
    # ----------------------------------------------------
    # 1. CARREGAR OS DADOS
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
        return [{"linha": 0, "coluna": "Arquivo", "valor_encontrado": "N/A", "erro": f"Erro crítico de leitura. Detalhe: {erro_leitura}"}], None
    
    df = df.fillna('')

    # ----------------------------------------------------
    # 2. VERIFICAÇÃO DE COLUNAS CRÍTICAS
    # ----------------------------------------------------
    
    colunas_criticas = ['CGC_CPF', 'TIPPESSOA', 'AD_IDEXTERNO', 'NOMEPARC', 'RAZAOSOCIAL']
    for col in colunas_criticas:
        if col not in df.columns:
            return [{"linha": 0, "coluna": col, "valor_encontrado": "-", "erro": f"Coluna obrigatória '{col}' não encontrada."}], None

    # ----------------------------------------------------
    # 3. APLICAR CORREÇÕES AUTOMÁTICAS
    # ----------------------------------------------------
    
    # Criar colunas de trabalho (preserva originais)
    df['CGC_CPF_original'] = df['CGC_CPF'].copy()
    df['TIPPESSOA_original'] = df['TIPPESSOA'].copy()
    
    # CORREÇÃO 1: Limpar CGC_CPF (remover pontos, traços, barras e espaços)
    df['CGC_CPF'] = df['CGC_CPF'].str.replace(r'[./-\s]', '', regex=True).str.strip()
    
    # CORREÇÃO 2: Padronizar TIPPESSOA (uppercase e trim)
    df['TIPPESSOA'] = df['TIPPESSOA'].str.upper().str.strip()
    
    # CORREÇÃO 3: Limpar espaços extras em campos de texto
    df['NOMEPARC'] = df['NOMEPARC'].str.strip()
    df['RAZAOSOCIAL'] = df['RAZAOSOCIAL'].str.strip()
    df['AD_IDEXTERNO'] = df['AD_IDEXTERNO'].str.strip()
    
    # CORREÇÃO 4: Corrigir Razão Social para Pessoa Física
    for index, row in df.iterrows():
        if row['TIPPESSOA'] == 'F' and row['NOMEPARC'] and not row['RAZAOSOCIAL']:
            df.at[index, 'RAZAOSOCIAL'] = row['NOMEPARC']
    
    # CORREÇÃO 5: Limpar CEP se existir
    if 'CEP' in df.columns:
        df['CEP'] = df['CEP'].str.replace('-', '', regex=False).str.strip()
    
    # ----------------------------------------------------
    # 4. VALIDAÇÃO DE DUPLICIDADE
    # ----------------------------------------------------
    
    duplicados_bool = df.duplicated(subset=['CGC_CPF'], keep=False)
    nao_vazios_bool = df['CGC_CPF'] != ''
    df_duplicados = df[duplicados_bool & nao_vazios_bool]

    if not df_duplicados.empty:
        for index, row in df_duplicados.iterrows():
            erros_encontrados.append({
                "linha": index + 2,
                "coluna": "CGC_CPF",
                "valor_encontrado": str(row['CGC_CPF_original']),
                "valor_corrigido": "",
                "erro": "Este CNPJ/CPF está duplicado em outra(s) linha(s) da planilha.",
                "corrigido": False
            })

    # ----------------------------------------------------
    # 5. VALIDAÇÃO LINHA A LINHA
    # ----------------------------------------------------
    
    print(f"Iniciando validação de {len(df)} parceiros...")

    for index, row in df.iterrows():
        linha_num = index + 2 
        
        def adicionar_erro(coluna, valor_original, valor_corrigido, mensagem, foi_corrigido=False):
            erros_encontrados.append({
                "linha": linha_num,
                "coluna": coluna,
                "valor_encontrado": str(valor_original),
                "valor_corrigido": str(valor_corrigido) if foi_corrigido else "",
                "erro": mensagem,
                "corrigido": foi_corrigido
            })

        # Registrar correções aplicadas
        if row['CGC_CPF'] != row['CGC_CPF_original']:
            adicionar_erro('CGC_CPF', row['CGC_CPF_original'], row['CGC_CPF'], 
                          "Formatação corrigida (removidos pontos, traços e espaços).", True)
        
        if row['TIPPESSOA'] != row['TIPPESSOA_original']:
            adicionar_erro('TIPPESSOA', row['TIPPESSOA_original'], row['TIPPESSOA'], 
                          "Padronizado para maiúscula.", True)

        # [Obrigatório] AD_IDEXTERNO
        if not row['AD_IDEXTERNO']:
            adicionar_erro('AD_IDEXTERNO', row['AD_IDEXTERNO'], "", 
                          "Campo obrigatório está vazio.", False)
        
        # [Obrigatório] NOMEPARC
        if not row['NOMEPARC']:
            adicionar_erro('NOMEPARC', row['NOMEPARC'], "", 
                          "Campo obrigatório (Nome do Parceiro) está vazio.", False)
        
        # [Domínio] TIPPESSOA
        tipo_pessoa = row['TIPPESSOA']
        if not tipo_pessoa:
            adicionar_erro('TIPPESSOA', row['TIPPESSOA_original'], "", 
                          "Campo obrigatório (Tipo de Pessoa) está vazio.", False)
        elif tipo_pessoa not in ('F', 'J'):
            adicionar_erro('TIPPESSOA', row['TIPPESSOA_original'], "", 
                          "Valor inválido. Permitido apenas 'F' ou 'J'.", False)

        # --- VALIDAÇÃO CPF/CNPJ ---
        documento = row['CGC_CPF']
        
        if not documento:
            adicionar_erro('CGC_CPF', row['CGC_CPF_original'], "", 
                          "Campo obrigatório (CNPJ/CPF) está vazio.", False)
        
        elif tipo_pessoa == 'F':
            if len(documento) != 11:
                adicionar_erro('CGC_CPF', row['CGC_CPF_original'], "", 
                              f"Tipo Pessoa 'F', mas documento tem {len(documento)} dígitos (esperado 11).", False)
            elif not validar_cpf(documento):
                adicionar_erro('CGC_CPF', row['CGC_CPF_original'], "", 
                              "Tipo Pessoa 'F', mas o CPF é inválido (dígito verificador não confere).", False)
                    
        elif tipo_pessoa == 'J':
            if len(documento) != 14:
                adicionar_erro('CGC_CPF', row['CGC_CPF_original'], "", 
                              f"Tipo Pessoa 'J', mas documento tem {len(documento)} dígitos (esperado 14).", False)
            elif not validar_cnpj(documento):
                adicionar_erro('CGC_CPF', row['CGC_CPF_original'], "", 
                              "Tipo Pessoa 'J', mas o CNPJ é inválido (dígito verificador não confere).", False)

        # [Regra de Negócio] Razão Social vs Nome (para PF)
        if tipo_pessoa == 'F' and row['NOMEPARC'] and row['NOMEPARC'] != row['RAZAOSOCIAL']:
            # Se corrigimos automaticamente
            if row['RAZAOSOCIAL'] == row['NOMEPARC']:
                adicionar_erro('RAZAOSOCIAL', "", row['RAZAOSOCIAL'], 
                              "Para Pessoa Física, Razão Social foi igualada ao Nome do Parceiro.", True)
            else:
                adicionar_erro('RAZAOSOCIAL', row['RAZAOSOCIAL'], "", 
                              "Para Pessoa Física, a Razão Social deve ser IDÊNTICA ao Nome do Parceiro.", False)
             
    print(f"Validação concluída. Total de erros encontrados: {len(erros_encontrados)}")
    
    # Remover colunas auxiliares antes de retornar
    df_corrigido = df.drop(columns=['CGC_CPF_original', 'TIPPESSOA_original'], errors='ignore')
    
    # Retorna erros e DataFrame corrigido
    if erros_encontrados:
        df_erros = pd.DataFrame(erros_encontrados)
        return df_erros.drop_duplicates().to_dict('records'), df_corrigido
    
    return [], df_corrigido
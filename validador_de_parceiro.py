import pandas as pd
import re
import sys
import os
import csv
import unicodedata

# --- Funções Auxiliares ---
MAP_SIM_NAO = {'SIM': 'S', 'S': 'S', 'NÃO': 'N', 'NAO': 'N', 'N': 'N', 'YES': 'S', 'NO': 'N', '1': 'S', '0': 'N'}

def remover_acentos(texto):
    if not isinstance(texto, str): return str(texto)
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper().strip()

def ler_csv_robusto(caminho_arquivo):
    """Lê CSV tentando detectar separador e encoding."""
    if not os.path.exists(caminho_arquivo): return None, "Arquivo não encontrado no servidor."
    
    tentativas = [
        ('\t', 'latin-1'), ('\t', 'utf-16'), ('\t', 'utf-8'),
        (';', 'latin-1'), (',', 'latin-1'), 
        (';', 'utf-8'), (',', 'utf-8')
    ]
    
    for sep, enc in tentativas:
        try:
            df = pd.read_csv(caminho_arquivo, sep=sep, encoding=enc, dtype=str, on_bad_lines='skip')
            if len(df.columns) > 1:
                df.columns = df.columns.str.upper().str.strip()
                # Remove BOM dos headers se existir
                df.columns = df.columns.str.replace('ï»¿', '', regex=False)
                return df, "Sucesso"
        except: continue
    return None, "Falha na leitura."

# --- CARREGAMENTO MESTRE ---
MAP_CIDADE_CODIGO = {}
MAP_UF_CODIGO = {}
ERRO_MESTRE_MSG = ""

def carregar_dados_mestre():
    global MAP_CIDADE_CODIGO, MAP_UF_CODIGO, ERRO_MESTRE_MSG
    base_path = os.path.dirname(os.path.abspath(__file__)) 
    
    f_cid1 = "cidades1.csv"
    f_cid2 = "cidades2.csv"
    f_uf = "estados.csv"

    # 1. CIDADES
    df1, s1 = ler_csv_robusto(os.path.join(base_path, f_cid1))
    df2, s2 = ler_csv_robusto(os.path.join(base_path, f_cid2))
    
    dfs = []
    if df1 is not None: dfs.append(df1)
    if df2 is not None: dfs.append(df2)
    
    if dfs:
        df_full = pd.concat(dfs, ignore_index=True)
        col_nome = next((c for c in df_full.columns if c in ['NOMECID', 'CIDADE', 'NOME_CIDADE']), None)
        col_cod = next((c for c in df_full.columns if c in ['CODCID', 'CODIGO', 'COD_CIDADE']), None)
        
        if col_nome and col_cod:
            df_full['CHAVE'] = df_full[col_nome].apply(remover_acentos)
            MAP_CIDADE_CODIGO = df_full.set_index('CHAVE')[col_cod].to_dict()
        else:
            ERRO_MESTRE_MSG += f" [CIDADES: Colunas não encontradas. Lidas: {list(df_full.columns)}]"
    else:
        ERRO_MESTRE_MSG += f" [CIDADES: Falha leitura. Status: {s1}/{s2}]"

    # 2. UF
    df_uf, s_uf = ler_csv_robusto(os.path.join(base_path, f_uf))
    if df_uf is not None:
        col_uf = next((c for c in df_uf.columns if c in ['UF', 'SIGLA', 'ESTADO']), None)
        col_cod = next((c for c in df_uf.columns if c in ['CODREG', 'CODIGO', 'CODUF']), None)
        
        if col_uf and col_cod:
            df_uf['CHAVE'] = df_uf[col_uf].apply(remover_acentos)
            MAP_UF_CODIGO = df_uf.set_index('CHAVE')[col_cod].to_dict()
        else:
            ERRO_MESTRE_MSG += f" [UF: Colunas não encontradas. Lidas: {list(df_uf.columns)}]"
    else:
        ERRO_MESTRE_MSG += f" [UF: Falha leitura. Status: {s_uf}]"

carregar_dados_mestre()

# --- Mapeamento e Validação ---
def limpar_documento(doc_series):
    return doc_series.astype(str).str.replace(r'[./-]', '', regex=True).str.strip()
    
def limpar_valor_monetario(df, coluna):
    if coluna in df.columns:
        df[coluna] = df[coluna].astype(str).str.strip().str.upper().str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df[coluna] = pd.to_numeric(df[coluna], errors='coerce') 
    return df

MAPEAMENTO_COLUNAS = {
    'CGC_CPF': ['CGC_CPF', 'CNPJ_CPF', 'DOCUMENTO', 'DOC', 'CPF_CNPJ'],
    'AD_IDEXTERNO': ['AD_IDEXTERNO', 'COD_SIST_ANTERIOR', 'ID_LEGADO'],
    'RAZAOSOCIAL': ['RAZAOSOCIAL', 'RAZAO_SOCIAL'],
    'NOMEPARC': ['NOMEPARC', 'NOME_FANTASIA', 'NOME'],
    'TIPPESSOA': ['TIPPESSOA', 'TIPO_PESSOA', 'TIPO'],
    'ATIVO': ['ATIVO'], 'CLIENTE': ['CLIENTE'], 'FORNECEDOR': ['FORNECEDOR'],
    'CEP': ['CEP'], 'CIDADE': ['CIDADE', 'NOMECID'], 'UF': ['UF', 'ESTADO'],
    'CODCID': ['CODCID', 'COD_CIDADE'], 'CODREG': ['CODREG', 'COD_REGIAO']
}

def mapear_colunas(df, mapeamento):
    colunas_encontradas = {}
    df.columns = df.columns.astype(str).str.replace('ï»¿', '', regex=False).str.replace(r'[^A-Z0-9_]', '', regex=True).str.upper().str.strip()
    for nome_oficial, alternativas in mapeamento.items():
        for alt in alternativas:
            alt_limpa = alt.upper().replace(' ', '_')
            if alt_limpa in df.columns: colunas_encontradas[alt_limpa] = nome_oficial; break 
    df.rename(columns=colunas_encontradas, inplace=True)
    return df

# Validadores CPF/CNPJ
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

# --- PRINCIPAL ---
def validar_parceiros(caminho_arquivo):
    if not MAP_CIDADE_CODIGO or not MAP_UF_CODIGO:
        return [{"linha": 0, "coluna": "SISTEMA", "valor_encontrado": "-", "erro": f"ERRO CRÍTICO CARREGAMENTO MESTRE: {ERRO_MESTRE_MSG}"}], None

    erros_encontrados = []
    
    # 1. Leitura
    df, msg_erro = ler_csv_robusto(caminho_arquivo)
    if df is None:
        return [{"linha": 0, "coluna": "Arquivo", "valor_encontrado": "N/A", "erro": f"Erro crítico de leitura. {msg_erro}"}], None
    df = df.fillna('')

    # 2. Pré-processamento
    df = mapear_colunas(df, MAPEAMENTO_COLUNAS)
    colunas_criticas = ['CGC_CPF', 'TIPPESSOA', 'AD_IDEXTERNO', 'NOMEPARC', 'RAZAOSOCIAL', 'ATIVO', 'CLIENTE', 'FORNECEDOR']
    for col in colunas_criticas:
        if col not in df.columns: return [{"linha": 0, "coluna": col, "valor_encontrado": "-", "erro": f"Coluna obrigatória '{col}' não encontrada."}], None

    tem_cep = 'CEP' in df.columns
    
    # --- LÓGICA DE CONVERSÃO (LOOKUP) ---
    if 'CIDADE' in df.columns:
        df['CIDADE_BUSCA'] = df['CIDADE'].apply(remover_acentos)
        # Busca o código no mapa
        df['CODCID_ENCONTRADO'] = df['CIDADE_BUSCA'].apply(lambda x: MAP_CIDADE_CODIGO.get(x, None))
    else: df['CODCID_ENCONTRADO'] = None

    if 'UF' in df.columns:
        df['UF_BUSCA'] = df['UF'].apply(remover_acentos)
        df['CODREG_ENCONTRADO'] = df['UF_BUSCA'].apply(lambda x: MAP_UF_CODIGO.get(x, None))
    else: df['CODREG_ENCONTRADO'] = None

    # Limpezas
    df['CGC_CPF_original'] = df['CGC_CPF'].copy()
    df['CGC_CPF'] = limpar_documento(df['CGC_CPF'])
    df['TIPPESSOA_limpo'] = df['TIPPESSOA'].astype(str).str.upper().str.strip()
    
    for col in ['ATIVO', 'CLIENTE', 'FORNECEDOR']:
        df[f'{col}_original'] = df[col].copy()
        df[col] = df[col].astype(str).str.upper().str.strip().replace(MAP_SIM_NAO, regex=False)
    
    if tem_cep: df['CEP_limpo'] = df['CEP'].astype(str).str.replace(r'[^0-9]', '', regex=True).str.strip()
    
    df = limpar_valor_monetario(df, 'LIMITECREDITO')

    # 3. Validação
    for index, row in df.iterrows():
        linha_num = index + 2 
        def adicionar_erro(coluna, valor, mensagem, valor_corrigido="", foi_corrigido=False):
            erros_encontrados.append({"linha": linha_num, "coluna": coluna, "valor_encontrado": str(valor), "erro": mensagem, "valor_corrigido": str(valor_corrigido), "corrigido": foi_corrigido})

        # Validação e Substituição Mestre
        if 'CIDADE' in df.columns:
            cod_encontrado = row['CODCID_ENCONTRADO']
            if cod_encontrado: 
                # SUCESSO: Encontrou o código. Substitui na validação futura e registra correção opcional
                pass
            elif row['CIDADE'] and str(row['CIDADE']).strip():
                adicionar_erro('CIDADE', row['CIDADE'], "Cidade não encontrada no mestre.", "", False)
        
        if 'UF' in df.columns:
            cod_encontrado = row['CODREG_ENCONTRADO']
            if cod_encontrado:
                pass
            elif row['UF'] and str(row['UF']).strip():
                 adicionar_erro('UF', row['UF'], "UF não encontrada no mestre.", "", False)

        # Correções
        if row['CGC_CPF'] != row['CGC_CPF_original']:
             adicionar_erro('CGC_CPF', row['CGC_CPF_original'], "Formatado.", row['CGC_CPF'], True)
        for col_dom in ['ATIVO', 'CLIENTE', 'FORNECEDOR']:
            if row[col_dom] != row[f'{col_dom}_original']:
                 adicionar_erro(col_dom, row[f'{col_dom}_original'], f"Padronizado {row[col_dom]}.", row[col_dom], True)

        # Validações Básicas
        if not row['AD_IDEXTERNO']: adicionar_erro('AD_IDEXTERNO', '', "Vazio.", "", False)
        if not row['NOMEPARC']: adicionar_erro('NOMEPARC', '', "Vazio.", "", False)
        tipo = row['TIPPESSOA_limpo']
        if not tipo: adicionar_erro('TIPPESSOA', '', "Vazio.", "", False)
        elif tipo not in ('F', 'J'): adicionar_erro('TIPPESSOA', row['TIPPESSOA'], "Inválido.", "", False)
        
        for c in ['ATIVO', 'CLIENTE', 'FORNECEDOR']:
            if row[c] not in ('S', 'N'): adicionar_erro(c, row[f'{c}_original'], "Inválido (S/N).", "", False)
        
        doc = row['CGC_CPF']
        if not doc: adicionar_erro('CGC_CPF', '', "Vazio.", "", False)
        elif tipo == 'F':
            if len(doc) != 11: adicionar_erro('CGC_CPF', row['CGC_CPF_original'], f"CPF tam. errado ({len(doc)}).", "", False)
            elif not validar_cpf(doc): adicionar_erro('CGC_CPF', row['CGC_CPF_original'], "CPF Inválido.", "", False)
        elif tipo == 'J':
            if len(doc) != 14: adicionar_erro('CGC_CPF', row['CGC_CPF_original'], f"CNPJ tam. errado ({len(doc)}).", "", False)
            elif not validar_cnpj(doc): adicionar_erro('CGC_CPF', row['CGC_CPF_original'], "CNPJ Inválido.", "", False)

        if tem_cep:
            if not row['CEP_limpo']: adicionar_erro('CEP', row['CEP'], "Vazio.", "", False)
            elif len(row['CEP_limpo']) != 8: adicionar_erro('CEP', row['CEP'], "CEP inválido.", "", False)

    # 4. SUBSTITUIÇÃO FINAL DE VALORES (O que vai para o Excel)
    # Aqui substituímos o NOME da cidade pelo CÓDIGO encontrado
    if 'CIDADE' in df.columns and 'CODCID_ENCONTRADO' in df.columns:
        # Onde achou código, substitui. Onde não achou, mantém o original (para o usuário ver o erro)
        df['CIDADE'] = df['CODCID_ENCONTRADO'].fillna(df['CIDADE'])
        # Se quiser criar a coluna CODCID separada também:
        df['CODCID'] = df['CODCID_ENCONTRADO']

    if 'UF' in df.columns and 'CODREG_ENCONTRADO' in df.columns:
        df['UF'] = df['CODREG_ENCONTRADO'].fillna(df['UF'])
        df['CODREG'] = df['CODREG_ENCONTRADO']

    # Remove colunas auxiliares
    cols_to_drop = [c for c in df.columns if '_original' in c or '_BUSCA' in c or '_ENCONTRADO' in c or '_limpo' in c]
    df_final = df.drop(columns=cols_to_drop, errors='ignore')

    if erros_encontrados:
        return pd.DataFrame(erros_encontrados).drop_duplicates().to_dict('records'), df_final
    return [], df_final
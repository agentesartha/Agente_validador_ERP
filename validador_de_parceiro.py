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
    """Lê CSV tentando detectar separador, inclusive TAB mascarado."""
    if not os.path.exists(caminho_arquivo): return None, "Arquivo não encontrado"
    
    # Lista de tentativas ordenada por probabilidade para seus arquivos
    tentativas = [
        ('\t', 'latin-1'), # Tabulação (Excel comum)
        ('\t', 'utf-16'),  # Tabulação (Excel Unicode)
        (';', 'latin-1'), 
        (',', 'latin-1'), 
        (';', 'utf-8'), 
        (',', 'utf-8')
    ]
    
    for sep, enc in tentativas:
        try:
            # Lê o arquivo
            df = pd.read_csv(caminho_arquivo, sep=sep, encoding=enc, dtype=str, on_bad_lines='skip')
            
            # SE leu apenas 1 coluna, verifica se não é um TAB escondido
            if len(df.columns) == 1:
                col_name = str(df.columns[0])
                if '\t' in col_name:
                    # Opa! Tem tabulação no nome da coluna. Vamos forçar a leitura com \t
                    df = pd.read_csv(caminho_arquivo, sep='\t', encoding=enc, dtype=str, on_bad_lines='skip')
                elif ';' in col_name and sep != ';':
                    # Opa! Tem ponto e vírgula. Força ;
                    df = pd.read_csv(caminho_arquivo, sep=';', encoding=enc, dtype=str, on_bad_lines='skip')
            
            # Se agora temos mais de 1 coluna, consideramos sucesso
            if len(df.columns) > 1:
                df.columns = df.columns.str.upper().str.strip()
                return df, "Sucesso"
                
        except: continue
        
    # Última tentativa: Engine Python automático (Sniffer)
    try:
        df = pd.read_csv(caminho_arquivo, sep=None, encoding='latin-1', dtype=str, engine='python', on_bad_lines='skip')
        if len(df.columns) > 1:
            df.columns = df.columns.str.upper().str.strip()
            return df, "Sucesso (Sniffer)"
    except: pass

    return None, "Falha na leitura (separador ou encoding desconhecido)"

# --- CARREGAMENTO MESTRE ---
MAP_CIDADE_CODIGO = {}
MAP_UF_CODIGO = {}
ERRO_MESTRE_MSG = ""

def carregar_dados_mestre():
    global MAP_CIDADE_CODIGO, MAP_UF_CODIGO, ERRO_MESTRE_MSG
    base_path = os.path.dirname(os.path.abspath(__file__)) 
    
    f_cid1 = "CIDADE DE 0 A 4999.xls - new sheet.csv"
    f_cid2 = "CIDADE DE 5000 A 5572.xls - new sheet.csv"
    f_uf = "UF ESTADOS.xls - new sheet.csv"

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
            ERRO_MESTRE_MSG += f" [CIDADES: Colunas NOMECID/CODCID não encontradas. Lidas: {list(df_full.columns)}]"
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
            ERRO_MESTRE_MSG += f" [UF: Colunas UF/CODREG não encontradas. Lidas: {list(df_uf.columns)}]"
    else:
        ERRO_MESTRE_MSG += f" [UF: Falha leitura. Status: {s_uf}]"

carregar_dados_mestre()

# --- Validação e Mapeamento ---
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
    'CEP': ['CEP'], 'CIDADE': ['CIDADE', 'NOMECID'], 'UF': ['UF', 'ESTADO']
}

def mapear_colunas(df, mapeamento):
    colunas_encontradas = {}
    df.columns = df.columns.astype(str).str.replace(r'[^A-Z0-9_]', '', regex=True).str.upper().str.strip()
    for nome_oficial, alternativas in mapeamento.items():
        for alt in alternativas:
            alt_limpa = alt.upper().replace(' ', '_')
            if alt_limpa in df.columns: colunas_encontradas[alt_limpa] = nome_oficial; break 
    df.rename(columns=colunas_encontradas, inplace=True)
    return df

# [Validadores CPF/CNPJ omitidos por brevidade, mantidos iguais]
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
    if not MAP_CIDADE_CODIGO or not MAP_UF_CODIGO:
        return [{"linha": 0, "coluna": "SISTEMA", "valor_encontrado": "-", "erro": f"ERRO CRÍTICO CARREGAMENTO MESTRE: {ERRO_MESTRE_MSG}"}], None

    erros_encontrados = []
    
    # 1. Leitura do Arquivo de Parceiros (Usando a mesma função robusta)
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
    
    # Lookup Cidade/UF
    if 'CIDADE' in df.columns:
        df['CIDADE_BUSCA'] = df['CIDADE'].apply(remover_acentos)
        df['CODCID'] = df['CIDADE_BUSCA'].apply(lambda x: MAP_CIDADE_CODIGO.get(x, None))
    else: df['CODCID'] = None

    if 'UF' in df.columns:
        df['UF_BUSCA'] = df['UF'].apply(remover_acentos)
        df['CODREG'] = df['UF_BUSCA'].apply(lambda x: MAP_UF_CODIGO.get(x, None))
    else: df['CODREG'] = None

    df['CGC_CPF_original'] = df['CGC_CPF'].copy()
    df['CGC_CPF'] = limpar_documento(df['CGC_CPF'])
    df['TIPPESSOA_limpo'] = df['TIPPESSOA'].astype(str).str.upper().str.strip()
    
    for col in ['ATIVO', 'CLIENTE', 'FORNECEDOR']:
        df[f'{col}_original'] = df[col].copy()
        df[col] = df[col].astype(str).str.upper().str.strip().replace(MAP_SIM_NAO, regex=False)
    
    if tem_cep: df['CEP_limpo'] = df['CEP'].astype(str).str.replace(r'[^0-9]', '', regex=True).str.strip()
    
    # 3. Validação
    for index, row in df.iterrows():
        linha_num = index + 2 
        def adicionar_erro(coluna, valor, mensagem, valor_corrigido="", foi_corrigido=False):
            erros_encontrados.append({"linha": linha_num, "coluna": coluna, "valor_encontrado": str(valor), "erro": mensagem, "valor_corrigido": str(valor_corrigido), "corrigido": foi_corrigido})

        # Mapeamento
        if 'CIDADE' in df.columns:
            if row['CODCID']: pass
            elif row['CIDADE'] and str(row['CIDADE']).strip():
                adicionar_erro('CIDADE', row['CIDADE'], "Cidade não encontrada no mestre.", "", False)
        if 'UF' in df.columns:
            if row['CODREG']: pass
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

    if erros_encontrados:
        return pd.DataFrame(erros_encontrados).drop_duplicates().to_dict('records'), df
    return [], df
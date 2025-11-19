import pandas as pd
import re
import sys

# --- Domínios e Mapeamentos ---
MAP_SIM_NAO = {'SIM': 'S', 'S': 'S', 'NÃO': 'N', 'NAO': 'N', 'N': 'N', 'YES': 'S', 'NO': 'N', '1': 'S', '0': 'N'}
DOMINIO_UNIDADE = {'CM', 'M', 'MM', 'KG', 'G', 'L', 'ML', 'UN', 'PC', 'CX', 'FD', 'MT', 'M2', 'M3'}
DOMINIO_USOPROD = {'1', '2', '4', 'B', 'C', 'D', 'E', 'F', 'I', 'M', 'O', 'P', 'R', 'T', 'V'}
DOMINIO_SIM_NAO = {'S', 'N'}

# Mapeamento de unidades comuns
MAP_UNIDADES = {
    'METRO': 'M', 'METROS': 'M', 'MTS': 'M', 'MT': 'M',
    'CENTIMETRO': 'CM', 'CENTIMETROS': 'CM', 'CENT': 'CM',
    'MILIMETRO': 'MM', 'MILIMETROS': 'MM',
    'QUILO': 'KG', 'QUILOGRAMA': 'KG', 'KILO': 'KG', 'KILOGRAMA': 'KG',
    'GRAMA': 'G', 'GRAMAS': 'G', 'GR': 'G',
    'LITRO': 'L', 'LITROS': 'L', 'LT': 'L',
    'MILILITRO': 'ML', 'MILILITROS': 'ML',
    'UNIDADE': 'UN', 'UNIDADES': 'UN', 'UND': 'UN',
    'PEÇA': 'PC', 'PECAS': 'PC', 'PECA': 'PC', 'PÇ': 'PC',
    'CAIXA': 'CX', 'CAIXAS': 'CX',
    'FARDO': 'FD', 'FARDOS': 'FD'
}

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

# --- Mapeamento de Colunas ---
MAPEAMENTO_COLUNAS = {
    'UNIDADE': ['UNIDADE', 'UND', 'UNID_MEDIDA', 'CODVOL', 'UN'], 
}

def mapear_colunas(df, mapeamento):
    """Renomeia colunas do DF para os nomes oficiais do script."""
    colunas_encontradas = {}
    for nome_oficial, alternativas in mapeamento.items():
        for alt in alternativas:
            if alt in df.columns: 
                colunas_encontradas[alt] = nome_oficial
                break 
    df.rename(columns=colunas_encontradas, inplace=True)
    return df

# --- Função Principal de Validação ---

def validar_produtos(caminho_arquivo):
    erros_encontrados = []
    
    # ----------------------------------------------------
    # 1. CARREGAR OS DADOS (Leitura Robusta)
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
    # 2. PRÉ-PROCESSAMENTO E CORREÇÕES
    # ----------------------------------------------------
    
    # 2.1 Limpeza de Cabeçalhos (Para evitar KeyErrors por espaço/caixa)
    df.columns = df.columns.str.upper().str.strip() 

    df = mapear_colunas(df, MAPEAMENTO_COLUNAS)
    
    colunas_criticas = ['AD_IDEXTERNO', 'DESCRPROD', 'NCM', 'MARCA', 'REFERENCIA', 'UNIDADE']
    for col in colunas_criticas:
        if col not in df.columns:
            alternativas = ', '.join(MAPEAMENTO_COLUNAS.get(col, [col]))
            return [{"linha": 0, "coluna": col, "valor_encontrado": "-", 
                     "erro": f"Coluna obrigatória '{col}' não encontrada. (Alternativas: {alternativas})."}], None
    
    # Backup de colunas originais
    colunas_para_backup = ['NCM', 'UNIDADE', 'PRECO_VENDA', 'PRECO_CUSTO', 'USOPROD']
    colunas_sim_nao = ['TEMIPICOMPRA', 'TEMIPIVENDA', 'USACODBARRASQTD', 'ATIVO']
    for col in colunas_para_backup + colunas_sim_nao:
        if col in df.columns: df[f'{col}_original'] = df[col].copy()
    
    # CORREÇÃO 1: Limpar NCM (Solução anti-RegEx)
    df['NCM'] = df['NCM'].astype(str).str.replace('.', '', regex=False)\
                         .str.replace('/', '', regex=False)\
                         .str.replace('-', '', regex=False)\
                         .str.replace(' ', '', regex=False)\
                         .str.strip()
    
    # CORREÇÃO 2: Padronizar UNIDADE e tratar por extenso
    df['UNIDADE'] = df['UNIDADE'].str.upper().str.strip()
    df['UNIDADE'] = df['UNIDADE'].replace(MAP_UNIDADES, regex=False)
    
    # CORREÇÃO 3: Limpar valores monetários
    df = limpar_valor_monetario(df, 'PRECO_VENDA')
    df = limpar_valor_monetario(df, 'PRECO_CUSTO')
    
    # CORREÇÃO 4: Padronizar campos Sim/Não
    for col in colunas_sim_nao:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()
            df[col] = df[col].replace(MAP_SIM_NAO, regex=False)
            
    # CORREÇÃO 5: Padronizar USOPROD
    if 'USOPROD' in df.columns:
        df['USOPROD'] = df['USOPROD'].str.upper().str.strip()

    # ----------------------------------------------------
    # 3. VALIDAÇÃO LINHA A LINHA
    # ----------------------------------------------------
    
    # [Omissão do loop de validação por brevidade]
    
    # Retorna erros e DataFrame corrigido
    # ... (lógica de retorno) ...
    
    # Retorna erros e DataFrame corrigido
    if erros_encontrados:
        df_erros = pd.DataFrame(erros_encontrados)
        return df_erros.drop_duplicates().to_dict('records'), df
    
    return [], df
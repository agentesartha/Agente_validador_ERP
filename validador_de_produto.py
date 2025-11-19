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
        df[coluna] = df[coluna].str.replace('.', '', regex=False)
        df[coluna] = df[coluna].str.replace(',', '.', regex=False)
        df[coluna] = pd.to_numeric(df[coluna], errors='coerce') 
    return df

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
    
    # 2.1 Limpeza de Cabeçalhos
    df.columns = df.columns.str.upper().str.strip() 

    # 2.2 Mapeamento de Colunas (Unidades)
    df = mapear_colunas(df, {'UNIDADE': ['UNIDADE', 'UND', 'UNID_MEDIDA', 'CODVOL', 'UN']})
    
    colunas_criticas = ['AD_IDEXTERNO', 'DESCRPROD', 'NCM', 'MARCA', 'REFERENCIA', 'UNIDADE']
    for col in colunas_criticas:
        if col not in df.columns:
            return [{"linha": 0, "coluna": col, "valor_encontrado": "-", "erro": f"Coluna obrigatória '{col}' não encontrada."}], None
    
    # Backup de colunas originais
    colunas_para_backup = ['NCM', 'UNIDADE', 'PRECO_VENDA', 'PRECO_CUSTO', 'USOPROD']
    colunas_sim_nao = ['TEMIPICOMPRA', 'TEMIPIVENDA', 'USACODBARRASQTD', 'ATIVO']
    for col in colunas_para_backup + colunas_sim_nao:
        if col in df.columns: df[f'{col}_original'] = df[col].copy()

    # 2.3 CORREÇÕES AUTOMÁTICAS
    
    # Limpeza NCM (Solução anti-RegEx)
    df['NCM'] = df['NCM'].astype(str).str.replace('.', '', regex=False).str.replace('/', '', regex=False).str.replace('-', '', regex=False).str.replace(' ', '', regex=False).str.strip()
    
    # Padronizar UNIDADE e tratar por extenso
    df['UNIDADE'] = df['UNIDADE'].str.upper().str.strip().replace(MAP_UNIDADES, regex=False)
    
    # Limpar valores monetários
    df = limpar_valor_monetario(df, 'PRECO_VENDA')
    df = limpar_valor_monetario(df, 'PRECO_CUSTO')
    
    # Padronizar campos Sim/Não (Resolve o erro do 'sim' e 'não')
    for col in colunas_sim_nao:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip().replace(MAP_SIM_NAO, regex=False)
    
    # Padronizar USOPROD
    if 'USOPROD' in df.columns:
        df['USOPROD'] = df['USOPROD'].str.upper().str.strip()

    # ----------------------------------------------------
    # 3. VALIDAÇÃO LINHA A LINHA
    # ----------------------------------------------------
    
    print(f"Iniciando validação de {len(df)} produtos...")

    for index, row in df.iterrows():
        linha_num = index + 2
        
        def adicionar_erro(coluna, valor_original, valor_corrigido, mensagem, foi_corrigido=False):
            erros_encontrados.append({
                "linha": linha_num, "coluna": coluna, "valor_encontrado": str(valor_original), 
                "valor_corrigido": str(valor_corrigido) if foi_corrigido else "", "erro": mensagem, 
                "corrigido": foi_corrigido
            })
        
        # --- Lógica de Correção de Domínio (Registra se S/N mudou) ---
        for col in colunas_sim_nao:
            if col in row and row[f'{col}_original'] != row[col]:
                adicionar_erro(col, row[f'{col}_original'], row[col], "Valor padronizado para 'S' ou 'N'.", True)

        # Validações obrigatórias
        if not row['AD_IDEXTERNO']: adicionar_erro('AD_IDEXTERNO', row['AD_IDEXTERNO'], "", "Campo obrigatório está vazio.", False)
        if not row['DESCRPROD']: adicionar_erro('DESCRPROD', row['DESCRPROD'], "", "Campo obrigatório (Descrição do Produto) está vazio.", False)
        
        # [Validações de Domínio/Tamanho omitidas por brevidade]

    # Retorna erros e DataFrame corrigido
    if erros_encontrados:
        df_erros = pd.DataFrame(erros_encontrados)
        return df_erros.drop_duplicates().to_dict('records'), df
    
    return [], df
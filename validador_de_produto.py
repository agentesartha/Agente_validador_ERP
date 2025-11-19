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

def limpar_valor_monetario(valor):
    """Remove R$, pontos de milhar e substitui vírgula por ponto decimal."""
    if pd.isna(valor) or valor == '':
        return ''
    valor = str(valor).strip().upper()
    valor = valor.replace('R$', '').replace('$', '')
    valor = valor.replace('.', '').replace(',', '.')
    return valor

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
    """
    Valida e corrige planilha de produtos.
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
    # 2. MAPEAR E VERIFICAR COLUNAS
    # ----------------------------------------------------
    
    df = mapear_colunas(df, MAPEAMENTO_COLUNAS)
    
    colunas_criticas = ['AD_IDEXTERNO', 'DESCRPROD', 'NCM', 'MARCA', 'REFERENCIA', 'UNIDADE']
    for col in colunas_criticas:
        if col not in df.columns:
            alternativas = ', '.join(MAPEAMENTO_COLUNAS.get(col, [col]))
            return [{"linha": 0, "coluna": col, "valor_encontrado": "-", 
                    "erro": f"Coluna obrigatória '{col}' não encontrada. (Alternativas: {alternativas})."}], None
    
    # ----------------------------------------------------
    # 3. APLICAR CORREÇÕES AUTOMÁTICAS
    # ----------------------------------------------------
    
    # Backup de colunas originais
    colunas_para_backup = ['NCM', 'UNIDADE']
    if 'PRECO_VENDA' in df.columns:
        colunas_para_backup.append('PRECO_VENDA')
    if 'PRECO_CUSTO' in df.columns:
        colunas_para_backup.append('PRECO_CUSTO')
    
    # Colunas Sim/Não
    colunas_sim_nao = ['TEMIPICOMPRA', 'TEMIPIVENDA', 'USACODBARRASQTD', 'ATIVO']
    for col in colunas_sim_nao:
        if col in df.columns:
            colunas_para_backup.append(col)
    
    for col in colunas_para_backup:
        if col in df.columns:
            df[f'{col}_original'] = df[col].copy()
    
    # CORREÇÃO 1: Limpar NCM (remover pontos, traços)
    df['NCM'] = df['NCM'].astype(str).str.replace(r'[./-\s]', '', regex=True).str.strip()
    
    # CORREÇÃO 2: Padronizar UNIDADE
    df['UNIDADE'] = df['UNIDADE'].str.upper().str.strip()
    # Tentar mapear unidades por extenso
    df['UNIDADE'] = df['UNIDADE'].replace(MAP_UNIDADES, regex=False)
    
    # CORREÇÃO 3: Limpar valores monetários
    if 'PRECO_VENDA' in df.columns:
        df['PRECO_VENDA'] = df['PRECO_VENDA'].apply(limpar_valor_monetario)
    if 'PRECO_CUSTO' in df.columns:
        df['PRECO_CUSTO'] = df['PRECO_CUSTO'].apply(limpar_valor_monetario)
    
    # CORREÇÃO 4: Padronizar campos Sim/Não
    for col in colunas_sim_nao:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()
            df[col] = df[col].replace(MAP_SIM_NAO, regex=False)
    
    # CORREÇÃO 5: Limpar espaços extras em campos de texto
    df['DESCRPROD'] = df['DESCRPROD'].str.strip()
    df['MARCA'] = df['MARCA'].str.strip()
    df['REFERENCIA'] = df['REFERENCIA'].str.strip()
    df['AD_IDEXTERNO'] = df['AD_IDEXTERNO'].str.strip()
    
    # CORREÇÃO 6: Padronizar USOPROD se existir
    if 'USOPROD' in df.columns:
        df['USOPROD_original'] = df['USOPROD'].copy()
        df['USOPROD'] = df['USOPROD'].str.upper().str.strip()
    
    # ----------------------------------------------------
    # 4. VALIDAÇÃO LINHA A LINHA
    # ----------------------------------------------------
    
    print(f"Iniciando validação de {len(df)} produtos...")

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
        if 'NCM_original' in row and row['NCM'] != row['NCM_original']:
            adicionar_erro('NCM', row['NCM_original'], row['NCM'], 
                          "Formatação corrigida (removidos pontos e traços).", True)
        
        if 'UNIDADE_original' in row and row['UNIDADE'] != row['UNIDADE_original']:
            adicionar_erro('UNIDADE', row['UNIDADE_original'], row['UNIDADE'], 
                          "Unidade padronizada.", True)
        
        # Valores monetários
        if 'PRECO_VENDA_original' in row and row['PRECO_VENDA'] != row['PRECO_VENDA_original']:
            adicionar_erro('PRECO_VENDA', row['PRECO_VENDA_original'], row['PRECO_VENDA'], 
                          "Formato monetário corrigido.", True)
        
        if 'PRECO_CUSTO_original' in row and row['PRECO_CUSTO'] != row['PRECO_CUSTO_original']:
            adicionar_erro('PRECO_CUSTO', row['PRECO_CUSTO_original'], row['PRECO_CUSTO'], 
                          "Formato monetário corrigido.", True)
        
        # Campos Sim/Não
        for col in colunas_sim_nao:
            col_orig = f'{col}_original'
            if col_orig in row and col in row and row[col] != row[col_orig]:
                adicionar_erro(col, row[col_orig], row[col], 
                              "Padronizado para 'S' ou 'N'.", True)
        
        # Validações obrigatórias
        if not row['AD_IDEXTERNO']:
            adicionar_erro('AD_IDEXTERNO', row['AD_IDEXTERNO'], "", 
                          "Campo obrigatório está vazio.", False)
        
        if not row['DESCRPROD']:
            adicionar_erro('DESCRPROD', row['DESCRPROD'], "", 
                          "Campo obrigatório (Descrição do Produto) está vazio.", False)
        
        # Validação NCM (deve ter 8 dígitos)
        ncm = row['NCM']
        if not ncm:
            adicionar_erro('NCM', row.get('NCM_original', ''), "", 
                          "Campo obrigatório (NCM) está vazio.", False)
        elif not ncm.isdigit():
            adicionar_erro('NCM', row.get('NCM_original', ncm), "", 
                          "NCM deve conter apenas números.", False)
        elif len(ncm) != 8:
            adicionar_erro('NCM', row.get('NCM_original', ncm), "", 
                          f"NCM deve ter 8 dígitos (encontrado: {len(ncm)}).", False)
        
        # Validação UNIDADE
        unidade = row['UNIDADE']
        if not unidade:
            adicionar_erro('UNIDADE', row.get('UNIDADE_original', ''), "", 
                          "Campo obrigatório (Unidade) está vazio.", False)
        elif unidade not in DOMINIO_UNIDADE:
            adicionar_erro('UNIDADE', row.get('UNIDADE_original', unidade), "", 
                          f"Unidade inválida. Permitidas: {', '.join(sorted(DOMINIO_UNIDADE))}", False)
        
        # Validação USOPROD se existir
        if 'USOPROD' in row:
            usoprod = row['USOPROD']
            if usoprod and usoprod not in DOMINIO_USOPROD:
                adicionar_erro('USOPROD', row.get('USOPROD_original', usoprod), "", 
                              f"Código de uso inválido. Permitidos: {', '.join(sorted(DOMINIO_USOPROD))}", False)
        
        # Validação campos Sim/Não
        for col in colunas_sim_nao:
            if col in row and row[col] and row[col] not in DOMINIO_SIM_NAO:
                adicionar_erro(col, row.get(f'{col}_original', row[col]), "", 
                              "Valor inválido. Esperado 'S' ou 'N'.", False)
    
    print(f"Validação concluída. Total de erros encontrados: {len(erros_encontrados)}")
    
    # Remover colunas auxiliares
    colunas_remover = [col for col in df.columns if col.endswith('_original')]
    df_corrigido = df.drop(columns=colunas_remover, errors='ignore')
    
    # Retorna erros e DataFrame corrigido
    if erros_encontrados:
        df_erros = pd.DataFrame(erros_encontrados)
        return df_erros.drop_duplicates().to_dict('records'), df_corrigido
    
    return [], df_corrigido
import pandas as pd
import re
import sys
from datetime import datetime

# --- Domínios ---
DOMINIO_TIPO_ESTOQUE = {'P', 'T'}
DOMINIO_ATIVO = {'S', 'N'}

# Mapeamentos
MAP_TIPO_ESTOQUE = {
    'PROPRIO': 'P', 'PRÓPRIO': 'P', 'P': 'P',
    'TERCEIRO': 'T', 'TERCEIROS': 'T', 'T': 'T'
}

MAP_ATIVO = {
    'SIM': 'S', 'S': 'S', 'ATIVO': 'S', 'YES': 'S', '1': 'S',
    'NÃO': 'N', 'NAO': 'N', 'N': 'N', 'INATIVO': 'N', 'NO': 'N', '0': 'N'
}

def carregar_mestre(caminho_arquivo, nome_coluna):
    """Carrega um arquivo mestre e retorna um SET com os valores válidos."""
    try:
        df_mestre = pd.read_csv(caminho_arquivo, sep=';', encoding='utf-8', encoding_errors='ignore', dtype=str, engine='python')
        if len(df_mestre.columns) < 2: 
            df_mestre = pd.read_csv(caminho_arquivo, sep=',', encoding='utf-8', encoding_errors='ignore', dtype=str, engine='python')
    except Exception:
        return None 
    if nome_coluna not in df_mestre.columns: 
        return None
    return set(df_mestre[nome_coluna].dropna().unique())

# --- Função Principal de Validação ---

def validar_estoque(caminho_arquivo):
    """
    Valida e corrige planilha de estoque.
    Retorna: (lista_erros, dataframe_corrigido)
    """
    erros_encontrados = []
    
    # 1. CARREGAR ARQUIVO MESTRE DE PRODUTOS
    produtos_validos = carregar_mestre("mestre_produtos.csv", 'CODPROD')
    if produtos_validos is None:
        return [{"linha": 0, "coluna": "Mestre", "valor_encontrado": "mestre_produtos.csv", 
                "erro": "Arquivo Mestre de Produtos não encontrado ou incompleto (Verifique o cabeçalho 'CODPROD')."}], None

    # 2. CARREGAR OS DADOS DE ESTOQUE
    df = None
    try:
        df_temp = pd.read_csv(caminho_arquivo, sep=';', encoding='utf-8', encoding_errors='ignore', dtype=str, engine='python')
        if len(df_temp.columns) < 2: 
            df = pd.read_csv(caminho_arquivo, sep=',', encoding='utf-8', encoding_errors='ignore', dtype=str, engine='python')
        else: 
            df = df_temp
    except Exception as e:
        return [{"linha": 0, "coluna": "Arquivo", "valor_encontrado": "N/A", 
                "erro": f"ERRO FATAL DE DADOS. O arquivo pode estar corrompido. Detalhe: {str(e)}"}], None
    
    if df is None:
        return [{"linha": 0, "coluna": "Arquivo", "valor_encontrado": "N/A", 
                "erro": "ERRO FATAL DE LEITURA. Não foi possível ler o arquivo com vírgula ou ponto e vírgula."}], None
    
    df = df.fillna('')

    # 3. VERIFICAR COLUNAS CRÍTICAS
    colunas_criticas = ['CODPROD', 'ESTOQUE', 'ESTMAX', 'ESTMIN', 'ATIVO', 'TIPO']
    for col in colunas_criticas:
        if col not in df.columns:
            return [{"linha": 0, "coluna": col, "valor_encontrado": "-", 
                    "erro": f"Coluna obrigatória '{col}' não encontrada no cabeçalho do arquivo de estoque."}], None
    
    # 4. APLICAR CORREÇÕES AUTOMÁTICAS
    
    # Backup das colunas originais
    df['TIPO_original'] = df['TIPO'].copy()
    df['ATIVO_original'] = df['ATIVO'].copy()
    df['CODPROD_original'] = df['CODPROD'].copy()
    
    # CORREÇÃO 1: Padronizar TIPO
    df['TIPO'] = df['TIPO'].astype(str).str.upper().str.strip()
    df['TIPO'] = df['TIPO'].replace(MAP_TIPO_ESTOQUE, regex=False)
    
    # CORREÇÃO 2: Padronizar ATIVO
    df['ATIVO'] = df['ATIVO'].astype(str).str.upper().str.strip()
    df['ATIVO'] = df['ATIVO'].replace(MAP_ATIVO, regex=False)
    
    # CORREÇÃO 3: Limpar CODPROD (remover espaços)
    df['CODPROD'] = df['CODPROD'].astype(str).str.strip()
    
    # CORREÇÃO 4: Limpar valores numéricos (estoque, min, max)
    for col in ['ESTOQUE', 'ESTMIN', 'ESTMAX']:
        if col in df.columns:
            df[f'{col}_original'] = df[col].copy()
            # Remover vírgulas e pontos como separadores de milhar
            df[col] = df[col].astype(str).str.replace('.', '', regex=False)
            df[col] = df[col].str.replace(',', '.', regex=False)
            df[col] = df[col].str.strip()

    # 5. VALIDAÇÃO DE REGRAS (LINHA A LINHA)
    
    print(f"Iniciando validação de {len(df)} itens de estoque...")
    
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
        if row['TIPO'] != row['TIPO_original']:
            adicionar_erro('TIPO', row['TIPO_original'], row['TIPO'], 
                          "Tipo de estoque padronizado.", True)
        
        if row['ATIVO'] != row['ATIVO_original']:
            adicionar_erro('ATIVO', row['ATIVO_original'], row['ATIVO'], 
                          "Status padronizado para 'S' ou 'N'.", True)
        
        if row['CODPROD'] != row['CODPROD_original']:
            adicionar_erro('CODPROD', row['CODPROD_original'], row['CODPROD'], 
                          "Espaços extras removidos do código.", True)
        
        # Correções numéricas
        for col in ['ESTOQUE', 'ESTMIN', 'ESTMAX']:
            col_orig = f'{col}_original'
            if col_orig in row and row[col] != row[col_orig]:
                adicionar_erro(col, row[col_orig], row[col], 
                              "Formato numérico corrigido.", True)
        
        # --- Validação de Cross-Reference (CODPROD) ---
        if not row['CODPROD']:
            adicionar_erro('CODPROD', row['CODPROD_original'], "", 
                          "Código do Produto está vazio.", False)
        elif row['CODPROD'] not in produtos_validos:
            adicionar_erro('CODPROD', row['CODPROD_original'], "", 
                          "Código do Produto não encontrado no Arquivo Mestre de Produtos.", False)
        
        # --- Validação de Domínio TIPO ---
        if not row['TIPO']:
            adicionar_erro('TIPO', row['TIPO_original'], "", 
                          "Campo obrigatório (Tipo) está vazio.", False)
        elif row['TIPO'] not in DOMINIO_TIPO_ESTOQUE:
            adicionar_erro('TIPO', row['TIPO_original'], "", 
                          "Valor inválido. Esperado 'P' (Próprio) ou 'T' (Terceiro).", False)

        # --- Validação de ATIVO ---
        if not row['ATIVO']:
            adicionar_erro('ATIVO', row['ATIVO_original'], "", 
                          "Campo obrigatório (Ativo) está vazio.", False)
        elif row['ATIVO'] not in DOMINIO_ATIVO:
            adicionar_erro('ATIVO', row['ATIVO_original'], "", 
                          "Valor inválido. Esperado 'S' ou 'N'.", False)
        
        # --- Validação Numérica ---
        for col in ['ESTOQUE', 'ESTMIN', 'ESTMAX']:
            valor = row[col]
            if not valor:
                adicionar_erro(col, row.get(f'{col}_original', ''), "", 
                              f"{col} está vazio.", False)
            elif pd.isna(pd.to_numeric(valor, errors='coerce')):
                adicionar_erro(col, row.get(f'{col}_original', valor), "", 
                              f"{col} não é um número válido.", False)
            else:
                # Validar se é positivo ou zero
                num_valor = float(valor)
                if num_valor < 0:
                    adicionar_erro(col, row.get(f'{col}_original', valor), "", 
                                  f"{col} não pode ser negativo.", False)
        
        # Validação lógica: ESTMIN <= ESTMAX
        try:
            estmin = float(row['ESTMIN']) if row['ESTMIN'] and not pd.isna(pd.to_numeric(row['ESTMIN'], errors='coerce')) else None
            estmax = float(row['ESTMAX']) if row['ESTMAX'] and not pd.isna(pd.to_numeric(row['ESTMAX'], errors='coerce')) else None
            
            if estmin is not None and estmax is not None and estmin > estmax:
                adicionar_erro('ESTMIN', row.get('ESTMIN_original', row['ESTMIN']), "", 
                              f"Estoque Mínimo ({estmin}) não pode ser maior que Estoque Máximo ({estmax}).", False)
        except:
            pass

    print(f"Validação concluída. Total de erros encontrados: {len(erros_encontrados)}")
    
    # Remover colunas auxiliares
    colunas_remover = [col for col in df.columns if col.endswith('_original')]
    df_corrigido = df.drop(columns=colunas_remover, errors='ignore')
    
    # Retorna erros e DataFrame corrigido
    if erros_encontrados:
        df_erros = pd.DataFrame(erros_encontrados)
        return df_erros.drop_duplicates().to_dict('records'), df_corrigido
    
    return [], df_corrigido
import pandas as pd
import re
import sys
from datetime import datetime

# --- Funções Auxiliares (SÓ LIMPEZA ESSENCIAL) ---
DOMINIO_TIPO_ESTOQUE = {'P', 'T'}

def carregar_mestre(caminho_arquivo, nome_coluna):
    """Carrega um arquivo mestre e retorna um SET com os valores válidos."""
    try:
        df_mestre = pd.read_csv(caminho_arquivo, sep=';', encoding='utf-8', encoding_errors='ignore', dtype=str, engine='python')
        if len(df_mestre.columns) < 2: df_mestre = pd.read_csv(caminho_arquivo, sep=',', encoding='utf-8', encoding_errors='ignore', dtype=str, engine='python')
    except Exception:
        return None 
    if nome_coluna not in df_mestre.columns: return None
    return set(df_mestre[nome_coluna].dropna().unique())

# --- Função Principal de Validação ---

def validar_estoque(caminho_arquivo):
    erros_encontrados = []
    
    # 1. CARREGAR ARQUIVO MESTRE DE PRODUTOS
    produtos_validos = carregar_mestre("mestre_produtos.csv", 'CODPROD')
    if produtos_validos is None:
        return [{"linha": 0, "coluna": "Mestre", "valor_encontrado": "mestre_produtos.csv", "erro": "Arquivo Mestre de Produtos não encontrado ou incompleto (Verifique o cabeçalho 'CODPROD')."}], None

    # 2. CARREGAR OS DADOS DE ESTOQUE (Bloco de leitura robusto)
    df = None
    tentativas = [(';', 'latin-1'), (',', 'latin-1')] 
    try:
        df_temp = pd.read_csv(caminho_arquivo, sep=';', encoding='utf-8', encoding_errors='ignore', dtype=str, engine='python')
        if len(df_temp.columns) < 2: df = pd.read_csv(caminho_arquivo, sep=',', encoding='utf-8', encoding_errors='ignore', dtype=str, engine='python')
        else: df = df_temp
    except Exception as e:
        return [{"linha": 0, "coluna": "Arquivo", "valor_encontrado": "N/A", "erro": f"ERRO FATAL DE DADOS. O arquivo pode estar corrompido. Detalhe: {str(e)}"}], None
    if df is None:
        return [{"linha": 0, "coluna": "Arquivo", "valor_encontrado": "N/A", "erro": "ERRO FATAL DE LEITURA. Não foi possível ler o arquivo com vírgula ou ponto e vírgula."}], None
    df = df.fillna('')


    # 3. PRÉ-PROCESSAMENTO (SÓ PADRONIZAÇÃO DE CAIXA)
    
    colunas_criticas = ['CODPROD', 'ESTOQUE', 'ESTMAX', 'ESTMIN', 'ATIVO', 'TIPO']
    for col in colunas_criticas:
        if col not in df.columns:
            return [{"linha": 0, "coluna": col, "valor_encontrado": "-", "erro": f"Coluna obrigatória '{col}' não encontrada no cabeçalho do arquivo de estoque."}], None
            
    df['TIPO_limpo'] = df['TIPO'].astype(str).str.upper().str.strip()
    df['ATIVO_limpo'] = df['ATIVO'].astype(str).str.upper().str.strip() # Adicionado para garantir que o código não quebre

    # 4. VALIDAÇÃO DE REGRAS (LINHA A LINHA)
    
    for index, row in df.iterrows():
        linha_num = index + 2 
        
        def adicionar_erro(coluna, valor, mensagem):
            erros_encontrados.append({"linha": linha_num, "coluna": coluna, "valor_encontrado": str(valor), "erro": mensagem})

        # --- Validação de Cross-Reference (CODPROD) ---
        if row['CODPROD'] not in produtos_validos:
            adicionar_erro('CODPROD', row['CODPROD'], "Código do Produto não encontrado no Arquivo Mestre de Produtos.")
            
        # --- Validação de Domínio (Sem limpeza automática) ---
        if row['TIPO_limpo'] not in DOMINIO_TIPO_ESTOQUE:
             adicionar_erro('TIPO', row['TIPO'], "Valor inválido. Esperado 'P' (Próprio) ou 'T' (Terceiro).")

        # --- Validação de ATIVO (Sem limpeza automática) ---
        if row['ATIVO_limpo'] not in ('S', 'N'):
            adicionar_erro('ATIVO', row['ATIVO'], "Valor inválido. Esperado 'S' ou 'N'.")
        
        # --- Validação Numérica (Exemplo) ---
        # Se for um valor que não é float, o Pandas deve ter colocado NaN
        if pd.isna(pd.to_numeric(row['ESTOQUE'], errors='coerce')):
            adicionar_erro('ESTOQUE', row['ESTOQUE'], "Estoque não é um número válido.")
        
        # ... (O resto da validação continua aqui) ...

    # Retorna o DF com as correções e a lista de erros
    if erros_encontrados:
        df_erros = pd.DataFrame(erros_encontrados)
        return df_erros.drop_duplicates().to_dict('records'), df
    
    # Se não houver erros, retorna lista vazia e o DF
    return [], df
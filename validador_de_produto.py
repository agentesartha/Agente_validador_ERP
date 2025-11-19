import pandas as pd
import re
import sys

# --- Listas de Domínio (Valores Permitidos) ---
DOMINIO_UNIDADE = {'CM', 'M', 'MM'}
DOMINIO_USOPROD = {'1', '2', '4', 'B', 'C', 'D', 'E', 'F', 'I', 'M', 'O', 'P', 'R', 'T', 'V'}
DOMINIO_SIM_NAO = {'S', 'N'}

# --- Mapeamento de Colunas ---
MAPEAMENTO_COLUNAS = {
    # Coluna no script: [Lista de nomes aceitáveis no CSV]
    'UNIDADE': ['UNIDADE', 'UND', 'UNID_MEDIDA', 'CODVOL'], 
}

def mapear_colunas(df, mapeamento):
    """Renomeia colunas do DF para os nomes oficiais do script."""
    colunas_encontradas = {}
    
    # Busca por nomes alternativos e prepara o dicionário de renomeação
    for nome_oficial, alternativas in mapeamento.items():
        for alt in alternativas:
            if alt in df.columns:
                colunas_encontradas[alt] = nome_oficial
                break 
    
    # Renomeia as colunas no DataFrame
    df.rename(columns=colunas_encontradas, inplace=True)
    return df


# --- Função Principal de Validação ---

def validar_produtos(caminho_arquivo):
    """
    Função principal para carregar e validar a planilha de produtos (TGFPRO).
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
            # engine='python' é mais tolerante a erros de formatação
            df_temp = pd.read_csv(caminho_arquivo, sep=sep, encoding=enc, dtype=str, engine='python')
            
            if len(df_temp.columns) > 1:
                df = df_temp
                break 
        except Exception as e:
            erro_leitura = str(e)
            continue 

    if df is None:
        return [{
            "linha": 0, 
            "coluna": "Arquivo", 
            "valor_encontrado": "N/A", 
            "erro": f"Erro crítico de leitura. Detalhe: {erro_leitura}"
        }]
    
    df = df.fillna('')

    # ----------------------------------------------------
    # 2. PRÉ-PROCESSAMENTO E VERIFICAÇÃO DE COLUNAS
    # ----------------------------------------------------
    
    # Mapeia colunas antes de começar a limpeza para garantir que 'UNIDADE' exista
    df = mapear_colunas(df, MAPEAMENTO_COLUNAS)

    # Verificação de colunas obrigatórias
    colunas_criticas = ['AD_IDEXTERNO', 'DESCRPROD', 'NCM', 'MARCA', 'REFERENCIA', 'UNIDADE']
    for col in colunas_criticas:
        if col not in df.columns:
            alternativas = ', '.join(MAPEAMENTO_COLUNAS.get(col, [col]))
            return [{"linha": 0, "coluna": col, "valor_encontrado": "-", "erro": f"Coluna obrigatória '{col}' não encontrada. (Alternativas: {alternativas})."}]
    
    # Limpeza
    df['UNIDADE_limpo'] = df['UNIDADE'].str.upper().str.strip()
    df['USOPROD_limpo'] = df['USOPROD'].str.upper().str.strip()
    df['TEMIPICOMPRA_limpo'] = df['TEMIPICOMPRA'].str.upper().str.strip()
    df['TEMIPIVENDA_limpo'] = df['TEMIPIVENDA'].str.upper().str.strip()
    df['USACODBARRASQTD_limpo'] = df['USACODBARRASQTD'].str.upper().str.strip()
    df['NCM_limpo'] = df['NCM'].str.replace(r'[./-]', '', regex=True).str.strip()


    # ----------------------------------------------------
    # 3. VALIDAÇÃO DE REGRAS (LINHA A LINHA)
    # ----------------------------------------------------
    print(f"Iniciando validação de {len(df)} produtos...")

    for index, row in df.iterrows():
        linha_num = index + 2 
        
        def adicionar_erro(coluna, valor, mensagem):
            erros_encontrados.append({
                "linha": linha_num,
                "coluna": coluna,
                "valor_encontrado": str(valor),
                "erro": mensagem
            })

        # --- Validações de Obrigatoriedade e Tamanho ---
        
        # [Obrigatório/Tamanho] AD_IDEXTERNO
        if not row['AD_IDEXTERNO']:
            adicionar_erro('AD_IDEXTERNO', row['AD_IDEXTERNO'], "Campo obrigatório está vazio.")
        elif len(row['AD_IDEXTERNO']) > 256:
            adicionar_erro('AD_IDEXTERNO', row['AD_IDEXTERNO'], "Tamanho máximo (256) excedido.")

        # [Obrigatório/Tamanho] DESCRPROD
        if not row['DESCRPROD']:
            adicionar_erro('DESCRPROD', row['DESCRPROD'], "Campo obrigatório (Descrição) está vazio.")
        elif len(row['DESCRPROD']) > 100:
            adicionar_erro('DESCRPROD', row['DESCRPROD'], "Tamanho máximo (100) excedido.")

        # [Obrigatório/Tamanho] MARCA
        if not row['MARCA']:
            adicionar_erro('MARCA', row['MARCA'], "Campo obrigatório está vazio.")
        elif len(row['MARCA']) > 20:
            adicionar_erro('MARCA', row['MARCA'], "Tamanho máximo (20) excedido.")
            
        # [Obrigatório/Tamanho] REFERENCIA
        if not row['REFERENCIA']:
            adicionar_erro('REFERENCIA', row['REFERENCIA'], "Campo obrigatório está vazio.")
        elif len(row['REFERENCIA']) > 15:
            adicionar_erro('REFERENCIA', row['REFERENCIA'], "Tamanho máximo (15) excedido.")
            
        # [Obrigatório/Tamanho] NCM
        ncm = row['NCM_limpo']
        if not ncm:
            adicionar_erro('NCM', row['NCM'], "Campo obrigatório está vazio.")
        elif not ncm.isdigit():
            adicionar_erro('NCM', row['NCM'], "NCM deve conter apenas números.")
        elif len(ncm) > 10:
            adicionar_erro('NCM', row['NCM'], "Tamanho máximo (10) excedido.")


        # --- Validação de Domínio ---

        # [Domínio] UNIDADE
        unidade = row['UNIDADE_limpo']
        if unidade and unidade not in DOMINIO_UNIDADE:
            adicionar_erro('UNIDADE', row['UNIDADE'], f"Valor inválido. Permitidos: {', '.join(DOMINIO_UNIDADE)}.")

        # [Domínio] USOPROD
        usoprod = row['USOPROD_limpo']
        if usoprod and usoprod not in DOMINIO_USOPROD:
            adicionar_erro('USOPROD', row['USOPROD'], f"Valor inválido. Não está na lista de 'Usado como'.")

        # [Domínio] TEMIPICOMPRA
        temipicompra = row['TEMIPICOMPRA_limpo']
        if temipicompra and temipicompra not in DOMINIO_SIM_NAO:
            adicionar_erro('TEMIPICOMPRA', row['TEMIPICOMPRA'], "Valor inválido. Permitido apenas 'S' ou 'N'.")

        # [Domínio] TEMIPIVENDA
        temipivenda = row['TEMIPIVENDA_limpo']
        if temipivenda and temipivenda not in DOMINIO_SIM_NAO:
            adicionar_erro('TEMIPIVENDA', row['TEMIPIVENDA'], "Valor inválido. Permitido apenas 'S' ou 'N'.")

        # [Domínio] USACODBARRASQTD
        usacodbq = row['USACODBARRASQTD_limpo']
        if usacodbq and usacodbq not in DOMINIO_SIM_NAO:
            adicionar_erro('USACODBARRASQTD', row['USACODBARRASQTD'], "Valor inválido. Permitido apenas 'S' ou 'N'.")

    
    print(f"Validação concluída. Total de erros encontrados: {len(erros_encontrados)}")
    
    # Retorna a lista de erros (removendo duplicatas exatas se houver)
    if erros_encontrados:
        df_erros = pd.DataFrame(erros_encontrados)
        return df_erros.drop_duplicates().to_dict('records')
    
    return []
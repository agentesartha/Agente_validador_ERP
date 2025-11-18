import pandas as pd
import re
import sys
from datetime import datetime

# --- NOMES DOS ARQUIVOS MESTRE ---
# O usuário DEVE fornecer um arquivo com este nome
ARQUIVO_MESTRE_PRODUTOS = "mestre_produtos.csv"

# --- Listas de Domínio (Valores Permitidos) ---
DOMINIO_SIM_NAO = {'S', 'N'}
DOMINIO_TIPO_ESTOQUE = {'P', 'T'}


def carregar_mestre(caminho_arquivo, nome_coluna):
    """
    Função helper para carregar um arquivo mestre (CSV)
    e retornar um SET com os valores de uma coluna específica.
    """
    try:
        # Tenta ler com latin-1, comum no Brasil
        df_mestre = pd.read_csv(caminho_arquivo, sep=';', dtype=str, encoding='latin-1')
    except Exception:
        try:
            # Tenta ler com utf-8 como alternativa
            df_mestre = pd.read_csv(caminho_arquivo, sep=';', dtype=str, encoding='utf-8')
        except Exception as e:
            print(f"Erro fatal: Não foi possível ler o arquivo mestre '{caminho_arquivo}'. Erro: {e}")
            return None # Retorna None em caso de falha

    if nome_coluna not in df_mestre.columns:
        print(f"Erro fatal: O arquivo mestre '{caminho_arquivo}' não contém a coluna necessária '{nome_coluna}'.")
        return None
    
    # Retorna um SET para performance de busca (O(1))
    return set(df_mestre[nome_coluna].dropna().unique())


def validar_estoque(caminho_arquivo):
    """
    Função principal para carregar e validar a planilha de estoque (TGFEST).
    """
    
    erros_encontrados = []

    # ----------------------------------------------------
    # 1. CARREGAR ARQUIVO MESTRE DE PRODUTOS
    # ----------------------------------------------------
    print(f"Carregando arquivo mestre de produtos de '{ARQUIVO_MESTRE_PRODUTOS}'...")
    produtos_validos = carregar_mestre(ARQUIVO_MESTRE_PRODUTOS, 'CODPROD')
    if produtos_validos is None:
        return None # Falha crítica

    print(f"Mestre de produtos carregado. {len(produtos_validos)} produtos válidos.")

    # ----------------------------------------------------
    # 2. CARREGAR OS DADOS DE ESTOQUE
    # ----------------------------------------------------
    try:
        df = pd.read_csv(caminho_arquivo, sep=';', dtype=str, encoding='latin-1')
        df = df.fillna('')
    except FileNotFoundError:
        print(f"Erro fatal: Arquivo não encontrado em '{caminho_arquivo}'")
        return None
    except Exception as e:
        print(f"Erro ao ler o CSV: {e}")
        return None

    # ----------------------------------------------------
    # 3. CORREÇÕES AUTOMÁTICAS E "LIMPEZA" (PREPARAÇÃO)
    # ----------------------------------------------------
    df['ATIVO_limpo'] = df['ATIVO'].str.upper().str.strip()
    df['TIPO_limpo'] = df['TIPO'].str.upper().str.strip()

    # ----------------------------------------------------
    # 4. VALIDAÇÃO DE REGRAS (LINHA A LINHA)
    # ----------------------------------------------------
    print(f"Iniciando validação de {len(df)} linhas de estoque...")

    for index, row in df.iterrows():
        linha_num = index + 2 
        
        def adicionar_erro(coluna, valor, mensagem):
            erros_encontrados.append({
                "linha": linha_num,
                "coluna": coluna,
                "valor_encontrado": str(valor),
                "erro": mensagem
            })

        # --- Regras do "Leia-me" (TGFEST) ---
        
        # [Obrigatório] AD_IDEXTERNO
        if not row['AD_IDEXTERNO']:
            adicionar_erro('AD_IDEXTERNO', row['AD_IDEXTERNO'], "Campo obrigatório está vazio.")
        
        # [Obrigatório] CODEMP
        if not row['CODEMP']:
            adicionar_erro('CODEMP', row['CODEMP'], "Campo obrigatório (Empresa) está vazio.")
        elif not row['CODEMP'].isdigit():
             adicionar_erro('CODEMP', row['CODEMP'], "Deve ser um número.")

        # [Obrigatório] CODLOCAL
        if not row['CODLOCAL']:
            adicionar_erro('CODLOCAL', row['CODLOCAL'], "Campo obrigatório (Local) está vazio.")
        elif not row['CODLOCAL'].isdigit():
             adicionar_erro('CODLOCAL', row['CODLOCAL'], "Deve ser um número.")

        # [Obrigatório] CODPARC (Ainda validamos se é obrigatório e numérico, como no "leia-me")
        if not row['CODPARC']:
            adicionar_erro('CODPARC', row['CODPARC'], "Campo obrigatório (Parceiro) está vazio.")
        elif not row['CODPARC'].isdigit():
             adicionar_erro('CODPARC', row['CODPARC'], "Deve ser um número.")

        # [Domínio] ATIVO
        ativo = row['ATIVO_limpo']
        if ativo and ativo not in DOMINIO_SIM_NAO:
            adicionar_erro('ATIVO', row['ATIVO'], "Valor inválido. Permitido apenas 'S' ou 'N'.")

        # [Domínio] TIPO
        tipo = row['TIPO_limpo']
        if tipo and tipo not in DOMINIO_TIPO_ESTOQUE:
            adicionar_erro('TIPO', row['TIPO'], "Valor inválido. Permitido apenas 'P' ou 'T'.")

        # --- Validação de Números (Float) ---
        for col_num in ['ESTMAX', 'ESTMIN', 'ESTOQUE']:
            valor_num = row[col_num].replace(',', '.') # Aceita vírgula ou ponto
            if not valor_num:
                adicionar_erro(col_num, row[col_num], "Campo obrigatório está vazio.")
            else:
                try:
                    float(valor_num) # Tenta converter para número
                except ValueError:
                    adicionar_erro(col_num, row[col_num], "Valor não é um número válido (ex: 10.50).")
        
        # --- Validação de Datas ---
        dt_fabricacao = None
        if row['DTFABRICACAO']:
            try:
                dt_fabricacao = datetime.strptime(row['DTFABRICACAO'], '%d/%m/%Y')
            except ValueError:
                 adicionar_erro('DTFABRICACAO', row['DTFABRICACAO'], "Formato de data inválido. Use DD/MM/AAAA.")
        
        if row['DTVAL']:
            try:
                dt_validade = datetime.strptime(row['DTVAL'], '%d/%m/%Y')
                # [Condicional] Validade vs Fabricação
                if dt_fabricacao and dt_validade < dt_fabricacao:
                    adicionar_erro('DTVAL', row['DTVAL'], "Data de Validade não pode ser ANTERIOR à Data de Fabricação.")
            except ValueError:
                 adicionar_erro('DTVAL', row['DTVAL'], "Formato de data inválido. Use DD/MM/AAAA.")

        # --- VALIDAÇÃO CRUZADA (A "INTELIGÊNCIA") ---
        
        # [Obrigatório e Mestre] CODPROD
        codprod = row['CODPROD']
        if not codprod:
            adicionar_erro('CODPROD', codprod, "Campo obrigatório (Cód. Prod.) está vazio.")
        elif not codprod.isdigit():
             adicionar_erro('CODPROD', codprod, "Deve ser um número.")
        elif codprod not in produtos_validos:
            adicionar_erro('CODPROD', codprod, f"Produto não encontrado no arquivo mestre '{ARQUIVO_MESTRE_PRODUTOS}'.")


    print(f"Validação concluída. Total de erros encontrados: {len(erros_encontrados)}")
    return erros_encontrados

# --- Bloco de Execução Principal ---

if __name__ == "__main__":
    
    ARQUIVO_DE_ENTRADA = "estoque.csv" 
    
    # 1. Executa o validador
    erros = validar_estoque(ARQUIVO_DE_ENTRADA)
    
    # 2. Exibe o relatório de erros
    if erros is None:
        print("\n❌ A validação falhou e não pôde ser concluída (Verifique o arquivo Mestre de Produtos).")
    elif not erros:
        print(f"\n✅ Nenhum erro encontrado. A planilha '{ARQUIVO_DE_ENTRADA}' está pronta para importação!")
    else:
        print("\n❌ Erros de validação encontrados:")
        df_erros = pd.DataFrame(erros)
        
        for linha, grupo in df_erros.groupby('linha'):
            print(f"\n--- Erros na Linha {linha} ---")
            for _, erro in grupo.iterrows():
                print(f"  - Coluna: '{erro['coluna']}'")
                print(f"    Valor:  '{erro['valor_encontrado']}'")
                print(f"    Erro:   {erro['erro']}")